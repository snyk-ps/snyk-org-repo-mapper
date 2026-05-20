"""Minimal Bitbucket Server (Data Center) REST client."""

from __future__ import annotations

import json
from collections.abc import Iterator
from http.client import RemoteDisconnected
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from integrations.http_retry import run_with_retries


def iter_paged_values(payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield ``values`` entries from a paginated Bitbucket JSON object."""
    values = payload.get("values")
    if not isinstance(values, list):
        return
    yield from (item for item in values if isinstance(item, dict))


def default_branch_tuple(repo: dict[str, Any]) -> tuple[str, str]:
    """Return ``(at_ref, display_id)`` for the repository default branch.

    ``at_ref`` is suitable for the ``at`` query parameter on raw file requests.
    ``display_id`` is the short branch name for human-readable output.

    Args:
        repo: Repository JSON object from the Bitbucket REST API.

    Returns:
        Tuple of ref (for ``at``) and display branch name.
    """
    ref = repo.get("defaultBranch")
    if ref is None:
        return "refs/heads/main", "main"
    if isinstance(ref, str):
        display = ref.rsplit("/", maxsplit=1)[-1] if "/" in ref else ref
        if ref.startswith("refs/"):
            return ref, display
        return f"refs/heads/{ref}", ref
    if isinstance(ref, dict):
        ref_id = ref.get("id")
        display = ref.get("displayId")
        if isinstance(ref_id, str) and ref_id.startswith("refs/"):
            disp = display if isinstance(display, str) and display else ref_id.rsplit("/", maxsplit=1)[-1]
            return ref_id, disp
        if isinstance(display, str) and display:
            return f"refs/heads/{display}", display
    return "refs/heads/main", "main"


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


class BitbucketServerClient:
    """Bitbucket Server REST API client using ``urllib`` (no third-party HTTP)."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout_s: float = 60.0,
        http_max_attempts: int = 5,
        http_backoff_seconds: float = 1.0,
    ) -> None:
        self._base = base_url.rstrip("/") + "/"
        self._token = token
        self._timeout = timeout_s
        self._http_max_attempts = http_max_attempts
        self._http_backoff_seconds = http_backoff_seconds

    def _request_json(self, path: str) -> dict[str, Any]:
        url = urljoin(self._base, path.lstrip("/"))
        req = Request(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="GET",
        )

        def inner() -> dict[str, Any]:
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    body = resp.read()
            except HTTPError as exc:
                if not _is_retriable_request_failure(exc):
                    msg = f"HTTP {exc.code} requesting Bitbucket API"
                    raise RuntimeError(msg) from exc
                raise
            except (URLError, TimeoutError, RemoteDisconnected):
                raise
            try:
                parsed = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                msg = "Invalid JSON from Bitbucket API"
                raise RuntimeError(msg) from exc
            if not isinstance(parsed, dict):
                msg = "Unexpected Bitbucket API response shape"
                raise RuntimeError(msg)
            return parsed

        try:
            return run_with_retries(
                inner,
                max_attempts=self._http_max_attempts,
                base_backoff_s=self._http_backoff_seconds,
                retry=_is_retriable_request_failure,
            )
        except HTTPError as exc:
            msg = f"HTTP {exc.code} requesting Bitbucket API"
            raise RuntimeError(msg) from exc
        except (URLError, TimeoutError, RemoteDisconnected) as exc:
            msg = "Network error calling Bitbucket API"
            raise RuntimeError(msg) from exc

    def iter_projects(self, *, page_limit: int = 100) -> Iterator[dict[str, Any]]:
        """Yield all projects (paginated)."""
        start = 0
        while True:
            path = f"rest/api/1.0/projects?limit={page_limit}&start={start}"
            page = self._request_json(path)
            yield from iter_paged_values(page)
            if page.get("isLastPage", True):
                break
            next_start = page.get("nextPageStart")
            if not isinstance(next_start, int):
                break
            start = next_start

    def iter_repositories(self, project_key: str, *, page_limit: int = 100) -> Iterator[dict[str, Any]]:
        """Yield all repositories in a project (paginated)."""
        key = quote(project_key, safe="")
        start = 0
        while True:
            path = (
                f"rest/api/1.0/projects/{key}/repos?limit={page_limit}&start={start}"
            )
            page = self._request_json(path)
            yield from iter_paged_values(page)
            if page.get("isLastPage", True):
                break
            next_start = page.get("nextPageStart")
            if not isinstance(next_start, int):
                break
            start = next_start

    def repository_has_commits(self, project_key: str, repo_slug: str) -> bool:
        """Return whether the repository has at least one commit."""
        pk = quote(project_key, safe="")
        slug = quote(repo_slug, safe="")
        path = f"rest/api/1.0/projects/{pk}/repos/{slug}/commits?limit=1"
        page = self._request_json(path)
        for _ in iter_paged_values(page):
            return True
        return False

    def fetch_raw_file(
        self,
        project_key: str,
        repo_slug: str,
        path_in_repo: str,
        at_ref: str,
    ) -> bytes | None:
        """Return raw bytes for a file at ``path_in_repo`` or ``None`` if missing."""
        pk = quote(project_key, safe="")
        slug = quote(repo_slug, safe="")
        encoded_path = quote(path_in_repo.lstrip("/"), safe="/")
        at_q = quote(at_ref, safe="")
        path = (
            f"rest/api/1.0/projects/{pk}/repos/{slug}/raw/{encoded_path}?at={at_q}"
        )
        url = urljoin(self._base, path.lstrip("/"))

        def inner() -> bytes | None:
            req = Request(
                url,
                headers={"Authorization": f"Bearer {self._token}"},
                method="GET",
            )
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    return resp.read()
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
