# branch-mismatch-target-reimport Specification

## Purpose
TBD - created by archiving change branch-mismatch-target-reimport. Update Purpose after archive.
## Requirements
### Requirement: Accept diff.json input format

The script SHALL accept a JSON array where each element contains `apm_code`, `repository_name`, `production_branch`, and `target_reference` as non-empty strings.

#### Scenario: Valid diff file loaded

- **WHEN** the user passes `--input` pointing to a valid diff.json array
- **THEN** the script loads and validates all entries before processing

#### Scenario: Invalid diff entry rejected

- **WHEN** an entry is missing a required key or has an empty value
- **THEN** the script exits with a validation error before any API calls

### Requirement: Resolve Snyk org by apm_code

The script SHALL resolve `org_id` by matching `apm_code` to the Snyk organization **name** in the configured `SNYK_GROUP_ID`.

#### Scenario: Org found for apm_code

- **WHEN** an entry has `apm_code` that matches an org name in the group
- **THEN** the script uses that org's id for target lookup

#### Scenario: Org not found

- **WHEN** no org in the group has name equal to `apm_code`
- **THEN** the entry is recorded under `not_found` with reason `org_not_found`
- **AND** the script continues with remaining entries

### Requirement: Match target by repository_name and target_reference

For each entry, the script SHALL find exactly one Snyk target in the resolved org where `display_name` equals `repository_name` and `target_reference` equals `target_reference` (case-sensitive).

#### Scenario: Single matching target found

- **WHEN** exactly one target matches both fields
- **THEN** the script proceeds to delete (or dry-run skip) that target

#### Scenario: No matching target

- **WHEN** zero targets match
- **THEN** the entry is recorded under `not_found`

#### Scenario: Ambiguous match

- **WHEN** more than one target matches
- **THEN** the entry is recorded under `ambiguous`
- **AND** no delete is performed

#### Scenario: Already correct branch skipped

- **WHEN** `production_branch` equals `target_reference`
- **THEN** the entry is recorded under `skipped` with reason `already_correct`

### Requirement: Delete matched target via REST API

The script SHALL delete the matched target using `DELETE /rest/orgs/{org_id}/targets/{target_id}` unless `--dry-run` is set.

#### Scenario: Successful delete

- **WHEN** a target is matched and `--dry-run` is not set
- **THEN** the target is deleted via the Snyk REST Targets API
- **AND** the entry is recorded under `deleted`

#### Scenario: Dry run delete

- **WHEN** `--dry-run` is set and a target is matched
- **THEN** no DELETE request is issued
- **AND** the entry is recorded under `skipped` with reason `dry_run`

### Requirement: Reimport with production_branch via snyk-api-import

After a successful delete, the script SHALL reimport the target with `target.branch` set to `production_branch` using `snyk-api-import import`, unless `--dry-run` or `--skip-import` is set.

#### Scenario: Successful reimport

- **WHEN** delete succeeds and neither `--dry-run` nor `--skip-import` is set
- **THEN** the script appends an import payload to a batch file and invokes `snyk-api-import import`
- **AND** the entry is recorded under `reimported`

#### Scenario: Skip import flag

- **WHEN** `--skip-import` is set and delete succeeds
- **THEN** no `snyk-api-import` subprocess is invoked
- **AND** the entry is recorded under `deleted` only

### Requirement: Versioned report output

The script SHALL write a versioned JSON report with per-entry outcomes grouped under `deleted`, `reimported`, `skipped`, `not_found`, `ambiguous`, and `failed`.

#### Scenario: Report written on completion

- **WHEN** processing completes (success or partial failure)
- **THEN** the report is written to `--output` (default `branch-reimport-report.json`)
- **AND** includes `version`, `group_id`, and entry counts

### Requirement: Require Snyk credentials

The script SHALL require `SNYK_TOKEN` and `SNYK_GROUP_ID`.

#### Scenario: Missing credentials

- **WHEN** required environment variables are unset
- **THEN** the script exits with a validation error before processing

