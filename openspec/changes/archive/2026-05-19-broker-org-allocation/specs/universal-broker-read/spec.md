## ADDED Requirements

### Requirement: List broker deployments for an install

The system SHALL perform an authenticated GET request to list all deployments for the given `tenant_id` and `install_id`, following JSON:API pagination until no `links.next` remains.

#### Scenario: Successful deployment listing

- **WHEN** the Broker API returns one or more deployment resources for the install
- **THEN** the client returns a list of deployment objects each containing at least `deployment_id`

#### Scenario: Pagination across pages

- **WHEN** the deployments response includes `links.next`
- **THEN** the client fetches subsequent pages and merges all deployment resources without duplication

### Requirement: List connections per deployment

The system SHALL list all connections for each deployment via GET on the deployment connections collection endpoint, with pagination.

#### Scenario: Connections retrieved for each deployment

- **WHEN** deployments are enumerated
- **THEN** the client requests connections for every `deployment_id` and returns connection records including `connection_id`, `deployment_id`, and connection type metadata

### Requirement: Filter bitbucket-server connections

The system SHALL include only connections whose type attribute normalizes to `bitbucket-server` in the set used for org allocation.

#### Scenario: Non-matching connection types excluded

- **WHEN** a connection has type other than `bitbucket-server` (e.g. `github`)
- **THEN** that connection is not included in the allocation candidate set

#### Scenario: bitbucket-server connection included

- **WHEN** a connection type is `bitbucket-server`
- **THEN** that connection is included in the allocation candidate set

### Requirement: List integrations on a connection

The system SHALL retrieve existing org integrations for a connection via GET `/tenants/{tenant_id}/brokers/connections/{connection_id}/integrations` with pagination.

#### Scenario: Integrations listed for pre-check

- **WHEN** pre-check runs for a `bitbucket-server` connection
- **THEN** the client returns org identifiers (at minimum org id when present) for each integration on that connection

### Requirement: Create org integration on connection

The broker client SHALL POST to `/tenants/{tenant_id}/brokers/connections/{connection_id}/orgs/{org_id}/integration` to link an organization to a broker connection, with retries on transient failures.

#### Scenario: Successful integration POST

- **WHEN** `create_org_integration` is called with valid ids
- **THEN** the client completes without error

#### Scenario: Conflict on duplicate link

- **WHEN** POST returns HTTP 409
- **THEN** the client raises a dedicated conflict exception or returns a result indicating already linked (for apply to skip)

### Requirement: No deployment or connection mutations

The broker client MUST NOT invoke POST, PATCH, or DELETE on deployments, connections, credentials, or contexts.

#### Scenario: Plan command uses GET only

- **WHEN** `snyk-broker-plan` runs
- **THEN** only GET requests are issued to Universal Broker endpoints

### Requirement: Retries on transient failures

The broker client SHALL retry GET requests on retriable HTTP failures (429, 5xx) and transient network errors using the same retry policy pattern as the existing Snyk REST client.

#### Scenario: Transient 503 retried

- **WHEN** a Broker GET returns HTTP 503
- **THEN** the client retries up to the configured maximum attempts before failing
