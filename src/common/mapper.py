"""Build JSON-serializable mapping rows for all repositories."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from common.appsec_yaml import parse_appsec_yaml, resolve_production_branch
from integrations.bitbucket import (
    BitbucketServerClient,
    DEFAULT_BRANCH_EMPTY_REPO,
    resolve_repository_branch,
)
from integrations.bitbucket.client import parse_committer_identity


def row_is_empty(row: dict[str, Any]) -> bool:
    """Return whether a discovery row is marked as an empty Bitbucket repository."""
    return row.get("is_empty") is True


def _project_name_from_repo(repo: dict[str, Any], project_key: str) -> str:
    project = repo.get("project")
    if isinstance(project, dict):
        name = project.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return project_key


def mapping_row(
    *,
    project_key: str,
    project_name: str,
    repo_slug: str,
    repo_name: str,
    file_bytes: bytes | None,
    default_display: str,
    is_empty: bool,
    last_committer_name: str | None = None,
    last_committer_email: str | None = None,
) -> dict[str, Any]:
    """Assemble one output row combining API metadata and optional file content."""
    apm_code: str | None = None
    yaml_branch: str | None = None
    if file_bytes is not None:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("utf-8", errors="replace")
        parsed = parse_appsec_yaml(text)
        apm_code = parsed.apm_code
        yaml_branch = parsed.production_branch

    production_branch = resolve_production_branch(yaml_branch, default_display)
    repository_path = f"{project_key}/{repo_slug}"
    return {
        "apm_code": apm_code,
        "repository_path": repository_path,
        "repository_name": repo_name,
        "production_branch": production_branch,
        "bitbucket_project_name": project_name,
        "is_empty": is_empty,
        "last_committer_name": last_committer_name,
        "last_committer_email": last_committer_email,
    }


def _empty_mapping_row(
    *,
    project_key: str,
    project_name: str,
    repo_slug: str,
    repo_name: str,
) -> dict[str, Any]:
    return mapping_row(
        project_key=project_key,
        project_name=project_name,
        repo_slug=repo_slug,
        repo_name=repo_name,
        file_bytes=None,
        default_display="master",
        is_empty=True,
        last_committer_name=None,
        last_committer_email=None,
    )


def _mapping_row_for_repository(
    client: BitbucketServerClient,
    *,
    project_key: str,
    project_name: str,
    repo_slug: str,
    repo: dict[str, Any],
    file_path: str,
) -> dict[str, Any]:
    """Build one discovery row for a repository JSON object from the Bitbucket API."""
    name = repo.get("name")
    repo_name = name if isinstance(name, str) and name.strip() else repo_slug

    branch = resolve_repository_branch(client, repo, project_key, repo_slug)
    if branch is DEFAULT_BRANCH_EMPTY_REPO:
        return _empty_mapping_row(
            project_key=project_key,
            project_name=project_name,
            repo_slug=repo_slug,
            repo_name=repo_name,
        )

    at_ref: str | None
    default_display: str | None
    if branch is not None:
        at_ref, default_display = branch
    else:
        at_ref = None
        default_display = None

    latest_commit = client.repository_latest_commit(project_key, repo_slug)
    is_empty = latest_commit is None
    committer_name: str | None = None
    committer_email: str | None = None
    if latest_commit is not None:
        committer_name, committer_email = parse_committer_identity(latest_commit)

    if is_empty:
        return _empty_mapping_row(
            project_key=project_key,
            project_name=project_name,
            repo_slug=repo_slug,
            repo_name=repo_name,
        )

    if at_ref is None:
        at_ref, default_display = "refs/heads/master", "master"

    raw = client.fetch_raw_file(project_key, repo_slug, file_path, at_ref)
    return mapping_row(
        project_key=project_key,
        project_name=project_name,
        repo_slug=repo_slug,
        repo_name=repo_name,
        file_bytes=raw,
        default_display=default_display,
        is_empty=is_empty,
        last_committer_name=committer_name,
        last_committer_email=committer_email,
    )


def iter_mapping_for_repos(
    client: BitbucketServerClient,
    file_path: str,
    repo_targets: Iterable[tuple[str, str]],
    *,
    completed_keys: set[tuple[str, str]],
    max_repos: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield mapping rows for explicit ``(project_key, repo_slug)`` pairs."""
    new_count = 0
    for project_key, repo_slug in repo_targets:
        key = (project_key, repo_slug)
        if key in completed_keys:
            continue
        if max_repos is not None and new_count >= max_repos:
            return
        repo = client.get_repository(project_key, repo_slug)
        project_name = _project_name_from_repo(repo, project_key)
        row = _mapping_row_for_repository(
            client,
            project_key=project_key,
            project_name=project_name,
            repo_slug=repo_slug,
            repo=repo,
            file_path=file_path,
        )
        new_count += 1
        yield row


def iter_mapping(
    client: BitbucketServerClient,
    file_path: str,
    *,
    completed_keys: set[tuple[str, str]],
    max_repos: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Enumerate repositories and yield mapping rows, skipping completed keys."""
    new_count = 0
    for project in client.iter_projects():
        pkey = project.get("key")
        pname = project.get("name")
        if not isinstance(pkey, str) or not isinstance(pname, str):
            continue
        for repo in client.iter_repositories(pkey):
            slug = repo.get("slug")
            if not isinstance(slug, str):
                continue
            key = (pkey, slug)
            if key in completed_keys:
                continue
            if max_repos is not None and new_count >= max_repos:
                return
            row = _mapping_row_for_repository(
                client,
                project_key=pkey,
                project_name=pname,
                repo_slug=slug,
                repo=repo,
                file_path=file_path,
            )
            new_count += 1
            yield row


def collect_mapping(client: BitbucketServerClient, file_path: str) -> list[dict[str, Any]]:
    """Enumerate all projects and repositories and build mapping rows."""
    return list(iter_mapping(client, file_path, completed_keys=set(), max_repos=None))
