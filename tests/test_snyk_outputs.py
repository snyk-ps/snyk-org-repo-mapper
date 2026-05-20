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
    assert t0["target"]["name"] == "Snyk api-import-circle-test"
    assert t0["target"]["branch"] == "main"


def test_default_org_target_name_uses_display_or_slug() -> None:
    from snyk.outputs import default_org_target_name

    assert default_org_target_name("P", "My Service", "my-service") == "P/My Service"
    assert default_org_target_name("P", None, "my-service") == "P/my-service"
    assert default_org_target_name("P", "  ", "my-service") == "P/my-service"


def test_build_snyk_import_document_default_org_composite_names() -> None:
    rows = [
        {
            "repository_path": "P1/foo",
            "repository_name": "foo",
            "production_branch": "",
        },
        {
            "repository_path": "P2/foo",
            "repository_name": "foo",
            "production_branch": "",
        },
    ]
    doc = build_snyk_import_document(
        rows,
        project_apm={},
        default_org_id="00000000-0000-0000-0000-000000000001",
    )
    names = [t["target"]["name"] for t in doc["targets"]]
    assert names == ["P1/foo", "P2/foo"]


def test_build_snyk_import_document_apm_project_unprefixed_name() -> None:
    rows = [
        {
            "repository_path": "P1/my-service",
            "repository_name": "My Service",
            "production_branch": "main",
        },
    ]
    doc = build_snyk_import_document(
        rows,
        project_apm={"P1": "APM1"},
        default_org_id="00000000-0000-0000-0000-000000000001",
    )
    assert doc["targets"][0]["target"]["name"] == "My Service"


def test_build_snyk_import_document_default_org_slug_fallback() -> None:
    rows = [
        {
            "repository_path": "NOPM/r1",
            "repository_name": None,
            "production_branch": "",
        },
    ]
    doc = build_snyk_import_document(
        rows,
        project_apm={},
        default_org_id="default-org-id",
    )
    assert doc["targets"][0]["target"]["name"] == "NOPM/r1"


def test_build_snyk_import_document_skips_empty_rows() -> None:
    rows = [
        {
            "repository_path": "P1/empty",
            "repository_name": "empty",
            "production_branch": "",
            "is_empty": True,
        },
        {
            "repository_path": "P1/active",
            "repository_name": "active",
            "production_branch": "main",
            "is_empty": False,
        },
    ]
    doc = build_snyk_import_document(rows)
    assert len(doc["targets"]) == 1
    assert doc["targets"][0]["target"]["repoSlug"] == "active"


def test_build_snyk_import_document_includes_legacy_rows_without_is_empty() -> None:
    rows = [
        {
            "repository_path": "P1/legacy",
            "repository_name": "legacy",
            "production_branch": "main",
        },
    ]
    doc = build_snyk_import_document(rows)
    assert len(doc["targets"]) == 1
