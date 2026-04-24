"""Tests for primary output file parsing and checkpoint helpers."""

import json
from pathlib import Path

import pytest

from common.output_state import (
    assert_safe_filesystem_path,
    atomic_write_json,
    build_primary_document,
    completed_keys_from_rows,
    load_primary_output_file,
    parse_primary_json_payload,
    row_repo_key,
)


def test_row_repo_key() -> None:
    assert row_repo_key({"repository_path": "PRJ/my-slug"}) == ("PRJ", "my-slug")
    assert row_repo_key({"repository_path": "bad"}) is None


def test_completed_keys_from_rows() -> None:
    rows = [
        {"repository_path": "A/r1"},
        {"repository_path": "B/r2"},
        {"foo": 1},
    ]
    assert completed_keys_from_rows(rows) == {("A", "r1"), ("B", "r2")}


def test_parse_legacy_array() -> None:
    rows, legacy = parse_primary_json_payload(
        [{"apm_code": "X", "repository_path": "P/s", "repository_name": "s"}]
    )
    assert legacy is True
    assert len(rows) == 1


def test_parse_wrapper() -> None:
    rows, legacy = parse_primary_json_payload(
        {"version": 1, "rows": [{"repository_path": "P/s"}]}
    )
    assert legacy is False
    assert len(rows) == 1


def test_load_primary_output_file_missing(tmp_path: Path) -> None:
    rows, legacy = load_primary_output_file(tmp_path / "none.json")
    assert rows == []
    assert legacy is False


def test_assert_safe_filesystem_path_rejects_dotdot() -> None:
    with pytest.raises(ValueError, match=r"\.\."):
        assert_safe_filesystem_path(Path("a/../b"))


def test_atomic_write_json_rejects_dotdot(tmp_path: Path) -> None:
    bad = tmp_path / "nested" / ".." / "x.json"
    with pytest.raises(ValueError, match=r"\.\."):
        atomic_write_json(bad, {"version": 1, "rows": []})


def test_atomic_write_json_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "out.json"
    payload = build_primary_document(
        [{"repository_path": "P/s", "apm_code": "A1"}],
        last_completed=("P", "s"),
    )
    atomic_write_json(path, payload)
    rows, legacy = load_primary_output_file(path)
    assert legacy is False
    assert rows[0]["apm_code"] == "A1"
    text = path.read_text(encoding="utf-8")
    assert "checkpoint" in json.loads(text)


def test_parse_invalid_version() -> None:
    with pytest.raises(ValueError, match="Unsupported primary output version"):
        parse_primary_json_payload({"version": 99, "rows": []})
