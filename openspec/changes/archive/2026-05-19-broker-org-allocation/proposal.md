## Why

After Stage 2 produces `snyk-orgs.json`, customers using Snyk Universal Broker often have **multiple existing** `bitbucket-server` connections across deployments. They need a deterministic plan that maps each new org to a broker connection, avoids double-assigning orgs already integrated on a connection, balances load across connections, and can **apply** those assignments by creating org–connection integrations via the Broker API.

This stage sits **between** org creation planning (`snyk-orgs`) and import enrichment (`snyk-import`), which today resolves org-level `integrationId` via the standard org integrations API and does not understand Universal Broker connection topology.

## What Changes

- Add **Stage 2.1 — Broker Plan** CLI `snyk-broker-plan`: reads `snyk-orgs.json` plus `tenant_id` and broker `install_id`; **read-only** Universal Broker GET calls; emits `broker-org-plan.json`.
- Add **Stage 2.2 — Broker Apply** CLI `snyk-broker-apply`: reads `broker-org-plan.json`; POSTs org–connection integrations for `assignments` only; emits `broker-org-apply-report.json`.
- Optional `SNYK_GROUP_ID` to resolve org **names** to org **UUIDs** before pre-check and apply.
- Update README pipeline documentation and dispatcher help text.

**Out of scope:**

- Creating or modifying Broker **deployments**, **connections**, **credentials**, or **contexts**.
- Changing Stage 3 `snyk-import` enrichment behavior (apply creates broker links; Stage 3 still uses org integrations API).

## Capabilities

### New Capabilities

- `universal-broker-read`: Paginated GET for deployments, connections (`bitbucket-server` filter), and per-connection integrations; retries consistent with existing Snyk client patterns.
- `broker-org-plan`: Stage 2.1 — Broker Plan CLI, round-robin allocation, pre-check, `broker-org-plan.json` v1 (plan command is GET-only).
- `broker-org-apply`: Stage 2.2 — Broker Apply CLI, POST org integration links from plan `assignments`, idempotent skip, apply report v1.

### Modified Capabilities

- _(none — no existing OpenSpec specs in this repository)_

## Impact

- **New modules**: `integrations/snyk/broker_client.py`, `snyk/broker_plan.py`, `snyk/broker_apply.py`, `commands/snyk_broker_plan_cli.py`, `commands/snyk_broker_apply_cli.py`.
- **Config**: `load_broker_settings` in [`config/snyk_settings.py`](../../../src/config/snyk_settings.py) for tenant/install and shared API auth.
- **CLI**: [`commands/dispatch.py`](../../../src/commands/dispatch.py) registers `snyk-broker-plan` and `snyk-broker-apply`.
- **APIs**: Universal Broker REST (GET for plan; POST `.../connections/{connection_id}/orgs/{org_id}/integration` for apply).
