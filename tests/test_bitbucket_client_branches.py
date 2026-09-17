"""Tests for Bitbucket branch listing and latest-active-branch resolution."""

import json
from io import BytesIO
from unittest.mock import patch

from integrations.bitbucket.client import (
    BitbucketServerClient,
    branch_at_ref,
    branch_tip_timestamp_ms,
    resolve_latest_active_branch,
)

_METADATA_KEY = "com.atlassian.bitbucket.server.bitbucket-branch:latest-commit-metadata"


def _branch(display: str, ts: int) -> dict:
    return {
        "id": f"refs/heads/{display}",
        "displayId": display,
        "metadata": {
            _METADATA_KEY: {
                "id": f"c-{display}",
                "committerTimestamp": ts,
                "committer": {"name": display, "emailAddress": f"{display}@example.com"},
            }
        },
    }


def test_branch_at_ref_from_id() -> None:
    at, disp = branch_at_ref({"id": "refs/heads/main", "displayId": "main"})
    assert at == "refs/heads/main"
    assert disp == "main"


def test_branch_tip_timestamp_ms() -> None:
    assert branch_tip_timestamp_ms(_branch("main", 100)) == 100


def test_iter_branches_paginates() -> None:
    page1 = json.dumps(
        {
            "values": [_branch("a", 1)],
            "isLastPage": False,
            "nextPageStart": 1,
        }
    ).encode()
    page2 = json.dumps({"values": [_branch("b", 2)], "isLastPage": True}).encode()
    client = BitbucketServerClient("https://bb.example.com", "token")
    responses = [BytesIO(page1), BytesIO(page2)]

    with patch("integrations.bitbucket.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.side_effect = responses
        branches = list(client.iter_branches("PRJ", "repo"))

    assert len(branches) == 2
    assert branches[0]["displayId"] == "a"
    assert branches[1]["displayId"] == "b"


def test_resolve_latest_active_branch_picks_newest() -> None:
    payload = json.dumps(
        {"values": [_branch("old", 100), _branch("new", 200)], "isLastPage": True}
    ).encode()
    client = BitbucketServerClient("https://bb.example.com", "token")

    with patch("integrations.bitbucket.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = BytesIO(payload)
        result = resolve_latest_active_branch(client, "PRJ", "repo")

    assert result is not None
    at_ref, display, commit = result
    assert at_ref == "refs/heads/new"
    assert display == "new"
    assert commit["id"] == "c-new"


def test_resolve_latest_active_branch_tiebreak_lexicographic() -> None:
    payload = json.dumps(
        {
            "values": [_branch("zebra", 200), _branch("alpha", 200)],
            "isLastPage": True,
        }
    ).encode()
    client = BitbucketServerClient("https://bb.example.com", "token")

    with patch("integrations.bitbucket.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = BytesIO(payload)
        result = resolve_latest_active_branch(client, "PRJ", "repo")

    assert result is not None
    assert result[1] == "alpha"


def test_resolve_latest_active_branch_empty_list() -> None:
    payload = json.dumps({"values": [], "isLastPage": True}).encode()
    client = BitbucketServerClient("https://bb.example.com", "token")

    with patch("integrations.bitbucket.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = BytesIO(payload)
        assert resolve_latest_active_branch(client, "PRJ", "repo") is None


def test_repository_latest_commit_on_ref() -> None:
    payload = json.dumps(
        {
            "values": [
                {
                    "id": "abc",
                    "committerTimestamp": 1_704_067_200_000,
                    "committer": {"name": "dev", "emailAddress": "dev@example.com"},
                }
            ]
        }
    ).encode()
    client = BitbucketServerClient("https://bb.example.com", "token")

    with patch("integrations.bitbucket.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = BytesIO(payload)
        commit = client.repository_latest_commit_on_ref(
            "PRJ", "repo", "refs/heads/feature"
        )

    assert commit is not None
    assert commit["id"] == "abc"
