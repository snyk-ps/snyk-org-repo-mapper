"""Per-repository ``apm_code`` lookup for Snyk import enrichment."""

from __future__ import annotations

from typing import Any

from common.output_state import row_repo_key

RepoApmMap = dict[tuple[str, str], str]


def repo_apm_map_from_rows(rows: list[dict[str, Any]]) -> RepoApmMap:
    """Build ``(project_key, repo_slug) → apm_code`` from discovery rows.

    Rows with null or empty ``apm_code`` are omitted. Multiple rows under the same
    Bitbucket project may have different codes.
    """
    result: RepoApmMap = {}
    for row in rows:
        key = row_repo_key(row)
        if key is None:
            continue
        raw = row.get("apm_code")
        if not isinstance(raw, str) or not raw.strip():
            continue
        result[key] = raw.strip()
    return result
