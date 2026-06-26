"""Tests for GitHub REST client."""

from __future__ import annotations

import base64
import json
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

from integrations.github.client import (
    GitHubClient,
    parse_committer_identity,
    parse_commit_timestamp,
    repository_has_default_branch,
)


class _FakeResp:
    def __init__(self, body: bytes, link: str | None = None) -> None:
        self._body = body
        self.headers = {"Link": link} if link else {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_repository_has_default_branch() -> None:
    assert repository_has_default_branch({"default_branch": "main"}) is True
    assert repository_has_default_branch({"default_branch": ""}) is False
    assert repository_has_default_branch({}) is False


def test_parse_committer_identity_from_committer() -> None:
    commit = {
        "commit": {
            "committer": {"name": "charlie", "email": "charlie@example.com"},
            "author": {"name": "other", "email": "other@example.com"},
        }
    }
    assert parse_committer_identity(commit) == ("charlie", "charlie@example.com")


def test_parse_commit_timestamp_from_committer() -> None:
    commit = {"commit": {"committer": {"date": "2024-03-15T10:30:00Z"}}}
    assert parse_commit_timestamp(commit) == "2024-03-15T10:30:00Z"


def test_repository_latest_commit_returns_first() -> None:
    payload = json.dumps([{"sha": "abc"}]).encode()
    client = GitHubClient("https://api.github.com", "token")

    with patch("integrations.github.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = _FakeResp(payload)
        commit = client.repository_latest_commit("acme", "svc", sha="main")

    assert commit is not None
    assert commit["sha"] == "abc"


def test_repository_latest_commit_none_when_empty() -> None:
    payload = json.dumps([]).encode()
    client = GitHubClient("https://api.github.com", "token")

    with patch("integrations.github.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = _FakeResp(payload)
        assert client.repository_latest_commit("acme", "svc") is None


def test_repository_latest_commit_none_when_github_empty_repo_409() -> None:
    client = GitHubClient("https://api.github.com", "token")

    def raise_409(*args: object, **kwargs: object) -> None:
        raise HTTPError(
            url="https://api.github.com/repos/acme/empty/commits?per_page=1",
            code=409,
            msg="Conflict",
            hdrs=None,
            fp=BytesIO(b'{"message":"Git Repository is empty."}'),
        )

    with patch("integrations.github.client.urlopen", side_effect=raise_409):
        assert client.repository_latest_commit("acme", "empty", sha="main") is None


def test_fetch_file_contents_decodes_base64() -> None:
    body = json.dumps({"encoding": "base64", "content": base64.b64encode(b"hello").decode()}).encode()
    client = GitHubClient("https://api.github.com", "token")

    with patch("integrations.github.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = _FakeResp(body)
        raw = client.fetch_file_contents("acme", "svc", "appsec.yaml", ref="main")

    assert raw == b"hello"


def test_iter_org_repositories_paginates() -> None:
    page1 = json.dumps([{"name": "a"}]).encode()
    page2 = json.dumps([{"name": "b"}]).encode()
    client = GitHubClient("https://api.github.com", "token")

    link = '<https://api.github.com/orgs/acme/repos?per_page=100&page=2>; rel="next"'
    with patch("integrations.github.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.side_effect = [
            _FakeResp(page1, link),
            _FakeResp(page2),
        ]
        names = [repo["name"] for repo in client.iter_org_repositories("acme")]

    assert names == ["a", "b"]
