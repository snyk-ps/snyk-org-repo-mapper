"""Tests for Stage 4 post-import cleanup."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from commands.snyk_post_import_cleanup_cli import main as cleanup_main
from snyk.integration_settings_defaults import SETTINGS_PROFILE_ID
from snyk.post_import_cleanup import run_post_import_cleanup
from snyk.python_language_settings_defaults import PYTHON_LANGUAGE_VERSION


def test_run_post_import_cleanup_dry_run() -> None:
    client = MagicMock()
    client.group_id = "group-uuid"
    client.iter_group_orgs.return_value = [{"id": "org-1", "name": "APM1"}]
    client.iter_org_projects.side_effect = [
        [{"id": "df-1", "name": "Dockerfile", "type": "dockerfile"}],
        [{"id": "p1", "name": "App", "type": "npm"}],
    ]

    report = run_post_import_cleanup(client, dry_run=True)

    assert report["version"] == 2
    assert report["group_id"] == "group-uuid"
    assert report["settings_profile"] == SETTINGS_PROFILE_ID
    assert report["python_version"] == PYTHON_LANGUAGE_VERSION
    assert report["dockerfile_projects"]["skipped"][0]["reason"] == "dry_run"
    assert report["recurring_test_frequency"]["skipped"][0]["project_id"] == "p1"
    assert report["integration_settings"]["skipped"][0]["reason"] == "dry_run"
    assert report["python_language_settings"]["skipped"][0]["reason"] == "dry_run"
    client.delete_org_project.assert_not_called()
    client.update_project_settings.assert_not_called()
    client.patch_org_language_settings.assert_not_called()


def test_run_post_import_cleanup_applies_changes() -> None:
    client = MagicMock()
    client.group_id = "group-uuid"
    client.iter_group_orgs.return_value = [{"id": "org-1", "name": "APM1"}]
    client.iter_org_projects.side_effect = [
        [{"id": "df-1", "name": "Dockerfile", "type": "dockerfile"}],
        [{"id": "p1", "name": "App", "type": "npm"}],
    ]
    client.iter_org_integrations.return_value = [
        {"id": "int-1", "type": "bitbucket-server"}
    ]

    report = run_post_import_cleanup(client, dry_run=False)

    assert len(report["dockerfile_projects"]["deleted"]) == 1
    assert len(report["recurring_test_frequency"]["updated"]) == 1
    assert report["integration_settings"]["updated"][0]["integration_id"] == "int-1"
    assert len(report["python_language_settings"]["updated"]) == 1
    client.delete_org_project.assert_called_once_with("org-1", "df-1")
    client.update_project_settings.assert_called_once()
    client.patch_org_language_settings.assert_called_once()


def test_run_post_import_cleanup_records_partial_failures() -> None:
    client = MagicMock()
    client.group_id = "group-uuid"
    client.iter_group_orgs.return_value = [{"id": "org-1", "name": "APM1"}]
    client.iter_org_projects.side_effect = [[], [{"id": "p1", "name": "App", "type": "npm"}]]
    client.update_project_settings.side_effect = RuntimeError("unsupported project type")
    client.iter_org_integrations.return_value = []

    report = run_post_import_cleanup(client, dry_run=False)

    assert len(report["recurring_test_frequency"]["failed"]) == 1
    assert len(report["integration_settings"]["failed"]) == 1


def test_run_post_import_cleanup_records_python_language_failure() -> None:
    client = MagicMock()
    client.group_id = "group-uuid"
    client.iter_group_orgs.return_value = [{"id": "org-1", "name": "APM1"}]
    client.iter_org_projects.side_effect = [[], []]
    client.iter_org_integrations.return_value = [
        {"id": "int-1", "type": "bitbucket-server"}
    ]
    client.patch_org_language_settings.side_effect = RuntimeError("forbidden")

    report = run_post_import_cleanup(client, dry_run=False)

    assert len(report["python_language_settings"]["failed"]) == 1
    assert report["python_language_settings"]["failed"][0]["error"] == "forbidden"


def test_cli_rejects_rest_integrations_api(monkeypatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "g")
    monkeypatch.setenv("SNYK_INTEGRATIONS_API", "rest")

    rc = cleanup_main(["--output", "out.json"])
    assert rc == 2


def test_cli_writes_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "group-uuid")
    monkeypatch.setenv("SNYK_INTEGRATIONS_API", "v1")

    out_path = tmp_path / "post-import-cleanup-report.json"
    fake_client = MagicMock()
    fake_client.group_id = "group-uuid"
    fake_client.iter_group_orgs.return_value = [{"id": "org-1", "name": "APM1"}]
    fake_client.iter_org_projects.side_effect = [[], []]
    fake_client.iter_org_integrations.return_value = [
        {"id": "int-1", "type": "bitbucket-server"}
    ]

    with patch(
        "commands.snyk_post_import_cleanup_cli.SnykRestClient",
        return_value=fake_client,
    ):
        rc = cleanup_main(["--output", str(out_path)])

    assert rc == 0
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["group_id"] == "group-uuid"
    assert data["integration_settings"]["updated"][0]["org_id"] == "org-1"
