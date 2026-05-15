"""Build Snyk API Import Tool companion JSON documents."""

from __future__ import annotations

from typing import Any


SNYK_PLACEHOLDER_GROUP_ID = "<public_snyk_group_id>"
SNYK_PLACEHOLDER_SOURCE_ORG_ID = "<public_snyk_organization_id>"
SNYK_PLACEHOLDER_ORG_ID = "******"
SNYK_PLACEHOLDER_INTEGRATION_ID = "******"


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


def build_snyk_import_document(
    rows: list[dict[str, Any]],
    *,
    project_apm: dict[str, str] | None = None,
    default_org_id: str | None = None,
) -> dict[str, Any]:
    """Build the Bitbucket Server import targets document from mapping rows.

    Args:
        rows: Mapping rows including ``repository_path``, ``repository_name``,
            ``production_branch``.
        project_apm: Optional ``projectKey → apm_code`` map from discovery.
        default_org_id: When set, targets whose project has no APM entry use
            composite ``target.name`` via :func:`default_org_target_name`.

    Returns:
        JSON object with a ``targets`` array.
    """
    apm_map = project_apm if project_apm is not None else {}
    use_default_naming = (
        default_org_id is not None
        and isinstance(default_org_id, str)
        and bool(default_org_id.strip())
    )
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
        if use_default_naming and project_key not in apm_map:
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
