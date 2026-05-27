"""Resolve org and integration IDs for Snyk import JSON (stage 2 logic)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from integrations.snyk.client import SnykRestClient, pick_bitbucket_server_integration_id
from snyk.project_context import RepoApmMap


def org_names_from_snyk_orgs_document(doc: dict[str, Any]) -> set[str]:
    """Return normalized org ``name`` strings from a snyk-orgs style document."""
    raw = doc.get("orgs")
    if not isinstance(raw, list):
        msg = "snyk-orgs document must contain an 'orgs' array"
        raise ValueError(msg)
    names: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str):
            stripped = name.strip()
            if stripped:
                names.add(stripped)
    return names


def _target_repo_key(tgt: dict[str, Any]) -> tuple[str, str] | None:
    pk = tgt.get("projectKey")
    slug = tgt.get("repoSlug")
    if not isinstance(pk, str) or not pk.strip():
        return None
    if not isinstance(slug, str) or not slug.strip():
        return None
    return pk.strip(), slug.strip()


def required_apm_codes_for_import(
    repo_apm: RepoApmMap,
    import_doc: dict[str, Any],
    *,
    default_org_id: str | None = None,
) -> set[str]:
    """Collect ``apm_code`` values needed for all import targets.

    Targets with no ``apm_code`` in ``repo_apm`` are skipped when
    ``default_org_id`` is a non-empty string (those targets use the default org).
    """
    targets = import_doc.get("targets")
    if not isinstance(targets, list):
        msg = "snyk-import document must contain a 'targets' array"
        raise ValueError(msg)
    needed: set[str] = set()
    for i, item in enumerate(targets):
        if not isinstance(item, dict):
            continue
        tgt = item.get("target")
        if not isinstance(tgt, dict):
            msg = f"targets[{i}] missing 'target' object"
            raise ValueError(msg)
        repo_key = _target_repo_key(tgt)
        if repo_key is None:
            pk = tgt.get("projectKey")
            slug = tgt.get("repoSlug")
            if not isinstance(pk, str) or not pk.strip():
                msg = f"targets[{i}].target.projectKey missing or invalid"
                raise ValueError(msg)
            msg = f"targets[{i}].target.repoSlug missing or invalid"
            raise ValueError(msg)
        project_key, repo_slug = repo_key
        code = repo_apm.get(repo_key)
        if code is None:
            if default_org_id is not None and default_org_id.strip():
                continue
            msg = (
                f"No apm_code for repository {project_key}/{repo_slug!r} "
                f"(targets[{i}]). Add discovery YAML APM or pass --default-org-id."
            )
            raise ValueError(msg)
        needed.add(code)
    return needed


def validate_orgs_file_lists_codes(
    *,
    org_names_in_file: set[str],
    required_codes: set[str],
) -> None:
    """Ensure every required APM/org name appears in the orgs file."""
    missing = sorted(required_codes - org_names_in_file)
    if missing:
        msg = (
            "Required organization names (apm_code) missing from snyk-orgs file: "
            + ", ".join(repr(m) for m in missing)
        )
        raise ValueError(msg)


def build_name_to_org_id(api_orgs: list[dict[str, str]]) -> dict[str, str]:
    """Map org name → id; raises if duplicate names."""
    out: dict[str, str] = {}
    for row in api_orgs:
        name = row["name"]
        oid = row["id"]
        if name in out and out[name] != oid:
            msg = f"Duplicate organization name in Snyk group: {name!r}"
            raise ValueError(msg)
        out[name] = oid
    return out


def enrich_import_document(
    import_doc: dict[str, Any],
    *,
    repo_apm: RepoApmMap,
    name_to_org_id: dict[str, str],
    org_to_integration_id: dict[str, str],
    default_org_id: str | None = None,
) -> dict[str, Any]:
    """Return a new import document with ``orgId`` and ``integrationId`` set."""
    targets = import_doc.get("targets")
    if not isinstance(targets, list):
        msg = "snyk-import document must contain a 'targets' array"
        raise ValueError(msg)
    new_targets: list[dict[str, Any]] = []
    for item in targets:
        if not isinstance(item, dict):
            new_targets.append(item)
            continue
        clone = dict(item)
        tgt = clone.get("target")
        if not isinstance(tgt, dict):
            new_targets.append(clone)
            continue
        repo_key = _target_repo_key(tgt)
        if repo_key is None:
            new_targets.append(clone)
            continue
        code = repo_apm.get(repo_key)
        if code is None:
            if default_org_id is None or not default_org_id.strip():
                new_targets.append(clone)
                continue
            org_id = default_org_id.strip()
            integ_id = org_to_integration_id.get(org_id)
            if integ_id is None:
                msg = f"No cached integration id for org {org_id!r}"
                raise RuntimeError(msg)
            clone["orgId"] = org_id
            clone["integrationId"] = integ_id
            new_targets.append(clone)
            continue
        org_id = name_to_org_id.get(code)
        if org_id is None:
            msg = f"No Snyk organization named {code!r} in group (after API listing)"
            raise ValueError(msg)
        integ_id = org_to_integration_id.get(org_id)
        if integ_id is None:
            msg = f"No cached integration id for org {org_id!r}"
            raise RuntimeError(msg)
        clone["orgId"] = org_id
        clone["integrationId"] = integ_id
        new_targets.append(clone)
    out_doc = dict(import_doc)
    out_doc["targets"] = new_targets
    return out_doc


def load_json_object(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        msg = f"Expected JSON object in {path}"
        raise ValueError(msg)
    return data


def integration_cache_for_orgs(
    client: SnykRestClient,
    org_ids: set[str],
) -> dict[str, str]:
    """Map org id → bitbucket-server integration id."""
    out: dict[str, str] = {}
    for oid in sorted(org_ids):
        integrations = client.iter_org_integrations(oid)
        out[oid] = pick_bitbucket_server_integration_id(integrations)
    return out


def summarize_enrichment_plan(
    import_doc: dict[str, Any],
    repo_apm: RepoApmMap,
    name_to_org_id: dict[str, str],
    org_to_integration_id: dict[str, str],
    *,
    default_org_id: str | None = None,
) -> str:
    """Human-readable dry-run summary."""
    lines: list[str] = []
    targets = import_doc.get("targets")
    if not isinstance(targets, list):
        return "Invalid import document"
    for i, item in enumerate(targets):
        if not isinstance(item, dict):
            continue
        tgt = item.get("target")
        if not isinstance(tgt, dict):
            continue
        repo_key = _target_repo_key(tgt)
        if repo_key is None:
            continue
        project_key, repo_slug = repo_key
        code = repo_apm.get(repo_key)
        if code is None:
            if default_org_id is not None and default_org_id.strip():
                oid = default_org_id.strip()
                iid = org_to_integration_id.get(oid, "?")
                cur_o = item.get("orgId")
                cur_i = item.get("integrationId")
                lines.append(
                    f"targets[{i}] {project_key}/{repo_slug}: no apm_code; "
                    f"default orgId={oid!r} integrationId={iid!r} "
                    f"(current orgId={cur_o!r} integrationId={cur_i!r})"
                )
            else:
                lines.append(
                    f"targets[{i}] {project_key}/{repo_slug}: NO apm_code in discovery"
                )
            continue
        oid = name_to_org_id.get(code, "?")
        iid = "?"
        if isinstance(oid, str) and oid != "?":
            iid = org_to_integration_id.get(oid, "?")
        cur_o = item.get("orgId")
        cur_i = item.get("integrationId")
        lines.append(
            f"targets[{i}] {project_key}/{repo_slug} apm={code!r} -> "
            f"orgId={oid} integrationId={iid} "
            f"(current orgId={cur_o!r} integrationId={cur_i!r})"
        )
    return "\n".join(lines) if lines else "(no targets)"
