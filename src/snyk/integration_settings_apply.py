"""Apply predefined Bitbucket Server integration settings to a single org."""

from __future__ import annotations

from typing import Any

from integrations.snyk.client import SnykRestClient, pick_bitbucket_server_integration_id
from snyk.integration_settings_defaults import BITBUCKET_SERVER_INTEGRATION_SETTINGS


def apply_bitbucket_integration_settings_to_org(
    client: SnykRestClient,
    org_id: str,
    org_name: str,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """PUT predefined settings for one org; return outcome dict with ``status``."""
    oid = org_id.strip()
    name = org_name.strip()

    if dry_run:
        return {
            "status": "skipped",
            "org_id": oid,
            "org_name": name,
            "reason": "dry_run",
        }

    try:
        integrations = client.iter_org_integrations(oid)
        integration_id = pick_bitbucket_server_integration_id(integrations)
        client.update_org_integration_settings(
            oid,
            integration_id,
            BITBUCKET_SERVER_INTEGRATION_SETTINGS,
        )
    except (ValueError, RuntimeError) as exc:
        return {
            "status": "failed",
            "org_id": oid,
            "org_name": name,
            "error": str(exc),
        }

    return {
        "status": "updated",
        "org_id": oid,
        "org_name": name,
        "integration_id": integration_id,
    }
