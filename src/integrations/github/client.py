"""Minimal GitHub REST API client (v3)."""

from __future__ import annotations

import base64
import binascii
import json
import re
from collections.abc import Iterator
from http.client import RemoteDisconnected
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from integrations.http_retry import run_with_retries


def _parse_link_next(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        segment = part.strip()
        if 'rel="next"' not in segment:
            continue
        url_match = re.match(r"<([^>]+)>", segment)
        if url_match:
            return url_match.group(1)
    return None


def _person_identity(person: Any) -> tuple[str | None, str | None]:
    if not isinstance(person, dict):
        return None, None
    name = person.get("name")
    email = person.get("email")
    n = name if isinstance(name, str) and name.strip() else None
    e = email if isinstance(email, str) and email.strip() else None
    return n, e


def parse_committer_identity(commit: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract committer name and email from a GitHub commit, falling back to author."""
    inner = commit.get("commit")
    if not isinstance(inner, dict):
        return None, None
    name, email = _person_identity(inner.get("committer"))
    if name is not None or email is not None:
        return name, email
    return _person_identity(inner.get("author"))


def parse_commit_timestamp(commit: dict[str, Any]) -> str | None:
    """Return commit time as ISO-8601 from GitHub commit metadata, or ``None``."""
    inner = commit.get("commit")
    if not isinstance(inner, dict):
        return None
    for key in ("committer", "author"):
        person = inner.get(key)
        if not isinstance(person, dict):
            continue
        date = person.get("date")
        if isinstance(date, str) and date.strip():
            return date.strip()
    return None


def repository_has_default_branch(repo: dict[str, Any]) -> bool:
    branch = repo.get("default_branch")
    return isinstance(branch, str) and bool(branch.strip())


def _is_retriable_request_failure(exc: BaseException) -> bool:
    if isinstance(exc, RemoteDisconnected):
        return True
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, URLError):
        return True
    if isinstance(exc, HTTPError):
        return exc.code in (403, 429, 500, 502, 503, 504)
    return False


class GitHubClient:
    """GitHub REST API client using ``urllib`` (no third-party HTTP)."""

    def __init__(
        self,
        api_url: str,
        token: str,
        *,
        timeout_s: float = 60.0,
        http_max_attempts: int = 5,
        http_backoff_seconds: float = 1.0,
    ) -> None:
        self._base = api_url.rstrip("/") + "/"
        self._token = token
        self._timeout = timeout_s
        self._http_max_attempts = http_max_attempts
        self._http_backoff_seconds = http_backoff_seconds

    def _request(
        self,
        path_or_url: str,
        *,
        absolute: bool = False,
    ) -> tuple[Any, str | None]:
        url = path_or_url if absolute else urljoin(self._base, path_or_url.lstrip("/"))
        req = Request(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="GET",
        )

        def inner() -> tuple[Any, str | None]:
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    link = resp.headers.get("Link")
                    body = resp.read()
            except HTTPError as exc:
                if not _is_retriable_request_failure(exc):
                    msg = f"HTTP {exc.code} requesting GitHub API"
                    raise RuntimeError(msg) from exc
                raise
            except (URLError, TimeoutError, RemoteDisconnected):
                raise
            if not body:
                return None, link
            try:
                parsed = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                msg = "Invalid JSON from GitHub API"
                raise RuntimeError(msg) from exc
            return parsed, link

        try:
            return run_with_retries(
                inner,
                max_attempts=self._http_max_attempts,
                base_backoff_s=self._http_backoff_seconds,
                retry=_is_retriable_request_failure,
            )
        except HTTPError as exc:
            msg = f"HTTP {exc.code} requesting GitHub API"
            raise RuntimeError(msg) from exc
        except (URLError, TimeoutError, RemoteDisconnected) as exc:
            msg = "Network error calling GitHub API"
            raise RuntimeError(msg) from exc

    def get_org(self, org_login: str) -> dict[str, Any]:
        """Return organization metadata."""
        login = quote(org_login, safe="")
        payload, _link = self._request(f"orgs/{login}")
        if not isinstance(payload, dict):
            msg = "Unexpected GitHub org API response shape"
            raise RuntimeError(msg)
        return payload

    def org_display_name(self, org_login: str) -> str:
        org = self.get_org(org_login)
        name = org.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
        login = org.get("login")
        if isinstance(login, str) and login.strip():
            return login.strip()
        return org_login

    def iter_org_repositories(
        self,
        org_login: str,
        *,
        per_page: int = 100,
    ) -> Iterator[dict[str, Any]]:
        """Yield all repositories for an organization (paginated)."""
        login = quote(org_login, safe="")
        path = f"orgs/{login}/repos?per_page={per_page}&page=1"
        while path:
            payload, link = self._request(path, absolute=path.startswith("http"))
            if not isinstance(payload, list):
                msg = "Unexpected GitHub org repos API response shape"
                raise RuntimeError(msg)
            yield from (item for item in payload if isinstance(item, dict))
            next_url = _parse_link_next(link)
            path = next_url if next_url else ""

    def repository_latest_commit(
        self,
        owner: str,
        repo: str,
        *,
        sha: str | None = None,
    ) -> dict[str, Any] | None:
        """Return the latest commit object, or ``None`` when no commits exist."""
        own = quote(owner, safe="")
        name = quote(repo, safe="")
        path = f"repos/{own}/{name}/commits?per_page=1"
        if sha:
            path += f"&sha={quote(sha, safe='')}"
        url = urljoin(self._base, path.lstrip("/"))

        def inner() -> dict[str, Any] | None:
            req = Request(
                url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                method="GET",
            )
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    body = resp.read()
            except HTTPError as exc:
                if exc.code == 409:
                    return None
                if not _is_retriable_request_failure(exc):
                    msg = f"HTTP {exc.code} requesting GitHub commits"
                    raise RuntimeError(msg) from exc
                raise
            except (URLError, TimeoutError, RemoteDisconnected):
                raise
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                msg = "Invalid JSON from GitHub commits API"
                raise RuntimeError(msg) from exc
            if not isinstance(payload, list) or not payload:
                return None
            first = payload[0]
            return first if isinstance(first, dict) else None

        try:
            return run_with_retries(
                inner,
                max_attempts=self._http_max_attempts,
                base_backoff_s=self._http_backoff_seconds,
                retry=_is_retriable_request_failure,
            )
        except HTTPError as exc:
            if exc.code == 409:
                return None
            msg = f"HTTP {exc.code} requesting GitHub commits"
            raise RuntimeError(msg) from exc
        except (URLError, TimeoutError, RemoteDisconnected) as exc:
            msg = "Network error calling GitHub commits API"
            raise RuntimeError(msg) from exc

    def fetch_file_contents(
        self,
        owner: str,
        repo: str,
        path_in_repo: str,
        *,
        ref: str,
    ) -> bytes | None:
        """Return raw bytes for a file at ``path_in_repo`` or ``None`` if missing."""
        own = quote(owner, safe="")
        name = quote(repo, safe="")
        encoded_path = quote(path_in_repo.lstrip("/"), safe="/")
        api_path = f"repos/{own}/{name}/contents/{encoded_path}?ref={quote(ref, safe='')}"
        url = urljoin(self._base, api_path.lstrip("/"))

        def inner() -> bytes | None:
            req = Request(
                url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                method="GET",
            )
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    body = resp.read()
            except HTTPError as exc:
                if exc.code == 404:
                    return None
                if not _is_retriable_request_failure(exc):
                    msg = f"HTTP {exc.code} fetching repository file"
                    raise RuntimeError(msg) from exc
                raise
            except (URLError, TimeoutError, RemoteDisconnected):
                raise
            try:
                parsed = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                msg = "Invalid JSON from GitHub contents API"
                raise RuntimeError(msg) from exc
            if not isinstance(parsed, dict):
                msg = "Unexpected GitHub contents API response shape"
                raise RuntimeError(msg)
            encoding = parsed.get("encoding")
            content = parsed.get("content")
            if encoding != "base64" or not isinstance(content, str):
                return None
            try:
                return base64.b64decode(content, validate=False)
            except (ValueError, binascii.Error):
                return None

        try:
            return run_with_retries(
                inner,
                max_attempts=self._http_max_attempts,
                base_backoff_s=self._http_backoff_seconds,
                retry=_is_retriable_request_failure,
            )
        except HTTPError as exc:
            if exc.code == 404:
                return None
            msg = f"HTTP {exc.code} fetching repository file"
            raise RuntimeError(msg) from exc
        except (URLError, TimeoutError, RemoteDisconnected) as exc:
            msg = "Network error fetching repository file"
            raise RuntimeError(msg) from exc
