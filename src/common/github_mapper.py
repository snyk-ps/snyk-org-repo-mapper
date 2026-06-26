"""Build discovery mapping rows for GitHub repositories."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from common.mapper import mapping_row
from integrations.github.client import (
    GitHubClient,
    parse_committer_identity,
    parse_commit_timestamp,
    repository_has_default_branch,
)


def _empty_mapping_row(
    *,
    org_login: str,
    org_name: str,
    repo_name: str,
) -> dict[str, Any]:
    return mapping_row(
        project_key=org_login,
        project_name=org_name,
        repo_slug=repo_name,
        repo_name=repo_name,
        file_bytes=None,
        default_display="main",
        is_empty=True,
        last_committer_name=None,
        last_committer_email=None,
        last_commit_date=None,
    )


def _mapping_row_for_repository(
    client: GitHubClient,
    *,
    org_login: str,
    org_name: str,
    repo: dict[str, Any],
    file_path: str,
) -> dict[str, Any]:
    name = repo.get("name")
    repo_name = name if isinstance(name, str) and name.strip() else org_login

    if not repository_has_default_branch(repo):
        return _empty_mapping_row(org_login=org_login, org_name=org_name, repo_name=repo_name)

    default_branch = repo.get("default_branch")
    branch_ref = default_branch if isinstance(default_branch, str) else "main"

    latest_commit = client.repository_latest_commit(org_login, repo_name, sha=branch_ref)
    if latest_commit is None:
        return _empty_mapping_row(org_login=org_login, org_name=org_name, repo_name=repo_name)

    committer_name, committer_email = parse_committer_identity(latest_commit)
    last_commit_date = parse_commit_timestamp(latest_commit)
    raw = client.fetch_file_contents(
        org_login,
        repo_name,
        file_path,
        ref=branch_ref,
    )
    return mapping_row(
        project_key=org_login,
        project_name=org_name,
        repo_slug=repo_name,
        repo_name=repo_name,
        file_bytes=raw,
        default_display=branch_ref,
        is_empty=False,
        last_committer_name=committer_name,
        last_committer_email=committer_email,
        last_commit_date=last_commit_date,
    )


def iter_github_mapping(
    client: GitHubClient,
    file_path: str,
    org_logins: Iterable[str],
    *,
    completed_keys: set[tuple[str, str]],
    max_repos: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield mapping rows for repositories under the given GitHub org logins."""
    new_count = 0
    for org_login in org_logins:
        org_name = client.org_display_name(org_login)
        for repo in client.iter_org_repositories(org_login):
            name = repo.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            repo_name = name.strip()
            key = (org_login, repo_name)
            if key in completed_keys:
                continue
            if max_repos is not None and new_count >= max_repos:
                return
            row = _mapping_row_for_repository(
                client,
                org_login=org_login,
                org_name=org_name,
                repo=repo,
                file_path=file_path,
            )
            new_count += 1
            yield row
