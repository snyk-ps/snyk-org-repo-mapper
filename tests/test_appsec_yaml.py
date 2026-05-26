"""Tests for AppSec YAML parsing and branch resolution."""

import logging

from common.appsec_yaml import (
    apm_code_matches_convention,
    parse_appsec_yaml,
    resolve_production_branch,
    warn_if_apm_code_unconventional,
)


def test_parse_appsec_yaml_full() -> None:
    text = """
appSec:
  apmCode: ABC1
  productionBranch: develop
"""
    parsed = parse_appsec_yaml(text)
    assert parsed.apm_code == "ABC1"
    assert parsed.production_branch == "develop"


def test_parse_appsec_yaml_optional_branch() -> None:
    text = """
appSec:
  apmCode: XYZ9
"""
    parsed = parse_appsec_yaml(text)
    assert parsed.apm_code == "XYZ9"
    assert parsed.production_branch is None


def test_parse_appsec_yaml_empty_branch_treated_as_missing() -> None:
    text = """
appSec:
  apmCode: ABC1
  productionBranch: ""
"""
    parsed = parse_appsec_yaml(text)
    assert parsed.apm_code == "ABC1"
    assert parsed.production_branch is None


def test_parse_appsec_yaml_invalid_returns_empty() -> None:
    parsed = parse_appsec_yaml("not: [")
    assert parsed.apm_code is None
    assert parsed.production_branch is None


def test_resolve_production_branch_prefers_yaml() -> None:
    assert resolve_production_branch("rel", "main") == "rel"


def test_resolve_production_branch_falls_back_to_default() -> None:
    assert resolve_production_branch(None, "main") == "main"
    assert resolve_production_branch("", "main") == "main"
    assert resolve_production_branch("   ", "stable") == "stable"


def test_apm_code_matches_convention() -> None:
    assert apm_code_matches_convention("ABC1") is True
    assert apm_code_matches_convention("XYZ9") is True
    assert apm_code_matches_convention("A1") is False
    assert apm_code_matches_convention("abc1") is False
    assert apm_code_matches_convention("ABC12") is False
    assert apm_code_matches_convention("AB-1") is False


def test_warn_if_apm_code_unconventional(caplog) -> None:
    with caplog.at_level(logging.WARNING):
        warn_if_apm_code_unconventional("apm1", repository_path="PRJ/repo")
    assert "apm1" in caplog.text
    assert "PRJ/repo" in caplog.text


def test_warn_if_apm_code_unconventional_skips_valid(caplog) -> None:
    with caplog.at_level(logging.WARNING):
        warn_if_apm_code_unconventional("ABC1", repository_path="PRJ/repo")
    assert caplog.text == ""
