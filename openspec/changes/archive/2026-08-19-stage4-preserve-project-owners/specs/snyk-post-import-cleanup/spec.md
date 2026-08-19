# snyk-post-import-cleanup Specification (change delta)

## ADDED Requirements

### Requirement: Preserve project ownership after recurring-test PATCH

After a successful recurring-test frequency PATCH, the stage SHALL remediate project ownership so pre-PATCH ownership is preserved. The stage SHALL read `owner_id` from the REST project list before PATCH. The stage SHALL use `SNYK_USER_ID` (or `--user-id`) only as the transition owner required by the PATCH payload.

#### Scenario: Previously unassigned project

- **WHEN** a project's pre-PATCH `owner_id` is absent
- **AND** the frequency PATCH succeeds
- **AND** `--dry-run` is not set
- **THEN** the stage SHALL clear project owner via v1 PUT with `{"owner": null}`
- **AND** the entry SHALL be recorded under `project_owner_remediation.cleared`

#### Scenario: Previously owned by another user

- **WHEN** a project's pre-PATCH `owner_id` is present and not equal to `SNYK_USER_ID`
- **AND** the frequency PATCH succeeds
- **AND** `--dry-run` is not set
- **THEN** the stage SHALL restore the prior owner via v1 PUT
- **AND** the entry SHALL be recorded under `project_owner_remediation.restored` with `prior_owner_id`

#### Scenario: Already owned by transition user

- **WHEN** a project's pre-PATCH `owner_id` equals `SNYK_USER_ID`
- **AND** the frequency PATCH succeeds
- **THEN** no owner remediation PUT SHALL be issued
- **AND** the entry SHALL be recorded under `project_owner_remediation.skipped` with reason `already_transition_user`

#### Scenario: Dry run for owner remediation

- **WHEN** `--dry-run` is set
- **THEN** no owner remediation PUT requests SHALL be issued
- **AND** each project that would be remediated SHALL appear under `project_owner_remediation.skipped` with reason `dry_run`

#### Scenario: Remediation skipped when frequency PATCH failed

- **WHEN** the frequency PATCH for a project failed or was skipped with reason other than dry run
- **THEN** no owner remediation PUT SHALL be issued for that project
- **AND** the entry SHALL be recorded under `project_owner_remediation.skipped` with reason `frequency_patch_failed` or `frequency_patch_skipped`

#### Scenario: Remediation failure

- **WHEN** an owner remediation PUT returns a non-success HTTP status
- **THEN** the entry SHALL be recorded under `project_owner_remediation.failed` with error detail
- **AND** the successful frequency PATCH for that project SHALL remain in effect

### Requirement: SnykRestClient project owner v1 PUT support

The implementation SHALL provide client methods for v1 project owner updates via `PUT /v1/org/{orgId}/project/{projectId}`: `clear_project_owner` (body `{"owner": null}`) and `set_project_owner` (body `{"owner": {"id": "<user_uuid>"}}`), using the same HTTP retry behavior as existing client methods.

#### Scenario: Clear project owner via v1 PUT

- **WHEN** the stage remediates a previously unassigned project
- **THEN** the client issues a v1 PUT with `{"owner": null}`

#### Scenario: Restore project owner via v1 PUT

- **WHEN** the stage remediates a project to its prior owner
- **THEN** the client issues a v1 PUT with `{"owner": {"id": "<prior_owner_id>"}}`

## MODIFIED Requirements

### Requirement: Require user id for project settings PATCH

The stage SHALL require `SNYK_USER_ID` or `--user-id` before issuing live project settings PATCH requests. Dry-run SHALL NOT require `user_id`. The configured user id SHALL be used only as the transition owner required by the REST PATCH payload; the stage SHALL remediate ownership afterward so pre-PATCH owners are preserved.

#### Scenario: Missing user id on live run

