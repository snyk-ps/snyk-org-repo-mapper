"""Snyk API client: REST JSON:API for group orgs; v1 or REST for integrations (urllib)."""

from __future__ import annotations

import json
import logging
import re
from http.client import RemoteDisconnected
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from config.snyk_settings import SnykSettings
from integrations.http_retry import run_with_retries

logging.basicConfig(level=logging.DEBUG)
_LOG = logging.getLogger(__name__)

def _is_retriable_request_failure(exc: BaseException) -> bool:
    if isinstance(exc, RemoteDisconnected):
        return True
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, URLError):
        return True
    if isinstance(exc, HTTPError):
        return exc.code in (429, 500, 502, 503, 504)
    return False


def _resolve_next_url(rest_root: str, next_link: str | None) -> str | None:
    if not next_link or not isinstance(next_link, str):
        return None
    link = next_link.strip()
    if not link:
        return None
    if link.startswith("http://") or link.startswith("https://"):
        return link
    root = rest_root.rstrip("/")
    if root.endswith("/rest"):
        origin = root[: -len("/rest")]
    else:
        parsed = urlparse(root)
        origin = f"{parsed.scheme}://{parsed.netloc}"
    return urljoin(origin + "/", link.lstrip("/"))


_V1_INTEGRATION_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_V1_INTEGRATIONS_MAP_BLOCKLIST = frozenset(
    {"integrations", "data", "results", "message", "code", "error", "errors", "status", "detail"}
)


def _v1_type_id_map_to_integration_list(parsed: dict[str, Any]) -> list[dict[str, Any]] | None:
    """If ``parsed`` is integration-type → UUID string, return list of ``{id, type}`` dicts."""
    if not parsed:
        return None
    if set(parsed) & _V1_INTEGRATIONS_MAP_BLOCKLIST:
        return None
    out: list[dict[str, Any]] = []
    for slug, raw_id in parsed.items():
        if not isinstance(slug, str) or not slug.strip():
            return None
        if not isinstance(raw_id, str) or not raw_id.strip():
            return None
        iid = raw_id.strip()
        if not _V1_INTEGRATION_UUID.match(iid):
            return None
        out.append({"id": iid, "type": slug})
    return out


def normalize_v1_projects_payload(parsed: Any) -> list[dict[str, Any]]:
    """Turn v1 GET /org/.../projects JSON into a list of project objects."""
    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]
    if isinstance(parsed, dict):
        for key in ("projects", "data", "results"):
            raw = parsed.get(key)
            if isinstance(raw, list):
                return [x for x in raw if isinstance(x, dict)]
    msg = "Unexpected v1 projects response shape"
    raise RuntimeError(msg)


def normalize_v1_integrations_payload(parsed: Any) -> list[dict[str, Any]]:
    """Turn v1 GET /org/.../integrations JSON into a list of integration objects.

    Accepts a top-level array, ``{"integrations"|"data"|"results": [...]}``, or a
    flat map ``{ "<integration-slug>": "<uuid>", ... }`` (slug may contain hyphens,
    e.g. ``github-cloud-app``).
    """
    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]
    if isinstance(parsed, dict):
        for key in ("integrations", "data", "results"):
            raw = parsed.get(key)
            if isinstance(raw, list):
                return [x for x in raw if isinstance(x, dict)]
        from_map = _v1_type_id_map_to_integration_list(parsed)
        if from_map is not None:
            return from_map
    msg = "Unexpected v1 integrations response shape"
    raise RuntimeError(msg)


def _v1_integrations_response_debug_summary(parsed: Any) -> str:
    """Short description of raw JSON for debug logs (no token or full bodies)."""
    if isinstance(parsed, list):
        return f"list(len={len(parsed)})"
    if isinstance(parsed, dict):
        keys = sorted(parsed.keys())
        return f"dict(keys={keys!r})"
    return type(parsed).__name__


