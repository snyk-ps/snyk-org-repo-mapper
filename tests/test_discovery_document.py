"""Tests for discovery JSON helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.discovery_document import (
    DISCOVERY_FORMAT_VERSION,
    build_discovery_document,
    load_resume_rows,
    load_rows_from_stage1_file,
    parse_discovery_payload,
)


def test_build_and_parse_discovery() -> None:
    rows = [{"repository_path": "A/b", "apm_code": "X"}]
    doc = build_discovery_document(rows, "bitbucket", last_completed=("A", "b"))
    assert doc["version"] == DISCOVERY_FORMAT_VERSION
    assert doc["source"] == "bitbucket"
    r, src, ck = parse_discovery_payload(doc)
    assert r == rows
    assert src == "bitbucket"
    assert ck == ("A", "b")


def test_load_rows_legacy_primary_wrapper(tmp_path: Path) -> None:
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps({"version": 1, "rows": [{"repository_path": "P/r", "apm_code": "Z"}]}),
        encoding="utf-8",
    )
    rows, src = load_rows_from_stage1_file(p)
    assert src == "bitbucket"
    assert rows[0]["apm_code"] == "Z"


def test_load_resume_rows_legacy(tmp_path: Path) -> None:
    p = tmp_path / "m.json"
    p.write_text(json.dumps([{"repository_path": "P/r", "apm_code": "Q"}]), encoding="utf-8")
    rows = load_resume_rows(p)
    assert len(rows) == 1


def test_parse_rejects_unknown_version() -> None:
    with pytest.raises(ValueError, match="Unsupported discovery"):
        parse_discovery_payload({"version": 99, "source": "bitbucket", "rows": []})
