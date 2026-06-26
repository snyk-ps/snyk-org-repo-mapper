# Delta spec: three-stage-snyk-pipeline

## ADDED Requirements

### Requirement: Stage 1 discovery produces a versioned intermediate document

The discovery command SHALL support **two** ingress modes—Bitbucket Server and spreadsheet—and SHALL write a single **versioned** JSON document containing `rows` equivalent to the primary mapping semantics needed for Snyk Stages 2 and 3, including `apm_code`, `repository_path`, `repository_name`, `production_branch`, and `bitbucket_project_name` where applicable.

#### Scenario: Bitbucket discovery writes intermediate

- **GIVEN** valid `BITBUCKET_*` configuration and repository access
- **WHEN** the user runs Stage 1 discovery for Bitbucket
- **THEN** the output document SHALL include `source` with value `bitbucket`
- **AND** each processed repository SHALL appear as a row with YAML-derived or defaulted branch and APM metadata per existing mapper rules

#### Scenario: Spreadsheet discovery writes equivalent intermediate

- **GIVEN** a valid `.xlsx` per spreadsheet column rules
- **WHEN** the user runs Stage 1 discovery for spreadsheet
- **THEN** the output document SHALL include `source` with value `spreadsheet`
- **AND** `rows` SHALL be sufficient for Stage 2 and Stage 3 to derive the same `apm_code` and `repository_path` conventions as the Bitbucket path except for documented field gaps

#### Scenario: Ambiguous APM per project fails discovery validation

- **GIVEN** two rows share the same Bitbucket `projectKey` but different non-empty `apm_code` values
- **WHEN** discovery completes validation before write
- **THEN** the command SHALL fail with a validation exit code
- **AND** SHALL name the conflicting project and repositories

### Requirement: Stage 2 emits snyk-orgs.json for orgs:create

The snyk-orgs command SHALL read **only** the Stage 1 intermediate document and SHALL write `snyk-orgs.json` whose structure matches the **Snyk API Import Tool** organization creation payload (one org per distinct non-null `apm_code`, with placeholders for group and source org identifiers).

#### Scenario: Stage 2 performs no remote API calls

- **WHEN** Stage 2 runs
- **THEN** it SHALL NOT perform HTTP requests to Bitbucket or Snyk

### Requirement: Stage 3 emits snyk-import.json with resolved Snyk identifiers

The snyk-import command SHALL read the Stage 1 intermediate document, SHALL build import `targets` compatible with the Snyk import tool, and SHALL query the **Snyk REST API** to set **`orgId`** and **`integrationId`** on each target using organization **name** equal to `apm_code` and the **Bitbucket Server** integration type.

#### Scenario: Stage 3 performs no Bitbucket HTTP

- **GIVEN** a complete Stage 1 intermediate
- **WHEN** Stage 3 runs
- **THEN** it SHALL NOT contact Bitbucket over the network

#### Scenario: Optional orgs file cross-check

- **GIVEN** a `snyk-orgs.json` path is supplied
- **WHEN** Stage 3 validates required APM names against that file before calling Snyk
- **THEN** missing expected names SHALL fail with a validation exit code and clear stderr

#### Scenario: Dry run for Stage 3

- **WHEN** the user passes `--dry-run` to Stage 3
- **THEN** the command SHALL NOT overwrite the output import file
- **AND** SHALL print a reviewable plan of org and integration resolution

### Requirement: Unified CLI dispatcher documents three stages first

The application entry router SHALL list **Stage 1 discovery**, **Stage 2 snyk-orgs**, and **Stage 3 snyk-import** before any auxiliary or legacy commands in top-level help text.

#### Scenario: Top-level help reflects new UX

- **WHEN** the user requests top-level help
- **THEN** the output SHALL enumerate the three stages in order with short descriptions

### Requirement: Backwards compatibility is not preserved

Breaking changes to command names, flags, and console script entry points are **explicitly allowed**; documentation and packaging SHALL be updated to match the new surface without retaining deprecated CLI behavior unless the implementation team chooses a temporary alias (optional, not required by this spec).

#### Scenario: Deprecated commands are not documented as primary

- **GIVEN** the README and top-level `--help` are updated for this change
- **WHEN** a user reads primary documentation
- **THEN** legacy command names such as `snyk-prepare-orgs` and `snyk-enrich-import` SHALL NOT appear as the recommended path unless explicitly marked as deprecated aliases
