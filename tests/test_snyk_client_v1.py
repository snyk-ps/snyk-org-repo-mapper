"""Tests for Snyk v1 integrations normalization and type detection."""

from __future__ import annotations

import pytest

from integrations.snyk.client import (
    normalize_v1_integrations_payload,
    pick_bitbucket_server_integration_id,
)


def test_normalize_v1_integrations_payload_array() -> None:
    raw = [{"id": "a", "type": "bitbucket-server"}]
    assert normalize_v1_integrations_payload(raw) == raw


def test_normalize_v1_integrations_payload_wrapped() -> None:
    raw = {"integrations": [{"id": "b", "type": "github"}]}
    assert normalize_v1_integrations_payload(raw) == [{"id": "b", "type": "github"}]


def test_normalize_v1_integrations_payload_invalid() -> None:
    with pytest.raises(RuntimeError, match="Unexpected v1"):
        normalize_v1_integrations_payload("nope")


def test_pick_bitbucket_server_integration_id_v1_flat() -> None:
    out = pick_bitbucket_server_integration_id(
        [{"id": "int-1", "type": "bitbucket-server"}]
    )
    assert out == "int-1"


def test_pick_bitbucket_server_integration_id_integration_type_camel() -> None:
    out = pick_bitbucket_server_integration_id(
        [{"id": "int-2", "integrationType": "bitbucket-server"}]
    )
    assert out == "int-2"


def test_pick_jsonapi_attributes_preferred_over_resource_type() -> None:
    out = pick_bitbucket_server_integration_id(
        [
            {
                "id": "int-3",
                "type": "integration",
                "attributes": {"integration_type": "bitbucket-server"},
            }
        ]
    )
    assert out == "int-3"
