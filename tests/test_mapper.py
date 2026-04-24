"""Tests for mapping row assembly."""

from common.mapper import (
    collect_mapping,
    iter_mapping,
    mapping_row,
)


def test_mapping_row_with_yaml() -> None:
    body = b"appSec:\n  apmCode: A1\n  productionBranch: prod\n"
    row = mapping_row(
        project_key="PRJ",
        project_name="Project",
        repo_slug="svc",
        repo_name="svc",
        file_bytes=body,
        default_display="main",
    )
    assert row["apm_code"] == "A1"
    assert row["repository_path"] == "PRJ/svc"
    assert row["repository_name"] == "svc"
    assert row["production_branch"] == "prod"
    assert row["bitbucket_project_name"] == "Project"


def test_mapping_row_without_file_uses_default_branch() -> None:
    row = mapping_row(
        project_key="PRJ",
        project_name="Project",
        repo_slug="svc",
        repo_name="svc",
        file_bytes=None,
        default_display="release",
    )
    assert row["apm_code"] is None
    assert row["production_branch"] == "release"


def test_collect_mapping_invokes_client() -> None:
    class FakeClient:
        def iter_projects(self, *, page_limit: int = 100):
            yield {"key": "PRJ", "name": "Proj"}

        def iter_repositories(self, project_key: str, *, page_limit: int = 100):
            assert project_key == "PRJ"
            yield {"slug": "r1", "name": "R1", "defaultBranch": "refs/heads/main"}

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            assert path == "f.yaml"
            return b"appSec:\n  apmCode: ZZ\n"

    rows = collect_mapping(FakeClient(), "f.yaml")
    assert len(rows) == 1
    assert rows[0]["apm_code"] == "ZZ"
    assert rows[0]["repository_path"] == "PRJ/r1"


def test_iter_mapping_skips_completed() -> None:
    class FakeClient:
        def iter_projects(self, *, page_limit: int = 100):
            yield {"key": "P", "name": "P"}

        def iter_repositories(self, project_key: str, *, page_limit: int = 100):
            assert project_key == "P"
            yield {"slug": "a", "name": "A", "defaultBranch": "refs/heads/main"}
            yield {"slug": "b", "name": "B", "defaultBranch": "refs/heads/main"}

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            return f"appSec:\n  apmCode: {slug}\n".encode()

    client = FakeClient()
    rows = list(
        iter_mapping(
            client,
            "f.yaml",
            completed_keys={("P", "a")},
            max_repos=None,
        )
    )
    assert len(rows) == 1
    assert rows[0]["repository_path"] == "P/b"


def test_iter_mapping_respects_max_repos() -> None:
    class FakeClient:
        def iter_projects(self, *, page_limit: int = 100):
            yield {"key": "P", "name": "P"}

        def iter_repositories(self, project_key: str, *, page_limit: int = 100):
            yield {"slug": "a", "name": "A", "defaultBranch": "refs/heads/main"}
            yield {"slug": "b", "name": "B", "defaultBranch": "refs/heads/main"}

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            return b"appSec:\n  apmCode: X\n"

    rows = list(iter_mapping(FakeClient(), "f.yaml", completed_keys=set(), max_repos=1))
    assert len(rows) == 1
    assert rows[0]["repository_path"] == "P/a"
