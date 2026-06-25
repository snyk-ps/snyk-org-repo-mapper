# broker-org-plan Specification

## Purpose
TBD - created by archiving change broker-org-allocation. Update Purpose after archive.
## Requirements
### Requirement: Accept snyk-orgs and broker install parameters

The broker-org-plan stage SHALL accept a path to `snyk-orgs.json`, a Snyk `tenant_id`, and a broker `install_id`, plus standard Snyk API authentication configuration.

#### Scenario: Required inputs provided

- **WHEN** the user runs `snyk-broker-plan` with `--snyk-orgs`, `--tenant-id`, and `--install-id` (or equivalent environment variables)
- **THEN** the stage proceeds to discover connections and build a plan

#### Scenario: Missing tenant or install id

- **WHEN** `tenant_id` or `install_id` is empty
- **THEN** the stage exits with a non-zero status and a clear error message

### Requirement: Parse snyk-orgs org names

The stage SHALL read the `orgs` array from `snyk-orgs.json` and extract each org's `name` field as the org identifier for planning.

#### Scenario: Valid snyk-orgs document

- **WHEN** `snyk-orgs.json` contains `orgs: [{ "name": "APM1", ... }, ...]`
- **THEN** the stage includes `APM1` in the set of orgs to plan for

#### Scenario: Invalid snyk-orgs document

- **WHEN** the file lacks an `orgs` array
- **THEN** the stage exits with a non-zero status and a validation error

### Requirement: Optional org id resolution via group listing

When `SNYK_GROUP_ID` (or `--group-id` if implemented) is configured, the stage SHALL resolve each org name to a Snyk organization UUID using the group orgs listing API before pre-check and assignment output.

#### Scenario: Name resolved to org id

- **WHEN** group listing returns an org with `name` matching a snyk-orgs entry
- **THEN** the plan output includes that `org_id` for the corresponding org name

#### Scenario: Name not found in group

- **WHEN** an org name from snyk-orgs is absent from the group listing
- **THEN** the stage adds a warning and continues pre-check using org name only where applicable

### Requirement: Pre-check orgs already integrated on a connection

For each `bitbucket-server` connection, the stage SHALL call the integrations listing API and mark any planned org that already appears on that connection as `already_integrated`.

#### Scenario: Org already on connection excluded from assignment

- **WHEN** org `APM1` is listed on connection `C1` integrations
- **THEN** `APM1` appears under `already_integrated` for `C1` and is not included in new `assignments`

#### Scenario: Org not on any connection eligible for assignment

- **WHEN** org `APM2` is not present on any connection's integrations list
- **THEN** `APM2` is eligible for round-robin assignment

### Requirement: Round-robin assignment across connections

The stage SHALL assign each eligible org to exactly one `bitbucket-server` connection using round-robin: each new assignment goes to the connection with the fewest new assignments in this run, with ties broken by lowest `connection_id` lexicographic order.

#### Scenario: Even distribution across two connections

- **WHEN** three orgs need assignment and two connections exist
- **THEN** two connections receive two and one org respectively (counts differ by at most one)

#### Scenario: Stable ordering

- **WHEN** the same inputs are provided twice
- **THEN** `assignments` are identical including connection choice per org

### Requirement: Fail when no bitbucket-server connections

The stage SHALL exit with a non-zero status when zero `bitbucket-server` connections exist for the install.

#### Scenario: No connections

- **WHEN** no deployment exposes a `bitbucket-server` connection
- **THEN** the stage fails with an error indicating no allocatable connections

### Requirement: Emit broker-org-plan.json

The stage SHALL write a version 1 JSON document containing `tenant_id`, `install_id`, `connections`, `already_integrated`, `assignments`, `unassigned`, and `warnings`.

#### Scenario: Plan written to output path

- **WHEN** the stage completes successfully without `--dry-run`
- **THEN** the output file contains `version: 1` and all assignment results

#### Scenario: Dry run prints plan

- **WHEN** `--dry-run` is set
- **THEN** the plan JSON is printed to stdout and no output file is written

### Requirement: Plan command does not mutate broker state

The `snyk-broker-plan` command MUST NOT create deployments, connections, or org-integration links via the Broker API (use `snyk-broker-apply` for integration POST).

#### Scenario: No write operations during plan

- **WHEN** `snyk-broker-plan` runs end-to-end
- **THEN** no POST, PATCH, or DELETE Broker requests are made

