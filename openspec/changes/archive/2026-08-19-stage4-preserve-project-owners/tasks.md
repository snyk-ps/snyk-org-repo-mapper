## 1. Client

- [x] 1.1 Add `SnykRestClient.set_project_owner(org_id, project_id, user_id)` — v1 PUT `{"owner": "<uuid>"}`
- [x] 1.2 Add client unit test for `set_project_owner` mirroring `test_clear_project_owner_put`

## 2. Stage 4 orchestration

- [x] 2.1 In `run_post_import_cleanup`, capture `owner_id` per project before frequency PATCH
- [x] 2.2 After successful PATCH, remediate ownership per decision table (clear / restore / skip)
- [x] 2.3 Skip remediation when frequency PATCH failed or was skipped (404, dry-run)
- [x] 2.4 Bump `POST_IMPORT_CLEANUP_REPORT_VERSION` to `3`; add `transition_user_id` and `project_owner_remediation` buckets
- [x] 2.5 Extend CLI failure detection for `project_owner_remediation.failed`

## 3. Tests

- [x] 3.1 Unassigned project: PATCH then `clear_project_owner` called
- [x] 3.2 Other owner: PATCH then `set_project_owner` with prior UUID
- [x] 3.3 Prior owner = `SNYK_USER_ID`: no remediation PUT
- [x] 3.4 Dry-run: remediation actions appear under `project_owner_remediation.skipped` with `dry_run`
- [x] 3.5 Remediation failure recorded; frequency update still in `updated`
- [x] 3.6 Update existing tests expecting report `version: 2` to `version: 3`

## 4. Documentation

- [x] 4.1 README Stage 4 overview: explain `SNYK_USER_ID` transition UUID and automatic owner preservation
- [x] 4.2 README Stage 4 env table: clarify `SNYK_USER_ID` purpose (PATCH requirement, not permanent owner)
- [x] 4.3 README report schema v3: document `project_owner_remediation` and `transition_user_id`
- [x] 4.4 README UAT checklist: validate owner preserved on project with pre-existing owner; unassigned stays unassigned after live run
- [x] 4.5 README `clear_project_owners.py`: mark as legacy/bulk tool; point to built-in Stage 4 behavior
- [x] 4.6 Update `snyk-post-import-cleanup` CLI help text
