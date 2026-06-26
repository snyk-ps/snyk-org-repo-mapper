# snyk-post-import-cleanup Specification

## Purpose

Stage 4 normalizes every organization in the configured Snyk group after import: deletes Dockerfile projects, disables recurring tests on all projects, and re-applies the Stage 2.3 Bitbucket Server integration settings profile.

## Requirements

### Requirement: Require Snyk group credentials

The stage SHALL require `SNYK_TOKEN` and `SNYK_GROUP_ID` and SHALL iterate all organizations returned by the Snyk group orgs API for that group id.

#### Scenario: Valid credentials

- **WHEN** the user runs `snyk-post-import-cleanup` with valid `SNYK_TOKEN` and `SNYK_GROUP_ID`
- **THEN** the stage processes every org in the group

#### Scenario: Missing group id

- **WHEN** `SNYK_GROUP_ID` is unset or empty
- **THEN** the stage exits with a non-zero status and a validation error

### Requirement: Delete dockerfile projects per org

For each org, the stage SHALL list Snyk projects filtered to type `dockerfile` and SHALL delete each listed project.

#### Scenario: Dockerfile project deleted

- **WHEN** an org has one or more projects with type `dockerfile`
- **AND** `--dry-run` is not set
- **THEN** each such project is deleted via the Snyk API
- **AND** each deletion is recorded under `dockerfile_projects.deleted` with `org_id`, `org_name`, `project_id`, and `project_name`

#### Scenario: No dockerfile projects

- **WHEN** an org has no dockerfile projects
- **THEN** no delete requests are issued for that org
- **AND** the stage continues to the next step for that org

#### Scenario: Delete HTTP error

- **WHEN** a project delete returns a non-success HTTP status
- **THEN** the entry is recorded under `dockerfile_projects.failed` with error detail
- **AND** the stage continues processing other projects and orgs

#### Scenario: Dry run for dockerfile delete

- **WHEN** `--dry-run` is set
- **THEN** no delete requests are issued
- **AND** each eligible dockerfile project appears under `dockerfile_projects.skipped` with reason `dry_run`

### Requirement: Set recurring test frequency to never

For each org, after dockerfile deletion, the stage SHALL list all Snyk projects in the org and SHALL PUT project settings so `recurringTests.frequency` is `never` on every project.

#### Scenario: Successful frequency update

- **WHEN** the project settings PUT succeeds for a project
- **THEN** the entry is recorded under `recurring_test_frequency.updated` with `org_id`, `project_id`, `project_name`, and `project_type`

#### Scenario: Frequency PUT HTTP error

- **WHEN** the project settings PUT returns a non-success HTTP status
- **THEN** the entry is recorded under `recurring_test_frequency.failed` with `org_id`, `project_id`, and error detail
- **AND** the stage continues processing other projects and orgs

#### Scenario: Dry run for frequency update

- **WHEN** `--dry-run` is set
- **THEN** no project settings PUT requests are issued
- **AND** each eligible project appears under `recurring_test_frequency.skipped` with reason `dry_run`

### Requirement: Require Snyk Integrations v1 API for integration settings

The integration settings step SHALL use the Snyk v1 API for integration listing and settings updates.

#### Scenario: REST integrations API configured

- **WHEN** `SNYK_INTEGRATIONS_API` is `rest`
- **THEN** the stage exits with a non-zero status and a message to set `SNYK_INTEGRATIONS_API=v1`

### Requirement: Apply predefined integration settings profile per org

For each org, the stage SHALL resolve the **bitbucket-server** integration id using the same rules as Stage 3 import enrichment and SHALL PUT the predefined settings object (profile `bitbucket-server-default-v1`) to `/v1/org/{orgId}/integrations/{integrationId}/settings`.

#### Scenario: Integration found and PUT succeeds

- **WHEN** a bitbucket-server integration exists for the org
- **AND** the settings PUT succeeds
- **THEN** the entry is recorded under `integration_settings.updated` with `org_id`, `org_name`, and `integration_id`

#### Scenario: No bitbucket-server integration

- **WHEN** no matching integration exists for an org
- **THEN** the entry is recorded under `integration_settings.failed` with a clear error
- **AND** dockerfile and frequency steps for that org SHALL still have run

#### Scenario: Integration settings PUT HTTP error

- **WHEN** the settings PUT returns a non-success HTTP status
- **THEN** the entry is recorded under `integration_settings.failed` with error detail

#### Scenario: Dry run for integration settings

- **WHEN** `--dry-run` is set
- **THEN** no integration settings PUT requests are issued
- **AND** each eligible org appears under `integration_settings.skipped` with reason `dry_run`

### Requirement: Emit post-import-cleanup-report.json

The stage SHALL write a version 1 report with `dockerfile_projects`, `recurring_test_frequency`, and `integration_settings` outcome buckets and metadata including `group_id` and `settings_profile`.

#### Scenario: Report written

- **WHEN** the stage completes
- **THEN** the output file contains `version: 1`, `group_id`, and `settings_profile: "bitbucket-server-default-v1"`

#### Scenario: Partial failure exit code

- **WHEN** any entry exists under `dockerfile_projects.failed`, `recurring_test_frequency.failed`, or `integration_settings.failed`
- **THEN** the CLI exits with a non-zero status

### Requirement: SnykRestClient project API support

The implementation SHALL add client methods for paginated org project listing, project deletion, and v1 project settings PUT, using the same HTTP retry behavior as existing client methods.

#### Scenario: List projects with type filter

- **WHEN** the stage requests dockerfile projects for an org
- **THEN** the client uses the v1 projects API with a dockerfile type filter

#### Scenario: Delete project via REST

- **WHEN** the stage deletes a project
- **THEN** the client issues a REST DELETE for that org and project id

#### Scenario: Update project settings via v1

- **WHEN** the stage sets recurring test frequency
- **THEN** the client issues a v1 PUT to `/org/{orgId}/project/{projectId}/settings`
