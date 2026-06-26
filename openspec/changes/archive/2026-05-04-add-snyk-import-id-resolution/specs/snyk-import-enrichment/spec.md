# Delta spec: snyk-orgs preparation + snyk-import enrichment

## ADDED Requirements

### Requirement: Prepare Snyk orgs file and project context (stage 1)

The snyk-prepare-orgs command SHALL read a primary mapping JSON file and SHALL write both a Snyk org-creation document (`snyk-orgs.json` semantics) and a versioned **`snyk-project-context.json`** containing exactly one resolved `apm_code` per Bitbucket project key present in the mapping, using the same conflict rules as import enrichment.

#### Scenario: Stage 1 emits orgs and project context from mapping

- **GIVEN** a valid primary mapping with consistent `apm_code` per project key
- **WHEN** the user runs snyk-prepare-orgs with output paths for orgs and project context
- **THEN** the orgs document SHALL contain one entry per distinct non-null `apm_code`
- **AND** the project-context document SHALL map each relevant `projectKey` to that project’s `apm_code`
- **AND** both files SHALL be written atomically

#### Scenario: Stage 1 fails on ambiguous APM per project

- **GIVEN** two rows share a project key but have different non-empty `apm_code` values
- **WHEN** the user runs snyk-prepare-orgs
- **THEN** the command SHALL exit with a validation exit code
- **AND** SHALL report the project key and conflicts

#### Scenario: Stage 1 performs no Snyk or Bitbucket API calls

- **GIVEN** only a mapping file path is supplied
- **WHEN** snyk-prepare-orgs runs
- **THEN** the process SHALL NOT perform HTTP requests to Snyk or Bitbucket

### Requirement: Enrich import targets using orgs file and project context (stage 2)

The snyk-enrich-import command SHALL accept a **`snyk-orgs.json`** input (orgs assumed to exist in Snyk), a **`snyk-project-context.json`** produced by stage 1, and a **`snyk-import.json`** file; it SHALL query the Snyk REST API and SHALL write resolved `orgId` and `integrationId` onto each target where resolution succeeds.

#### Scenario: Successful enrichment using project context

- **GIVEN** project-context maps each import target’s `projectKey` to an `apm_code`
- **AND** the orgs file lists those `apm_code` values as organization names
- **AND** the Snyk group contains matching organizations each with a single Bitbucket Server integration
- **WHEN** the user runs snyk-enrich-import with valid `SNYK_TOKEN` and `SNYK_GROUP_ID`
- **THEN** every target SHALL receive the correct `orgId` and `integrationId`
- **AND** the import file SHALL be written atomically

#### Scenario: Stage 2 performs no Bitbucket API calls

- **WHEN** snyk-enrich-import runs with project-context and without Bitbucket configuration
- **THEN** absence of `BITBUCKET_URL` and `BITBUCKET_PAT` SHALL NOT cause validation failure
- **AND** the command SHALL NOT contact Bitbucket over the network

#### Scenario: Dry run on stage 2 produces no import write

- **WHEN** the user passes `--dry-run` to snyk-enrich-import
- **THEN** the import JSON file SHALL NOT be modified
- **AND** the command SHALL output enough detail to review planned id assignments

### Requirement: Match Snyk organizations by APM code name

The snyk-enrich-import command SHALL match Snyk organizations using equality between `apm_code` from project-context and the organization name returned by the Snyk API for orgs in the specified group (after documented normalization such as trim).

#### Scenario: Missing organization fails

- **GIVEN** a required `apm_code` has no matching organization name in the group
- **WHEN** snyk-enrich-import runs without `--dry-run`
- **THEN** the command SHALL fail with a non-zero exit code and SHALL report unmatched codes or project keys

### Requirement: Cross-check orgs file against required APM codes

When a snyk-orgs input file is provided, snyk-enrich-import SHALL validate that required `apm_code` values (derived from project-context and import targets) appear as organization names in that file unless a documented override flag disables strict checking.

#### Scenario: Org missing from orgs file fails before API dependency

- **GIVEN** project-context requires an `apm_code` absent from the orgs file’s `orgs` entries
- **WHEN** strict validation is enabled (default)
- **THEN** the command SHALL fail with a validation exit code and SHALL not rely on accidental API matches alone

### Requirement: Bitbucket Server integration selection

For each resolved organization id snyk-enrich-import SHALL determine the Bitbucket Server integration id suitable for import APIs via the Snyk integrations API.

#### Scenario: Missing or ambiguous integration fails

- **GIVEN** no Bitbucket Server integration exists for an organization **OR** more than one exists without disambiguation
- **WHEN** snyk-enrich-import runs
- **THEN** the command SHALL fail with an actionable error naming the organization

### Requirement: Optional primary mapping fallback for stage 2

The snyk-enrich-import command MAY accept an optional primary mapping path that reconstructs the project-context semantics when project-context file is omitted; when both are provided, the command SHALL prefer project-context or SHALL fail with a clear error—behavior MUST be documented as a single deterministic rule.

#### Scenario: Project-context is the default input for projectKey resolution

- **GIVEN** `--snyk-project-context` is supplied
- **WHEN** snyk-enrich-import resolves `apm_code` for a target
- **THEN** resolution SHALL use the context file’s `projects` map

### Requirement: CLI routed through main dispatcher

Both snyk-prepare-orgs and snyk-enrich-import SHALL be exposed only via the shared application entry router [`src/main.py`](../../../../../src/main.py), not as independent argparse roots that bypass global dispatch.

#### Scenario: Main help lists both Snyk stages

- **WHEN** the user requests top-level help for `main.py`
- **THEN** the output SHALL list snyk-prepare-orgs and snyk-enrich-import alongside bitbucket and spreadsheet commands

### Requirement: Optional emission of project-context from mapper flush

When `--snyk-project-context-output` is set, bitbucket or spreadsheet mapper commands SHALL write the project-context JSON using the **same** canonical builder as snyk-prepare-orgs so semantic output matches stage 1 without an extra mapping read beyond in-memory rows.

#### Scenario: Mapper-emitted context matches stage 1

- **GIVEN** identical mapping rows
- **WHEN** project-context is produced once via snyk-prepare-orgs and once via mapper flush using the shared builder
- **THEN** the semantic content of `projects` and conflict detection SHALL be equivalent
