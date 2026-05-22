"""Parse bb-repo-mapping.xlsx: ProjectKey + semicolon-delimited repo slugs."""

from __future__ import annotations

import sys
from pathlib import Path

from common.spreadsheet.xlsx import iter_first_sheet_ab

EXPECTED_HEADER_A = "ProjectKey"
EXPECTED_HEADER_B = "RepoName"


def _split_repo_names(cell: str | None) -> list[str]:
    if cell is None:
        return []
    return [part.strip() for part in cell.split(";") if part.strip()]


def parse_bb_repo_mapping_sheet(path: Path) -> list[tuple[str, str]]:
    """Return ``(project_key, repo_slug)`` pairs from the first worksheet.

    Row 1 must be headers ``ProjectKey`` / ``RepoName``. Duplicate pairs are
    skipped (first occurrence wins) with a stderr warning.

    Raises:
        ValueError: Invalid file, headers, or empty project key.
    """
    path = Path(path)
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row_idx, col_a, col_b in iter_first_sheet_ab(path):
        if row_idx == 1:
            a = (col_a or "").strip()
            b = (col_b or "").strip()
            if a != EXPECTED_HEADER_A or b != EXPECTED_HEADER_B:
                msg = (
                    f"Row 1 must be headers {EXPECTED_HEADER_A!r} and {EXPECTED_HEADER_B!r}; "
                    f"got {a!r} and {b!r}"
                )
                raise ValueError(msg)
            continue
        project_key = (col_a or "").strip()
        if not project_key:
            msg = f"Row {row_idx}: project key (column A) is empty"
            raise ValueError(msg)
        for slug in _split_repo_names(col_b):
            key = (project_key, slug)
            if key in seen:
                print(
                    f"Warning: duplicate repository {project_key}/{slug} in spreadsheet; "
                    "using first occurrence only",
                    file=sys.stderr,
                )
                continue
            seen.add(key)
            pairs.append(key)
    if not pairs:
        msg = "Spreadsheet contains no repository entries after the header row"
        raise ValueError(msg)
    return pairs
