"""Tests for broker org plan building."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from integrations.snyk.broker_client import BrokerConnection, BrokerConnectionIntegration
from snyk.broker_plan import build_broker_org_plan


def test_round_robin_two_connections_three_orgs() -> None:
    broker = MagicMock()
    broker._settings = MagicMock(tenant_id="t1", install_id="i1")
    broker.list_bitbucket_server_connections.return_value = [
        BrokerConnection("c-b", "d1", "bitbucket-server", None),
        BrokerConnection("c-a", "d1", "bitbucket-server", None),
    ]
    broker.list_connection_integrations.return_value = []

    orgs_doc = {
        "orgs": [
            {"name": "O1", "groupId": "g", "sourceOrgId": "s"},
            {"name": "O2", "groupId": "g", "sourceOrgId": "s"},
            {"name": "O3", "groupId": "g", "sourceOrgId": "s"},
        ]
    }
    plan = build_broker_org_plan(orgs_doc=orgs_doc, broker=broker, snyk=None)
    by_org = {a["org_name"]: a["connection_id"] for a in plan["assignments"]}
    assert len(by_org) == 3
    counts: dict[str, int] = {}
    for cid in by_org.values():
        counts[cid] = counts.get(cid, 0) + 1
    assert counts == {"c-a": 2, "c-b": 1}


def test_already_integrated_excluded_from_assignments() -> None:
    broker = MagicMock()
    broker._settings = MagicMock(tenant_id="t1", install_id="i1")
    broker.list_bitbucket_server_connections.return_value = [
        BrokerConnection("c1", "d1", "bitbucket-server", None),
    ]

    def integrations(cid: str) -> list[BrokerConnectionIntegration]:
        if cid == "c1":
            return [BrokerConnectionIntegration(org_id="org-existing", org_name="O1", integration_id="int-1")]
        return []

    broker.list_connection_integrations.side_effect = integrations

    orgs_doc = {"orgs": [{"name": "O1", "groupId": "g", "sourceOrgId": "s"}, {"name": "O2", "groupId": "g", "sourceOrgId": "s"}]}
    snyk = MagicMock()
    snyk.iter_group_orgs.return_value = [
        {"id": "org-existing", "name": "O1"},
        {"id": "org-new", "name": "O2"},
    ]
    plan = build_broker_org_plan(orgs_doc=orgs_doc, broker=broker, snyk=snyk)
    assert len(plan["already_integrated"]) == 1
    assert plan["already_integrated"][0]["org_name"] == "O1"
    assert len(plan["assignments"]) == 1
    assert plan["assignments"][0]["org_name"] == "O2"


def test_accp_style_one_repo_with_apm_sibling_gets_different_assignment() -> None:
    """Same project key: only YAML repo is pre-integrated; sibling is assigned."""
    broker = MagicMock()
    broker._settings = MagicMock(tenant_id="t1", install_id="i1")
    broker.list_bitbucket_server_connections.return_value = [
        BrokerConnection("c1", "d1", "bitbucket-server", None),
    ]

    def integrations(cid: str) -> list[BrokerConnectionIntegration]:
        return [
            BrokerConnectionIntegration(
                org_id="org-abcd",
                org_name="ABCD",
                integration_id="int-1",
            )
        ]

    broker.list_connection_integrations.side_effect = integrations

    orgs_doc = {
        "orgs": [
            {"name": "ABCD", "groupId": "g", "sourceOrgId": "s"},
            {"name": "OTHER", "groupId": "g", "sourceOrgId": "s"},
        ]
    }
    snyk = MagicMock()
    snyk.iter_group_orgs.return_value = [
        {"id": "org-abcd", "name": "ABCD"},
        {"id": "org-other", "name": "OTHER"},
    ]
    plan = build_broker_org_plan(orgs_doc=orgs_doc, broker=broker, snyk=snyk)
    assert len(plan["already_integrated"]) == 1
    assert plan["already_integrated"][0]["org_name"] == "ABCD"
    assert len(plan["assignments"]) == 1
    assert plan["assignments"][0]["org_name"] == "OTHER"
    assert plan["assignments"][0]["org_id"] == "org-other"


def test_no_connections_raises() -> None:
    broker = MagicMock()
    broker._settings = MagicMock(tenant_id="t1", install_id="i1")
    broker.list_bitbucket_server_connections.return_value = []
    with pytest.raises(ValueError, match="No bitbucket-server"):
        build_broker_org_plan(
            orgs_doc={"orgs": [{"name": "X", "groupId": "g", "sourceOrgId": "s"}]},
            broker=broker,
        )
