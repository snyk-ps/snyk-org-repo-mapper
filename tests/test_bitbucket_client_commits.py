"""Tests for Bitbucket repository commit checks and committer parsing."""

import json
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from integrations.bitbucket.client import (
    BitbucketServerClient,
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


def test_parse_committer_identity_partial_committer_uses_author() -> None:
    commit = {
        "committer": {"name": "", "emailAddress": ""},
        "author": {"name": "bob", "emailAddress": "bob@example.com"},
    }
    assert parse_committer_identity(commit) == ("bob", "bob@example.com")
