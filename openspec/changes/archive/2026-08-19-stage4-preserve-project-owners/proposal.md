## Why

Stage 4 (`snyk-post-import-cleanup`) PATCHes recurring test frequency to `never` via the Snyk REST Projects API. That PATCH **requires** `relationships.owner` with `SNYK_USER_ID`, which **assigns that user as project owner** on every project touched — overwriting existing owners and assigning an owner where none existed.

The one-off script from `2026-08-12-clear-project-owner-script` clears owners group-wide after the fact, but it is blunt: it removes **all** owners in scope, not just the unintended `SNYK_USER_ID` assignments. Operators need Stage 4 itself to **preserve pre-existing project ownership** and only revert the transition UUID side effect.

## What Changes

- Extend Stage 4 recurring-test step: **capture `owner_id` from REST project list before PATCH**, PATCH settings with `SNYK_USER_ID` as today, then **remediate ownership** per project:
  - **Previously unassigned** (`owner_id` absent): v1 PUT `{"owner": null}` (reuse `clear_project_owner`); skip PUT when already unassigned and PATCH was not attempted.
  - **Previously owned by another user** (`owner_id` ≠ `SNYK_USER_ID`): v1 PUT restore original owner UUID.
  - **Already owned by `SNYK_USER_ID`**: no remediation PUT.
- Add **`SnykRestClient.set_project_owner(org_id, project_id, user_id)`** (v1 PUT wrapper) for the restore path.
- Reuse remediation patterns from [`src/snyk/clear_project_owners.py`](../../../src/snyk/clear_project_owners.py); do not invoke the script from Stage 4.
- Bump **`post-import-cleanup-report.json` to version 3** with `project_owner_remediation` outcome buckets (`cleared`, `restored`, `skipped`, `failed`) and metadata `transition_user_id` (= `SNYK_USER_ID`).
- Update README Stage 4 docs, CLI help, and UAT checklist: **`SNYK_USER_ID` is required for the PATCH payload only** — Stage 4 does **not** intend to leave that user as permanent owner on previously unassigned or differently owned projects.
- Update README `scripts/clear_project_owners.py` section: retained for **legacy** Stage 4 runs and bulk org-wide cleanup; **not required** after this change for normal Stage 4 operation.

**Out of scope:**

- Changing the REST PATCH to omit `relationships.owner` (API requirement).
- Replacing v1 owner PUT with REST for remediation.
- Selective scope by org list / `--orgs` on Stage 4 (continues to process full `SNYK_GROUP_ID`).
- Migrating recurring-test update from REST PATCH to v1 settings-only PUT.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `snyk-post-import-cleanup`: After recurring-test PATCH, selectively remediate project ownership to preserve pre-PATCH state; report schema v3.

## Impact

- **Code**: [`src/snyk/post_import_cleanup.py`](../../../src/snyk/post_import_cleanup.py), [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py), [`src/commands/snyk_post_import_cleanup_cli.py`](../../../src/commands/snyk_post_import_cleanup_cli.py).
- **Tests**: extend [`tests/test_post_import_cleanup.py`](../../../tests/test_post_import_cleanup.py); client tests for `set_project_owner`; remediation scenarios (unassigned → clear, other owner → restore, same owner → skip).
- **Docs**: [`README.md`](../../../README.md) Stage 4 section, report schema, UAT checklist, `clear_project_owners` script note.
- **APIs**: existing REST project PATCH; v1 `PUT /org/{orgId}/project/{projectId}` with `owner: null` or `owner: "<uuid>"`.
