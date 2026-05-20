"""Tests for Bitbucket repository commit checks."""

import json
from io import BytesIO
from unittest.mock import patch

from integrations.bitbucket import BitbucketServerClient


def test_repository_has_commits_true() -> None:
    payload = json.dumps({"values": [{"id": "abc"}]}).encode()
    client = BitbucketServerClient("https://bb.example.com", "token")

    with patch("integrations.bitbucket.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = BytesIO(payload)
        assert client.repository_has_commits("PRJ", "repo") is True


def test_repository_has_commits_false() -> None:
    payload = json.dumps({"values": []}).encode()
    client = BitbucketServerClient("https://bb.example.com", "token")

    with patch("integrations.bitbucket.client.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = BytesIO(payload)
        assert client.repository_has_commits("PRJ", "repo") is False
