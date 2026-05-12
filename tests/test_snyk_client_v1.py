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


def test_normalize_v1_integrations_payload_type_to_id_map() -> None:
    bb = "5ca7813c-174e-4710-a767-de1160e32414"
    gh = "b71dcf23-49f0-4f72-948e-5bdc118da005"
    raw = {"bitbucket-server": bb, "github": gh}
    assert normalize_v1_integrations_payload(raw) == [
        {"id": bb, "type": "bitbucket-server"},
        {"id": gh, "type": "github"},
    ]


def test_normalize_v1_integrations_payload_type_to_id_map_realistic_slugs() -> None:
    """v1 map shape with multi-segment slugs (e.g. github-cloud-app) and short names (api, cli)."""
    raw = {
        "github-cloud-app": "3ffe13f9-b06e-4000-882e-711ef087687a",
        "api": "96421b8b-8fff-4c06-849e-d81ee1578090",
        "github": "f950f590-3c1a-490a-aeac-4cb638b021d6",
        "bitbucket-cloud": "d51015e4-eca1-4d9b-bd3e-7e6f956ab9e6",
        "cli": "2069136b-5131-4ed6-bac6-c049661c5679",
        "gitlab": "1c84a9c0-cdc0-4a65-b75c-f24fe8837bfc",
    }
    assert normalize_v1_integrations_payload(raw) == [
        {"id": "3ffe13f9-b06e-4000-882e-711ef087687a", "type": "github-cloud-app"},
        {"id": "96421b8b-8fff-4c06-849e-d81ee1578090", "type": "api"},
        {"id": "f950f590-3c1a-490a-aeac-4cb638b021d6", "type": "github"},
        {"id": "d51015e4-eca1-4d9b-bd3e-7e6f956ab9e6", "type": "bitbucket-cloud"},
        {"id": "2069136b-5131-4ed6-bac6-c049661c5679", "type": "cli"},
        {"id": "1c84a9c0-cdc0-4a65-b75c-f24fe8837bfc", "type": "gitlab"},
    ]


def test_normalize_v1_integrations_payload_type_to_id_map_requires_uuid_values() -> None:
    with pytest.raises(RuntimeError, match="Unexpected v1"):
        normalize_v1_integrations_payload({"bitbucket-server": "not-a-uuid"})


def test_normalize_v1_integrations_payload_rejects_error_like_dicts() -> None:
    with pytest.raises(RuntimeError, match="Unexpected v1"):
        normalize_v1_integrations_payload({"message": "not found"})


def test_normalize_v1_integrations_payload_empty_object() -> None:
    with pytest.raises(RuntimeError, match="Unexpected v1"):
        normalize_v1_integrations_payload({})


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
