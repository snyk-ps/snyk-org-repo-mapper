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


def _person_identity(person: Any) -> tuple[str | None, str | None]:
    """Return ``(name, email)`` from a Bitbucket commit author/committer object."""
    if not isinstance(person, dict):
        return None, None
    name = person.get("name")
    email = person.get("emailAddress")
    n = name if isinstance(name, str) and name.strip() else None
    e = email if isinstance(email, str) and email.strip() else None
    return n, e


def parse_committer_identity(commit: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract committer name and email from a commit, falling back to author."""
    name, email = _person_identity(commit.get("committer"))
    if name is not None or email is not None:
        return name, email
    return _person_identity(commit.get("author"))


def repository_has_default_branch(repo: dict[str, Any]) -> bool:
    """Return whether ``repo.defaultBranch`` on a repository object is usable.

    Gate 1 in discovery: only inspects the repository list/GET payload. When
    this returns false, callers should try ``GET .../default-branch`` before
    treating the repository as having no default branch.
    """
    ref = repo.get("defaultBranch")
    if ref is None:
        return False
    if isinstance(ref, str) and ref.strip():
        return True
    if isinstance(ref, dict):
        ref_id = ref.get("id")
        display = ref.get("displayId")
        if isinstance(ref_id, str) and ref_id.strip():
            return True
        if isinstance(display, str) and display.strip():
            return True
    return False


def default_branch_tuple(repo: dict[str, Any]) -> tuple[str, str]:
    """Return ``(at_ref, display_id)`` for the repository default branch.

    Gate 3 in discovery: normalizes ``defaultBranch`` on a repository object (or
    a synthetic ``{"defaultBranch": branch_object}`` from the default-branch API).
    When shape is unrecognized, falls back to ``refs/heads/master`` / ``master``.
    This fallback is only reached when Gate 1 passed or the default-branch API
    returned a branch object.
    """
    ref = repo.get("defaultBranch")
    if ref is None:
        return "refs/heads/master", "master"
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
    return "refs/heads/master", "master"


# Sentinel: Bitbucket returned 204 No Content for default-branch (empty repository).
DEFAULT_BRANCH_EMPTY_REPO = object()


def default_branch_tuple_from_branch_object(branch: dict[str, Any]) -> tuple[str, str]:
    """Normalize a branch object from the default-branch API to ``(at_ref, display)``."""
    return default_branch_tuple({"defaultBranch": branch})


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


def resolve_repository_branch(
    client: BitbucketServerClient,
    repo: dict[str, Any],
    project_key: str,
    repo_slug: str,
) -> tuple[str, str] | object | None:
    """Resolve ``(at_ref, display)`` for discovery YAML fetch.

    Resolution order (see tests in ``test_bitbucket_helpers.py`` for matrix):

    1. ``repository_has_default_branch(repo)`` → ``default_branch_tuple(repo)``
    2. ``GET .../default-branch`` → branch object normalized like ``defaultBranch``
    3. ``DEFAULT_BRANCH_EMPTY_REPO`` when the API returns 204 (empty repository)
    4. ``None`` when the API returns 404 (configured ref not created); mapper may
       fall back to synthetic ``master`` when commits exist
    """
    if repository_has_default_branch(repo):
        return default_branch_tuple(repo)
    branch = client.get_default_branch(project_key, repo_slug)
    if branch is DEFAULT_BRANCH_EMPTY_REPO:
        return DEFAULT_BRANCH_EMPTY_REPO
    if isinstance(branch, dict):
        return default_branch_tuple_from_branch_object(branch)
    return None


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

    def get_repository(self, project_key: str, repo_slug: str) -> dict[str, Any]:
        """Return repository metadata for a single repo.

        Raises:
            ValueError: If the repository does not exist (HTTP 404).
            RuntimeError: On other HTTP or network failures.
        """
        pk = quote(project_key, safe="")
        slug = quote(repo_slug, safe="")
        path = f"rest/api/1.0/projects/{pk}/repos/{slug}"
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
                if exc.code == 404:
                    msg = f"Repository not found: {project_key}/{repo_slug}"
                    raise ValueError(msg) from exc
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
        except ValueError:
            raise
        except HTTPError as exc:
            msg = f"HTTP {exc.code} requesting Bitbucket API"
            raise RuntimeError(msg) from exc
        except (URLError, TimeoutError, RemoteDisconnected) as exc:
            msg = "Network error calling Bitbucket API"
            raise RuntimeError(msg) from exc

    def get_default_branch(
        self,
        project_key: str,
        repo_slug: str,
    ) -> dict[str, Any] | object | None:
        """Return the configured default branch for a repository.

        Returns:
            Branch object (``id``, ``displayId``) on HTTP 200.
            ``DEFAULT_BRANCH_EMPTY_REPO`` on HTTP 204 (empty repository).
            ``None`` on HTTP 404 (configured branch ref not created).
        """
        pk = quote(project_key, safe="")
        slug = quote(repo_slug, safe="")
        path = f"rest/api/1.0/projects/{pk}/repos/{slug}/default-branch"
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

        def inner() -> dict[str, Any] | object | None:
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    if resp.getcode() == 204:
                        return DEFAULT_BRANCH_EMPTY_REPO
                    body = resp.read()
            except HTTPError as exc:
                if exc.code == 404:
                    return None
                if exc.code == 204:
                    return DEFAULT_BRANCH_EMPTY_REPO
                if not _is_retriable_request_failure(exc):
                    msg = f"HTTP {exc.code} requesting Bitbucket default branch"
                    raise RuntimeError(msg) from exc
                raise
            except (URLError, TimeoutError, RemoteDisconnected):
                raise
            if not body:
                return DEFAULT_BRANCH_EMPTY_REPO
            try:
                parsed = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                msg = "Invalid JSON from Bitbucket default-branch API"
                raise RuntimeError(msg) from exc
            if not isinstance(parsed, dict):
                msg = "Unexpected Bitbucket default-branch API response shape"
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
            if exc.code == 404:
                return None
            if exc.code == 204:
                return DEFAULT_BRANCH_EMPTY_REPO
            msg = f"HTTP {exc.code} requesting Bitbucket default branch"
            raise RuntimeError(msg) from exc
        except (URLError, TimeoutError, RemoteDisconnected) as exc:
            msg = "Network error calling Bitbucket default-branch API"
            raise RuntimeError(msg) from exc

    def repository_latest_commit(
        self,
        project_key: str,
        repo_slug: str,
    ) -> dict[str, Any] | None:
        """Return the latest commit object, or ``None`` when the repository has no commits."""
        pk = quote(project_key, safe="")
        slug = quote(repo_slug, safe="")
        path = f"rest/api/1.0/projects/{pk}/repos/{slug}/commits?limit=1"
        page = self._request_json(path)
        for commit in iter_paged_values(page):
            return commit
        return None

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
