"""Versioned ``projectKey → apm_code`` context for Snyk import enrichment."""

from __future__ import annotations

from typing import Any

from common.output_state import row_repo_key


PROJECT_CONTEXT_FORMAT_VERSION = 1


def project_apm_map_from_rows(rows: list[dict[str, Any]]) -> dict[str, str]:
    """Build one ``apm_code`` per Bitbucket project key.

    Args:
        rows: Primary mapping rows.

    Returns:
        Map ``project_key`` → non-empty ``apm_code`` string.

    Raises:
        ValueError: If two rows under the same project key disagree on ``apm_code``.
    """
    codes_per_project: dict[str, set[str]] = {}
    evidence: dict[str, list[tuple[str, str]]] = {}

    for row in rows:
        key = row_repo_key(row)
        if key is None:
            continue
        project_key, slug = key
        raw = row.get("apm_code")
        if not isinstance(raw, str) or not raw.strip():
            continue
        code = raw.strip()
        codes_per_project.setdefault(project_key, set()).add(code)
        evidence.setdefault(project_key, []).append((slug, code))

    result: dict[str, str] = {}
    for project_key, codes in sorted(codes_per_project.items()):
        if len(codes) > 1:
            lines = [
                f"Conflicting apm_code values for Bitbucket project {project_key!r}: "
                f"{', '.join(sorted(codes))}",
                "Repositories:",
            ]
            for slug, code in sorted(evidence.get(project_key, [])):
                lines.append(f"  - {project_key}/{slug} → {code!r}")
            raise ValueError("\n".join(lines))
        result[project_key] = next(iter(codes))

    return result


def build_project_context_document(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build ``snyk-project-context.json`` payload."""
    proj_map = project_apm_map_from_rows(rows)
    return {
        "version": PROJECT_CONTEXT_FORMAT_VERSION,
        "derived_from": "primary_mapping",
        "projects": {pk: {"apm_code": code} for pk, code in sorted(proj_map.items())},
    }


def parse_project_context_document(data: Any) -> dict[str, str]:
    """Parse project-context JSON into ``project_key → apm_code``.

    Raises:
        ValueError: If structure or version is invalid.
    """
    if not isinstance(data, dict):
        msg = "Project context must be a JSON object"
        raise ValueError(msg)
    version = data.get("version")
    if version != PROJECT_CONTEXT_FORMAT_VERSION:
        msg = f"Unsupported project context version: {version!r}"
        raise ValueError(msg)
    raw_projects = data.get("projects")
    if not isinstance(raw_projects, dict):
        msg = "Project context must contain a 'projects' object"
        raise ValueError(msg)
    out: dict[str, str] = {}
    for pk, meta in raw_projects.items():
        if not isinstance(pk, str) or not pk.strip():
            continue
        if not isinstance(meta, dict):
            msg = f"Invalid project entry for key {pk!r}"
            raise ValueError(msg)
        code = meta.get("apm_code")
        if not isinstance(code, str) or not code.strip():
            msg = f"Missing apm_code for project {pk!r}"
            raise ValueError(msg)
        out[pk.strip()] = code.strip()
    return out
