"""Tests for per-repository APM map derivation."""

from __future__ import annotations

from snyk.project_context import repo_apm_map_from_rows


def test_repo_apm_map_single_project_same_code() -> None:
    rows = [
        {"repository_path": "P1/a", "apm_code": "A1"},
        {"repository_path": "P1/b", "apm_code": "A1"},
    ]
    assert repo_apm_map_from_rows(rows) == {("P1", "a"): "A1", ("P1", "b"): "A1"}


def test_repo_apm_map_multi_apm_same_project() -> None:
    rows = [
        {"repository_path": "ACCP/accelerator", "apm_code": "ABCD"},
        {"repository_path": "ACCP/accelerator-build-engine", "apm_code": "ABCE"},
        {"repository_path": "ACCP/accelerator-jenkins-scripts", "apm_code": "ABCF"},
    ]
    assert repo_apm_map_from_rows(rows) == {
        ("ACCP", "accelerator"): "ABCD",
        ("ACCP", "accelerator-build-engine"): "ABCE",
        ("ACCP", "accelerator-jenkins-scripts"): "ABCF",
    }


def test_repo_apm_map_skips_null_apm() -> None:
    rows = [
        {"repository_path": "P1/a", "apm_code": None},
        {"repository_path": "P1/b", "apm_code": "A1"},
    ]
    assert repo_apm_map_from_rows(rows) == {("P1", "b"): "A1"}
