"""Snyk API client: REST JSON:API for group orgs; v1 or REST for integrations (urllib)."""

from __future__ import annotations

import json
from http.client import RemoteDisconnected
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from config.snyk_settings import SnykSettings
from integrations.http_retry import run_with_retries


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


def normalize_v1_integrations_payload(parsed: Any) -> list[dict[str, Any]]:
    """Turn v1 GET /org/.../integrations JSON into a list of integration objects."""
    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]
    if isinstance(parsed, dict):
        for key in ("integrations", "data", "results"):
            raw = parsed.get(key)
            if isinstance(raw, list):
                return [x for x in raw if isinstance(x, dict)]
    msg = "Unexpected v1 integrations response shape"
    raise RuntimeError(msg)


class SnykRestClient:
    """Snyk API client using ``urllib``."""

    def __init__(self, settings: SnykSettings, *, timeout_s: float = 60.0) -> None:
        self._settings = settings
        self._timeout = timeout_s

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

    def iter_org_integrations(self, org_id: str) -> list[dict[str, Any]]:
        """Return integration objects for JSON:API (rest) or flat v1 payloads."""
        if self._settings.integrations_api == "rest":
            return self._iter_org_integrations_rest(org_id)
        return self._iter_org_integrations_v1(org_id)

    def _iter_org_integrations_v1(self, org_id: str) -> list[dict[str, Any]]:
        oid = org_id.strip()
        url = f"{self._settings.v1_root}/org/{oid}/integrations"
        parsed = self._request_json_value(url, accept="application/json")
        return normalize_v1_integrations_payload(parsed)

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
