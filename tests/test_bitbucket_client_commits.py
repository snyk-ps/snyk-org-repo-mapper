"""Tests for Bitbucket repository commit checks and committer parsing."""

import json
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from integrations.bitbucket.client import (
    BitbucketServerClient,
    DEFAULT_BRANCH_EMPTY_REPO,
    parse_committer_identity,
)


def test_repository_latest_commit_returns_first_value() -> None:
    payload = json.dumps(
        {
            "values": [
                {
                    "id": "abc",
                    "committer": {"name": "charlie", "emailAddress": "charlie@example.com"},
                }
            ]
        }
    ).encode()
    client = BitbucketServerClient("https://bb.example.com", "token")

    with patch("integrations.bitbucket.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = BytesIO(payload)
        commit = client.repository_latest_commit("PRJ", "repo")

    assert commit is not None
    assert commit["id"] == "abc"


def test_repository_latest_commit_none_when_empty() -> None:
    payload = json.dumps({"values": []}).encode()
    client = BitbucketServerClient("https://bb.example.com", "token")

    with patch("integrations.bitbucket.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = BytesIO(payload)
        assert client.repository_latest_commit("PRJ", "repo") is None


def test_parse_committer_identity_from_committer() -> None:
    commit = {
        "committer": {"name": "charlie", "emailAddress": "charlie@example.com"},
        "author": {"name": "other", "emailAddress": "other@example.com"},
    }
    assert parse_committer_identity(commit) == ("charlie", "charlie@example.com")


def test_parse_committer_identity_author_fallback() -> None:
    commit = {"author": {"name": "jane", "emailAddress": "jane@example.com"}}
    assert parse_committer_identity(commit) == ("jane", "jane@example.com")


def test_parse_committer_identity_missing_returns_none() -> None:
    assert parse_committer_identity({}) == (None, None)
    assert parse_committer_identity({"committer": {}, "author": {}}) == (None, None)


def test_get_repository_returns_payload() -> None:
    payload = json.dumps({"slug": "repo", "name": "Repo"}).encode()
    client = BitbucketServerClient("https://bb.example.com", "token")

    with patch("integrations.bitbucket.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = BytesIO(payload)
        repo = client.get_repository("PRJ", "repo")

    assert repo["slug"] == "repo"


def test_get_repository_404_raises_value_error() -> None:
    client = BitbucketServerClient("https://bb.example.com", "token")

    def raise_404(*_a, **_k):
        raise HTTPError("http://x", 404, "Not Found", None, None)

    with patch("integrations.bitbucket.client.urlopen", side_effect=raise_404):
        with pytest.raises(ValueError, match="not found"):
            client.get_repository("PRJ", "missing")


def _http_error(code: int, body: dict | None = None) -> HTTPError:
    payload = json.dumps(body).encode() if body is not None else b""
    return HTTPError(
        "http://x",
        code,
        "Error",
        None,
        BytesIO(payload) if payload else None,
    )


def test_get_default_branch_no_default_branch_404_is_empty() -> None:
    client = BitbucketServerClient("https://bb.example.com", "token")
    err = _http_error(
        404,
        {
            "errors": [
                {
                    "context": None,
                    "message": "No default branch is defined",
                    "exceptionName": (
                        "com.atlassian.bitbucket.repository.NoDefaultBranchException"
                    ),
                }
            ]
        },
    )

    with patch("integrations.bitbucket.client.urlopen", side_effect=err):
        assert client.get_default_branch("ACCP", "z_deleted_pipeline-common-commands") is (
            DEFAULT_BRANCH_EMPTY_REPO
        )


def test_get_default_branch_404_missing_ref_returns_none() -> None:
    client = BitbucketServerClient("https://bb.example.com", "token")
    err = _http_error(
        404,
        {"errors": [{"context": None, "message": "Not found", "exceptionName": None}]},
    )

    with patch("integrations.bitbucket.client.urlopen", side_effect=err):
        assert client.get_default_branch("PRJ", "repo") is None


def test_get_default_branch_204_is_empty() -> None:
    client = BitbucketServerClient("https://bb.example.com", "token")

    def raise_204(*_a, **_k):
        raise HTTPError("http://x", 204, "No Content", None, None)

    with patch("integrations.bitbucket.client.urlopen", side_effect=raise_204):
        assert client.get_default_branch("PRJ", "empty") is DEFAULT_BRANCH_EMPTY_REPO


def test_get_default_branch_200_returns_branch() -> None:
    payload = json.dumps(
        {"id": "refs/heads/main", "displayId": "main", "type": "BRANCH"}
    ).encode()
    client = BitbucketServerClient("https://bb.example.com", "token")

    class FakeResponse(BytesIO):
        def getcode(self) -> int:
            return 200

    with patch("integrations.bitbucket.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = FakeResponse(payload)
        branch = client.get_default_branch("PRJ", "repo")

    assert branch == {
        "id": "refs/heads/main",
        "displayId": "main",
        "type": "BRANCH",
    }


def test_parse_committer_identity_partial_committer_uses_author() -> None:
    commit = {
        "committer": {"name": "", "emailAddress": ""},
        "author": {"name": "bob", "emailAddress": "bob@example.com"},
    }
    assert parse_committer_identity(commit) == ("bob", "bob@example.com")
