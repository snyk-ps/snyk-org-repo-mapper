"""Tests for Stage 2.3 broker integration settings."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from commands.snyk_broker_integration_settings_cli import main as settings_main
from snyk.broker_integration_settings import apply_integration_settings, load_broker_apply_report
from snyk.integration_settings_defaults import BITBUCKET_SERVER_INTEGRATION_SETTINGS


def test_load_broker_apply_report_rejects_bad_version(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    path.write_text(json.dumps({"version": 99, "applied": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported broker apply report"):
        load_broker_apply_report(path)


def test_apply_integration_settings_success_and_failure() -> None:
    apply_report = {
        "version": 1,
        "applied": [
            {
                "org_name": "O1",
                "org_id": "org-1",
                "connection_id": "c1",
                "status": "created",
            },
            {
                "org_name": "O2",
                "org_id": "org-2",
                "connection_id": "c1",
                "status": "created",
            },
        ],
    }
    client = MagicMock()
    client.iter_org_integrations.side_effect = [
        [{"id": "int-1", "type": "bitbucket-server"}],
        [],
    ]

    report = apply_integration_settings(
        apply_report,
        client=client,
        source_report_path="apply.json",
        dry_run=False,
    )
    assert len(report["updated"]) == 1
    assert report["updated"][0]["integration_id"] == "int-1"
    assert len(report["failed"]) == 1
    client.update_org_integration_settings.assert_called_once_with(
        "org-1",
        "int-1",
        BITBUCKET_SERVER_INTEGRATION_SETTINGS,
    )


def test_apply_integration_settings_dry_run() -> None:
    apply_report = {
        "version": 1,
        "applied": [{"org_name": "O1", "org_id": "org-1", "status": "created"}],
    }
    client = MagicMock()
    report = apply_integration_settings(
        apply_report,
        client=client,
        source_report_path="apply.json",
        dry_run=True,
    )
    assert report["skipped"][0]["reason"] == "dry_run"
    client.iter_org_integrations.assert_not_called()


def test_cli_rejects_rest_integrations_api(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "g")
    monkeypatch.setenv("SNYK_INTEGRATIONS_API", "rest")

    report_path = tmp_path / "apply.json"
    report_path.write_text(
        json.dumps({"version": 1, "applied": [], "skipped": [], "failed": []}),
        encoding="utf-8",
    )
    rc = settings_main(
        [
            "--report",
            str(report_path),
            "--output",
            str(tmp_path / "out.json"),
        ]
    )
    assert rc == 2


def test_cli_writes_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "g")
    monkeypatch.setenv("SNYK_INTEGRATIONS_API", "v1")

    apply_path = tmp_path / "apply.json"
    apply_path.write_text(
        json.dumps(
            {
                "version": 1,
                "applied": [
                    {
                        "org_name": "APM1",
                        "org_id": "org-uuid",
                        "connection_id": "c1",
                        "status": "created",
                    }
                ],
                "skipped": [],
                "failed": [],
            }
        ),
        encoding="utf-8",
    )
    out_path = tmp_path / "settings-report.json"

    fake_client = MagicMock()
    fake_client.iter_org_integrations.return_value = [
        {"id": "int-uuid", "type": "bitbucket-server"}
    ]

    with patch(
        "commands.snyk_broker_integration_settings_cli.SnykRestClient",
        return_value=fake_client,
    ):
        rc = settings_main(
            [
                "--report",
                str(apply_path),
                "--output",
                str(out_path),
            ]
        )
    assert rc == 0
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["updated"][0]["org_id"] == "org-uuid"
    fake_client.update_org_integration_settings.assert_called_once()
