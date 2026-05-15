"""Tests for broker settings loading."""

from __future__ import annotations

import pytest

from config.snyk_settings import load_broker_settings


def test_load_broker_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "tok")
    monkeypatch.setenv("SNYK_TENANT_ID", "tenant-1")
    monkeypatch.setenv("SNYK_BROKER_INSTALL_ID", "install-1")
    s = load_broker_settings()
    assert s.tenant_id == "tenant-1"
    assert s.install_id == "install-1"
    assert s.rest_root.endswith("/rest")


def test_load_broker_settings_cli_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "tok")
    monkeypatch.setenv("SNYK_TENANT_ID", "env-tenant")
    monkeypatch.setenv("SNYK_BROKER_INSTALL_ID", "env-install")
    s = load_broker_settings(tenant_id="cli-tenant", install_id="cli-install")
    assert s.tenant_id == "cli-tenant"
    assert s.install_id == "cli-install"
