"""Stage 1 discovery JSON: versioned artifact for Stages 2 and 3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from common.output_state import assert_safe_filesystem_path, parse_primary_json_payload


DISCOVERY_FORMAT_VERSION = 1

DiscoverySource = Literal["bitbucket", "spreadsheet"]

ALLOWED_SOURCES: frozenset[str] = frozenset({"bitbucket", "spreadsheet"})


def build_discovery_document(
    rows: list[dict[str, Any]],
    source: DiscoverySource,
    *,
    last_completed: tuple[str, str] | None,
) -> dict[str, Any]:
    """Build on-disk discovery JSON (Stage 1 output)."""
    doc: dict[str, Any] = {
        "version": DISCOVERY_FORMAT_VERSION,
        "source": source,
        "rows": rows,
    }
    if last_completed is not None:
        doc["checkpoint"] = {
            "project_key": last_completed[0],
            "repo_slug": last_completed[1],
        }
    else:
        doc["checkpoint"] = None
    return doc


def _checkpoint_tuple(data: dict[str, Any]) -> tuple[str, str] | None:
    ck = data.get("checkpoint")
    if ck is None or ck is False:
        return None
    if not isinstance(ck, dict):
        return None
    pk = ck.get("project_key")
    sl = ck.get("repo_slug")
    if isinstance(pk, str) and isinstance(sl, str):
        return pk, sl
    return None


def parse_discovery_payload(data: Any) -> tuple[list[dict[str, Any]], str, tuple[str, str] | None]:
    """Parse discovery JSON object.

    Returns:
        Tuple of ``rows``, ``source``, and optional checkpoint ``(project_key, repo_slug)``.

    Raises:
        ValueError: If structure or version is invalid.
    """
    if not isinstance(data, dict):
        msg = "Discovery document must be a JSON object"
        raise ValueError(msg)
    version = data.get("version")
    if version != DISCOVERY_FORMAT_VERSION:
        msg = f"Unsupported discovery version: {version!r}"
        raise ValueError(msg)
    source = data.get("source")
    if not isinstance(source, str) or source not in ALLOWED_SOURCES:
        msg = f"Discovery document must set 'source' to one of {sorted(ALLOWED_SOURCES)}"
        raise ValueError(msg)
    raw_rows = data.get("rows")
    if not isinstance(raw_rows, list):
        msg = "Discovery document must contain a 'rows' array"
        raise ValueError(msg)
    rows: list[dict[str, Any]] = []
    for item in raw_rows:
        if isinstance(item, dict):
            rows.append(item)
    return rows, source, _checkpoint_tuple(data)


def load_resume_rows(path: Path) -> list[dict[str, Any]]:
    """Load rows from a discovery file or legacy primary mapping for Bitbucket resume.

    Returns an empty list if the path is missing or empty.
    """
    assert_safe_filesystem_path(path)
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON in discovery file: {exc}"
        raise ValueError(msg) from exc

    if isinstance(data, dict) and data.get("source") in ALLOWED_SOURCES and data.get("version") == DISCOVERY_FORMAT_VERSION:
        rows, _src, _ck = parse_discovery_payload(data)
        return rows

    rows, _legacy = parse_primary_json_payload(data)
    return rows


def load_rows_from_stage1_file(path: Path) -> tuple[list[dict[str, Any]], str]:
    """Load mapping rows from a Stage 1 discovery file or legacy primary mapping.

    Legacy formats (no ``source``): treated as ``bitbucket`` for row compatibility.

    Raises:
        ValueError: If the file is missing or JSON is invalid.
    """
    assert_safe_filesystem_path(path)
    if not path.is_file():
        msg = f"Discovery file not found: {path}"
        raise ValueError(msg)
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return [], "bitbucket"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON in discovery file: {exc}"
        raise ValueError(msg) from exc

    if isinstance(data, dict) and data.get("source") in ALLOWED_SOURCES and data.get("version") == DISCOVERY_FORMAT_VERSION:
        rows, source, _ck = parse_discovery_payload(data)
        return rows, source

    rows, _legacy = parse_primary_json_payload(data)
    return rows, "bitbucket"
