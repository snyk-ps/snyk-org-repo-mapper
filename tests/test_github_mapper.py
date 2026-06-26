"""Tests for GitHub discovery mapping."""

from __future__ import annotations

from unittest.mock import MagicMock

from common.github_mapper import iter_github_mapping


def test_iter_github_mapping_empty_repo_skips_yaml() -> None:
    client = MagicMock()
    client.org_display_name.return_value = "Acme Corp"
    client.iter_org_repositories.return_value = [
        {"name": "empty-repo", "default_branch": "main"},
    ]
    client.repository_latest_commit.return_value = None

    rows = list(
        iter_github_mapping(
            client,
            "appsec.yaml",
            ["acme"],
            completed_keys=set(),
        )
    )

    assert len(rows) == 1
    assert rows[0]["is_empty"] is True
    assert rows[0]["repository_path"] == "acme/empty-repo"
    assert rows[0]["bitbucket_project_name"] == "Acme Corp"
    client.fetch_file_contents.assert_not_called()


def test_iter_github_mapping_non_empty_reads_yaml() -> None:
    client = MagicMock()
    client.org_display_name.return_value = "Acme Corp"
    client.iter_org_repositories.return_value = [
        {"name": "svc", "default_branch": "main"},
    ]
    client.repository_latest_commit.return_value = {
        "commit": {
            "committer": {"name": "charlie", "email": "charlie@example.com", "date": "2024-01-01T00:00:00Z"},
            "author": {"name": "charlie", "email": "charlie@example.com", "date": "2024-01-01T00:00:00Z"},
        }
    }
    yaml_text = b"security:\n  apmCode: ABC1\n  productionBranch: main\n"
    client.fetch_file_contents.return_value = yaml_text

    rows = list(
        iter_github_mapping(
            client,
            "appsec.yaml",
            ["acme"],
            completed_keys=set(),
        )
    )

    assert len(rows) == 1
    assert rows[0]["is_empty"] is False
    assert rows[0]["apm_code"] == "ABC1"
    assert rows[0]["production_branch"] == "main"
    client.fetch_file_contents.assert_called_once_with(
        "acme",
        "svc",
        "appsec.yaml",
        ref="main",
    )
