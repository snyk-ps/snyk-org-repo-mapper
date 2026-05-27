"""Stage 2.3 — Apply predefined SCM integration settings from Broker Apply report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from integrations.snyk.client import SnykRestClient, pick_bitbucket_server_integration_id
from snyk.integration_settings_defaults import (
    BITBUCKET_SERVER_INTEGRATION_SETTINGS,
    SETTINGS_PROFILE_ID,
)

BROKER_APPLY_REPORT_VERSION = 1
INTEGRATION_SETTINGS_REPORT_VERSION = 1


def load_broker_apply_report(path: Path) -> dict[str, Any]:
    """Load and validate broker-org-apply-report.json."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"Invalid apply report JSON in {path}: {exc}"
        raise ValueError(msg) from exc
    if not isinstance(data, dict):
        msg = f"Apply report must be a JSON object: {path}"
        raise ValueError(msg)
    version = data.get("version")
    if version != BROKER_APPLY_REPORT_VERSION:
        msg = f"Unsupported broker apply report version: {version!r}"
        raise ValueError(msg)
    applied = data.get("applied")
    if not isinstance(applied, list):
        msg = "Apply report must contain an 'applied' array"
        raise ValueError(msg)
    return data


def apply_integration_settings(
    report: dict[str, Any],
    *,
    client: SnykRestClient,
    source_report_path: str | Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """PUT predefined settings for each org in ``report['applied']``."""
    applied = report.get("applied")
    if not isinstance(applied, list):
        msg = "Apply report missing 'applied' array"
        raise ValueError(msg)

    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for item in applied:
        if not isinstance(item, dict):
            continue
        org_name = item.get("org_name")
        org_id = item.get("org_id")
        if not isinstance(org_name, str) or not org_name.strip():
            continue
        org_name = org_name.strip()

        if not isinstance(org_id, str) or not org_id.strip():
            failed.append(
                {
                    "org_name": org_name,
                    "org_id": org_id,
                    "error": "missing org_id on applied entry",
                }
            )
            continue
        org_id = org_id.strip()

        if dry_run:
            skipped.append(
                {
                    "org_name": org_name,
                    "org_id": org_id,
                    "reason": "dry_run",
                }
            )
            continue

        try:
            integrations = client.iter_org_integrations(org_id)
            integration_id = pick_bitbucket_server_integration_id(integrations)
            client.update_org_integration_settings(
                org_id,
                integration_id,
                BITBUCKET_SERVER_INTEGRATION_SETTINGS,
            )
            updated.append(
                {
                    "org_name": org_name,
                    "org_id": org_id,
                    "integration_id": integration_id,
                    "status": "updated",
                }
            )
        except (ValueError, RuntimeError) as exc:
            failed.append(
                {
                    "org_name": org_name,
                    "org_id": org_id,
                    "error": str(exc),
                }
            )

    return {
        "version": INTEGRATION_SETTINGS_REPORT_VERSION,
        "source_report_path": str(source_report_path),
        "settings_profile": SETTINGS_PROFILE_ID,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
    }
