"""Tests for mapping row assembly."""

import json
import logging

from common.mapper import (
    collect_mapping,
    iter_mapping,
    iter_mapping_for_repos,
    mapping_row,
    row_is_empty,
)

_METADATA_KEY = "com.atlassian.bitbucket.server.bitbucket-branch:latest-commit-metadata"


def _branch(display: str, ts: int, *, name: str = "dev", email: str = "dev@example.com") -> dict:
    return {
        "id": f"refs/heads/{display}",
        "displayId": display,
        "metadata": {
            _METADATA_KEY: {
                "committer": {"name": name, "emailAddress": email},
                "committerTimestamp": ts,
            }
        },
    }


def _branches_payload(*branches: dict) -> bytes:
    return json.dumps({"values": list(branches), "isLastPage": True}).encode()


def test_mapping_row_with_yaml() -> None:
    body = b"security:\n  apmCode: A1\n  productionBranch: prod\n"
    row = mapping_row(
        project_key="PRJ",
        project_name="Project",
        repo_slug="svc",
        repo_name="svc",
        file_bytes=body,
        is_empty=False,
        bitbucket_default_branch="main",
        latest_active_branch="feature",
        is_archived=False,
        last_committer_name="alice",
        last_committer_email="alice@example.com",
        last_commit_date="2024-01-01T00:00:00+00:00",
    )
    assert row["apm_code"] == "A1"
    assert row["is_empty"] is False
    assert row["bitbucket_default_branch"] == "main"
    assert row["latest_active_branch"] == "feature"
    assert row["is_archived"] is False
    assert row["last_committer_name"] == "alice"
    assert row["last_committer_email"] == "alice@example.com"
    assert row["last_commit_date"] == "2024-01-01T00:00:00+00:00"
    assert row["repository_path"] == "PRJ/svc"
    assert row["repository_name"] == "svc"
    assert row["production_branch"] == "prod"
    assert row["bitbucket_project_name"] == "Project"


def test_mapping_row_without_file_has_null_production_branch() -> None:
    row = mapping_row(
        project_key="PRJ",
        project_name="Project",
        repo_slug="svc",
        repo_name="svc",
        file_bytes=None,
        is_empty=False,
        bitbucket_default_branch="release",
        latest_active_branch="release",
    )
    assert row["apm_code"] is None
    assert row["production_branch"] is None
    assert row["last_commit_date"] is None


def test_collect_mapping_invokes_client() -> None:
    class FakeClient:
        def iter_projects(self, *, page_limit: int = 100):
            yield {"key": "PRJ", "name": "Proj"}

        def iter_repositories(self, project_key: str, *, page_limit: int = 100):
            assert project_key == "PRJ"
            yield {"slug": "r1", "name": "R1", "defaultBranch": "refs/heads/main"}

        def repository_latest_commit(self, project_key: str, repo_slug: str):
            return {"committerTimestamp": 1_704_067_200_000}

        def iter_branches(self, project_key: str, repo_slug: str, *, details=True, page_limit=100):
            yield _branch("main", 1_704_067_200_000)

        def get_repository(self, project_key: str, repo_slug: str):
            raise AssertionError("full crawl should not call get_repository")

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            assert path == "f.yaml"
            assert at_ref == "refs/heads/main"
            return b"security:\n  apmCode: ZZ\n"

    rows = collect_mapping(FakeClient(), "f.yaml")
    assert len(rows) == 1
    assert rows[0]["apm_code"] == "ZZ"
    assert rows[0]["repository_path"] == "PRJ/r1"
    assert rows[0]["bitbucket_default_branch"] == "main"
    assert rows[0]["latest_active_branch"] == "main"
    assert rows[0]["is_archived"] is False
    assert rows[0]["last_committer_name"] == "dev"
    assert rows[0]["last_committer_email"] == "dev@example.com"
    assert rows[0]["last_commit_date"] == "2024-01-01T00:00:00+00:00"


