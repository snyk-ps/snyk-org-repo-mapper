"""Tests for Snyk project APIs used by Stage 4 post-import cleanup."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch

from config.snyk_settings import SnykSettings
from integrations.snyk.client import (
    SnykRestClient,
    normalize_rest_project,
    normalize_v1_projects_payload,
)


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


def test_normalize_v1_projects_payload_list() -> None:
    parsed = [{"id": "p1", "name": "proj", "type": "npm"}]
    assert normalize_v1_projects_payload(parsed) == parsed


def test_normalize_rest_project() -> None:
    item = {
        "id": "p1",
        "type": "project",
        "attributes": {"name": "docker", "type": "dockerfile"},
    }
    assert normalize_rest_project(item) == {
        "id": "p1",
        "name": "docker",
        "type": "dockerfile",
    }


def test_iter_org_projects_pagination_and_type_filter() -> None:
    calls: list[str] = []

    def fake_urlopen(req: object, timeout: float | None = None) -> object:
        url = getattr(req, "full_url", "")
        calls.append(url)
        if "limit=100" in url and "starting_after" not in url:
            body = json.dumps(
                {
                    "data": [
                        {
                            "id": "p1",
                            "type": "project",
                            "attributes": {"name": "docker", "type": "dockerfile"},
                        },
                        {
                            "id": "p2",
                            "type": "project",
                            "attributes": {"name": "app", "type": "npm"},
                        },
                    ],
                    "links": {
                        "next": "/rest/orgs/org-uuid/projects?version=2024-10-15&limit=100&starting_after=cursor",
                    },
                }
            ).encode()
        elif "starting_after=cursor" in url:
            body = json.dumps({"data": [], "links": {}}).encode()
        else:
            body = json.dumps({"data": [], "links": {}}).encode()
        return BytesIO(body)

    client = SnykRestClient(_settings())
    with patch("integrations.snyk.client.urlopen", side_effect=fake_urlopen):
        projects = client.iter_org_projects("org-uuid", project_type="dockerfile")

    assert len(projects) == 1
    assert projects[0]["id"] == "p1"
    assert calls[0] == (
        "https://api.snyk.io/rest/orgs/org-uuid/projects?version=2024-10-15&limit=100"
    )
    assert len(calls) == 2


def test_delete_org_project_delete() -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: float | None = None) -> object:
        captured["method"] = getattr(req, "method", None)
        captured["url"] = getattr(req, "full_url", None)
        return BytesIO(b"")

    client = SnykRestClient(_settings())
    with patch("integrations.snyk.client.urlopen", side_effect=fake_urlopen):
        client.delete_org_project("org-uuid", "proj-uuid")

    assert captured["method"] == "DELETE"
    assert (
        captured["url"]
        == "https://api.snyk.io/rest/orgs/org-uuid/projects/proj-uuid?version=2024-10-15"
    )


def test_update_project_settings_patch() -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: float | None = None) -> object:
        captured["method"] = getattr(req, "method", None)
        captured["url"] = getattr(req, "full_url", None)
        captured["data"] = getattr(req, "data", None)
        return BytesIO(b"{}")

    settings = {"recurringTests": {"frequency": "never"}}
    client = SnykRestClient(_settings())
    with patch("integrations.snyk.client.urlopen", side_effect=fake_urlopen):
        client.update_project_settings("org-uuid", "proj-uuid", settings)

    assert captured["method"] == "PATCH"
    assert captured["url"] == (
        "https://api.snyk.io/rest/orgs/org-uuid/projects/proj-uuid?version=2024-10-15"
    )
    assert json.loads(captured["data"]) == {
        "data": {
            "id": "proj-uuid",
            "type": "project",
            "attributes": {
                "settings": {
                    "recurring_tests": {"frequency": "never"},
                },
            },
        },
    }
