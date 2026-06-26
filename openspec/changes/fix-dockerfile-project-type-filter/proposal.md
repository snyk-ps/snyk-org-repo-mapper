## Why

Stage 4 (`snyk-post-import-cleanup`) fails immediately for customers with **HTTP 400 Bad Request** when listing Dockerfile projects. The root cause is an incorrect Snyk v1 query parameter: the client sends `type=dockerfile` but the API expects `types=dockerfile`. Stage 4 never reaches project deletion because the first filtered list call fails per org.

## What Changes

- Fix `SnykRestClient.iter_org_projects` to append `types={value}` (not `type={value}`) when `project_type` is set.
- Update the unit test that asserts the constructed v1 projects URL.
- Clarify the OpenSpec requirement and design note for the correct Snyk v1 filter parameter.

**Out of scope:**

- Changing delete or project-settings APIs (audited as correct).
- Consolidating Stage 4 to a single unfiltered project list per org (optional future optimization).
- Migrating Stage 4 project listing from v1 to REST.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `snyk-post-import-cleanup`: Dockerfile project listing SHALL use the Snyk v1 `types` query parameter per API documentation.

## Impact

- **Code**: [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py) (`iter_org_projects`).
- **Tests**: [`tests/test_snyk_client_post_import_cleanup.py`](../../../tests/test_snyk_client_post_import_cleanup.py).
- **Docs / specs**: OpenSpec delta under this change; no README change required (user-facing behavior is unchanged—Stage 4 should work as originally documented).
