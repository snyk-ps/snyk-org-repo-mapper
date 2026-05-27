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


def test_snyk_orgs_with_group_and_template_org_ids(tmp_path: Path) -> None:
    discovery = tmp_path / "d.json"
    discovery.write_text(
        json.dumps(
            {
                "version": 1,
                "source": "spreadsheet",
                "rows": [
                    {
                        "apm_code": "X9",
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
    gid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    tid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    rc = snyk_orgs_main(
        [
            "--discovery",
            str(discovery),
            "--output",
            str(orgs),
            "--group-id",
            gid,
            "--template-org-id",
            tid,
        ]
    )
    assert rc == 0
    org_doc = json.loads(orgs.read_text(encoding="utf-8"))
    assert org_doc["orgs"][0]["groupId"] == gid
    assert org_doc["orgs"][0]["sourceOrgId"] == tid


def test_snyk_orgs_multi_apm_same_bitbucket_project(tmp_path: Path) -> None:
    discovery = tmp_path / "d.json"
    discovery.write_text(
        json.dumps(
            {
                "version": 1,
                "source": "bitbucket",
                "rows": [
                    {
                        "apm_code": "ABCD",
                        "repository_path": "ACCP/accelerator",
                        "repository_name": "accelerator",
                        "production_branch": "main",
                        "bitbucket_project_name": "ACCP",
                    },
                    {
                        "apm_code": "ABCE",
                        "repository_path": "ACCP/accelerator-build-engine",
                        "repository_name": "accelerator-build-engine",
                        "production_branch": "main",
                        "bitbucket_project_name": "ACCP",
                    },
                    {
                        "apm_code": "ABCF",
                        "repository_path": "ACCP/accelerator-jenkins-scripts",
                        "repository_name": "accelerator-jenkins-scripts",
                        "production_branch": "main",
                        "bitbucket_project_name": "ACCP",
                    },
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
    names = {entry["name"] for entry in org_doc["orgs"]}
    assert names == {"ABCD", "ABCE", "ABCF"}
