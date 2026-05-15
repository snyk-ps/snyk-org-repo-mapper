"""Integration tests for snyk-broker-plan CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from commands.snyk_broker_plan_cli import main as broker_plan_main


def test_broker_plan_cli_writes_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_TENANT_ID", "tenant-1")
    monkeypatch.setenv("SNYK_BROKER_INSTALL_ID", "install-1")

    orgs = tmp_path / "orgs.json"
    orgs.write_text(
        json.dumps({"orgs": [{"name": "APM1", "groupId": "g", "sourceOrgId": "s"}]}),
        encoding="utf-8",
    )
    out = tmp_path / "plan.json"

    fake_plan = {
        "version": 1,
        "tenant_id": "tenant-1",
        "install_id": "install-1",
        "connections": [],
        "already_integrated": [],
        "assignments": [{"org_name": "APM1", "org_id": None, "connection_id": "c1"}],
        "unassigned": [],
        "warnings": [],
    }

    with patch("commands.snyk_broker_plan_cli.build_broker_org_plan", return_value=fake_plan):
        rc = broker_plan_main(["--snyk-orgs", str(orgs), "--output", str(out)])

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert len(data["assignments"]) == 1


def test_broker_plan_cli_no_connections_returns_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_TENANT_ID", "tenant-1")
    monkeypatch.setenv("SNYK_BROKER_INSTALL_ID", "install-1")

    orgs = tmp_path / "orgs.json"
    orgs.write_text(
        json.dumps({"orgs": [{"name": "APM1", "groupId": "g", "sourceOrgId": "s"}]}),
        encoding="utf-8",
    )

    with patch(
        "commands.snyk_broker_plan_cli.build_broker_org_plan",
        side_effect=ValueError("No bitbucket-server broker connections"),
    ):
        rc = broker_plan_main(["--snyk-orgs", str(orgs), "--output", str(tmp_path / "p.json")])

    assert rc == 1
