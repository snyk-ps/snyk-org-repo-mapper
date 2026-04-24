"""Load, save, and migrate primary mapping output files (resume support)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


PRIMARY_FORMAT_VERSION = 1


def assert_safe_filesystem_path(path: Path) -> None:
    """Reject paths containing parent traversal segments (``..``).

    Args:
        path: User-supplied or derived filesystem path.

    Raises:
        ValueError: If ``path`` contains a ``..`` component.
    """
    if ".." in path.parts:
        msg = "Paths must not contain '..' components"
        raise ValueError(msg)


def row_repo_key(row: dict[str, Any]) -> tuple[str, str] | None:
    """Return ``(project_key, repo_slug)`` from a mapping row, or ``None`` if invalid."""
    path = row.get("repository_path")
    if not isinstance(path, str) or "/" not in path:
        return None
    project_key, _, slug = path.partition("/")
    if not project_key or not slug:
        return None
    return project_key, slug


def completed_keys_from_rows(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    """Build a set of repository keys already present in saved rows."""
    keys: set[tuple[str, str]] = set()
    for row in rows:
        k = row_repo_key(row)
        if k is not None:
            keys.add(k)
    return keys


def parse_primary_json_payload(data: Any) -> tuple[list[dict[str, Any]], bool]:
    """Parse top-level JSON into rows and whether it was legacy bare-array format.

    Args:
        data: Parsed JSON (typically from ``json.loads``).

    Returns:
        Tuple of mapping rows and ``True`` if ``data`` was a bare JSON array (legacy).

    Raises:
        ValueError: If the structure is not recognized.
    """
    if isinstance(data, list):
        rows: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                rows.append(item)
        return rows, True
    if isinstance(data, dict):
        version = data.get("version")
        raw_rows = data.get("rows")
        if version is not None and version != PRIMARY_FORMAT_VERSION:
            msg = f"Unsupported primary output version: {version!r}"
            raise ValueError(msg)
        if not isinstance(raw_rows, list):
            msg = "Primary output wrapper must contain a 'rows' array"
            raise ValueError(msg)
        out: list[dict[str, Any]] = []
        for item in raw_rows:
            if isinstance(item, dict):
                out.append(item)
        return out, False
    msg = "Primary output must be a JSON array or an object with 'rows'"
    raise ValueError(msg)


def load_primary_output_file(path: Path) -> tuple[list[dict[str, Any]], bool]:
    """Read primary output from disk.

    Args:
        path: Output file path.

    Returns:
        Rows and whether the file used legacy bare-array encoding.

    Raises:
        ValueError: If JSON is invalid or shape is wrong.
        OSError: If reading fails (excluding missing file).
    """
    assert_safe_filesystem_path(path)
    if not path.is_file():
        return [], False
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return [], False
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON in primary output file: {exc}"
        raise ValueError(msg) from exc
    return parse_primary_json_payload(data)


def build_primary_document(
    rows: list[dict[str, Any]],
    *,
    last_completed: tuple[str, str] | None,
) -> dict[str, Any]:
    """Build the on-disk wrapper document for resumable runs.

    Args:
        rows: All mapping rows written so far.
        last_completed: Last successfully processed repository, if any.
    """
    doc: dict[str, Any] = {
        "version": PRIMARY_FORMAT_VERSION,
        "rows": rows,
    }
    if last_completed is not None:
        doc["checkpoint"] = {
            "project_key": last_completed[0],
            "repo_slug": last_completed[1],
        }
    return doc


def atomic_write_json(path: Path, payload: Any) -> None:
    """Atomically write JSON to ``path`` using a temporary file in the same directory."""
    assert_safe_filesystem_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        Path(tmp_name).replace(path)
    except BaseException:
        try:
            Path(tmp_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise
