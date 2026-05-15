"""HTTP tests for Universal Broker client (mocked urlopen)."""

from __future__ import annotations

import json
from http.client import RemoteDisconnected
from io import BytesIO
from unittest.mock import patch

from config.snyk_settings import BrokerSettings
from integrations.snyk.broker_client import BrokerClient


def _broker_settings() -> BrokerSettings:
    return BrokerSettings(
        token="tok",
        api_origin="https://api.snyk.io",
        rest_root="https://api.snyk.io/rest",
        api_version="2024-10-15",
        tenant_id="tenant-1",
        install_id="install-1",
        group_id=None,
        http_max_attempts=3,
        http_backoff_seconds=0.0,
    )


def test_list_deployments_retries_then_succeeds() -> None:
    payload = {
        "data": [{"id": "dep-1", "type": "deployment", "attributes": {}}],
        "links": {},
    }
    body = json.dumps(payload).encode("utf-8")
    calls: list[int] = []

    def fake_urlopen(req: object, timeout: float | None = None) -> object:
        calls.append(1)
        if len(calls) == 1:
            raise RemoteDisconnected("closed")
        return BytesIO(body)

    with patch("integrations.snyk.broker_client.urlopen", side_effect=fake_urlopen):
        client = BrokerClient(_broker_settings())
        items = client._iter_paginated_data(  # noqa: SLF001
            "https://api.snyk.io/rest/tenants/t/brokers/installs/i/deployments?version=2024-10-15"
        )
    assert len(items) == 1
    assert items[0]["id"] == "dep-1"
    assert len(calls) == 2


def test_create_org_integration_post() -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: float | None = None) -> object:
        captured["method"] = getattr(req, "method", None)
        captured["data"] = getattr(req, "data", None)
        return BytesIO(b"{}")

    with patch("integrations.snyk.broker_client.urlopen", side_effect=fake_urlopen):
        client = BrokerClient(_broker_settings())
        client.create_org_integration("conn-1", "org-1")

    assert captured["method"] == "POST"
    assert captured["data"] == b"{}"
