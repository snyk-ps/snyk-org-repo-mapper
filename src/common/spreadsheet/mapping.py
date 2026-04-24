"""Build primary mapping rows from spreadsheet columns A/B/D."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.spreadsheet.xlsx import iter_first_sheet_abd


def mapping_row_from_abd(
    col_a: str | None,
    col_b: str | None,
    col_d: str | None,
) -> dict[str, Any] | None:
    """Return one mapper row dict, or ``None`` if this spreadsheet row is skipped."""
    if col_b is None:
        return None
    b = col_b.strip()
    if not b.startswith("BB::"):
        return None
    parts = b.split("::")
    if len(parts) != 3 or parts[0] != "BB":
        return None
    project_key, repo_slug = parts[1], parts[2]
    if not project_key.strip() or not repo_slug.strip():
        return None
    project_key = project_key.strip()
    repo_slug = repo_slug.strip()

    apm_val = None
    if col_a is not None:
        stripped = col_a.strip()
        apm_val = stripped if stripped else None

    display = col_d.strip() if col_d is not None and col_d.strip() else repo_slug

    repository_path = f"{project_key}/{repo_slug}"
    return {
        "apm_code": apm_val,
        "repository_path": repository_path,
        "repository_name": display,
        "production_branch": "",
        "bitbucket_project_name": project_key,
    }


def mapping_rows_from_xlsx(path: Path) -> list[dict[str, Any]]:
    """Load all mapping rows from the first worksheet of an ``.xlsx`` file."""
    rows: list[dict[str, Any]] = []
    for _, a, b, d in iter_first_sheet_abd(path):
        row = mapping_row_from_abd(a, b, d)
        if row is not None:
            rows.append(row)
    return rows