def test_iter_mapping_skips_completed() -> None:
    class FakeClient:
        def iter_projects(self, *, page_limit: int = 100):
            yield {"key": "P", "name": "P"}

        def iter_repositories(self, project_key: str, *, page_limit: int = 100):
            assert project_key == "P"
            yield {"slug": "a", "name": "A", "defaultBranch": "refs/heads/main"}
            yield {"slug": "b", "name": "B", "defaultBranch": "refs/heads/main"}

        def repository_latest_commit(self, project_key: str, repo_slug: str):
            return {"committerTimestamp": 1}

        def iter_branches(self, project_key: str, repo_slug: str, *, details=True, page_limit=100):
            yield _branch("main", 1)

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            return f"security:\n  apmCode: {slug}\n".encode()

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

        def repository_latest_commit(self, project_key: str, repo_slug: str):
            return {"committerTimestamp": 1}

        def iter_branches(self, project_key: str, repo_slug: str, *, details=True, page_limit=100):
            yield _branch("main", 1)

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            return b"security:\n  apmCode: X\n"

    rows = list(iter_mapping(FakeClient(), "f.yaml", completed_keys=set(), max_repos=1))
    assert len(rows) == 1
    assert rows[0]["repository_path"] == "P/a"


def test_iter_mapping_empty_repo_skips_yaml() -> None:
    fetched: list[str] = []

    class FakeClient:
        def iter_projects(self, *, page_limit: int = 100):
            yield {"key": "P", "name": "P"}

        def iter_repositories(self, project_key: str, *, page_limit: int = 100):
            yield {"slug": "empty", "name": "Empty", "defaultBranch": "refs/heads/main"}

        def repository_latest_commit(self, project_key: str, repo_slug: str):
            return None

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            fetched.append(slug)
            return b"security:\n  apmCode: X\n"

    rows = list(iter_mapping(FakeClient(), "f.yaml", completed_keys=set(), max_repos=None))
    assert len(rows) == 1
    assert rows[0]["is_empty"] is True
    assert rows[0]["apm_code"] is None
    assert rows[0]["latest_active_branch"] is None
    assert rows[0]["last_committer_name"] is None
    assert rows[0]["last_committer_email"] is None
    assert rows[0]["last_commit_date"] is None
    assert fetched == []


def test_iter_mapping_no_default_branch_is_empty() -> None:
    class FakeClient:
        def iter_projects(self, *, page_limit: int = 100):
            yield {"key": "P", "name": "P"}

        def iter_repositories(self, project_key: str, *, page_limit: int = 100):
            yield {"slug": "nobranch", "name": "No Branch"}

        def get_default_branch(self, project_key: str, repo_slug: str):
            from integrations.bitbucket import DEFAULT_BRANCH_EMPTY_REPO

            return DEFAULT_BRANCH_EMPTY_REPO

        def repository_latest_commit(self, project_key: str, repo_slug: str):
            raise AssertionError("should not check commits when no default branch")

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            raise AssertionError("should not fetch yaml")

    rows = list(iter_mapping(FakeClient(), "f.yaml", completed_keys=set(), max_repos=None))
    assert len(rows) == 1
    assert rows[0]["is_empty"] is True
    assert rows[0]["apm_code"] is None


def test_iter_mapping_skips_archived_by_default() -> None:
    class FakeClient:
        def iter_projects(self, *, page_limit: int = 100):
            yield {"key": "P", "name": "P"}

        def iter_repositories(self, project_key: str, *, page_limit: int = 100):
            yield {
                "slug": "archived",
                "name": "Archived",
                "archived": True,
                "defaultBranch": "refs/heads/main",
            }

        def repository_latest_commit(self, project_key: str, repo_slug: str):
            raise AssertionError("archived repo should be skipped")

    rows = list(iter_mapping(FakeClient(), "f.yaml", completed_keys=set(), max_repos=None))
    assert rows == []


