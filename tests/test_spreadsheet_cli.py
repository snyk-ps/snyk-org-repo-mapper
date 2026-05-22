"""CLI tests for spreadsheet-driven Bitbucket discovery."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from commands.spreadsheet_cli import main
from tests.test_spreadsheet_mapping import _minimal_bb_mapping_xlsx


def test_main_requires_input() -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_main_missing_input(tmp_path: Path) -> None:
    missing = tmp_path / "nope.xlsx"
    rc = main(["--input", str(missing)])
    assert rc == 2


@patch("commands.spreadsheet_cli.BitbucketServerClient")
def test_main_stdout_json_array(mock_client_cls, tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("BITBUCKET_URL", "https://bb.example.com")
    monkeypatch.setenv("BITBUCKET_PAT", "token")

    client = mock_client_cls.return_value
    client.get_repository.return_value = {
        "slug": "repo-a",
        "name": "Repo A",
        "defaultBranch": "refs/heads/main",
        "project": {"key": "MYPROJ", "name": "My Project"},
    }
    client.repository_latest_commit.return_value = {
        "committer": {"name": "dev", "emailAddress": "dev@example.com"},
    }
    client.fetch_raw_file.return_value = b"security:\n  apmCode: APM1\n"

    inp = tmp_path / "mini.xlsx"
    inp.write_bytes(_minimal_bb_mapping_xlsx())
    rc = main(["-i", str(inp)])
    assert rc == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["repository_path"] == "MYPROJ/repo-a"
    assert rows[0]["apm_code"] == "APM1"
    assert rows[0]["is_empty"] is False


@patch("commands.spreadsheet_cli.BitbucketServerClient")
def test_main_writes_discovery_json(mock_client_cls, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BITBUCKET_URL", "https://bb.example.com")
    monkeypatch.setenv("BITBUCKET_PAT", "token")

    client = mock_client_cls.return_value
    client.get_repository.return_value = {
        "slug": "repo-a",
        "name": "Repo A",
        "defaultBranch": {"id": "refs/heads/main", "displayId": "main"},
    }
    client.repository_latest_commit.return_value = None

    inp = tmp_path / "mini.xlsx"
    inp.write_bytes(_minimal_bb_mapping_xlsx())
    out = tmp_path / "discovery.json"
    rc = main(["-i", str(inp), "-o", str(out), "--no-empty-repos-output"])
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["version"] == 1
    assert doc["source"] == "bitbucket"
    assert doc["rows"][0]["is_empty"] is True
