"""Tests for snyk-orgs CLI (Stage 2)."""

from __future__ import annotations

import json
from pathlib import Path

from commands.snyk_orgs_cli import main as snyk_orgs_main


def test_snyk_orgs_from_discovery(tmp_path: Path) -> None:
    discovery = tmp_path / "d.json"
    discovery.write_text(
        json.dumps(
            {
                "version": 1,
                "source": "spreadsheet",
                "rows": [
                    {
                        "apm_code": "C1",
                        "repository_path": "PK/slug",
                        "repository_name": "slug",
                        "production_branch": "",
                        "bitbucket_project_name": "PK",
                    }
                ],
                "checkpoint": None,
            }
        ),
        encoding="utf-8",
    )
    orgs = tmp_path / "orgs.json"
    rc = snyk_orgs_main(
        [
            "--discovery",
            str(discovery),
            "--output",
            str(orgs),
        ]
    )
    assert rc == 0
    org_doc = json.loads(orgs.read_text(encoding="utf-8"))
    assert len(org_doc["orgs"]) == 1
    assert org_doc["orgs"][0]["name"] == "C1"
