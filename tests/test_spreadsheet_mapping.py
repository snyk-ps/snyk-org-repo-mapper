"""Tests for spreadsheet column mapping into mapper rows."""

from __future__ import annotations

from pathlib import Path

from common.spreadsheet.mapping import (
    mapping_row_from_abd,
    mapping_rows_from_xlsx,
)


def test_bb_row_basic() -> None:
    row = mapping_row_from_abd("ABC", "BB::MYPROJ::my-slug", "Pretty Name")
    assert row == {
        "apm_code": "ABC",
        "repository_path": "MYPROJ/my-slug",
        "repository_name": "Pretty Name",
        "production_branch": "",
        "bitbucket_project_name": "MYPROJ",
    }


def test_pg_row_skipped() -> None:
    assert mapping_row_from_abd("X", "PG::BC3V::creditor-insurance-administration", "y") is None


def test_empty_apm_none() -> None:
    row = mapping_row_from_abd("  ", "BB::P::r", "nm")
    assert row is not None
    assert row["apm_code"] is None


def test_none_apm() -> None:
    row = mapping_row_from_abd(None, "BB::P::slug", "nm")
    assert row["apm_code"] is None


def test_empty_d_fallback_to_slug() -> None:
    row = mapping_row_from_abd("A", "BB::P::fallback-name", "")
    assert row["repository_name"] == "fallback-name"


def test_none_d_fallback_to_slug() -> None:
    row = mapping_row_from_abd("A", "BB::P::sluggy", None)
    assert row["repository_name"] == "sluggy"


def test_malformed_b_wrong_segments() -> None:
    assert mapping_row_from_abd("A", "BB::onlytwo", "D") is None


def test_malformed_b_extra_segments() -> None:
    assert mapping_row_from_abd("A", "BB::x::y::z", "D") is None


def test_empty_b_skipped() -> None:
    assert mapping_row_from_abd("A", "", "D") is None


def test_sample_xlsx_contains_path_and_skips_pg() -> None:
    sample = (
        Path(__file__).resolve().parents[1] / "data" / "AppSec Repo to APM - Sample.xlsx"
    )
    rows = mapping_rows_from_xlsx(sample)
    paths = {r["repository_path"] for r in rows}
    assert "CGITRADE/CONFIG_FILES" in paths
    assert "BC3V/creditor-insurance-administration" not in paths
