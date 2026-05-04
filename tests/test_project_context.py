"""Tests for snyk-project-context derivation."""

from __future__ import annotations

import pytest

from snyk.project_context import (
    PROJECT_CONTEXT_FORMAT_VERSION,
    build_project_context_document,
    parse_project_context_document,
    project_apm_map_from_rows,
)


def test_project_apm_map_single_project() -> None:
    rows = [
        {"repository_path": "P1/a", "apm_code": "A1"},
        {"repository_path": "P1/b", "apm_code": "A1"},
    ]
    assert project_apm_map_from_rows(rows) == {"P1": "A1"}


def test_project_apm_map_conflict() -> None:
    rows = [
        {"repository_path": "P1/a", "apm_code": "X"},
        {"repository_path": "P1/b", "apm_code": "Y"},
    ]
    with pytest.raises(ValueError, match="Conflicting apm_code"):
        project_apm_map_from_rows(rows)


def test_build_and_parse_roundtrip() -> None:
    rows = [{"repository_path": "Z/r", "apm_code": "CODE"}]
    doc = build_project_context_document(rows)
    assert doc["version"] == PROJECT_CONTEXT_FORMAT_VERSION
    assert parse_project_context_document(doc) == {"Z": "CODE"}


def test_parse_rejects_bad_version() -> None:
    with pytest.raises(ValueError, match="Unsupported project context"):
        parse_project_context_document({"version": 99, "projects": {}})
