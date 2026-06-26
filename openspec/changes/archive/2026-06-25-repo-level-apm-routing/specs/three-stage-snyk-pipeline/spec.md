# three-stage-snyk-pipeline Specification (change delta)

## REMOVED Requirements

### Requirement: Ambiguous APM per project fails discovery validation

**Reason:** Bitbucket projects may contain repositories with different non-empty `apm_code` values. Routing is per repository, not per project. The prior scenario was not implemented in Stage 1 and incorrectly blocked valid customer data in Stages 2–3.

**Migration:** Remove `project_apm_map_from_rows` conflict validation from Stage 2 and Stage 3. Use per-repository `apm_code` from discovery rows instead.

#### Scenario: Ambiguous APM per project fails discovery validation

- **REMOVED** — no longer a requirement.

## MODIFIED Requirements

### Requirement: Stage 1 discovery produces a versioned intermediate document

The discovery command SHALL support **two** ingress modes—Bitbucket Server and spreadsheet—and SHALL write a single **versioned** JSON document containing `rows` equivalent to the primary mapping semantics needed for Snyk Stages 2 and 3, including `apm_code`, `repository_path`, `repository_name`, `production_branch`, and `bitbucket_project_name` where applicable. For **Bitbucket** discovery, each row SHALL include a boolean **`is_empty`** set using the repository commits API: when `GET .../commits?limit=1` returns no commits, `is_empty` SHALL be `true`; otherwise `is_empty` SHALL be `false`. For **Bitbucket** rows with `is_empty` false, the row SHALL include **`last_committer_name`** and **`last_committer_email`** derived from the first commit in that same commits response, preferring the API **`committer`** object (`name`, `emailAddress`) and falling back to **`author`** when committer is absent or incomplete. For **Bitbucket** rows with `is_empty` true, both committer fields SHALL be **`null`**. Spreadsheet rows MAY omit `is_empty` and MAY omit both committer fields. Multiple rows MAY share the same Bitbucket `projectKey` while having different non-empty `apm_code` values; Stage 1 SHALL NOT fail validation for that condition.

#### Scenario: Bitbucket discovery writes intermediate

- **GIVEN** valid `BITBUCKET_*` configuration and repository access
- **WHEN** the user runs Stage 1 discovery for Bitbucket
- **THEN** the output document SHALL include `source` with value `bitbucket`
- **AND** each processed repository SHALL appear as a row with YAML-derived or defaulted branch and APM metadata per existing mapper rules
- **AND** each row SHALL include `is_empty` as defined above
- **AND** each non-empty row SHALL include `last_committer_name` and `last_committer_email` as defined above

#### Scenario: Spreadsheet discovery writes equivalent intermediate

- **GIVEN** a valid `.xlsx` per spreadsheet column rules
- **WHEN** the user runs Stage 1 discovery for spreadsheet
- **THEN** the output document SHALL include `source` with value `spreadsheet`
- **AND** `rows` SHALL be sufficient for Stage 2 and Stage 3 to derive the same `apm_code` and `repository_path` conventions as the Bitbucket path except for documented field gaps
- **AND** rows MAY omit `last_committer_name` and `last_committer_email`

#### Scenario: Multiple APM codes under one Bitbucket project

- **GIVEN** two discovery rows share the same `projectKey` (from `repository_path`) but have different non-empty `apm_code` values
- **WHEN** Stage 1 discovery completes
- **THEN** both rows SHALL appear in the output document
- **AND** the command SHALL NOT fail solely because `apm_code` values differ within the project

#### Scenario: Empty repository marked in discovery

- **GIVEN** a Bitbucket repository with zero commits
- **WHEN** Stage 1 Bitbucket discovery processes that repository
- **THEN** the row SHALL appear in `rows` with `is_empty` set to `true`
- **AND** `last_committer_name` and `last_committer_email` SHALL be `null`
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

### Requirement: Stage 2 emits snyk-orgs.json for orgs:create

The snyk-orgs command SHALL read **only** the Stage 1 intermediate document and SHALL write `snyk-orgs.json` whose structure matches the **Snyk API Import Tool** organization creation payload (one org per distinct non-null `apm_code` across all discovery rows, with placeholders for group and source org identifiers). The command SHALL NOT reject discovery documents because multiple rows under the same Bitbucket `projectKey` have different non-empty `apm_code` values.

#### Scenario: Stage 2 performs no remote API calls

