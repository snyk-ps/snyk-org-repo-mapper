## Context

The main pipeline (Stages 1–4) generates `snyk-import.json` for external import but does not list, delete, or reimport SCM targets. Scotia's branch-mismatch remediation requires processing a pre-built `diff.json` artifact (896 entries) that maps `apm_code`, `repository_name`, `production_branch`, and `target_reference`.

Custom branching was validated in UAT; reimport uses `snyk-api-import` (same workflow as initial onboarding). The discussion noted that deleting `imported-targets.log` mid-run causes skipped imports.

[`SnykRestClient`](../../../src/integrations/snyk/client.py) already supports group org listing, integrations, and project operations. Targets API (REST) is not yet implemented.

## Goals / Non-Goals

**Goals:**

- Accept `diff.json` and process each entry: resolve org by `apm_code`, find target by `repository_name` + `target_reference`, delete, reimport with `production_branch`.
- Use `snyk-api-import import` for reimport (preserves resume via `imported-targets.log`).
- Support `--dry-run`, `--limit`, `--repos-per-batch`, versioned report JSON.
- Reuse existing settings (`SNYK_TOKEN`, `SNYK_GROUP_ID`), HTTP retry, and org name resolution from Stage 3.

**Non-Goals:**

- Generating `diff.json`.
- Native v1 Import API (chose `snyk-api-import` per operator preference).
- Empty-target cleanup, broker changes, or main CLI registration.

## Decisions

### 1. Script location: `scripts/` entrypoint + `src/` library

**Choice:** Thin CLI at `scripts/reimport_mismatched_targets.py`; logic in `src/snyk/branch_mismatch_reimport.py`.

**Rationale:** Matches plan request for `scripts/` while keeping testable library code alongside existing `src/snyk/` modules.

### 2. Target identification: display_name + target_reference

**Choice:** List targets per org via `GET /rest/orgs/{org_id}/targets` (optional `display_name` filter). Match where `attributes.display_name == repository_name` and `attributes.target_reference == target_reference` (case-sensitive).

**Rationale:** `diff.json` provides both fields; disambiguates when multiple branch targets exist for the same repo.

**Alternative:** Match display_name only — rejected; ambiguous when multiple branches imported.

### 3. Reimport via snyk-api-import subprocess

**Choice:** Build import JSON batches; invoke `snyk-api-import import --file=...` with `SNYK_TOKEN` in environment.

**Rationale:** Validated UAT workflow; handles rate limiting and job polling internally.

### 4. Import payload shape

**Choice:** Match Stage 3 `snyk-import.json` target shape: `projectKey`, `repoSlug`, `name` (with `BB/` prefix per [`outputs.py`](../../../src/snyk/outputs.py)), `branch` = `production_branch`. Extract `projectKey`/`repoSlug`/`integrationId` from target detail before delete.

### 5. Per-org target cache

**Choice:** Cache listed targets per `org_id` when processing multiple diff rows in the same org (159 orgs, 896 rows).

**Rationale:** Reduces API calls.

### 6. Partial failure semantics

**Choice:** Continue on per-entry failures; exit non-zero if any `failed` entries.

**Rationale:** Matches Stage 4 pattern; maximizes remediation in one run.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Target REST payload missing `projectKey`/`repoSlug` | Parse from target attributes; fail entry with clear error if missing |
| `snyk-api-import` not installed | Preflight check with actionable error |
| `imported-targets.log` interference | Document in README; optional `--import-log-dir` to run from isolated cwd |
| 896 deletes + imports — rate limits | HTTP retry in client; batch import files |
| Case-sensitive branch names (`Develop` vs `develop`) | Match exact `target_reference` from diff |

## Migration Plan

1. Enable custom branching in target environment (already done in UAT).
2. Run `--dry-run --limit 5` against UAT group.
3. Live run on 1–2 repos; verify `target_reference == production_branch`.
4. Full batch run; monitor `imported-targets.log` and broker.

## Open Questions

- None for v1.
