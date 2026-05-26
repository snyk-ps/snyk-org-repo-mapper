"""Tests for mapping row assembly."""

import logging

from common.mapper import (
    collect_mapping,
    iter_mapping,
    mapping_row,
    row_is_empty,
)


def test_mapping_row_with_yaml() -> None:
    body = b"security:\n  apmCode: A1\n  productionBranch: prod\n"
    row = mapping_row(
        project_key="PRJ",
        project_name="Project",
        repo_slug="svc",
        repo_name="svc",
        file_bytes=body,
        default_display="main",
        is_empty=False,
        last_committer_name="alice",
        last_committer_email="alice@example.com",
        last_commit_date="2024-01-01T00:00:00+00:00",
    )
    assert row["apm_code"] == "A1"
    assert row["is_empty"] is False
    assert row["last_committer_name"] == "alice"
    assert row["last_committer_email"] == "alice@example.com"
    assert row["last_commit_date"] == "2024-01-01T00:00:00+00:00"
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
        is_empty=False,
    )
    assert row["apm_code"] is None
    assert row["production_branch"] == "release"
    assert row["last_commit_date"] is None


def test_collect_mapping_invokes_client() -> None:
    class FakeClient:
        def iter_projects(self, *, page_limit: int = 100):
            yield {"key": "PRJ", "name": "Proj"}

        def iter_repositories(self, project_key: str, *, page_limit: int = 100):
            assert project_key == "PRJ"
            yield {"slug": "r1", "name": "R1", "defaultBranch": "refs/heads/main"}

        def repository_latest_commit(self, project_key: str, repo_slug: str):
            return {
                "committer": {"name": "dev", "emailAddress": "dev@example.com"},
                "committerTimestamp": 1_704_067_200_000,
            }

        def get_repository(self, project_key: str, repo_slug: str):
            raise AssertionError("full crawl should not call get_repository")

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            assert path == "f.yaml"
            return b"security:\n  apmCode: ZZ\n"

    rows = collect_mapping(FakeClient(), "f.yaml")
    assert len(rows) == 1
    assert rows[0]["apm_code"] == "ZZ"
    assert rows[0]["repository_path"] == "PRJ/r1"
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
            return {"committer": {"name": "u", "emailAddress": "u@example.com"}}

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
            return {"committer": {"name": "u", "emailAddress": "u@example.com"}}

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
            return {
                "author": {"name": "a", "emailAddress": "a@x.com"},
                "authorTimestamp": 1_704_067_200_000,
            }

        def fetch_raw_file(self, pk: str, slug: str, path: str, at_ref: str):
            return b"security:\n  apmCode: Z9\n"

    from common.mapper import iter_mapping_for_repos

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
            default_display="main",
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