- **WHEN** the user runs `snyk-post-import-cleanup` without `--dry-run`
- **AND** neither `SNYK_USER_ID` nor `--user-id` is set
- **THEN** the CLI exits with a validation error before any PATCH requests

#### Scenario: User id provided on live run

- **WHEN** `SNYK_USER_ID` or `--user-id` is set
- **AND** `--dry-run` is not set
- **THEN** each project settings PATCH includes `relationships.owner` with that user id
- **AND** owner remediation runs per the preserve-ownership requirement after each successful PATCH

### Requirement: Set recurring test frequency to never

For each org, after dockerfile deletion, the stage SHALL list all Snyk projects in the org via the REST Projects API and SHALL PATCH project settings so `attributes.settings.recurring_tests.frequency` is `never` on every remaining project, including `relationships.owner` referencing the configured user id. After each successful PATCH, the stage SHALL run owner remediation per the preserve-ownership requirement.

#### Scenario: Successful frequency update

- **WHEN** the project settings PATCH succeeds for a project
- **THEN** the entry is recorded under `recurring_test_frequency.updated` with `org_id`, `project_id`, `project_name`, and `project_type`
- **AND** owner remediation is attempted for that project

#### Scenario: Frequency PATCH HTTP error

- **WHEN** the project settings PATCH returns a non-success HTTP status other than 404
- **THEN** the entry is recorded under `recurring_test_frequency.failed` with `org_id`, `project_id`, and error detail
- **AND** the stage continues processing other projects and orgs
- **AND** no owner remediation PUT is issued for that project

#### Scenario: Dry run for frequency update

- **WHEN** `--dry-run` is set
- **THEN** no project settings PATCH requests are issued
- **AND** each eligible project appears under `recurring_test_frequency.skipped` with reason `dry_run`
- **AND** intended owner remediation appears under `project_owner_remediation.skipped` with reason `dry_run`

### Requirement: Emit post-import-cleanup-report.json

The stage SHALL write a version 3 report with `dockerfile_projects`, `recurring_test_frequency`, `integration_settings`, `python_language_settings`, and `project_owner_remediation` outcome buckets and metadata including `group_id`, `settings_profile`, `python_version`, and `transition_user_id`.

#### Scenario: Report written

- **WHEN** the stage completes
- **THEN** the output file contains `version: 3`, `group_id`, `settings_profile: "bitbucket-server-default-v1"`, `python_version: "3.12"`, and `transition_user_id` set to the configured user id used for PATCH

#### Scenario: Partial failure exit code

- **WHEN** any entry exists under `dockerfile_projects.failed`, `recurring_test_frequency.failed`, `integration_settings.failed`, `python_language_settings.failed`, or `project_owner_remediation.failed`
- **THEN** the CLI exits with a non-zero status

### Requirement: SnykRestClient project API support

The implementation SHALL provide client methods for paginated REST org project listing, REST project deletion, REST project settings PATCH with `relationships.owner`, and v1 project owner PUT (clear and set), using the same HTTP retry behavior as existing client methods.

#### Scenario: List projects with type filter

- **WHEN** the stage requests dockerfile projects for an org
- **THEN** the client uses `GET /rest/orgs/{orgId}/projects` with pagination
- **AND** filters to type `dockerfile` client-side

#### Scenario: Delete project via REST

- **WHEN** the stage deletes a project
- **THEN** the client issues a REST DELETE for that org and project id

#### Scenario: Update project settings via REST PATCH

- **WHEN** the stage sets recurring test frequency
- **THEN** the client issues a REST PATCH to `/rest/orgs/{orgId}/projects/{projectId}`
- **AND** the request body includes `attributes.settings.recurring_tests.frequency` and `relationships.owner`

#### Scenario: Remediate project owner via v1 PUT

- **WHEN** the stage remediates project ownership after a successful frequency PATCH
- **THEN** the client issues a v1 PUT to `/v1/org/{orgId}/project/{projectId}` with the appropriate owner body
