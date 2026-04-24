"""Tests for AppSec YAML parsing and branch resolution."""

from common.appsec_yaml import (
    parse_appsec_yaml,
    resolve_production_branch,
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
