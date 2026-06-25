# three-stage-snyk-pipeline Specification (change delta)

## MODIFIED Requirements

### Requirement: Stage 1 discovery produces a versioned intermediate document

The discovery command SHALL support **two** ingress modes—Bitbucket Server and spreadsheet—and SHALL write a single **versioned** JSON document containing `rows` equivalent to the primary mapping semantics needed for Snyk Stages 2 and 3, including `apm_code`, `repository_path`, `repository_name`, `production_branch`, and `bitbucket_project_name` where applicable. For **Bitbucket** discovery, each row SHALL include a boolean **`is_empty`** set using the repository commits API: when `GET .../commits?limit=1` returns no commits, `is_empty` SHALL be `true`; otherwise `is_empty` SHALL be `false`. Spreadsheet rows MAY omit `is_empty`.

#### Scenario: Bitbucket discovery writes intermediate

- **GIVEN** valid `BITBUCKET_*` configuration and repository access
- **WHEN** the user runs Stage 1 discovery for Bitbucket
- **THEN** the output document SHALL include `source` with value `bitbucket`
- **AND** each processed repository SHALL appear as a row with YAML-derived or defaulted branch and APM metadata per existing mapper rules
- **AND** each row SHALL include `is_empty` as defined above

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

#### Scenario: Empty repository marked in discovery

- **GIVEN** a Bitbucket repository with zero commits
- **WHEN** Stage 1 Bitbucket discovery processes that repository
- **THEN** the row SHALL appear in `rows` with `is_empty` set to `true`
- **AND** the implementation SHALL NOT fetch the configured AppSec YAML file for that repository

#### Scenario: Non-empty repository marked in discovery

- **GIVEN** a Bitbucket repository with at least one commit
- **WHEN** Stage 1 Bitbucket discovery processes that repository
- **THEN** the row SHALL have `is_empty` set to `false`
- **AND** existing YAML and branch resolution behavior SHALL apply

#### Scenario: Empty-repos artifact written with file output

- **GIVEN** the user runs Bitbucket discovery with a file output path
- **WHEN** discovery completes or flushes incremental output
- **THEN** the implementation SHALL write `bitbucket-empty-repos.json` (or the path from `--empty-repos-output`) listing every repository with `is_empty` true
- **AND** the file SHALL use document version 1 with a `repositories` array

### Requirement: Stage 3 emits snyk-import.json with resolved Snyk identifiers

The snyk-import command SHALL read the Stage 1 intermediate document, SHALL build import `targets` compatible with the Snyk import tool, and SHALL query the **Snyk REST API** to set **`orgId`** and **`integrationId`** on each target. The command SHALL **not** include import targets for discovery rows where `is_empty` is `true`. Rows that omit `is_empty` or set it to `false` SHALL be eligible for targets. For each target, when the Bitbucket `projectKey` appears in the Stage 1–derived `projectKey → apm_code` map with a non-empty `apm_code`, the command SHALL resolve the Snyk organization whose **name** equals that `apm_code` and SHALL select the **Bitbucket Server** integration for that org. When the `projectKey` has **no** entry in that map (including when every repository row under the project has null or empty `apm_code`), the command SHALL fail with a clear validation error **unless** the user supplies an optional **default Snyk organization identifier**; when supplied, the command SHALL verify that identifier refers to an organization in the configured Snyk group, SHALL assign that value as **`orgId`**, and SHALL assign the **Bitbucket Server** **`integrationId`** for that organization.

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

#### Scenario: Default organization id for projects without APM mapping

- **GIVEN** at least one import target whose `projectKey` is absent from the `projectKey → apm_code` map derived from Stage 1 rows
- **AND** the user passes a valid default Snyk organization identifier flag recognized by the implementation
- **WHEN** Stage 3 completes successfully
- **THEN** every such target SHALL have `orgId` set to that identifier
- **AND** SHALL have `integrationId` set to the Bitbucket Server integration for that org
- **AND** the identifier SHALL have been validated as belonging to the configured Snyk group

#### Scenario: Missing APM mapping without default org id

- **GIVEN** at least one import target whose `projectKey` is absent from the `projectKey → apm_code` map
- **AND** the user does not supply the default organization identifier option
- **WHEN** Stage 3 runs validation
- **THEN** the command SHALL fail with a clear error naming the affected project key

#### Scenario: Empty rows omitted from import

- **GIVEN** a discovery document with one row where `is_empty` is `true` and one row where `is_empty` is `false`
- **WHEN** Stage 3 builds the import document
- **THEN** the `targets` array SHALL contain exactly one entry for the non-empty row

#### Scenario: Legacy rows without is_empty included in import

- **GIVEN** a discovery row with no `is_empty` field
- **WHEN** Stage 3 builds the import document
- **THEN** the row SHALL produce an import target
