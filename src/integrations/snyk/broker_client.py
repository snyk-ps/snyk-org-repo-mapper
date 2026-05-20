"""Snyk Universal Broker REST client (read + org integration POST).

JSON:API list responses use top-level ``data`` (array of resources) and ``links.next``
for pagination. Each resource has ``id`` and ``attributes``.

- **Deployment** resources: ``id`` is the deployment UUID.
- **Connection** resources: SCM type is usually ``attributes.integrationType`` (or
  ``integration_type`` / ``type``); JSON:API resource ``type`` is often ``connection``.
  Only ``bitbucket-server`` is used for org allocation.
- **Integration** resources on a connection: ``attributes.org_id`` / ``org_name`` (or
  ``relationships.organization.data.id``) identify linked Snyk orgs.

POST org integration: empty JSON body ``{}`` with ``Content-Type: application/vnd.api+json``.
HTTP 409 indicates the org is already linked (treated as skip during apply).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from http.client import RemoteDisconnected
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config.snyk_settings import BrokerSettings
from integrations.http_retry import run_with_retries
from integrations.snyk.client import _is_retriable_request_failure, _resolve_next_url


class BrokerIntegrationConflictError(Exception):
    """Org is already integrated on this broker connection (HTTP 409)."""


@dataclass(frozen=True)
class BrokerConnection:
    """A bitbucket-server connection under a deployment."""

    connection_id: str
    deployment_id: str
    connection_type: str
    display_name: str | None


@dataclass(frozen=True)
class BrokerConnectionIntegration:
    """An org linked to a broker connection."""

    org_id: str | None
    org_name: str | None
    integration_id: str | None


_JSONAPI_RESOURCE_KIND_SLUGS = frozenset(
    {"connection", "broker-connection", "integration", "deployment"}
)

_ATTR_SCM_TYPE_KEYS = (
    "integrationType",
    "integration_type",
    "type",
    "scmType",
    "scm_type",
    "connectionType",
    "connection_type",
    "slug",
)


def _scm_type_slug_from_string(raw: str) -> str | None:
    slug = raw.strip().lower().replace("_", "-")
    if slug in _JSONAPI_RESOURCE_KIND_SLUGS:
        return None
    return slug


def _connection_type_slug(item: dict[str, Any]) -> str | None:
    attrs = item.get("attributes")
    if isinstance(attrs, dict):
        for key in _ATTR_SCM_TYPE_KEYS:
            raw = attrs.get(key)
            if isinstance(raw, str) and raw.strip():
                slug = _scm_type_slug_from_string(raw)
                if slug is not None:
                    return slug
    for key in ("integrationType", "integration_type"):
        raw = item.get(key)
        if isinstance(raw, str) and raw.strip():
            slug = _scm_type_slug_from_string(raw)
            if slug is not None:
                return slug
    raw_type = item.get("type")
    if isinstance(raw_type, str) and raw_type.strip():
        return _scm_type_slug_from_string(raw_type)
    return None


def _display_name_from_item(item: dict[str, Any]) -> str | None:
    attrs = item.get("attributes")
    if isinstance(attrs, dict):
        for key in ("name", "display_name", "displayName"):
            raw = attrs.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
    return None


def _org_refs_from_integration_item(item: dict[str, Any]) -> tuple[str | None, str | None]:
    oid: str | None = None
    name: str | None = None
    attrs = item.get("attributes")
    if isinstance(attrs, dict):
        for key in ("org_id", "organization_id", "organizationId"):
            raw = attrs.get(key)
            if isinstance(raw, str) and raw.strip():
                oid = raw.strip()
        for key in ("org_name", "organization_name", "organizationName", "name"):
            raw = attrs.get(key)
            if isinstance(raw, str) and raw.strip():
                name = raw.strip()
    rel = item.get("relationships")
    if isinstance(rel, dict):
        org_rel = rel.get("organization") or rel.get("org")
        if isinstance(org_rel, dict):
            data = org_rel.get("data")
            if isinstance(data, dict):
                rid = data.get("id")
                if isinstance(rid, str) and rid.strip():
                    oid = oid or rid.strip()
    return oid, name


class BrokerClient:
    """Universal Broker API client using ``urllib``."""

    def __init__(self, settings: BrokerSettings, *, timeout_s: float = 60.0) -> None:
        self._settings = settings
        self._timeout = timeout_s

    def _version_query(self) -> str:
        return urlencode({"version": self._settings.api_version})

    def _install_base(self) -> str:
        s = self._settings
        return (
            f"{s.rest_root}/tenants/{s.tenant_id}/brokers/installs/{s.install_id}"
        )

    def _request_json(
        self,
        url: str,
        *,
        method: str = "GET",
        body: bytes | None = None,
    ) -> Any:
        headers = {
            "Authorization": f"token {self._settings.token}",
            "Accept": "application/vnd.api+json",
        }
        if method != "GET":
            headers["Content-Type"] = "application/vnd.api+json"
        req = Request(url, data=body, headers=headers, method=method)

        def inner() -> Any:
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    raw = resp.read()
            except HTTPError as exc:
                if exc.code == 409 and method == "POST":
                    raise BrokerIntegrationConflictError(
                        f"Integration already exists for {url}"
                    ) from exc
                if not _is_retriable_request_failure(exc):
                    detail = exc.read().decode("utf-8", errors="replace")
                    msg = f"Snyk Broker API HTTP {exc.code} for {url}: {detail[:500]}"
                    raise RuntimeError(msg) from exc
                raise
            if not raw:
                return {}
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                msg = f"Invalid JSON from Snyk Broker API: {exc}"
                raise RuntimeError(msg) from exc

        return run_with_retries(
            inner,
            max_attempts=self._settings.http_max_attempts,
            base_backoff_s=self._settings.http_backoff_seconds,
            retry=_is_retriable_request_failure,
        )

    def _iter_paginated_data(self, first_url: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        url: str | None = first_url
        seen: set[str] = set()
        while url:
            if url in seen:
                msg = "Snyk Broker API pagination loop detected"
                raise RuntimeError(msg)
            seen.add(url)
            payload = self._request_json(url)
            if not isinstance(payload, dict):
                msg = "Snyk Broker API returned non-object JSON"
                raise RuntimeError(msg)
            data = payload.get("data")
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        items.append(item)
            links = payload.get("links")
            next_link = None
            if isinstance(links, dict):
                raw_next = links.get("next")
                if isinstance(raw_next, str):
                    next_link = raw_next
            url = _resolve_next_url(self._settings.rest_root, next_link)
        return items

    def list_bitbucket_server_connections(self) -> list[BrokerConnection]:
        """Return all ``bitbucket-server`` connections for the configured install."""
        sep = "&" if "?" in self._install_base() else "?"
        dep_url = f"{self._install_base()}/deployments?{self._version_query()}"
        deployments = self._iter_paginated_data(dep_url)
        out: list[BrokerConnection] = []
        total_seen = 0
        sample_attr_keys: list[str] | None = None
        for dep in deployments:
            dep_id = dep.get("id")
            if not isinstance(dep_id, str) or not dep_id.strip():
                continue
            dep_id = dep_id.strip()
            conn_base = f"{self._install_base()}/deployments/{dep_id}/connections"
            sep_c = "&" if "?" in conn_base else "?"
            conn_url = f"{conn_base}{sep_c}{self._version_query()}"
            for conn in self._iter_paginated_data(conn_url):
                cid = conn.get("id")
                if not isinstance(cid, str) or not cid.strip():
                    continue
                total_seen += 1
                if sample_attr_keys is None:
                    attrs = conn.get("attributes")
                    if isinstance(attrs, dict):
                        sample_attr_keys = sorted(str(k) for k in attrs)
                ctype = _connection_type_slug(conn)
                if ctype != "bitbucket-server":
                    continue
                out.append(
                    BrokerConnection(
                        connection_id=cid.strip(),
                        deployment_id=dep_id,
                        connection_type=ctype,
                        display_name=_display_name_from_item(conn),
                    )
                )
        if not out and total_seen > 0:
            keys_hint = (
                ", ".join(sample_attr_keys) if sample_attr_keys else "(no attributes object)"
            )
            msg = (
                f"Found {total_seen} broker connection(s) but none with SCM type "
                f"bitbucket-server (check attributes.integrationType or "
                f"integration_type). Sample attribute keys: {keys_hint}"
            )
            raise ValueError(msg)
        return out

    def list_connection_integrations(
        self, connection_id: str
    ) -> list[BrokerConnectionIntegration]:
        """List org integrations already on a broker connection."""
        cid = connection_id.strip()
        base = (
            f"{self._settings.rest_root}/tenants/{self._settings.tenant_id}"
            f"/brokers/connections/{cid}/integrations"
        )
        sep = "&" if "?" in base else "?"
        url = f"{base}{sep}{self._version_query()}"
        out: list[BrokerConnectionIntegration] = []
        for item in self._iter_paginated_data(url):
            oid, oname = _org_refs_from_integration_item(item)
            iid = item.get("id")
            integration_id = (
                iid.strip() if isinstance(iid, str) and iid.strip() else None
            )
            out.append(
                BrokerConnectionIntegration(
                    org_id=oid,
                    org_name=oname,
                    integration_id=integration_id,
                )
            )
        return out

    def create_org_integration(self, connection_id: str, org_id: str) -> dict[str, Any]:
        """POST org–connection integration link. Body: empty JSON object."""
        cid = connection_id.strip()
        oid = org_id.strip()
        base = (
            f"{self._settings.rest_root}/tenants/{self._settings.tenant_id}"
            f"/brokers/connections/{cid}/orgs/{oid}/integration"
        )
        sep = "&" if "?" in base else "?"
        url = f"{base}{sep}{self._version_query()}"
        body = b"{}"
        parsed = self._request_json(url, method="POST", body=body)
        if isinstance(parsed, dict):
            return parsed
        return {}
