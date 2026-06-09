"""Build Snyk API Import Tool companion JSON documents."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from common.mapper import row_is_empty


SNYK_PLACEHOLDER_GROUP_ID = "<public_snyk_group_id>"
SNYK_PLACEHOLDER_SOURCE_ORG_ID = "<public_snyk_organization_id>"
SNYK_PLACEHOLDER_ORG_ID = "******"
SNYK_PLACEHOLDER_INTEGRATION_ID = "******"

APP_TYPE_PREFIX = "BB/"

def build_snyk_orgs_document(
    apm_codes: set[str],
    *,
    group_id: str | None = None,
    template_org_id: str | None = None,
) -> dict[str, Any]:
    """Build the org-creation JSON with one entry per distinct APM code.

    Args:
        apm_codes: Non-empty APM code strings (caller filters nulls).
        group_id: If set, written as ``groupId`` for every org; otherwise the
            placeholder string is used.
        template_org_id: If set, written as ``sourceOrgId`` for every org;
            otherwise the placeholder string is used.

    Returns:
        JSON object with an ``orgs`` array.
    """
    gid = group_id if group_id is not None else SNYK_PLACEHOLDER_GROUP_ID
    src = template_org_id if template_org_id is not None else SNYK_PLACEHOLDER_SOURCE_ORG_ID
    orgs: list[dict[str, str]] = []
    for code in sorted(apm_codes):
        orgs.append(
            {
                "groupId": gid,
                "name": code,
                "sourceOrgId": src,
            }
        )
    return {"orgs": orgs}


def default_org_target_name(
    project_key: str,
    repository_name: str | None,
    repo_slug: str,
) -> str:
    """Build ``target.name`` for default-org imports: ``{projectKey}/{repo part}``."""
    if isinstance(repository_name, str) and repository_name.strip():
        repo_part = repository_name.strip()
    else:
        repo_part = repo_slug
    return f"{project_key}/{repo_part}"


def _row_apm_code(row: dict[str, Any]) -> str | None:
    raw = row.get("apm_code")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def build_snyk_import_document(
    rows: list[dict[str, Any]],
    *,
    default_org_id: str | None = None,
) -> dict[str, Any]:
    """Build the Bitbucket Server import targets document from mapping rows.

    Args:
        rows: Mapping rows including ``repository_path``, ``repository_name``,
            ``production_branch``.
        default_org_id: When set, targets whose row has no ``apm_code`` use
            composite ``target.name`` via :func:`default_org_target_name`.

    Returns:
        JSON object with a ``targets`` array.
    """
    use_default_naming = (
        default_org_id is not None
        and isinstance(default_org_id, str)
        and bool(default_org_id.strip())
    )
    targets: list[dict[str, Any]] = []
    for row in rows:
        if row_is_empty(row):
            continue
        path = row.get("repository_path")
        if not isinstance(path, str) or "/" not in path:
            continue
        project_key, _, repo_slug = path.partition("/")
        if not project_key or not repo_slug:
            continue
        name = row.get("repository_name")
        branch = row.get("production_branch")
        if use_default_naming and _row_apm_code(row) is None:
            repo_name = default_org_target_name(project_key, name, repo_slug)
        else:
            repo_name = name if isinstance(name, str) else repo_slug
        branch_name = branch if isinstance(branch, str) else ""
        targets.append(
            {
                "orgId": SNYK_PLACEHOLDER_ORG_ID,
                "integrationId": SNYK_PLACEHOLDER_INTEGRATION_ID,
                "target": {
                    "projectKey": project_key,
                    "repoSlug": repo_slug,
                    "name": f"{APP_TYPE_PREFIX}{repo_name}",
                    "branch": branch_name,
                },
            }
        )
    return {"targets": targets}


def batch_import_output_paths(output: Path, num_batches: int) -> list[Path]:
    """Return numbered output paths for batched import JSON files."""
    if num_batches < 1:
        return []
    stem = output.stem or "snyk-import"
    suffix = output.suffix or ".json"
    parent = output.parent if str(output.parent) else Path(".")
    return [parent / f"{stem}-{index:03d}{suffix}" for index in range(1, num_batches + 1)]


def split_import_targets(
    targets: list[dict[str, Any]],
    repos_per_batch: int,
) -> list[list[dict[str, Any]]]:
    """Split import targets into contiguous batches of at most ``repos_per_batch``."""
    if repos_per_batch < 1:
        msg = "repos_per_batch must be >= 1"
        raise ValueError(msg)
    if not targets:
        return []
    num_batches = math.ceil(len(targets) / repos_per_batch)
    return [
        targets[i * repos_per_batch : (i + 1) * repos_per_batch]
        for i in range(num_batches)
    ]


def apm_codes_from_rows(rows: list[dict[str, Any]]) -> set[str]:
    """Collect distinct non-null APM codes from mapping rows."""
    codes: set[str] = set()
    for row in rows:
        code = row.get("apm_code")
        if isinstance(code, str) and code.strip():
            codes.add(code.strip())
    return codes
