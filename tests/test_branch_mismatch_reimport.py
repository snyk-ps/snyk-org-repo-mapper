"""Tests for branch mismatch target reimport."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.snyk_settings import SnykSettings
from integrations.snyk.client import SnykRestClient
from snyk.branch_mismatch_reimport import (
    BranchMismatchReimportOptions,
    DiffEntry,
    build_import_payload,
    import_target_name,
    load_diff_entries,
    run_branch_mismatch_reimport,
    target_branch_reference,
    target_display_name,
    target_integration_id,
    target_project_key_and_slug,
)


def _settings() -> SnykSettings:
    return SnykSettings(
        token="token",
        group_id="group-uuid",
        api_origin="https://api.snyk.io",
        rest_root="https://api.snyk.io/rest",
        v1_root="https://api.snyk.io/v1",
        integrations_api="v1",
        api_version="2024-10-15",
        http_max_attempts=1,
        http_backoff_seconds=0.0,
    )


def _target(
    *,
    target_id: str = "tgt-1",
    display_name: str = "BB/my-service",
    branch: str = "develop",
    project_key: str = "P1",
    repo_slug: str = "my-service",
    integration_id: str = "int-1",
) -> dict[str, object]:
    return {
        "id": target_id,
        "attributes": {
            "display_name": display_name,
            "target_reference": branch,
            "projectKey": project_key,
            "repoSlug": repo_slug,
        },
        "relationships": {
            "integration": {"data": {"id": integration_id}},
        },
    }


def test_load_diff_entries_valid(tmp_path: Path) -> None:
    path = tmp_path / "diff.json"
    path.write_text(
        json.dumps(
            [
                {
                    "apm_code": "ABCD",
                    "repository_name": "BB/foo",
                    "production_branch": "master",
                    "target_reference": "develop",
                }
            ]
        ),
        encoding="utf-8",
    )
    entries = load_diff_entries(path)
    assert len(entries) == 1
    assert entries[0].apm_code == "ABCD"


def test_load_diff_entries_rejects_missing_key(tmp_path: Path) -> None:
    path = tmp_path / "diff.json"
    path.write_text(json.dumps([{"apm_code": "ABCD"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="repository_name"):
        load_diff_entries(path)


def test_target_helpers() -> None:
    target = _target()
    assert target_display_name(target) == "BB/my-service"
    assert target_branch_reference(target) == "develop"
    assert target_integration_id(target) == "int-1"
    assert target_project_key_and_slug(target) == ("P1", "my-service")


def test_import_target_name_normalizes_bb_prefix() -> None:
    assert import_target_name("BB/foo") == "BB/foo"
    assert import_target_name("foo") == "BB/foo"


def test_build_import_payload() -> None:
    payload = build_import_payload(
        org_id="org-1",
        integration_id="int-1",
        project_key="P1",
        repo_slug="my-service",
        repository_name="BB/my-service",
        production_branch="master",
    )
    assert payload["target"]["branch"] == "master"
    assert payload["target"]["name"] == "BB/my-service"


def test_run_branch_mismatch_reimport_dry_run() -> None:
    entry = DiffEntry(
        apm_code="ORG1",
        repository_name="BB/my-service",
        production_branch="master",
        target_reference="develop",
    )
    client = MagicMock(spec=SnykRestClient)
    client.group_id = "group-uuid"
    client.iter_group_orgs.return_value = [{"id": "org-1", "name": "ORG1"}]
    client.iter_org_targets.return_value = [_target()]

    report = run_branch_mismatch_reimport(
        client,
        [entry],
        BranchMismatchReimportOptions(dry_run=True),
    )

    assert report["skipped"][0]["reason"] == "dry_run"
    client.delete_org_target.assert_not_called()


def test_run_branch_mismatch_reimport_delete_and_import(tmp_path: Path) -> None:
    entry = DiffEntry(
        apm_code="ORG1",
        repository_name="BB/my-service",
        production_branch="master",
        target_reference="develop",
    )
    client = MagicMock(spec=SnykRestClient)
    client.group_id = "group-uuid"
    client.token = "token"
    client.iter_group_orgs.return_value = [{"id": "org-1", "name": "ORG1"}]
    client.iter_org_targets.return_value = [_target()]
    client.get_org_target.return_value = _target()

    def fake_import(cmd: str, batch_file: Path, *, token: str, cwd: Path | None) -> subprocess.CompletedProcess[str]:
        assert token == "token"
        assert batch_file.exists()
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    with patch("snyk.branch_mismatch_reimport.check_snyk_api_import_available"):
        report = run_branch_mismatch_reimport(
            client,
            [entry],
            BranchMismatchReimportOptions(
                import_batch_dir=tmp_path,
                repos_per_batch=10,
            ),
            import_runner=fake_import,
        )

    assert len(report["deleted"]) == 1
    assert len(report["reimported"]) == 1
    client.delete_org_target.assert_called_once_with("org-1", "tgt-1")


def test_run_branch_mismatch_reimport_not_found() -> None:
    entry = DiffEntry(
        apm_code="ORG1",
        repository_name="BB/missing",
        production_branch="master",
        target_reference="develop",
    )
    client = MagicMock(spec=SnykRestClient)
    client.group_id = "group-uuid"
    client.iter_group_orgs.return_value = [{"id": "org-1", "name": "ORG1"}]
    client.iter_org_targets.return_value = []

    report = run_branch_mismatch_reimport(
        client,
        [entry],
        BranchMismatchReimportOptions(dry_run=True),
    )

    assert report["not_found"][0]["reason"] == "target_not_found"


def test_run_branch_mismatch_reimport_already_correct() -> None:
    entry = DiffEntry(
        apm_code="ORG1",
        repository_name="BB/my-service",
        production_branch="master",
        target_reference="master",
    )
    client = MagicMock(spec=SnykRestClient)
    client.group_id = "group-uuid"
    client.iter_group_orgs.return_value = [{"id": "org-1", "name": "ORG1"}]

    report = run_branch_mismatch_reimport(
        client,
        [entry],
        BranchMismatchReimportOptions(dry_run=True),
    )

    assert report["skipped"][0]["reason"] == "already_correct"
    client.iter_org_targets.assert_not_called()
