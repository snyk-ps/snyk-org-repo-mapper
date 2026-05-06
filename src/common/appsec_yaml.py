"""Parse AppSec YAML snippets from repository files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml


@dataclass(frozen=True)
class ParsedAppSec:
    """Values extracted from the repository YAML file."""

    apm_code: str | None
    production_branch: str | None


def parse_appsec_yaml(content: str) -> ParsedAppSec:
    """Parse ``appSec`` fields from YAML text.

    Missing or invalid structures yield ``None`` fields without raising, so callers
    can fall back to API metadata.

    Args:
        content: Raw YAML text from the repository file.

    Returns:
        Parsed AppSec values.
    """
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        return ParsedAppSec(apm_code=None, production_branch=None)
    if not isinstance(data, dict):
        return ParsedAppSec(apm_code=None, production_branch=None)
    app_sec = data.get("security")
    if not isinstance(app_sec, dict):
        return ParsedAppSec(apm_code=None, production_branch=None)
    apm = _string_or_none(app_sec.get("apmCode"))
    prod = _string_or_none(app_sec.get("productionBranch"))
    return ParsedAppSec(apm_code=apm, production_branch=prod)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value).strip() or None


def resolve_production_branch(
    from_yaml: str | None,
    default_branch_display: str,
) -> str:
    """Pick the production branch name for output.

    If the YAML value is missing or blank, use the repository default branch
    display id from the API.

    Args:
        from_yaml: Optional branch from YAML.
        default_branch_display: Non-empty display id from Bitbucket (e.g. ``main``).

    Returns:
        Branch name to record in the mapping.
    """
    if from_yaml and from_yaml.strip():
        return from_yaml.strip()
    return default_branch_display
