"""Build Snyk API Import Tool companion JSON documents."""

from __future__ import annotations

from typing import Any


SNYK_PLACEHOLDER_GROUP_ID = "<public_snyk_group_id>"
SNYK_PLACEHOLDER_SOURCE_ORG_ID = "<public_snyk_organization_id>"
SNYK_PLACEHOLDER_ORG_ID = "******"
SNYK_PLACEHOLDER_INTEGRATION_ID = "******"


def build_snyk_orgs_document(apm_codes: set[str]) -> dict[str, Any]:
    """Build the org-creation JSON with one entry per distinct APM code.

    Args:
        apm_codes: Non-empty APM code strings (caller filters nulls).

    Returns:
        JSON object with an ``orgs`` array.
    """
    orgs: list[dict[str, str]] = []
    for code in sorted(apm_codes):
        orgs.append(
            {
                "groupId": SNYK_PLACEHOLDER_GROUP_ID,
                "name": code,
                "sourceOrgId": SNYK_PLACEHOLDER_SOURCE_ORG_ID,
            }
        )
    return {"orgs": orgs}


def build_snyk_import_document(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the Bitbucket Server import targets document from mapping rows.

    Args:
        rows: Mapping rows including ``repository_path``, ``repository_name``,
            ``production_branch``.

    Returns:
        JSON object with a ``targets`` array.
    """
    targets: list[dict[str, Any]] = []
    for row in rows:
        path = row.get("repository_path")
        if not isinstance(path, str) or "/" not in path:
            continue
        project_key, _, repo_slug = path.partition("/")
        if not project_key or not repo_slug:
            continue
        name = row.get("repository_name")
        branch = row.get("production_branch")
        repo_name = name if isinstance(name, str) else repo_slug
        branch_name = branch if isinstance(branch, str) else ""
        targets.append(
            {
                "orgId": SNYK_PLACEHOLDER_ORG_ID,
                "integrationId": SNYK_PLACEHOLDER_INTEGRATION_ID,
                "target": {
                    "projectKey": project_key,
                    "repoSlug": repo_slug,
                    "name": repo_name,
                    "branch": branch_name,
                },
            }
        )
    return {"targets": targets}


def apm_codes_from_rows(rows: list[dict[str, Any]]) -> set[str]:
    """Collect distinct non-null APM codes from mapping rows."""
    codes: set[str] = set()
    for row in rows:
        code = row.get("apm_code")
        if isinstance(code, str) and code.strip():
            codes.add(code.strip())
    return codes
