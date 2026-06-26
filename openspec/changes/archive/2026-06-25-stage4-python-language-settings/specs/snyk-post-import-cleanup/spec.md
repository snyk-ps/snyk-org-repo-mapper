# snyk-post-import-cleanup Specification (change delta)

## ADDED Requirements

### Requirement: Set org Python language version to 3.12

For each org, after integration settings, the stage SHALL PATCH org Python language settings via the Snyk REST LanguagesSettings API so the org default Python version for Pip is **3.12**.

#### Scenario: Successful Python language update

- **WHEN** the org language settings PATCH succeeds
- **AND** `--dry-run` is not set
- **THEN** the entry is recorded under `python_language_settings.updated` with `org_id` and `org_name`

#### Scenario: Python language PATCH HTTP error

- **WHEN** the org language settings PATCH returns a non-success HTTP status
- **THEN** the entry is recorded under `python_language_settings.failed` with `org_id`, `org_name`, and error detail
- **AND** the stage continues processing other orgs

#### Scenario: Dry run for Python language settings

- **WHEN** `--dry-run` is set
- **THEN** no org language settings PATCH requests are issued
- **AND** each org appears under `python_language_settings.skipped` with reason `dry_run`

### Requirement: SnykRestClient org language settings API support

The implementation SHALL add a client method for org language settings PATCH using JSON:API request headers, the REST `version` query parameter, and the same HTTP retry behavior as existing client methods.

#### Scenario: Patch org Python language settings via REST

- **WHEN** the stage sets org Python language version
- **THEN** the client issues a REST PATCH to `/orgs/{orgId}/settings/open_source/languages/python`
- **AND** the request includes `Accept: application/vnd.api+json` and `Content-Type: application/vnd.api+json`
- **AND** the request body sets Python version to `3.12`

## MODIFIED Requirements

### Requirement: Emit post-import-cleanup-report.json

The stage SHALL write a version 2 report with `dockerfile_projects`, `recurring_test_frequency`, `integration_settings`, and `python_language_settings` outcome buckets and metadata including `group_id`, `settings_profile`, and `python_version`.

#### Scenario: Report written

- **WHEN** the stage completes
- **THEN** the output file contains `version: 2`, `group_id`, `settings_profile: "bitbucket-server-default-v1"`, and `python_version: "3.12"`

#### Scenario: Partial failure exit code

- **WHEN** any entry exists under `dockerfile_projects.failed`, `recurring_test_frequency.failed`, `integration_settings.failed`, or `python_language_settings.failed`
- **THEN** the CLI exits with a non-zero status
