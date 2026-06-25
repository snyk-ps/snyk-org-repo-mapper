## Context

Stage 2.2 writes [`broker-org-apply-report.json`](../../../broker-org-apply-report.json) with `applied`, `skipped`, and `failed` ([`src/snyk/broker_apply.py`](../../../src/snyk/broker_apply.py)). Stage 3 already lists org integrations via [`SnykRestClient.iter_org_integrations`](../../../src/integrations/snyk/client.py) and [`pick_bitbucket_server_integration_id`](../../../src/integrations/snyk/client.py).

Snyk documents **PUT** `/v1/org/{orgId}/integrations/{integrationId}/settings` for SCM integration settings (separate from integration credentials PUT).

## Goals / Non-Goals

**Goals:**

- Process only `applied` rows with non-empty `org_id`.
- PUT fixed `BITBUCKET_SERVER_INTEGRATION_SETTINGS` per org.
- `--dry-run`, versioned output report, non-zero exit on any failure.
- Require `SNYK_INTEGRATIONS_API=v1` (default).

**Non-Goals:**

- `skipped` / `failed` apply report rows.
- REST settings endpoint.
- Parameterized PR assignee.

## Decisions

### 1. Input: broker-org-apply-report only

**Choice:** `--report` points at apply report v1; iterate `applied` only.

**Rationale:** User confirmed scope; those orgs have broker links and `org_id`.

### 2. v1 settings PUT on existing client

**Choice:** `update_org_integration_settings(org_id, integration_id, settings)` using `urllib` + `run_with_retries`, JSON body = settings dict.

**Rationale:** Matches existing v1 integration listing; REST has no settings helper in this repo today.

### 3. Settings as code constant

**Choice:** [`integration_settings_defaults.py`](../../../src/snyk/integration_settings_defaults.py) with profile id `bitbucket-server-default-v1`.

**Rationale:** User-supplied fixed profile; no file path flag in v1.

### 4. Report mirrors broker apply

**Choice:** `updated` / `skipped` (dry-run) / `failed` arrays; exit 1 if any failed.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Token lacks Edit Integrations | Document in README; clear HTTP error text |
| API rejects unknown settings keys | Validate in customer env; adjust constant in follow-up |
| Integration not yet visible after Broker POST | Process only `applied`; optional retry already on HTTP layer |

## Migration Plan

1. Run after `snyk-broker-apply` (non-dry-run) for orgs in `applied`.
2. Safe to re-run (idempotent PUT overwrite).

## Open Questions

- None for v1.
