"""Tests for Snyk REST target APIs."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch

from config.snyk_settings import SnykSettings
from integrations.snyk.client import SnykRestClient


def _settings() -> SnykSettings:
    return SnykSettings(
        token="t",
        group_id="group-uuid",
        api_origin="https://api.snyk.io",
        rest_root="https://api.snyk.io/rest",
        v1_root="https://api.snyk.io/v1",
        integrations_api="v1",
        api_version="2024-10-15",
        http_max_attempts=1,
        http_backoff_seconds=0.0,
    )


def test_iter_org_targets_pagination_and_display_name_filter() -> None:
    calls: list[str] = []

    def fake_urlopen(req: object, timeout: float | None = None) -> object:
        url = getattr(req, "full_url", "")
        calls.append(url)
        if "targets" in url and "targets/tgt" not in url:
            body = json.dumps(
                {
                    "data": [
                        {
                            "id": "tgt-1",
                            "attributes": {
                                "display_name": "BB/my-service",
                                "target_reference": "develop",
                            },
                        }
                    ],
                    "links": {},
                }
            ).encode()
        else:
            body = b"{}"
        return BytesIO(body)

    client = SnykRestClient(_settings())
    with patch("integrations.snyk.client.urlopen", side_effect=fake_urlopen):
        targets = client.iter_org_targets("org-uuid", display_name="BB/my-service")

    assert len(targets) == 1
    assert targets[0]["id"] == "tgt-1"
    assert "display_name=BB%2Fmy-service" in calls[0]


def test_get_org_target() -> None:
    payload = {
        "data": {
            "id": "tgt-1",
            "attributes": {
                "display_name": "BB/my-service",
                "target_reference": "develop",
                "projectKey": "P1",
                "repoSlug": "my-service",
            },
            "relationships": {
                "integration": {"data": {"id": "int-1"}},
            },
        }
    }

    def fake_urlopen(req: object, timeout: float | None = None) -> object:
        return BytesIO(json.dumps(payload).encode())

    client = SnykRestClient(_settings())
    with patch("integrations.snyk.client.urlopen", side_effect=fake_urlopen):
        target = client.get_org_target("org-uuid", "tgt-1")

    assert target["id"] == "tgt-1"


def test_delete_org_target() -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: float | None = None) -> object:
        captured["method"] = getattr(req, "method", None)
        captured["url"] = getattr(req, "full_url", None)
        return BytesIO(b"")

    client = SnykRestClient(_settings())
    with patch("integrations.snyk.client.urlopen", side_effect=fake_urlopen):
        client.delete_org_target("org-uuid", "tgt-1")

    assert captured["method"] == "DELETE"
    assert (
        captured["url"]
        == "https://api.snyk.io/rest/orgs/org-uuid/targets/tgt-1?version=2024-10-15"
    )
