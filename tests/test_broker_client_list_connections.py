"""Tests for BrokerClient.list_bitbucket_server_connections."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from config.snyk_settings import BrokerSettings
from integrations.snyk.broker_client import BrokerClient


def _settings() -> BrokerSettings:
    return BrokerSettings(
        token="t",
        api_origin="https://api.example.com",
        rest_root="https://api.example.com/rest",
        api_version="2024-10-15",
        tenant_id="tenant-1",
        install_id="install-1",
        group_id=None,
        http_max_attempts=1,
        http_backoff_seconds=0.1,
    )


def test_list_bitbucket_server_connections_parses_integration_type_camel() -> None:
    client = BrokerClient(_settings())

    def fake_iter(url: str) -> list[dict]:
        if "/deployments?" in url:
            return [{"id": "dep-1"}]
        if "/connections?" in url:
            return [
                {
                    "id": "conn-1",
                    "type": "connection",
                    "attributes": {"integrationType": "bitbucket-server", "name": "BB"},
                }
            ]
        return []

    with patch.object(client, "_iter_paginated_data", side_effect=fake_iter):
        conns = client.list_bitbucket_server_connections()
    assert len(conns) == 1
    assert conns[0].connection_id == "conn-1"
    assert conns[0].connection_type == "bitbucket-server"


def test_list_bitbucket_server_connections_raises_when_types_unrecognized() -> None:
    client = BrokerClient(_settings())

    def fake_iter(url: str) -> list[dict]:
        if "/deployments?" in url:
            return [{"id": "dep-1"}]
        if "/connections?" in url:
            return [
                {
                    "id": "conn-1",
                    "type": "connection",
                    "attributes": {"integrationType": "github"},
                }
            ]
        return []

    with patch.object(client, "_iter_paginated_data", side_effect=fake_iter):
        with pytest.raises(ValueError, match="Found 1 broker connection"):
            client.list_bitbucket_server_connections()
