"""Build broker-org-plan.json from snyk-orgs and Universal Broker connections."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from integrations.snyk.broker_client import BrokerClient
from integrations.snyk.client import SnykRestClient
from snyk.enrichment import load_json_object, org_names_from_snyk_orgs_document


BROKER_PLAN_VERSION = 1


def _org_id_by_name(api_orgs: list[dict[str, str]]) -> dict[str, str]:
    return {row["name"]: row["id"] for row in api_orgs}


def _integrated_org_keys(
    integrations: list[Any],
) -> tuple[set[str], set[str]]:
    """Return sets of org ids and lowercased org names on a connection."""
    ids: set[str] = set()
    names: set[str] = set()
    for item in integrations:
        oid = getattr(item, "org_id", None)
        oname = getattr(item, "org_name", None)
        if isinstance(oid, str) and oid.strip():
            ids.add(oid.strip())
        if isinstance(oname, str) and oname.strip():
            names.add(oname.strip().lower())
    return ids, names


def _org_matches_integration(
    org_name: str,
    org_id: str | None,
    integ_org_ids: set[str],
    integ_org_names: set[str],
) -> bool:
    if org_id and org_id in integ_org_ids:
        return True
    return org_name.strip().lower() in integ_org_names


def build_broker_org_plan(
    *,
    orgs_doc: dict[str, Any],
    broker: BrokerClient,
    snyk: SnykRestClient | None = None,
) -> dict[str, Any]:
    """Discover connections, pre-check integrations, round-robin assign orgs."""
    settings = broker._settings  # noqa: SLF001 — plan shares tenant/install for output
    org_names = sorted(org_names_from_snyk_orgs_document(orgs_doc))
    name_to_id: dict[str, str | None] = {n: None for n in org_names}
    warnings: list[str] = []

    if snyk is not None:
        api_orgs = snyk.iter_group_orgs()
        mapping = _org_id_by_name(api_orgs)
        for name in org_names:
            if name in mapping:
                name_to_id[name] = mapping[name]
            else:
                warnings.append(
                    f"Organization name {name!r} not found in Snyk group listing"
                )

    connections = broker.list_bitbucket_server_connections()
    if not connections:
        msg = (
            "No bitbucket-server broker connections found for this tenant/install. "
            "Provision connections in Universal Broker before running this stage."
        )
        raise ValueError(msg)

    integ_by_conn: dict[str, tuple[set[str], set[str]]] = {}
    for conn in connections:
        integrations = broker.list_connection_integrations(conn.connection_id)
        integ_by_conn[conn.connection_id] = _integrated_org_keys(integrations)

    already_integrated: list[dict[str, Any]] = []
    to_assign: list[str] = []

    for org_name in org_names:
        org_id = name_to_id.get(org_name)
        found_conn: str | None = None
        for cid, (iids, inames) in integ_by_conn.items():
            if _org_matches_integration(org_name, org_id, iids, inames):
                found_conn = cid
                break
        if found_conn is not None:
            already_integrated.append(
                {
                    "org_name": org_name,
                    "org_id": org_id,
                    "connection_id": found_conn,
                }
            )
        else:
            to_assign.append(org_name)

    sorted_conns = sorted(connections, key=lambda c: c.connection_id)
    assign_counts: dict[str, int] = {c.connection_id: 0 for c in sorted_conns}
    assignments: list[dict[str, Any]] = []

    for org_name in sorted(to_assign):
        cid = min(
            sorted_conns,
            key=lambda c: (assign_counts[c.connection_id], c.connection_id),
        ).connection_id
        assign_counts[cid] += 1
        assignments.append(
            {
                "org_name": org_name,
                "org_id": name_to_id.get(org_name),
                "connection_id": cid,
            }
        )

    return {
        "version": BROKER_PLAN_VERSION,
        "tenant_id": settings.tenant_id,
        "install_id": settings.install_id,
        "connections": [
            {
                "connection_id": c.connection_id,
                "deployment_id": c.deployment_id,
                "type": c.connection_type,
                "display_name": c.display_name,
            }
            for c in sorted(connections, key=lambda x: x.connection_id)
        ],
        "already_integrated": already_integrated,
        "assignments": assignments,
        "unassigned": [],
        "warnings": warnings,
    }


def load_broker_org_plan(path: Path) -> dict[str, Any]:
    doc = load_json_object(path)
    version = doc.get("version")
    if version != BROKER_PLAN_VERSION:
        msg = f"Unsupported broker-org-plan version: {version!r} (expected {BROKER_PLAN_VERSION})"
        raise ValueError(msg)
    for key in ("tenant_id", "install_id", "assignments", "already_integrated"):
        if key not in doc:
            msg = f"broker-org-plan missing required key {key!r}"
            raise ValueError(msg)
    return doc
