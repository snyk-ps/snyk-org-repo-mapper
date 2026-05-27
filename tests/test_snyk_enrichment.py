"""Tests for Snyk import enrichment helpers."""

from __future__ import annotations

import pytest

from snyk.enrichment import (
    build_name_to_org_id,
    enrich_import_document,
    org_names_from_snyk_orgs_document,
    required_apm_codes_for_import,
    summarize_enrichment_plan,
    validate_orgs_file_lists_codes,
)


def test_org_names_from_orgs_doc() -> None:
    doc = {"orgs": [{"name": " A "}, {"name": "B"}, {"groupId": "x"}]}
    assert org_names_from_snyk_orgs_document(doc) == {"A", "B"}


def test_required_apm_codes() -> None:
    doc = {
        "targets": [
            {
                "target": {"projectKey": "P1", "repoSlug": "r"},
            }
        ]
    }
    assert required_apm_codes_for_import({("P1", "r"): "APM1"}, doc) == {"APM1"}


def test_required_apm_codes_skips_missing_project_when_default_org() -> None:
    doc = {
        "targets": [
            {"target": {"projectKey": "P1", "repoSlug": "a"}},
            {"target": {"projectKey": "P2", "repoSlug": "b"}},
        ]
    }
    assert required_apm_codes_for_import(
        {("P1", "a"): "APM1"}, doc, default_org_id="org-fallback-uuid"
    ) == {"APM1"}


def test_required_apm_codes_missing_project_raises_without_default() -> None:
    doc = {"targets": [{"target": {"projectKey": "PX", "repoSlug": "r"}}]}
    with pytest.raises(ValueError, match="No apm_code"):
        required_apm_codes_for_import({}, doc)


def test_enrich_import_document_uses_default_org_when_no_apm() -> None:
    import_doc = {
        "targets": [
            {
                "orgId": "******",
                "integrationId": "******",
                "target": {"projectKey": "P1", "repoSlug": "r", "name": "r", "branch": ""},
            }
        ]
    }
    out = enrich_import_document(
        import_doc,
        repo_apm={},
        name_to_org_id={},
        org_to_integration_id={"default-org-uuid": "int-uuid"},
        default_org_id="default-org-uuid",
    )
    t0 = out["targets"][0]
    assert t0["orgId"] == "default-org-uuid"
    assert t0["integrationId"] == "int-uuid"


def test_summarize_plan_shows_default_org() -> None:
    import_doc = {
        "targets": [
            {
                "orgId": "******",
                "target": {"projectKey": "P1", "repoSlug": "r", "name": "r", "branch": ""},
            }
        ]
    }
    text = summarize_enrichment_plan(
        import_doc,
        {},
        {},
        {"fallback-id": "int-1"},
        default_org_id="fallback-id",
    )
    assert "no apm_code" in text
    assert "fallback-id" in text
    assert "int-1" in text


def test_validate_orgs_file_missing() -> None:
    with pytest.raises(ValueError, match="missing from snyk-orgs"):
        validate_orgs_file_lists_codes(org_names_in_file={"A"}, required_codes={"A", "B"})


def test_build_name_to_org_id_duplicate() -> None:
    with pytest.raises(ValueError, match="Duplicate organization name"):
        build_name_to_org_id(
            [
                {"name": "X", "id": "1"},
                {"name": "X", "id": "2"},
            ]
        )


def test_enrich_import_document_two_apm_codes_same_project() -> None:
    import_doc = {
        "targets": [
            {
                "orgId": "******",
                "integrationId": "******",
                "target": {
                    "projectKey": "ACCP",
                    "repoSlug": "accelerator",
                    "name": "accelerator",
                    "branch": "",
                },
            },
            {
                "orgId": "******",
                "integrationId": "******",
                "target": {
                    "projectKey": "ACCP",
                    "repoSlug": "accelerator-build-engine",
                    "name": "accelerator-build-engine",
                    "branch": "",
                },
            },
        ]
    }
    out = enrich_import_document(
        import_doc,
        repo_apm={
            ("ACCP", "accelerator"): "ABCD",
            ("ACCP", "accelerator-build-engine"): "ABCE",
        },
        name_to_org_id={"ABCD": "org-abcd", "ABCE": "org-abce"},
        org_to_integration_id={"org-abcd": "int-abcd", "org-abce": "int-abce"},
    )
    assert out["targets"][0]["orgId"] == "org-abcd"
    assert out["targets"][1]["orgId"] == "org-abce"


def test_enrich_import_document_mixed_default_org_in_same_project() -> None:
    import_doc = {
        "targets": [
            {
                "orgId": "******",
                "integrationId": "******",
                "target": {"projectKey": "P1", "repoSlug": "a", "name": "a", "branch": ""},
            },
            {
                "orgId": "******",
                "integrationId": "******",
                "target": {"projectKey": "P1", "repoSlug": "b", "name": "P1/b", "branch": ""},
            },
        ]
    }
    out = enrich_import_document(
        import_doc,
        repo_apm={("P1", "a"): "APM1"},
        name_to_org_id={"APM1": "org-apm"},
        org_to_integration_id={"org-apm": "int-apm", "default-org": "int-default"},
        default_org_id="default-org",
    )
    assert out["targets"][0]["orgId"] == "org-apm"
    assert out["targets"][1]["orgId"] == "default-org"


def test_enrich_import_document() -> None:
    import_doc = {
        "targets": [
            {
                "orgId": "******",
                "integrationId": "******",
                "target": {"projectKey": "P1", "repoSlug": "r", "name": "r", "branch": ""},
            }
        ]
    }
    out = enrich_import_document(
        import_doc,
        repo_apm={("P1", "r"): "APM1"},
        name_to_org_id={"APM1": "org-uuid"},
        org_to_integration_id={"org-uuid": "int-uuid"},
    )
    t0 = out["targets"][0]
    assert t0["orgId"] == "org-uuid"
    assert t0["integrationId"] == "int-uuid"
