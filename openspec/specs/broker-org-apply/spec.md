# broker-org-apply Specification

## Purpose
TBD - created by archiving change broker-org-allocation. Update Purpose after archive.
## Requirements
### Requirement: Accept broker-org-plan.json

The broker-org-apply stage SHALL accept a path to a version 1 `broker-org-plan.json` containing `tenant_id`, `install_id`, and `assignments`.

#### Scenario: Valid plan document

- **WHEN** the user runs `snyk-broker-apply` with `--plan` pointing to a valid v1 plan file
- **THEN** the stage processes each entry in `assignments`

#### Scenario: Invalid plan version

- **WHEN** the plan file has an unsupported `version`
- **THEN** the stage exits with a non-zero status and a validation error

### Requirement: Require org UUID for apply

Each assignment processed for POST MUST have a resolvable Snyk organization UUID.

#### Scenario: org_id present in plan

- **WHEN** an assignment includes a non-empty `org_id`
- **THEN** the stage uses that id for the integration POST

#### Scenario: org_id missing with group configured

- **WHEN** an assignment lacks `org_id` and `SNYK_GROUP_ID` is configured
- **THEN** the stage resolves `org_name` via group org listing before POST

#### Scenario: org_id missing without resolution

- **WHEN** an assignment lacks `org_id` and cannot be resolved
- **THEN** the entry is recorded under `failed` with a clear error

### Requirement: Skip already integrated orgs

The apply stage SHALL NOT POST for orgs already listed under `already_integrated` for the target connection, or already returned by a fresh integrations GET for that connection.

#### Scenario: Skip from plan already_integrated

- **WHEN** an org appears in `already_integrated` for the assignment's `connection_id`
- **THEN** the entry is recorded under `skipped` with reason `already_integrated`

#### Scenario: Defensive skip after GET

- **WHEN** a fresh integrations listing shows the org on the connection
- **THEN** the stage skips POST and records `skipped`

### Requirement: Create org integration via Broker API

For each eligible assignment, the stage SHALL POST to create the org–connection integration link.

#### Scenario: Successful POST

- **WHEN** POST succeeds for `(tenant_id, connection_id, org_id)`
- **THEN** the entry is recorded under `applied` with status `created`

#### Scenario: Conflict treated as skip

- **WHEN** POST returns HTTP 409 or an equivalent conflict indicating the link exists
- **THEN** the entry is recorded under `skipped` rather than `failed`

### Requirement: Dry run without POST

When `--dry-run` is set, the apply stage SHALL print or report intended POST operations without mutating Broker state.

#### Scenario: Dry run

- **WHEN** `--dry-run` is set
- **THEN** no POST requests are issued

### Requirement: Emit broker-org-apply-report.json

The stage SHALL write a version 1 report with `applied`, `skipped`, and `failed` arrays.

#### Scenario: Report written

- **WHEN** apply completes without `--dry-run`
- **THEN** the output file contains `version: 1` and per-org outcomes

#### Scenario: Partial failure exit code

- **WHEN** any entry is under `failed`
- **THEN** the CLI exits with a non-zero status

### Requirement: Apply does not create deployments or connections

The apply stage MUST NOT POST or PATCH deployments, connections, credentials, or contexts.

#### Scenario: Only integration POST

- **WHEN** `snyk-broker-apply` runs
- **THEN** the only write operation is org integration link POST (or none in dry-run)

