"""Tests for broker org plan apply."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from integrations.snyk.broker_client import BrokerIntegrationConflictError
from snyk.broker_apply import apply_broker_org_plan


def _minimal_plan() -> dict:
    return {
        "version": 1,
        "tenant_id": "t1",
        "install_id": "i1",
        "connections": [],
        "already_integrated": [
            {"org_name": "O1", "org_id": "org-1", "connection_id": "c1"},
        ],
        "assignments": [
            {"org_name": "O2", "org_id": "org-2", "connection_id": "c1"},
            {"org_name": "O3", "org_id": None, "connection_id": "c1"},
        ],
        "unassigned": [],
        "warnings": [],
    }


def test_apply_skips_already_integrated_and_posts_new() -> None:
    broker = MagicMock()
    broker.list_connection_integrations.return_value = []
    plan = _minimal_plan()
    report = apply_broker_org_plan(plan, broker=broker, snyk=None, dry_run=False)
    assert not any(a["org_name"] == "O1" for a in report["applied"])
    broker.create_org_integration.assert_called_once_with("c1", "org-2")
    assert len(report["failed"]) == 1
    assert report["failed"][0]["org_name"] == "O3"


def test_apply_dry_run_no_post() -> None:
    broker = MagicMock()
    plan = {
        "version": 1,
        "tenant_id": "t1",
        "install_id": "i1",
        "connections": [],
        "already_integrated": [],
        "assignments": [{"org_name": "O2", "org_id": "org-2", "connection_id": "c1"}],
        "unassigned": [],
        "warnings": [],
    }
    report = apply_broker_org_plan(plan, broker=broker, snyk=None, dry_run=True)
    broker.create_org_integration.assert_not_called()
    assert report["applied"][0]["status"] == "dry_run"


def test_apply_conflict_treated_as_skip() -> None:
    broker = MagicMock()
    broker.list_connection_integrations.return_value = []
    broker.create_org_integration.side_effect = BrokerIntegrationConflictError("conflict")
    plan = {
        "version": 1,
        "tenant_id": "t1",
        "install_id": "i1",
        "connections": [],
        "already_integrated": [],
        "assignments": [{"org_name": "O2", "org_id": "org-2", "connection_id": "c1"}],
        "unassigned": [],
        "warnings": [],
    }
    report = apply_broker_org_plan(plan, broker=broker, snyk=None, dry_run=False)
    assert len(report["skipped"]) == 1
    assert report["skipped"][0]["reason"] == "already_integrated"
