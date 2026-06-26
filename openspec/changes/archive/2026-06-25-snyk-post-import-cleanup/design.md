## Context

The pipeline on main runs through Stage 2.3 ([`snyk-broker-integration-settings`](../../../src/commands/snyk_broker_integration_settings_cli.py)) and Stage 3 ([`snyk-import`](../../../src/commands/snyk_import_cli.py)). Stage 2.3 PUTs [`BITBUCKET_SERVER_INTEGRATION_SETTINGS`](../../../src/snyk/integration_settings_defaults.py) (`SETTINGS_PROFILE_ID = "bitbucket-server-default-v1"`) only for orgs in `broker-org-apply-report.json` → `applied`.

[`SnykRestClient`](../../../src/integrations/snyk/client.py) already supports `iter_group_orgs`, `iter_org_integrations`, `pick_bitbucket_server_integration_id`, and `update_org_integration_settings`. It does **not** yet expose project list, delete, or project settings APIs.

Dockerfile Snyk projects may exist after import (e.g. from prior `dockerfileSCMEnabled` settings, manual creation, or legacy onboarding). Stage 4 step 1 removes them group-wide. Recurring tests are set to `never` to avoid background scan load across the onboarded estate.

## Goals / Non-Goals

**Goals:**

- Process **all orgs** returned by `SnykRestClient.iter_group_orgs(group_id)`.
- Per org, in order: delete dockerfile projects → set recurring test `never` on all projects → PUT integration settings defaults.
- `--dry-run`, versioned output report, non-zero exit if any `failed` entry (consistent with Stage 2.3).
- Require `SNYK_TOKEN`, `SNYK_GROUP_ID`; require `SNYK_INTEGRATIONS_API=v1` for step 3.
- Reuse integration resolution and settings payload from Stage 2.3 via shared helper.

**Non-Goals:**

- Scoping to broker apply or import report orgs only.
- GET/compare integration settings before PUT.
- Configurable delete filters beyond `type == dockerfile`.
- Skipping orgs that lack bitbucket-server integration silently (record under `failed`).

## Decisions

### 1. Scope: whole Snyk group

**Choice:** Iterate every org from `iter_group_orgs()` using `SNYK_GROUP_ID`.

**Rationale:** User confirmed group-wide normalization; catches orgs outside broker apply / import paths.

**Alternative:** Restrict to orgs in `snyk-import.json` or apply report — rejected; incomplete coverage.

### 2. Project APIs: v1 list/settings, REST delete

**Choice:**

- List projects: v1 `GET /org/{orgId}/projects` with optional `?type=dockerfile` for step 1; list all projects for step 2.
- Delete: REST `DELETE /orgs/{org_id}/projects/{project_id}` (matches existing REST root usage in client).
- Update settings: v1 `PUT /org/{orgId}/project/{projectId}/settings` with `{"recurringTests": {"frequency": "never"}}`.

**Rationale:** v1 exposes type filter and project settings PUT; REST delete is documented and aligns with `rest_root` patterns already in the client.

**Alternative:** v1 delete if available — use REST first for consistency with group/org REST paths.

### 3. Processing order within each org

**Choice:** (1) delete dockerfile projects, (2) update recurring test on remaining projects, (3) PUT integration settings.

**Rationale:** Remove unwanted dockerfile targets before tuning schedules; org-level integration settings last.

### 4. Integration settings: always PUT

**Choice:** Always PUT [`BITBUCKET_SERVER_INTEGRATION_SETTINGS`](../../../src/snyk/integration_settings_defaults.py) — no GET/compare.

**Rationale:** User choice; idempotent with Stage 2.3; simpler report semantics.

### 5. Shared integration apply helper

**Choice:** Extract `apply_bitbucket_integration_settings_to_org(client, org_id, org_name, *, dry_run)` into [`integration_settings_apply.py`](../../../src/snyk/integration_settings_apply.py); Stage 2.3 and Stage 4 call it.

**Rationale:** Avoid duplicating integration resolution + PUT + outcome shape.

### 6. Partial failure semantics

**Choice:** Continue processing remaining projects/orgs after a failure; exit non-zero if any `failed` entries exist in the report.

**Rationale:** Matches Stage 2.3; maximizes remediation in one run.

### 7. Recurring test PUT: always attempt, no GET optimization

**Choice:** PUT `never` for every listed project; record API errors under `failed` without aborting the org loop.

**Rationale:** Idempotent; some project types may reject the setting — captured per project rather than failing the stage early.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Destructive dockerfile delete | Document clearly; `--dry-run` lists intended deletes; report records all outcomes |
| Token lacks project delete or integration edit | README permissions note; HTTP errors in `failed` |
| Project type rejects `recurringTests.frequency: never` | Per-project `failed` entry; stage continues |
| Org without bitbucket-server integration | Record under `integration_settings.failed`; continue other steps for that org |
| Large groups — long runtime | Paginated list APIs; existing HTTP retries |

## Migration Plan

1. Run **after** Stage 3 import (and optionally after Stage 2.3).
2. First run with `--dry-run` to review report.
3. Safe to re-run: dockerfile delete is no-op when none exist; PUT settings and test frequency are idempotent overwrites.

## Open Questions

- None for v1.
