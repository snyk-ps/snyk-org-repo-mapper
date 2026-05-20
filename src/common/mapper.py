"""Build JSON-serializable mapping rows for all repositories."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from common.appsec_yaml import parse_appsec_yaml, resolve_production_branch
from integrations.bitbucket import (
    BitbucketServerClient,
    default_branch_tuple,
)
from integrations.bitbucket.client import parse_committer_identity


def row_is_empty(row: dict[str, Any]) -> bool:
    """Return whether a discovery row is marked as an empty Bitbucket repository."""
    return row.get("is_empty") is True


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
    """Assemble one output row combining API metadata and optional file content.

    Args:
        project_key: Bitbucket project key.
        project_name: Bitbucket project display name.
        repo_slug: Repository slug.
        repo_name: Repository display name.
        file_bytes: Raw file bytes from the configured path, or ``None`` if absent.
        default_display: Default branch display id from the API.

    Returns:
        Dictionary matching the DESIGN output fields.
    """
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


def iter_mapping(
    client: BitbucketServerClient,
    file_path: str,
    *,
    completed_keys: set[tuple[str, str]],
    max_repos: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Enumerate repositories and yield mapping rows, skipping completed keys.

    Repository pairs listed in ``completed_keys`` are not fetched again (resume).
    When ``max_repos`` is set, stop after that many **new** repositories are
    processed in this run.

    Args:
        client: Bitbucket API client.
        file_path: Path to the YAML file inside each repository.
        completed_keys: ``(project_key, repo_slug)`` pairs already persisted.
        max_repos: Optional cap on new repositories processed in this invocation.
    """
    new_count = 0
    for project in client.iter_projects():
        pkey = project.get("key")
        pname = project.get("name")
        if not isinstance(pkey, str) or not isinstance(pname, str):
            continue
        for repo in client.iter_repositories(pkey):
            slug = repo.get("slug")
            name = repo.get("name")
            if not isinstance(slug, str):
                continue
            key = (pkey, slug)
            if key in completed_keys:
                continue
            if max_repos is not None and new_count >= max_repos:
                return
            repo_name = name if isinstance(name, str) else slug
            at_ref, default_display = default_branch_tuple(repo)
            latest_commit = client.repository_latest_commit(pkey, slug)
            is_empty = latest_commit is None
            committer_name: str | None = None
            committer_email: str | None = None
            if latest_commit is not None:
                committer_name, committer_email = parse_committer_identity(latest_commit)
            raw = None
            if not is_empty:
                raw = client.fetch_raw_file(pkey, slug, file_path, at_ref)
            row = mapping_row(
                project_key=pkey,
                project_name=pname,
                repo_slug=slug,
                repo_name=repo_name,
                file_bytes=raw,
                default_display=default_display,
                is_empty=is_empty,
                last_committer_name=committer_name,
                last_committer_email=committer_email,
            )
            new_count += 1
            yield row


def collect_mapping(client: BitbucketServerClient, file_path: str) -> list[dict[str, Any]]:
    """Enumerate all projects and repositories and build mapping rows."""
    return list(iter_mapping(client, file_path, completed_keys=set(), max_repos=None))
