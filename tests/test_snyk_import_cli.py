"""Tests for snyk-import CLI (Stage 3) with mocked Snyk API."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from commands.snyk_import_cli import main as snyk_import_main


def test_snyk_import_writes_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "g")

    discovery = tmp_path / "d.json"
    discovery.write_text(
        json.dumps(
            {
                "version": 1,
                "source": "spreadsheet",
                "rows": [
                    {
                        "apm_code": "APM1",
                        "repository_path": "P1/r",
                        "repository_name": "r",
                        "production_branch": "",
                        "bitbucket_project_name": "P1",
                    }
                ],
                "checkpoint": None,
            }
        ),
        encoding="utf-8",
    )
    orgs = tmp_path / "orgs.json"
    orgs.write_text(
        json.dumps({"orgs": [{"name": "APM1", "groupId": "x", "sourceOrgId": "y"}]}),
        encoding="utf-8",
    )
    out_imp = tmp_path / "imp.json"

    fake_client = MagicMock()
    fake_client.iter_group_orgs.return_value = [{"id": "org-uuid", "name": "APM1"}]
    fake_client.iter_org_integrations.return_value = [
        {
            "id": "int-uuid",
            "type": "bitbucket-server",
            "attributes": {"integration_type": "bitbucket-server"},
        }
    ]

    with patch("commands.snyk_import_cli.SnykRestClient", return_value=fake_client):
        rc = snyk_import_main(
            [
                "--discovery",
                str(discovery),
                "--snyk-orgs",
                str(orgs),
                "--output",
                str(out_imp),
            ]
        )
    assert rc == 0
    data = json.loads(out_imp.read_text(encoding="utf-8"))
    assert data["targets"][0]["orgId"] == "org-uuid"
    assert data["targets"][0]["integrationId"] == "int-uuid"


def test_snyk_import_default_org_for_null_apm_project(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "g")

    discovery = tmp_path / "d.json"
    discovery.write_text(
        json.dumps(
            {
                "version": 1,
                "source": "bitbucket",
                "rows": [
                    {
                        "apm_code": None,
                        "repository_path": "NOPM/r1",
                        "repository_name": "r1",
                        "production_branch": "",
                        "bitbucket_project_name": "NOPM",
                    }
                ],
                "checkpoint": None,
            }
        ),
        encoding="utf-8",
    )
    out_imp = tmp_path / "imp.json"

    fake_client = MagicMock()
    fake_client.iter_group_orgs.return_value = [{"id": "default-org-id", "name": "Any"}]
    fake_client.iter_org_integrations.return_value = [
        {
            "id": "int-default",
            "type": "bitbucket-server",
            "attributes": {"integration_type": "bitbucket-server"},
        }
    ]

    with patch("commands.snyk_import_cli.SnykRestClient", return_value=fake_client):
        rc = snyk_import_main(
            [
                "--discovery",
                str(discovery),
                "--output",
                str(out_imp),
                "--default-org-id",
                "default-org-id",
            ]
        )
    assert rc == 0
    data = json.loads(out_imp.read_text(encoding="utf-8"))
    assert data["targets"][0]["orgId"] == "default-org-id"
    assert data["targets"][0]["integrationId"] == "int-default"
    assert data["targets"][0]["target"]["name"] == "NOPM/r1"


def test_snyk_import_rejects_default_org_not_in_group(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "g")

    discovery = tmp_path / "d.json"
    discovery.write_text(
        json.dumps(
            {
                "version": 1,
                "source": "bitbucket",
                "rows": [
                    {
                        "apm_code": None,
                        "repository_path": "NOPM/r1",
                        "repository_name": "r1",
                        "production_branch": "",
                        "bitbucket_project_name": "NOPM",
                    }
                ],
                "checkpoint": None,
            }
        ),
        encoding="utf-8",
    )
    out_imp = tmp_path / "imp.json"

    fake_client = MagicMock()
    fake_client.iter_group_orgs.return_value = [{"id": "other-id", "name": "X"}]

    with patch("commands.snyk_import_cli.SnykRestClient", return_value=fake_client):
        rc = snyk_import_main(
            [
                "--discovery",
                str(discovery),
                "--output",
                str(out_imp),
                "--default-org-id",
                "missing-id",
            ]
        )
    assert rc == 1


def test_snyk_import_raises_when_null_apm_and_no_default_org(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("SNYK_GROUP_ID", "g")

    discovery = tmp_path / "d.json"
    discovery.write_text(
        json.dumps(
            {
                "version": 1,
                "source": "bitbucket",
                "rows": [
                    {
                        "apm_code": None,
                        "repository_path": "NOPM/r1",
                        "repository_name": "r1",
                        "production_branch": "",
                        "bitbucket_project_name": "NOPM",
                    }
                ],
                "checkpoint": None,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="No apm_code"):
        snyk_import_main(
            [
                "--discovery",
                str(discovery),
                "--output",
                str(tmp_path / "out.json"),
            ]
        )
