"""Tests for broker client normalization helpers."""

from __future__ import annotations

from integrations.snyk.broker_client import _connection_type_slug, _org_refs_from_integration_item


def test_connection_type_from_attributes() -> None:
    item = {"id": "c1", "type": "connection", "attributes": {"type": "bitbucket-server"}}
    assert _connection_type_slug(item) == "bitbucket-server"


def test_org_refs_from_attributes() -> None:
    item = {
        "id": "int-1",
        "attributes": {"org_id": "org-uuid", "org_name": "APM1"},
    }
    oid, oname = _org_refs_from_integration_item(item)
    assert oid == "org-uuid"
    assert oname == "APM1"