class SnykRestClient:
    """Snyk API client using ``urllib``."""

    def __init__(self, settings: SnykSettings, *, timeout_s: float = 60.0) -> None:
        self._settings = settings
        self._timeout = timeout_s

    @property
    def group_id(self) -> str:
        return self._settings.group_id

    def _request_rest_json_object(self, url: str) -> dict[str, Any]:
        req = Request(
            url,
            headers={
                "Authorization": f"token {self._settings.token}",
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
            },
            method="GET",
        )

        def inner() -> dict[str, Any]:
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    body = resp.read()
            except HTTPError as exc:
                if not _is_retriable_request_failure(exc):
                    detail = exc.read().decode("utf-8", errors="replace")
                    msg = f"Snyk API HTTP {exc.code} for {url}: {detail[:500]}"
                    raise RuntimeError(msg) from exc
                raise
            try:
                parsed = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                msg = f"Invalid JSON from Snyk API: {exc}"
                raise RuntimeError(msg) from exc
            if not isinstance(parsed, dict):
                msg = "Snyk API returned non-object JSON"
                raise RuntimeError(msg)
            return parsed

        return run_with_retries(
            inner,
            max_attempts=self._settings.http_max_attempts,
            base_backoff_s=self._settings.http_backoff_seconds,
            retry=_is_retriable_request_failure,
        )

    def _request_json_value(self, url: str, *, accept: str) -> Any:
        req = Request(
            url,
            headers={
                "Authorization": f"token {self._settings.token}",
                "Accept": accept,
            },
            method="GET",
        )

        def inner() -> Any:
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    body = resp.read()
            except HTTPError as exc:
                if not _is_retriable_request_failure(exc):
                    detail = exc.read().decode("utf-8", errors="replace")
                    msg = f"Snyk API HTTP {exc.code} for {url}: {detail[:500]}"
                    raise RuntimeError(msg) from exc
                raise
            try:
                return json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                msg = f"Invalid JSON from Snyk API: {exc}"
                raise RuntimeError(msg) from exc

        return run_with_retries(
            inner,
            max_attempts=self._settings.http_max_attempts,
            base_backoff_s=self._settings.http_backoff_seconds,
            retry=_is_retriable_request_failure,
        )

    def iter_group_orgs(self) -> list[dict[str, str]]:
        """Return ``{\"id\", \"name\"}`` for each org in the configured group."""
        s = self._settings
        base_path = f"{s.rest_root}/groups/{s.group_id}/orgs"
        sep = "&" if "?" in base_path else "?"
        first = f"{base_path}{sep}version={s.api_version}"
        out: list[dict[str, str]] = []
        url: str | None = first
        seen_urls: set[str] = set()
        while url:
            if url in seen_urls:
                msg = "Snyk API pagination loop detected for group orgs"
                raise RuntimeError(msg)
            seen_urls.add(url)
            payload = self._request_rest_json_object(url)
            data = payload.get("data")
            if not isinstance(data, list):
                msg = "Unexpected group orgs response: missing data array"
                raise RuntimeError(msg)
            for item in data:
                if not isinstance(item, dict):
                    continue
                oid = item.get("id")
                attrs = item.get("attributes")
                name: str | None = None
                if isinstance(attrs, dict):
                    raw_name = attrs.get("name")
                    if isinstance(raw_name, str) and raw_name.strip():
                        name = raw_name.strip()
                if isinstance(oid, str) and oid.strip() and name:
                    out.append({"id": oid.strip(), "name": name})
            links = payload.get("links")
            next_link = None
            if isinstance(links, dict):
                raw_next = links.get("next")
                if isinstance(raw_next, str):
                    next_link = raw_next
            url = _resolve_next_url(s.rest_root, next_link)
        return out

    def update_org_integration_settings(
        self,
        org_id: str,
        integration_id: str,
        settings: dict[str, Any],
    ) -> None:
        """PUT integration settings via Snyk Integrations v1 API."""
        oid = org_id.strip()
        iid = integration_id.strip()
        url = f"{self._settings.v1_root}/org/{oid}/integrations/{iid}/settings"
        body = json.dumps(settings).encode("utf-8")
        req = Request(
            url,
            data=body,
            headers={
                "Authorization": f"token {self._settings.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="PUT",
        )

        def inner() -> None:
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    resp.read()
            except HTTPError as exc:
                if not _is_retriable_request_failure(exc):
                    detail = exc.read().decode("utf-8", errors="replace")
                    msg = f"Snyk API HTTP {exc.code} for {url}: {detail[:500]}"
                    raise RuntimeError(msg) from exc
                raise

        run_with_retries(
            inner,
            max_attempts=self._settings.http_max_attempts,
            base_backoff_s=self._settings.http_backoff_seconds,
            retry=_is_retriable_request_failure,
        )

    def iter_org_projects(
        self,
        org_id: str,
        *,
        project_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return v1 project objects for an org, optionally filtered by type."""
        oid = org_id.strip()
        page_size = 100
        from_idx = 1
        out: list[dict[str, Any]] = []
        while True:
            to_idx = from_idx + page_size - 1
            url = f"{self._settings.v1_root}/org/{oid}/projects?from={from_idx}&to={to_idx}"
            if project_type is not None and project_type.strip():
                url = f"{url}&types={project_type.strip()}"
            parsed = self._request_json_value(url, accept="application/json")
            batch = normalize_v1_projects_payload(parsed)
            if not batch:
                break
            out.extend(batch)
            if len(batch) < page_size:
                break
            from_idx += page_size
        return out

    def delete_org_project(self, org_id: str, project_id: str) -> None:
        """DELETE a project via Snyk REST API."""
        s = self._settings
        oid = org_id.strip()
        pid = project_id.strip()
        base_path = f"{s.rest_root}/orgs/{oid}/projects/{pid}"
        sep = "&" if "?" in base_path else "?"
        url = f"{base_path}{sep}version={s.api_version}"
        req = Request(
            url,
            headers={
                "Authorization": f"token {self._settings.token}",
                "Accept": "application/vnd.api+json",
            },
            method="DELETE",
        )

        def inner() -> None:
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    resp.read()
            except HTTPError as exc:
                if not _is_retriable_request_failure(exc):
                    detail = exc.read().decode("utf-8", errors="replace")
                    msg = f"Snyk API HTTP {exc.code} for {url}: {detail[:500]}"
                    raise RuntimeError(msg) from exc
                raise

        run_with_retries(
            inner,
            max_attempts=self._settings.http_max_attempts,
            base_backoff_s=self._settings.http_backoff_seconds,
            retry=_is_retriable_request_failure,
        )

    def update_project_settings(
        self,
        org_id: str,
        project_id: str,
        settings: dict[str, Any],
    ) -> None:
        """PUT project settings via Snyk v1 API."""
        oid = org_id.strip()
        pid = project_id.strip()
        url = f"{self._settings.v1_root}/org/{oid}/project/{pid}/settings"
        body = json.dumps(settings).encode("utf-8")
        req = Request(
            url,
            data=body,
            headers={
                "Authorization": f"token {self._settings.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="PUT",
        )

        def inner() -> None:
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    resp.read()
            except HTTPError as exc:
                if not _is_retriable_request_failure(exc):
                    detail = exc.read().decode("utf-8", errors="replace")
                    msg = f"Snyk API HTTP {exc.code} for {url}: {detail[:500]}"
                    raise RuntimeError(msg) from exc
                raise

        run_with_retries(
            inner,
            max_attempts=self._settings.http_max_attempts,
            base_backoff_s=self._settings.http_backoff_seconds,
            retry=_is_retriable_request_failure,
        )

    def iter_org_integrations(self, org_id: str) -> list[dict[str, Any]]:
        """Return integration objects for JSON:API (rest) or flat v1 payloads."""
        if self._settings.integrations_api == "rest":
            return self._iter_org_integrations_rest(org_id)
        return self._iter_org_integrations_v1(org_id)

    def _iter_org_integrations_v1(self, org_id: str) -> list[dict[str, Any]]:
        oid = org_id.strip()
        url = f"{self._settings.v1_root}/org/{oid}/integrations"
        _LOG.debug("Snyk v1 integrations GET %s", url)
        parsed = self._request_json_value(url, accept="application/json")
        _LOG.debug(
            "Snyk v1 integrations org_id=%s raw=%s",
            oid,
            _v1_integrations_response_debug_summary(parsed),
        )
        items = normalize_v1_integrations_payload(parsed)
        _LOG.debug(
            "Snyk v1 integrations org_id=%s normalized_item_count=%d",
            oid,
            len(items),
        )
        return items

    def _iter_org_integrations_rest(self, org_id: str) -> list[dict[str, Any]]:
        s = self._settings
        oid = org_id.strip()
        base_path = f"{s.rest_root}/orgs/{oid}/integrations"
        sep = "&" if "?" in base_path else "?"
        first = f"{base_path}{sep}version={s.api_version}"
        items: list[dict[str, Any]] = []
        url: str | None = first
        seen_urls: set[str] = set()
        while url:
            if url in seen_urls:
                msg = "Snyk API pagination loop detected for org integrations"
                raise RuntimeError(msg)
            seen_urls.add(url)
            payload = self._request_rest_json_object(url)
            data = payload.get("data")
            if not isinstance(data, list):
                msg = "Unexpected integrations response: missing data array"
                raise RuntimeError(msg)
            for item in data:
                if isinstance(item, dict):
                    items.append(item)
            links = payload.get("links")
            next_link = None
            if isinstance(links, dict):
                raw_next = links.get("next")
                if isinstance(raw_next, str):
                    next_link = raw_next
            url = _resolve_next_url(s.rest_root, next_link)
        return items


def pick_bitbucket_server_integration_id(integrations: list[dict[str, Any]]) -> str:
    """Return integration id for Bitbucket Server, or raise."""
    matches: list[str] = []
    for item in integrations:
        iid = item.get("id")
        if not isinstance(iid, str) or not iid.strip():
            continue
        itype = _integration_type_slug(item)
        if itype == "bitbucket-server":
            matches.append(iid.strip())
    if not matches:
        msg = "No bitbucket-server integration found for this organization"
        raise ValueError(msg)
    if len(matches) > 1:
        msg = "Multiple bitbucket-server integrations found; disambiguation is not implemented"
        raise ValueError(msg)
    return matches[0]


def _integration_type_slug(item: dict[str, Any]) -> str | None:
    attrs = item.get("attributes")
    if isinstance(attrs, dict):
        for key in ("integration_type", "type", "slug"):
            raw = attrs.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip().lower().replace("_", "-")
    for key in ("integration_type", "integrationType"):
        raw = item.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip().lower().replace("_", "-")
    itype = item.get("type")
    if isinstance(itype, str) and itype.strip():
        slug = itype.strip().lower().replace("_", "-")
        if slug == "integration":
            return None
        return slug
    return None
