"""Build bitbucket-empty-repos.json from discovery rows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.mapper import row_is_empty
from common.output_state import atomic_write_json


EMPTY_REPOS_VERSION = 1
DEFAULT_EMPTY_REPOS_FILENAME = "bitbucket-empty-repos.json"


def _empty_repo_entry(row: dict[str, Any]) -> dict[str, str] | None:
    path = row.get("repository_path")
    if not isinstance(path, str) or "/" not in path:
        return None
    project_key, _, repo_slug = path.partition("/")
    if not project_key or not repo_slug:
        return None
    name = row.get("repository_name")
    repo_name = name if isinstance(name, str) else repo_slug
    project_name = row.get("bitbucket_project_name")
    bitbucket_project_name = project_name if isinstance(project_name, str) else project_key
    return {
        "repository_path": path,
        "project_key": project_key,
        "repo_slug": repo_slug,
        "repository_name": repo_name,
        "bitbucket_project_name": bitbucket_project_name,
    }


def build_empty_repos_document(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build version 1 empty-repositories JSON from discovery rows."""
    repositories: list[dict[str, str]] = []
    for row in rows:
        if not row_is_empty(row):
            continue
        entry = _empty_repo_entry(row)
        if entry is not None:
            repositories.append(entry)
    repositories.sort(key=lambda item: item["repository_path"])
    return {
        "version": EMPTY_REPOS_VERSION,
        "source": "bitbucket",
        "repositories": repositories,
    }


def write_empty_repos_document(path: Path, rows: list[dict[str, Any]]) -> None:
    """Atomically write empty-repositories JSON."""
    atomic_write_json(path, build_empty_repos_document(rows))
