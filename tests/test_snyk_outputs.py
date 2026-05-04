"""Tests for Snyk companion JSON builders."""

from snyk.outputs import (
    SNYK_PLACEHOLDER_GROUP_ID,
    SNYK_PLACEHOLDER_INTEGRATION_ID as SNYK_PLACEHOLDER_INTEGRATION,
    SNYK_PLACEHOLDER_ORG_ID as SNYK_PLACEHOLDER_ORG,
    SNYK_PLACEHOLDER_SOURCE_ORG_ID,
    apm_codes_from_rows,
    build_snyk_import_document,
    build_snyk_orgs_document,
)


def test_build_snyk_orgs_document_sorted_distinct() -> None:
    doc = build_snyk_orgs_document({"B", "A", "B"})
    assert doc["orgs"][0]["name"] == "A"
    assert doc["orgs"][1]["name"] == "B"
    assert doc["orgs"][0]["groupId"] == SNYK_PLACEHOLDER_GROUP_ID
    assert doc["orgs"][0]["sourceOrgId"] == SNYK_PLACEHOLDER_SOURCE_ORG_ID


def test_build_snyk_orgs_document_with_resolved_ids() -> None:
    doc = build_snyk_orgs_document(
        {"Z"},
        group_id="11111111-1111-1111-1111-111111111111",
        template_org_id="22222222-2222-2222-2222-222222222222",
    )
    assert doc["orgs"][0]["name"] == "Z"
    assert doc["orgs"][0]["groupId"] == "11111111-1111-1111-1111-111111111111"
    assert doc["orgs"][0]["sourceOrgId"] == "22222222-2222-2222-2222-222222222222"


def test_apm_codes_from_rows() -> None:
    rows = [
        {"apm_code": "Z"},
        {"apm_code": None},
        {"apm_code": "  "},
        {"apm_code": "Y"},
    ]
    assert apm_codes_from_rows(rows) == {"Y", "Z"}


def test_build_snyk_import_document() -> None:
    rows = [
        {
            "repository_path": "MYPROJ/api-import-circle-test",
            "repository_name": "Snyk api-import-circle-test",
            "production_branch": "main",
        }
    ]
    doc = build_snyk_import_document(rows)
    assert len(doc["targets"]) == 1
    t0 = doc["targets"][0]
    assert t0["orgId"] == SNYK_PLACEHOLDER_ORG
    assert t0["integrationId"] == SNYK_PLACEHOLDER_INTEGRATION
    assert t0["target"]["projectKey"] == "MYPROJ"
    assert t0["target"]["repoSlug"] == "api-import-circle-test"
    assert t0["target"]["branch"] == "main"
