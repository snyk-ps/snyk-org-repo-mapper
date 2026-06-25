"""Predefined org Python language settings for Stage 4."""

from __future__ import annotations

from typing import Any

PYTHON_LANGUAGE = "python"
PYTHON_LANGUAGE_VERSION = "3.12"
PYTHON_LANGUAGE_SETTINGS_PROFILE_ID = "python-org-default-3.12"


def build_python_org_language_settings_payload(org_id: str) -> dict[str, Any]:
    """Build JSON:API PATCH body for org Python language settings."""
    return {
        "data": {
            "type": "language_settings",
            "id": org_id.strip(),
            "attributes": {
                "package_managers": {
                    "pip": {
                        "python_version": PYTHON_LANGUAGE_VERSION,
                    },
                },
            },
        },
    }