- **WHEN** Stage 2 runs
- **THEN** it SHALL NOT perform HTTP requests to Bitbucket or Snyk

#### Scenario: Stage 2 accepts multi-APM discovery per project

- **GIVEN** a discovery document where project `ACCP` has rows with `apm_code` values `ABCD`, `ABCE`, and `ABCF`
- **WHEN** the user runs Stage 2
- **THEN** the command SHALL exit successfully
- **AND** `snyk-orgs.json` SHALL include org entries whose `name` values are `ABCD`, `ABCE`, and `ABCF`

### Requirement: Stage 3 emits snyk-import.json with resolved Snyk identifiers

The snyk-import command SHALL read the Stage 1 intermediate document, SHALL build import `targets` compatible with the Snyk import tool, and SHALL query the **Snyk REST API** to set **`orgId`** and **`integrationId`** on each target. The command SHALL **not** include import targets for discovery rows where `is_empty` is `true`. Rows that omit `is_empty` or set it to `false` SHALL be eligible for targets. For each target, the command SHALL derive a repository key from `target.projectKey` and `target.repoSlug`, look up the corresponding discovery row’s non-empty `apm_code`, and SHALL resolve the Snyk organization whose **name** equals that `apm_code`, selecting the **Bitbucket Server** integration for that org. When the discovery row for that repository has null or empty `apm_code`, the command SHALL fail with a clear validation error **unless** the user supplies an optional **default Snyk organization identifier**; when supplied, the command SHALL verify that identifier refers to an organization in the configured Snyk group, SHALL assign that value as **`orgId`**, and SHALL assign the **Bitbucket Server** **`integrationId`** for that organization.

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

#### Scenario: Per-repository org resolution in a multi-APM project

- **GIVEN** discovery rows for `ACCP/accelerator` with `apm_code` `ABCD` and `ACCP/accelerator-build-engine` with `apm_code` `ABCE`
- **AND** Snyk organizations named `ABCD` and `ABCE` exist in the configured group
- **WHEN** Stage 3 completes successfully
- **THEN** the import target for `accelerator` SHALL resolve to org `ABCD`
- **AND** the import target for `accelerator-build-engine` SHALL resolve to org `ABCE`

#### Scenario: Default organization id for repositories without APM

- **GIVEN** at least one import target whose discovery row has null or empty `apm_code`
- **AND** the user passes a valid default Snyk organization identifier flag recognized by the implementation
- **WHEN** Stage 3 completes successfully
- **THEN** every such target SHALL have `orgId` set to that identifier
- **AND** SHALL have `integrationId` set to the Bitbucket Server integration for that org
- **AND** the identifier SHALL have been validated as belonging to the configured Snyk group

#### Scenario: Default org in a project with mixed APM rows

- **GIVEN** discovery rows under project `P1` where `P1/repo-a` has `apm_code` `APM1` and `P1/repo-b` has null `apm_code`
- **AND** the user passes a valid default Snyk organization identifier
- **WHEN** Stage 3 completes successfully
- **THEN** the target for `repo-a` SHALL resolve to org `APM1`
- **AND** the target for `repo-b` SHALL resolve to the default organization

#### Scenario: Missing APM on a repository without default org id

- **GIVEN** at least one import target whose discovery row has null or empty `apm_code`
- **AND** the user does not supply the default organization identifier option
- **WHEN** Stage 3 runs validation
- **THEN** the command SHALL fail with a clear error identifying the affected repository (project key and repo slug)

#### Scenario: Default-org target uses composite name

- **GIVEN** an import target built from a discovery row with null `apm_code` and default org id supplied
- **WHEN** Stage 3 builds the import document
- **THEN** `target.name` SHALL be `{projectKey}/{repository_name}` using repository slug when display name is absent

#### Scenario: APM-mapped target keeps unprefixed name

- **GIVEN** an import target built from a discovery row with non-empty `apm_code`
- **WHEN** Stage 3 builds the import document
- **THEN** `target.name` SHALL be the repository display name or slug only (no project prefix)

#### Scenario: Empty rows omitted from import

- **GIVEN** a discovery document with one row where `is_empty` is `true` and one row where `is_empty` is `false`
- **WHEN** Stage 3 builds the import document
- **THEN** the `targets` array SHALL contain exactly one entry for the non-empty row

#### Scenario: Legacy rows without is_empty included in import

- **GIVEN** a discovery row with no `is_empty` field
- **WHEN** Stage 3 builds the import document
- **THEN** the row SHALL produce an import target
