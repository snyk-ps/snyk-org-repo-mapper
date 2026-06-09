"""Tests for Snyk v1 integration settings PUT."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch

from config.snyk_settings import SnykSettings
from integrations.snyk.client import SnykRestClient
from snyk.integration_settings_defaults import BITBUCKET_SERVER_INTEGRATION_SETTINGS


def _settings() -> SnykSettings:
    return SnykSettings(
        token="t",
        group_id="g",
        api_origin="https://api.snyk.io",
        rest_root="https://api.snyk.io/rest",
        v1_root="https://api.snyk.io/v1",
        integrations_api="v1",
        api_version="2024-10-15",
        http_max_attempts=1,
        http_backoff_seconds=0.0,
    )


def test_update_org_integration_settings_put() -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: float | None = None) -> object:
        captured["method"] = getattr(req, "method", None)
        captured["url"] = getattr(req, "full_url", None)
        captured["data"] = getattr(req, "data", None)
        return BytesIO(b"{}")

    client = SnykRestClient(_settings())
    with patch("integrations.snyk.client.urlopen", side_effect=fake_urlopen):
        client.update_org_integration_settings(
            "org-uuid",
            "int-uuid",
            BITBUCKET_SERVER_INTEGRATION_SETTINGS,
        )

    assert captured["method"] == "PUT"
    assert captured["url"] == "https://api.snyk.io/v1/org/org-uuid/integrations/int-uuid/settings"
    assert json.loads(captured["data"]) == BITBUCKET_SERVER_INTEGRATION_SETTINGS
