"""Tests for Snyk org language settings REST PATCH used by Stage 4."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch

from config.snyk_settings import SnykSettings
from integrations.snyk.client import SnykRestClient
from snyk.python_language_settings_defaults import (
    PYTHON_LANGUAGE,
    PYTHON_LANGUAGE_VERSION,
    build_python_org_language_settings_payload,
)


def _settings() -> SnykSettings:
    return SnykSettings(
        token="t",
        group_id="group-uuid",
        api_origin="https://api.snyk.io",
        rest_root="https://api.snyk.io/rest",
        v1_root="https://api.snyk.io/v1",
        integrations_api="v1",
        api_version="2024-10-15",
        http_max_attempts=1,
        http_backoff_seconds=0.0,
    )


def test_build_python_org_language_settings_payload() -> None:
    payload = build_python_org_language_settings_payload("org-uuid")
    assert payload == {
        "data": {
            "type": "language_settings",
            "id": "org-uuid",
            "attributes": {
                "package_managers": {
                    "pip": {
                        "python_version": PYTHON_LANGUAGE_VERSION,
                    },
                },
            },
        },
    }


def test_patch_org_language_settings() -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: float | None = None) -> object:
        captured["method"] = getattr(req, "method", None)
        captured["url"] = getattr(req, "full_url", None)
        captured["headers"] = dict(getattr(req, "header_items", lambda: [])())
        captured["data"] = getattr(req, "data", None)
        return BytesIO(b"{}")

    payload = build_python_org_language_settings_payload("org-uuid")
    client = SnykRestClient(_settings())
    with patch("integrations.snyk.client.urlopen", side_effect=fake_urlopen):
        client.patch_org_language_settings("org-uuid", PYTHON_LANGUAGE, payload)

    assert captured["method"] == "PATCH"
    assert captured["url"] == (
        "https://api.snyk.io/rest/orgs/org-uuid/settings/open_source/languages/python"
        "?version=2024-10-15"
    )
    headers = captured["headers"]
    assert headers["Accept"] == "application/vnd.api+json"
    assert headers["Content-type"] == "application/vnd.api+json"
    assert json.loads(captured["data"]) == payload
