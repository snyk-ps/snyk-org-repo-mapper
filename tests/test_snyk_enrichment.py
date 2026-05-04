"""Tests for Snyk import enrichment helpers."""

from __future__ import annotations

import pytest

from snyk.enrichment import (
    build_name_to_org_id,
    enrich_import_document,
    org_names_from_snyk_orgs_document,
    required_apm_codes_for_import,
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
    assert required_apm_codes_for_import({"P1": "APM1"}, doc) == {"APM1"}


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
        project_apm={"P1": "APM1"},
        name_to_org_id={"APM1": "org-uuid"},
        org_to_integration_id={"org-uuid": "int-uuid"},
    )
    t0 = out["targets"][0]
    assert t0["orgId"] == "org-uuid"
    assert t0["integrationId"] == "int-uuid"
