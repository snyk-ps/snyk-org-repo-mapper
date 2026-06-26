# broker-integration-settings Specification

## Purpose

Stage 2.3 applies a predefined Bitbucket Server SCM integration settings profile to each organization listed under `applied` in a Broker Apply report, using the Snyk Integrations v1 settings API.

## Requirements

### Requirement: Accept broker-org-apply-report.json

The stage SHALL accept a path to a version 1 `broker-org-apply-report.json` produced by `snyk-broker-apply`.

#### Scenario: Valid apply report

- **WHEN** the user runs `snyk-broker-integration-settings` with `--report` pointing to a valid v1 apply report
- **THEN** the stage processes entries in the `applied` array only

#### Scenario: Invalid report version

- **WHEN** the report file has an unsupported `version`
- **THEN** the stage exits with a non-zero status and a validation error

### Requirement: Require Snyk Integrations v1 API

The stage SHALL use the Snyk v1 API for integration listing and settings updates.

#### Scenario: REST integrations API configured

- **WHEN** `SNYK_INTEGRATIONS_API` is `rest`
- **THEN** the stage exits with a non-zero status and a message to set `SNYK_INTEGRATIONS_API=v1`

### Requirement: Resolve bitbucket-server integration per org

For each `applied` entry with a non-empty `org_id`, the stage SHALL list org integrations and select the **bitbucket-server** integration id using the same rules as Stage 3 import enrichment.

#### Scenario: Integration found

- **WHEN** exactly one bitbucket-server integration exists for the org
- **THEN** the stage uses that integration id for the settings PUT

#### Scenario: No bitbucket-server integration

- **WHEN** no matching integration exists
- **THEN** the entry is recorded under `failed` with a clear error

### Requirement: Apply predefined settings profile

The stage SHALL PUT the predefined settings object (profile `bitbucket-server-default-v1`) to `/v1/org/{orgId}/integrations/{integrationId}/settings` for each eligible org.

#### Scenario: Successful PUT

- **WHEN** the settings PUT succeeds
- **THEN** the entry is recorded under `updated` with `org_id` and `integration_id`

#### Scenario: PUT HTTP error

- **WHEN** the settings PUT returns a non-success HTTP status
- **THEN** the entry is recorded under `failed` with error detail

### Requirement: Dry run without PUT

When `--dry-run` is set, the stage SHALL record intended operations without issuing settings PUT requests.

#### Scenario: Dry run

- **WHEN** `--dry-run` is set
- **THEN** no settings PUT requests are issued
- **AND** eligible entries appear under `skipped` with reason `dry_run`

### Requirement: Emit broker-integration-settings-report.json

The stage SHALL write a version 1 report with `updated`, `skipped`, and `failed` arrays and metadata including `source_report_path` and `settings_profile`.

#### Scenario: Report written

- **WHEN** the stage completes without `--dry-run`
- **THEN** the output file contains `version: 1` and per-org outcomes

#### Scenario: Partial failure exit code

- **WHEN** any entry is under `failed`
- **THEN** the CLI exits with a non-zero status

### Requirement: Missing org_id on applied row

Entries under `applied` without a non-empty `org_id` SHALL be recorded under `failed`.

#### Scenario: Applied row without org_id

- **WHEN** an `applied` object lacks `org_id`
- **THEN** the entry is under `failed` with a clear error
- **AND** no settings PUT is attempted for that row

### Requirement: Do not process skipped or failed apply rows

The stage SHALL NOT read `skipped` or `failed` from the apply report for settings updates.

#### Scenario: Skipped apply entries ignored

- **WHEN** the apply report contains `skipped` entries
- **THEN** those entries are not processed by this stage
