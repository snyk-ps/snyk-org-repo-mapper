"""HTTP retry behavior for Bitbucket and Snyk urllib clients."""

from __future__ import annotations

import json
from http.client import RemoteDisconnected
from unittest.mock import patch

import pytest

from integrations.bitbucket.client import BitbucketServerClient, _is_retriable_request_failure
from integrations.snyk.client import _is_retriable_request_failure as snyk_is_retriable


def test_bitbucket_predicate_treats_remote_disconnected_as_retriable() -> None:
    assert _is_retriable_request_failure(RemoteDisconnected("closed")) is True


def test_snyk_predicate_treats_remote_disconnected_as_retriable() -> None:
    assert snyk_is_retriable(RemoteDisconnected("closed")) is True


def test_bitbucket_request_json_retries_then_succeeds() -> None:
    ok = json.dumps({"values": [], "isLastPage": True}).encode("utf-8")

    class Resp:
        def __enter__(self) -> Resp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return ok

    calls: list[int] = []

    def fake_urlopen(req: object, timeout: float | None = None) -> Resp:
        calls.append(1)
        if len(calls) == 1:
            raise RemoteDisconnected("Remote end closed connection without response")
        return Resp()

    with patch("integrations.bitbucket.client.urlopen", side_effect=fake_urlopen):
        client = BitbucketServerClient(
            "https://bb.example/",
            "token",
            http_max_attempts=5,
            http_backoff_seconds=0.0,
        )
        out = client._request_json("rest/api/1.0/projects?limit=1&start=0")
    assert out == {"values": [], "isLastPage": True}
    assert len(calls) == 2


def test_bitbucket_request_json_wraps_after_exhausted_remote_disconnected() -> None:
    class Resp:
        def __enter__(self) -> Resp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"{}"

    with patch(
        "integrations.bitbucket.client.urlopen",
        side_effect=RemoteDisconnected("Remote end closed connection without response"),
    ):
        client = BitbucketServerClient(
            "https://bb.example/",
            "token",
            http_max_attempts=2,
            http_backoff_seconds=0.0,
        )
        with pytest.raises(RuntimeError, match="Network error calling Bitbucket API"):
            client._request_json("rest/api/1.0/projects?limit=1&start=0")


def test_snyk_request_json_retries_remote_disconnected() -> None:
    from config.snyk_settings import SnykSettings
    from integrations.snyk.client import SnykRestClient

    settings = SnykSettings(
        token="t",
        group_id="g",
        api_origin="https://api.snyk.io",
        rest_root="https://api.snyk.io/rest",
        v1_root="https://api.snyk.io/v1",
        integrations_api="v1",
        api_version="2024-01-01",
        http_max_attempts=3,
        http_backoff_seconds=0.0,
    )

    ok = json.dumps({"data": []}).encode("utf-8")

    class Resp:
        def __enter__(self) -> Resp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return ok

    n = 0

    def fake_urlopen(req: object, timeout: float | None = None) -> Resp:
        nonlocal n
        n += 1
        if n == 1:
            raise RemoteDisconnected("boom")
        return Resp()

    with patch("integrations.snyk.client.urlopen", side_effect=fake_urlopen):
        client = SnykRestClient(settings)
        out = client._request_rest_json_object(
            "https://api.snyk.io/rest/orgs/x?version=2024-01-01"
        )
    assert out == {"data": []}
    assert n == 2
