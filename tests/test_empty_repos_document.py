"""Tests for bitbucket-empty-repos.json builder."""

from common.empty_repos_document import build_empty_repos_document


def test_build_empty_repos_document_filters_and_sorts() -> None:
    rows = [
        {
            "repository_path": "P2/s",
            "repository_name": "s",
            "bitbucket_project_name": "P2",
            "is_empty": True,
        },
        {
            "repository_path": "P1/s",
            "repository_name": "s",
            "bitbucket_project_name": "P1",
            "is_empty": True,
        },
        {
            "repository_path": "P1/full",
            "repository_name": "full",
            "bitbucket_project_name": "P1",
            "is_empty": False,
        },
    ]
    doc = build_empty_repos_document(rows)
    assert doc["version"] == 1
    assert doc["source"] == "bitbucket"
    assert len(doc["repositories"]) == 2
    assert doc["repositories"][0]["repository_path"] == "P1/s"
    assert doc["repositories"][1]["repository_path"] == "P2/s"


def test_build_empty_repos_document_empty_list() -> None:
    doc = build_empty_repos_document([])
    assert doc["repositories"] == []