def test_iter_mapping_includes_archived_when_requested() -> None:
    class FakeClient:
        def iter_projects(self, *, page_limit: int = 100):
            yield {"key": "P", "name": "P"}

        def iter_repositories(self, project_key: str, *, page_limit: int = 100):
            yield {
                "slug": "archived",
                "name": "Archived",
                "archived": True,
                "defaultBranch": "refs/heads/main",
            }

        def repository_latest_commit(self, project_key: str, repo_slug: str):
            return {"committerTimestamp": 1}

        def iter_branches(self, project_key: str, repo_slug: str, *, details=True, page_limit=100):
            yield _branch("main", 1)

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            return None

    rows = list(
        iter_mapping(
            FakeClient(),
            "f.yaml",
            completed_keys=set(),
            max_repos=None,
            include_archived=True,
        )
    )
    assert len(rows) == 1
    assert rows[0]["is_archived"] is True


def test_iter_mapping_reads_yaml_from_latest_active_branch() -> None:
    fetched_at: list[str] = []

    class FakeClient:
        def iter_projects(self, *, page_limit: int = 100):
            yield {"key": "P", "name": "P"}

        def iter_repositories(self, project_key: str, *, page_limit: int = 100):
            yield {"slug": "svc", "name": "Svc", "defaultBranch": "refs/heads/main"}

        def repository_latest_commit(self, project_key: str, repo_slug: str):
            return {"committerTimestamp": 1}

        def iter_branches(self, project_key: str, repo_slug: str, *, details=True, page_limit=100):
            yield _branch("main", 100)
            yield _branch("feature", 200, name="feat", email="feat@example.com")

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            fetched_at.append(at_ref)
            return b"security:\n  apmCode: FEAT\n  productionBranch: feature\n"

    rows = list(iter_mapping(FakeClient(), "f.yaml", completed_keys=set(), max_repos=None))
    assert fetched_at == ["refs/heads/feature"]
    assert rows[0]["latest_active_branch"] == "feature"
    assert rows[0]["bitbucket_default_branch"] == "main"
    assert rows[0]["apm_code"] == "FEAT"
    assert rows[0]["production_branch"] == "feature"
    assert rows[0]["last_committer_name"] == "feat"


def test_iter_mapping_for_repos_from_sheet() -> None:
    class FakeClient:
        def get_repository(self, project_key: str, repo_slug: str):
            assert project_key == "PRJ" and repo_slug == "svc"
            return {
                "slug": "svc",
                "name": "Service",
                "defaultBranch": "refs/heads/main",
                "project": {"name": "Project"},
            }

        def repository_latest_commit(self, project_key: str, repo_slug: str):
            return {"committerTimestamp": 1_704_067_200_000}

        def iter_branches(self, project_key: str, repo_slug: str, *, details=True, page_limit=100):
            yield _branch("main", 1_704_067_200_000, name="a", email="a@x.com")

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            return b"security:\n  apmCode: Z9\n"

    rows = list(
        iter_mapping_for_repos(
            FakeClient(),
            "appsec.yaml",
            [("PRJ", "svc")],
            completed_keys=set(),
            max_repos=None,
        )
    )
    assert rows[0]["apm_code"] == "Z9"
    assert rows[0]["last_committer_name"] == "a"
    assert rows[0]["last_commit_date"] == "2024-01-01T00:00:00+00:00"


def test_mapping_row_warns_on_unconventional_apm_code(caplog) -> None:
    body = b"security:\n  apmCode: A1\n"
    with caplog.at_level(logging.WARNING):
        row = mapping_row(
            project_key="PRJ",
            project_name="Project",
            repo_slug="svc",
            repo_name="svc",
            file_bytes=body,
            is_empty=False,
        )
    assert row["apm_code"] == "A1"
    assert "A1" in caplog.text
    assert "PRJ/svc" in caplog.text


def test_row_is_empty_strict() -> None:
    assert row_is_empty({"is_empty": True}) is True
    assert row_is_empty({"is_empty": False}) is False
    assert row_is_empty({}) is False
    assert row_is_empty({"is_empty": "true"}) is False
