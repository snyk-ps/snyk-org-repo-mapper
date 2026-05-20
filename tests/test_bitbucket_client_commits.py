"""Tests for Bitbucket repository commit checks and committer parsing."""

import json
from io import BytesIO
from unittest.mock import patch

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


def test_parse_committer_identity_partial_committer_uses_author() -> None:
    commit = {
        "committer": {"name": "", "emailAddress": ""},
        "author": {"name": "bob", "emailAddress": "bob@example.com"},
    }
    assert parse_committer_identity(commit) == ("bob", "bob@example.com")
