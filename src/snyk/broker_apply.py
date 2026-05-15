"""Stage 2.2 — Broker Apply: apply broker-org-plan.json by POSTing org–connection integrations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from integrations.snyk.broker_client import (
    BrokerClient,
    BrokerIntegrationConflictError,
)
from integrations.snyk.client import SnykRestClient
from snyk.broker_plan import load_broker_org_plan


BROKER_APPLY_REPORT_VERSION = 1


def _already_on_connection(
    plan: dict[str, Any],
    org_name: str,
    connection_id: str,
) -> bool:
    for row in plan.get("already_integrated", []):
        if not isinstance(row, dict):
            continue
        if row.get("org_name") == org_name and row.get("connection_id") == connection_id:
            return True
    return False


def _resolve_org_id(
    org_name: str,
    org_id: str | None,
    name_to_id: dict[str, str],
) -> str | None:
    if isinstance(org_id, str) and org_id.strip():
        return org_id.strip()
    return name_to_id.get(org_name)


def _live_integrated_org_ids(
    broker: BrokerClient,
    connection_id: str,
) -> set[str]:
    ids: set[str] = set()
    for item in broker.list_connection_integrations(connection_id):
        if item.org_id:
            ids.add(item.org_id)
    return ids


def apply_broker_org_plan(
    plan: dict[str, Any],
    *,
    broker: BrokerClient,
    snyk: SnykRestClient | None = None,
    plan_path: str | Path = "broker-org-plan.json",
    dry_run: bool = False,
) -> dict[str, Any]:
    """POST integrations for each assignment; return apply report."""
    assignments = plan.get("assignments")
    if not isinstance(assignments, list):
        msg = "broker-org-plan missing 'assignments' array"
        raise ValueError(msg)

    name_to_id: dict[str, str] = {}
    if snyk is not None:
        for row in snyk.iter_group_orgs():
            name_to_id[row["name"]] = row["id"]

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    live_cache: dict[str, set[str]] = {}

    for item in assignments:
        if not isinstance(item, dict):
            continue
        org_name = item.get("org_name")
        connection_id = item.get("connection_id")
        raw_org_id = item.get("org_id")
        if not isinstance(org_name, str) or not org_name.strip():
            continue
        if not isinstance(connection_id, str) or not connection_id.strip():
            failed.append(
                {
                    "org_name": org_name,
                    "org_id": raw_org_id,
                    "connection_id": connection_id,
                    "error": "missing connection_id",
                }
            )
            continue
        org_name = org_name.strip()
        connection_id = connection_id.strip()

        if _already_on_connection(plan, org_name, connection_id):
            skipped.append(
                {
                    "org_name": org_name,
                    "connection_id": connection_id,
                    "reason": "already_integrated",
                }
            )
            continue

        org_id = _resolve_org_id(
            org_name,
            raw_org_id if isinstance(raw_org_id, str) else None,
            name_to_id,
        )
        if org_id is None:
            failed.append(
                {
                    "org_name": org_name,
                    "org_id": None,
                    "connection_id": connection_id,
                    "error": (
                        "org_id required: set SNYK_GROUP_ID and ensure org exists in "
                        "Snyk, or include org_id in broker-org-plan assignments"
                    ),
                }
            )
            continue

        if connection_id not in live_cache:
            live_cache[connection_id] = _live_integrated_org_ids(broker, connection_id)
        if org_id in live_cache[connection_id]:
            skipped.append(
                {
                    "org_name": org_name,
                    "connection_id": connection_id,
                    "reason": "already_integrated",
                }
            )
            continue

        if dry_run:
            applied.append(
                {
                    "org_name": org_name,
                    "org_id": org_id,
                    "connection_id": connection_id,
                    "status": "dry_run",
                }
            )
            continue

        try:
            broker.create_org_integration(connection_id, org_id)
            live_cache[connection_id].add(org_id)
            applied.append(
                {
                    "org_name": org_name,
                    "org_id": org_id,
                    "connection_id": connection_id,
                    "status": "created",
                }
            )
        except BrokerIntegrationConflictError:
            skipped.append(
                {
                    "org_name": org_name,
                    "connection_id": connection_id,
                    "reason": "already_integrated",
                }
            )
        except RuntimeError as exc:
            failed.append(
                {
                    "org_name": org_name,
                    "org_id": org_id,
                    "connection_id": connection_id,
                    "error": str(exc),
                }
            )

    return {
        "version": BROKER_APPLY_REPORT_VERSION,
        "plan_path": str(plan_path),
        "applied": applied,
        "skipped": skipped,
        "failed": failed,
    }


def load_and_apply_plan_file(
    plan_path: Path,
    *,
    broker: BrokerClient,
    snyk: SnykRestClient | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    plan = load_broker_org_plan(plan_path)
    return apply_broker_org_plan(
        plan,
        broker=broker,
        snyk=snyk,
        plan_path=plan_path,
        dry_run=dry_run,
    )
