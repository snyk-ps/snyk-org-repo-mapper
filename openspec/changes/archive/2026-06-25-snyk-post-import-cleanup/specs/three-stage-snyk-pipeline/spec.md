# three-stage-snyk-pipeline Specification (change delta)

## ADDED Requirements

### Requirement: Stage 4 post-import group cleanup

The application SHALL provide a **Stage 4** command `snyk-post-import-cleanup` that runs after Stage 3 import and SHALL normalize every organization in the configured Snyk group by deleting Dockerfile Snyk projects, setting recurring test frequency to `never` on all projects, and applying the Stage 2.3 Bitbucket Server integration settings profile. The command SHALL require `SNYK_TOKEN` and `SNYK_GROUP_ID`, SHALL support `--dry-run`, and SHALL write a versioned post-import cleanup report.

#### Scenario: Stage 4 documented after Stage 3

- **WHEN** a user reads the primary README pipeline section
- **THEN** Stage 4 SHALL appear after the Stage 3 import step with example invocation and permission notes

#### Scenario: Stage 4 requires group credentials

- **WHEN** the user runs Stage 4 without `SNYK_GROUP_ID`
- **THEN** the command SHALL fail with a clear validation error

#### Scenario: Stage 4 dry run

- **WHEN** the user passes `--dry-run` to Stage 4
- **THEN** the command SHALL NOT issue destructive or mutating Snyk API requests
- **AND** SHALL write a report describing intended operations

## MODIFIED Requirements

### Requirement: Unified CLI dispatcher documents three stages first

The application entry router SHALL list **Stage 1 discovery**, **Stage 2 snyk-orgs**, and **Stage 3 snyk-import** before any auxiliary or legacy commands in top-level help text. The router SHALL also document **Stage 4 snyk-post-import-cleanup** and broker sub-stages (2.1–2.3) in pipeline order where applicable.

#### Scenario: Top-level help reflects new UX

- **WHEN** the user requests top-level help
- **THEN** the output SHALL enumerate Stages 1–4 in order with short descriptions

#### Scenario: Deprecated commands are not documented as primary

- **GIVEN** the README and top-level `--help` are updated for this change
- **WHEN** a user reads primary documentation
- **THEN** legacy command names such as `snyk-prepare-orgs` and `snyk-enrich-import` SHALL NOT appear as the recommended path unless explicitly marked as deprecated aliases
