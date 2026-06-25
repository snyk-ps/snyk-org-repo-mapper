## Context

The repo-mapper pipeline today:

1. **Stage 1** — discovery JSON from Bitbucket or spreadsheet.
2. **Stage 2** — `snyk-orgs.json` (one org per distinct `apm_code`, placeholders or real UUIDs for `groupId` / `sourceOrgId`).
3. **Stage 3** — `snyk-import.json` enriched with `orgId` and `integrationId` via group org listing and org-level integrations API ([`integrations/snyk/client.py`](../../../src/integrations/snyk/client.py)).

Customers on **Universal Broker** already have broker app installed (`install_id`), deployments, and `bitbucket-server` **connections** provisioned outside this tool. New orgs must be assigned to a connection before (or as part of) SCM integration. Stage 3 does not model connection-level assignment.

Reference: [Universal Broker REST API](https://docs.snyk.io/snyk-api/reference/universal-broker).

## Goals / Non-Goals

**Goals:**

- Discover all `bitbucket-server` connections under `tenant_id` + `install_id` (all deployments).
- Pre-check which orgs from `snyk-orgs.json` are **already** integrated on each connection.
- Assign each **remaining** org to exactly one connection using **round-robin** (even distribution of new assignments).
- Write **`broker-org-plan.json`** (version 1) suitable for human review and a future apply step.
- Fail fast with clear errors when zero connections exist or org resolution fails when required.

**Non-Goals:**

- Creating deployments, connections, credentials, or contexts.
- Modifying `snyk-import` enrichment or discovery stages.
- Supporting non–`bitbucket-server` connection types in allocation (they may be listed for visibility but not used for assignment).

## Decisions

### 1. Read-only Broker API surface

| Operation | Method | Path |
|-----------|--------|------|
| List deployments | GET | `/rest/tenants/{tenant_id}/brokers/installs/{install_id}/deployments` |
| List connections | GET | `.../deployments/{deployment_id}/connections` |
| List integrations on connection | GET | `/rest/tenants/{tenant_id}/brokers/connections/{connection_id}/integrations` |

All requests use JSON:API headers (`Accept` / `Content-Type`: `application/vnd.api+json`), `Authorization: token {SNYK_TOKEN}`, and `version={SNYK_API_VERSION}` query param (default `2024-10-15`, overridable). Base URL from `SNYK_API` (same derivation as [`config/snyk_settings.py`](../../../src/config/snyk_settings.py)).

Pagination: follow `links.next` like `SnykRestClient.iter_group_orgs` ([`_resolve_next_url`](../../../src/integrations/snyk/client.py)).

**Connection type filter:** keep resources where `attributes.type` (or equivalent documented field from OpenAPI spike) normalizes to `bitbucket-server`. Log and skip other types.

**Rationale:** Matches Snyk docs; no write permissions required for plan-only stage.

### 2. Org identity for pre-check

- `snyk-orgs.json` entries use **`name`** (= APM code) as the org identifier for matching.
- Pre-check compares against org ids (and names if present) returned from `GET .../connections/{connection_id}/integrations`.
- When `--group-id` / `SNYK_GROUP_ID` is set, resolve `name → org_id` via existing `iter_group_orgs` before pre-check so matching is reliable after orgs exist in Snyk.
- Orgs found on **any** connection’s integration list are placed in `already_integrated` and **excluded** from round-robin (not reassigned).

**Alternative considered:** org-side `GET /orgs/{org_id}/brokers/connections` only — rejected as primary path because assignment is connection-centric and integrations listing is the direct pre-check for “already on this connection.”

### 3. Round-robin allocation

- Sort eligible connections by `connection_id` (stable).
- Maintain a per-connection count of **new** assignments in this run.
- Iterate orgs to assign (sorted by org name) and assign each to the connection with the **minimum** current new-assignment count; tie-break by lowest `connection_id`.
- If no `bitbucket-server` connections: exit non-zero with message.
- If all orgs already integrated: success with empty `assignments` and populated `already_integrated`.

**Alternative considered:** capacity limits from API — only adopt if OpenAPI documents per-connection org limits during implementation spike.

### 4. Output artifact: `broker-org-plan.json` (version 1)

```json
{
  "version": 1,
  "tenant_id": "<uuid>",
  "install_id": "<uuid>",
  "connections": [
    {
      "connection_id": "<uuid>",
      "deployment_id": "<uuid>",
      "type": "bitbucket-server",
      "display_name": "<optional string from API>"
    }
  ],
  "already_integrated": [
    {
      "org_name": "APM1",
      "org_id": "<uuid or null>",
      "connection_id": "<uuid>"
    }
  ],
  "assignments": [
    {
      "org_name": "APM2",
      "org_id": "<uuid or null>",
      "connection_id": "<uuid>"
    }
  ],
  "unassigned": [],
  "warnings": []
}
```

- `unassigned`: orgs that could not be placed (should be empty unless future capacity rules apply).
- `warnings`: non-fatal issues (e.g. org name not found in group when `--group-id` set).

### 5. CLI and configuration

- Command: `snyk-broker-plan` (Stage 2.1 — Broker Plan).
- Flags: `--snyk-orgs`, `--output` (default `broker-org-plan.json`), `--tenant-id`, `--install-id`, `--dry-run` (print plan to stdout), `--env-file`.
- Env: `SNYK_TOKEN`, `SNYK_API`, `SNYK_API_VERSION`, optional `SNYK_GROUP_ID`, `SNYK_TENANT_ID`, `SNYK_BROKER_INSTALL_ID` as defaults for flags.

### 6. Apply: `snyk-broker-apply` (Stage 2.2 — Broker Apply)

| Operation | Method | Path |
|-----------|--------|------|
| Create org integration | POST | `/rest/tenants/{tenant_id}/brokers/connections/{connection_id}/orgs/{org_id}/integration` |

- **Input:** `broker-org-plan.json` v1; process `assignments` only.
- **POST body:** empty JSON object `{}` with `Content-Type: application/vnd.api+json` (confirm in spike; adjust if OpenAPI requires attributes).
- **Idempotency:** skip `already_integrated`; re-GET integrations before POST; treat HTTP **409** as skip.
- **org_id:** required on each assignment or resolved via `SNYK_GROUP_ID` + `iter_group_orgs`.
- **Output:** `broker-org-apply-report.json` v1:

```json
{
  "version": 1,
  "plan_path": "broker-org-plan.json",
  "applied": [{ "org_name": "APM2", "org_id": "...", "connection_id": "...", "status": "created" }],
  "skipped": [{ "org_name": "APM1", "connection_id": "...", "reason": "already_integrated" }],
  "failed": [{ "org_name": "APM3", "org_id": null, "connection_id": "...", "error": "..." }]
}
```

- **CLI:** `snyk-broker-apply --plan broker-org-plan.json [--output broker-org-apply-report.json] [--dry-run]`
- Non-zero exit if any `failed` entries.

### 7. Relationship to Stage 3

Stage 3 continues to set `integrationId` from org-level integrations. Broker apply creates **connection ↔ org** links; org-level integrations may appear after linking. Optional future: persist `integration_id` from POST response into the apply report for Stage 3.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| OpenAPI field names differ from assumptions (`type`, org id in integrations) | Implementation spike task; normalize in one module; unit tests with fixture JSON |
| Org names in `snyk-orgs` not yet created in Snyk | Document that pre-check is best-effort without `--group-id`; warn in `warnings` |
| Large tenant: many deployments × connections | Paginate all list endpoints; optional debug logging only |
| Token lacks Broker permissions | Surface HTTP 403 with doc link in error message |

## Migration Plan

- No data migration. New optional stage in pipeline documentation.
- Existing users skip `snyk-broker-plan` until they use Universal Broker multi-connection topology.

## Open Questions

- Confirm exact `attributes` keys for connection `type` and integration org reference in live API responses (resolved in task 1.1 spike, documented in client module docstring).
- Whether `display_name` exists on connection resources or only `id` (optional in output schema).
