"""Stage 4 — Post-import group cleanup and normalization."""

from __future__ import annotations

from typing import Any

from integrations.snyk.client import SnykRestClient
from snyk.integration_settings_apply import apply_bitbucket_integration_settings_to_org
from snyk.integration_settings_defaults import SETTINGS_PROFILE_ID
from snyk.python_language_settings_defaults import (
    PYTHON_LANGUAGE,
    PYTHON_LANGUAGE_SETTINGS_PROFILE_ID,
    PYTHON_LANGUAGE_VERSION,
    build_python_org_language_settings_payload,
)

POST_IMPORT_CLEANUP_REPORT_VERSION = 3
RECURRING_TEST_FREQUENCY_NEVER = {"recurringTests": {"frequency": "never"}}


def _project_field(project: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        raw = project.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def _owner_remediation_base_entry(
    *,
    org_id: str,
    project_id: str,
    project_name: str | None,
    project_type: str | None,
) -> dict[str, Any]:
    return {
        "org_id": org_id,
        "project_id": project_id,
        "project_name": project_name,
        "project_type": project_type,
    }


def _remediate_project_owner(
    client: SnykRestClient,
    *,
    org_id: str,
    project_id: str,
    project_name: str | None,
    project_type: str | None,
    prior_owner_id: str | None,
    transition_user_id: str,
    dry_run: bool,
    owner_cleared: list[dict[str, Any]],
    owner_restored: list[dict[str, Any]],
    owner_skipped: list[dict[str, Any]],
    owner_failed: list[dict[str, Any]],
) -> None:
    """Restore pre-PATCH ownership after recurring-test PATCH assigned transition user."""
    base_entry = _owner_remediation_base_entry(
        org_id=org_id,
        project_id=project_id,
        project_name=project_name,
        project_type=project_type,
    )

    if dry_run:
        if prior_owner_id == transition_user_id:
            owner_skipped.append({**base_entry, "reason": "already_transition_user"})
        else:
            owner_skipped.append({**base_entry, "reason": "dry_run"})
        return

    if prior_owner_id == transition_user_id:
        owner_skipped.append({**base_entry, "reason": "already_transition_user"})
        return

    try:
        if prior_owner_id is None:
            client.clear_project_owner(org_id, project_id)
            owner_cleared.append(base_entry)
        else:
            client.set_project_owner(org_id, project_id, prior_owner_id)
            owner_restored.append({**base_entry, "prior_owner_id": prior_owner_id})
    except RuntimeError as exc:
        owner_failed.append({**base_entry, "error": str(exc)})


def run_post_import_cleanup(
    client: SnykRestClient,
    *,
    user_id: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Normalize every org in the configured Snyk group."""
    group_id = client.group_id
    transition_user_id = user_id.strip()

    dockerfile_deleted: list[dict[str, Any]] = []
    dockerfile_skipped: list[dict[str, Any]] = []
    dockerfile_failed: list[dict[str, Any]] = []

    frequency_updated: list[dict[str, Any]] = []
    frequency_skipped: list[dict[str, Any]] = []
    frequency_failed: list[dict[str, Any]] = []

    owner_cleared: list[dict[str, Any]] = []
    owner_restored: list[dict[str, Any]] = []
    owner_skipped: list[dict[str, Any]] = []
    owner_failed: list[dict[str, Any]] = []

    integration_updated: list[dict[str, Any]] = []
    integration_skipped: list[dict[str, Any]] = []
    integration_failed: list[dict[str, Any]] = []

    python_updated: list[dict[str, Any]] = []
    python_skipped: list[dict[str, Any]] = []
    python_failed: list[dict[str, Any]] = []

    for org in client.iter_group_orgs():
        org_id = org["id"]
        org_name = org["name"]

        for project in client.iter_org_projects(org_id, project_type="dockerfile"):
            project_id = _project_field(project, "id")
            project_name = _project_field(project, "name", "projectName")
            if not project_id:
                continue

            if dry_run:
                dockerfile_skipped.append(
                    {
                        "org_id": org_id,
                        "org_name": org_name,
                        "project_id": project_id,
                        "project_name": project_name,
                        "reason": "dry_run",
                    }
                )
                continue

            try:
                client.delete_org_project(org_id, project_id)
                dockerfile_deleted.append(
                    {
                        "org_id": org_id,
                        "org_name": org_name,
                        "project_id": project_id,
                        "project_name": project_name,
                    }
                )
            except RuntimeError as exc:
                dockerfile_failed.append(
                    {
                        "org_id": org_id,
                        "org_name": org_name,
                        "project_id": project_id,
                        "project_name": project_name,
                        "error": str(exc),
                    }
                )

        for project in client.iter_org_projects(org_id):
            project_id = _project_field(project, "id")
            project_name = _project_field(project, "name", "projectName")
            project_type = _project_field(project, "type")
            prior_owner_id = _project_field(project, "owner_id")
            if not project_id:
                continue

            owner_base = _owner_remediation_base_entry(
                org_id=org_id,
                project_id=project_id,
                project_name=project_name,
                project_type=project_type,
            )

            if dry_run:
                frequency_skipped.append(
                    {
                        "org_id": org_id,
                        "project_id": project_id,
                        "project_name": project_name,
                        "project_type": project_type,
                        "reason": "dry_run",
                    }
                )
                _remediate_project_owner(
                    client,
                    org_id=org_id,
                    project_id=project_id,
                    project_name=project_name,
                    project_type=project_type,
                    prior_owner_id=prior_owner_id,
                    transition_user_id=transition_user_id,
                    dry_run=True,
                    owner_cleared=owner_cleared,
                    owner_restored=owner_restored,
                    owner_skipped=owner_skipped,
                    owner_failed=owner_failed,
                )
                continue

            try:
                client.update_project_settings(
                    org_id,
                    project_id,
                    RECURRING_TEST_FREQUENCY_NEVER,
                    transition_user_id,
                )
                frequency_updated.append(
                    {
                        "org_id": org_id,
                        "project_id": project_id,
                        "project_name": project_name,
                        "project_type": project_type,
                    }
                )
                _remediate_project_owner(
                    client,
                    org_id=org_id,
                    project_id=project_id,
                    project_name=project_name,
                    project_type=project_type,
                    prior_owner_id=prior_owner_id,
                    transition_user_id=transition_user_id,
                    dry_run=False,
                    owner_cleared=owner_cleared,
                    owner_restored=owner_restored,
                    owner_skipped=owner_skipped,
                    owner_failed=owner_failed,
                )
            except RuntimeError as exc:
                error = str(exc)
                if "HTTP 404" in error:
                    frequency_skipped.append(
                        {
                            "org_id": org_id,
                            "project_id": project_id,
                            "project_name": project_name,
                            "project_type": project_type,
                            "reason": "project_not_found",
                        }
                    )
                    owner_skipped.append(
                        {**owner_base, "reason": "frequency_patch_skipped"}
                    )
                else:
                    frequency_failed.append(
                        {
                            "org_id": org_id,
                            "project_id": project_id,
                            "project_name": project_name,
                            "project_type": project_type,
                            "error": error,
                        }
                    )
                    owner_skipped.append(
                        {**owner_base, "reason": "frequency_patch_failed"}
                    )

        outcome = apply_bitbucket_integration_settings_to_org(
            client,
            org_id,
            org_name,
            dry_run=dry_run,
        )
        if outcome["status"] == "updated":
            integration_updated.append(
                {
                    "org_id": outcome["org_id"],
                    "org_name": outcome["org_name"],
                    "integration_id": outcome["integration_id"],
                }
            )
        elif outcome["status"] == "skipped":
            integration_skipped.append(
                {
                    "org_id": outcome["org_id"],
                    "org_name": outcome["org_name"],
                    "reason": outcome.get("reason", "dry_run"),
                }
            )
        else:
            integration_failed.append(
                {
                    "org_id": outcome["org_id"],
                    "org_name": outcome.get("org_name"),
                    "error": outcome.get("error", "unknown error"),
                }
            )

        if dry_run:
            python_skipped.append(
                {
                    "org_id": org_id,
                    "org_name": org_name,
                    "reason": "dry_run",
                }
            )
        else:
            try:
                client.patch_org_language_settings(
                    org_id,
                    PYTHON_LANGUAGE,
                    build_python_org_language_settings_payload(org_id),
                )
                python_updated.append(
                    {
                        "org_id": org_id,
                        "org_name": org_name,
                    }
                )
            except RuntimeError as exc:
                python_failed.append(
                    {
                        "org_id": org_id,
                        "org_name": org_name,
                        "error": str(exc),
                    }
                )

    return {
        "version": POST_IMPORT_CLEANUP_REPORT_VERSION,
        "group_id": group_id,
        "transition_user_id": transition_user_id,
        "settings_profile": SETTINGS_PROFILE_ID,
        "python_version": PYTHON_LANGUAGE_VERSION,
        "python_language_settings_profile": PYTHON_LANGUAGE_SETTINGS_PROFILE_ID,
        "dockerfile_projects": {
            "deleted": dockerfile_deleted,
            "skipped": dockerfile_skipped,
            "failed": dockerfile_failed,
        },
        "recurring_test_frequency": {
            "updated": frequency_updated,
            "skipped": frequency_skipped,
            "failed": frequency_failed,
        },
        "project_owner_remediation": {
            "cleared": owner_cleared,
            "restored": owner_restored,
            "skipped": owner_skipped,
            "failed": owner_failed,
        },
        "integration_settings": {
            "updated": integration_updated,
            "skipped": integration_skipped,
            "failed": integration_failed,
        },
        "python_language_settings": {
            "updated": python_updated,
            "skipped": python_skipped,
            "failed": python_failed,
        },
    }
