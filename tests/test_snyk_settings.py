"""Tests for Snyk settings loading (SNYK_API, legacy SNYK_API_BASE)."""

from __future__ import annotations

import pytest

from config.snyk_settings import load_snyk_settings


def test_load_snyk_settings_default_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "g")
    monkeypatch.delenv("SNYK_API", raising=False)
    monkeypatch.delenv("SNYK_API_BASE", raising=False)
    s = load_snyk_settings()
    assert s.api_origin == "https://api.snyk.io"
    assert s.rest_root == "https://api.snyk.io/rest"
    assert s.v1_root == "https://api.snyk.io/v1"
    assert s.integrations_api == "v1"


def test_load_snyk_settings_legacy_api_base_strips_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "g")
    monkeypatch.delenv("SNYK_API", raising=False)
    monkeypatch.setenv("SNYK_API_BASE", "https://api.snyk.io/rest")
    s = load_snyk_settings()
    assert s.api_origin == "https://api.snyk.io"
    assert s.rest_root == "https://api.snyk.io/rest"


def test_load_snyk_settings_snyk_api_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "g")
    monkeypatch.setenv("SNYK_API", "https://custom.example")
    monkeypatch.setenv("SNYK_API_BASE", "https://wrong.example/rest")
    s = load_snyk_settings()
    assert s.api_origin == "https://custom.example"
    assert s.rest_root == "https://custom.example/rest"
    assert s.v1_root == "https://custom.example/v1"


def test_load_snyk_settings_integrations_api_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "g")
    monkeypatch.setenv("SNYK_INTEGRATIONS_API", "rest")
    s = load_snyk_settings()
    assert s.integrations_api == "rest"


def test_load_snyk_settings_invalid_integrations_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "g")
    monkeypatch.setenv("SNYK_INTEGRATIONS_API", "graphql")
    with pytest.raises(ValueError, match="SNYK_INTEGRATIONS_API"):
        load_snyk_settings()
