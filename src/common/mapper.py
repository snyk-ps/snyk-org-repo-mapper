"""Build JSON-serializable mapping rows for all repositories."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from common.appsec_yaml import parse_appsec_yaml, warn_if_apm_code_unconventional
from integrations.bitbucket import (
    BitbucketServerClient,
    DEFAULT_BRANCH_EMPTY_REPO,
    resolve_latest_active_branch,
    resolve_repository_branch,
)
from integrations.bitbucket.client import parse_committer_identity, parse_commit_timestamp


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


def _repository_is_archived(repo: dict[str, Any]) -> bool:
    return repo.get("archived") is True


def _bitbucket_default_branch_display(
    client: BitbucketServerClient,
    repo: dict[str, Any],
    project_key: str,
    repo_slug: str,
) -> str | None:
    branch = resolve_repository_branch(client, repo, project_key, repo_slug)
    if branch is DEFAULT_BRANCH_EMPTY_REPO or branch is None:
        return None
    _, display = branch
    return display


def mapping_row(
    *,
    project_key: str,
    project_name: str,
    repo_slug: str,
    repo_name: str,
    file_bytes: bytes | None,
    is_empty: bool,
    bitbucket_default_branch: str | None = None,
    latest_active_branch: str | None = None,
    is_archived: bool = False,
    last_committer_name: str | None = None,
    last_committer_email: str | None = None,
    last_commit_date: str | None = None,
) -> dict[str, Any]:
    """Assemble one output row combining API metadata and optional file content."""
    apm_code: str | None = None
    production_branch: str | None = None
    if file_bytes is not None:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("utf-8", errors="replace")
        parsed = parse_appsec_yaml(text)
        apm_code = parsed.apm_code
        production_branch = parsed.production_branch

    repository_path = f"{project_key}/{repo_slug}"
    if apm_code is not None:
        warn_if_apm_code_unconventional(apm_code, repository_path=repository_path)
    return {
        "apm_code": apm_code,
        "repository_path": repository_path,
        "repository_name": repo_name,
        "production_branch": production_branch,
        "bitbucket_project_name": project_name,
        "bitbucket_default_branch": bitbucket_default_branch,
        "latest_active_branch": latest_active_branch,
        "is_archived": is_archived,
        "is_empty": is_empty,
        "last_committer_name": last_committer_name,
        "last_committer_email": last_committer_email,
        "last_commit_date": last_commit_date,
    }


def _empty_mapping_row(
    *,
    project_key: str,
    project_name: str,
    repo_slug: str,
    repo_name: str,
    bitbucket_default_branch: str | None = None,
    is_archived: bool = False,
) -> dict[str, Any]:
    return mapping_row(
        project_key=project_key,
        project_name=project_name,
        repo_slug=repo_slug,
        repo_name=repo_name,
        file_bytes=None,
        is_empty=True,
        bitbucket_default_branch=bitbucket_default_branch,
        latest_active_branch=None,
        is_archived=is_archived,
        last_committer_name=None,
        last_committer_email=None,
        last_commit_date=None,
    )


def _mapping_row_for_repository(
    client: BitbucketServerClient,
    *,
    project_key: str,
    project_name: str,
    repo_slug: str,
    repo: dict[str, Any],
    file_path: str,
    include_archived: bool = False,
) -> dict[str, Any] | None:
    """Build one discovery row for a repository JSON object from the Bitbucket API."""
    if _repository_is_archived(repo) and not include_archived:
        return None

    name = repo.get("name")
    repo_name = name if isinstance(name, str) and name.strip() else repo_slug
    is_archived = _repository_is_archived(repo)
    bitbucket_default_branch = _bitbucket_default_branch_display(
        client, repo, project_key, repo_slug
    )

    branch = resolve_repository_branch(client, repo, project_key, repo_slug)
    if branch is DEFAULT_BRANCH_EMPTY_REPO:
        return _empty_mapping_row(
            project_key=project_key,
            project_name=project_name,
            repo_slug=repo_slug,
            repo_name=repo_name,
            bitbucket_default_branch=bitbucket_default_branch,
            is_archived=is_archived,
        )

    latest_commit = client.repository_latest_commit(project_key, repo_slug)
    if latest_commit is None:
        return _empty_mapping_row(
            project_key=project_key,
            project_name=project_name,
            repo_slug=repo_slug,
            repo_name=repo_name,
            bitbucket_default_branch=bitbucket_default_branch,
            is_archived=is_archived,
        )

    active = resolve_latest_active_branch(client, project_key, repo_slug)
    latest_active_branch: str | None = None
    tip_commit: dict[str, Any] | None = None
    raw: bytes | None = None

    if active is not None:
        yaml_at_ref, latest_active_branch, tip_commit = active
        if parse_commit_timestamp(tip_commit) is None:
            refetched = client.repository_latest_commit_on_ref(
                project_key, repo_slug, yaml_at_ref
            )
            if refetched is not None:
                tip_commit = refetched
        raw = client.fetch_raw_file(project_key, repo_slug, file_path, yaml_at_ref)
    else:
        tip_commit = latest_commit

    committer_name: str | None = None
    committer_email: str | None = None
    last_commit_date: str | None = None
    if tip_commit is not None:
        committer_name, committer_email = parse_committer_identity(tip_commit)
        last_commit_date = parse_commit_timestamp(tip_commit)

    return mapping_row(
        project_key=project_key,
        project_name=project_name,
        repo_slug=repo_slug,
        repo_name=repo_name,
        file_bytes=raw,
        is_empty=False,
        bitbucket_default_branch=bitbucket_default_branch,
        latest_active_branch=latest_active_branch,
        is_archived=is_archived,
        last_committer_name=committer_name,
        last_committer_email=committer_email,
        last_commit_date=last_commit_date,
    )


def iter_mapping_for_repos(
    client: BitbucketServerClient,
    file_path: str,
    repo_targets: Iterable[tuple[str, str]],
    *,
    completed_keys: set[tuple[str, str]],
    max_repos: int | None = None,
    include_archived: bool = False,
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
            include_archived=include_archived,
        )
        if row is None:
            continue
        new_count += 1
        yield row


def iter_mapping(
    client: BitbucketServerClient,
    file_path: str,
    *,
    completed_keys: set[tuple[str, str]],
    max_repos: int | None = None,
    include_archived: bool = False,
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
                include_archived=include_archived,
            )
            if row is None:
                continue
            new_count += 1
            yield row


def collect_mapping(
    client: BitbucketServerClient,
    file_path: str,
    *,
    include_archived: bool = False,
) -> list[dict[str, Any]]:
    """Enumerate all projects and repositories and build mapping rows."""
    return list(
        iter_mapping(
            client,
            file_path,
            completed_keys=set(),
            max_repos=None,
            include_archived=include_archived,
        )
    )
