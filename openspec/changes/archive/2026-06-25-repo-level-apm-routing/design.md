## Context

Stage 1 discovery rows include `apm_code` per repository from AppSec YAML ([`src/common/mapper.py`](../../../src/common/mapper.py)). [`project_apm_map_from_rows()`](../../../src/snyk/project_context.py) collapses rows to `projectKey → apm_code` and raises when codes disagree—used as a gate in Stage 2 ([`snyk_orgs_cli.py`](../../../src/commands/snyk_orgs_cli.py)) and as the routing table in Stage 3 ([`enrichment.py`](../../../src/snyk/enrichment.py)). Stage 2 org list generation already uses [`apm_codes_from_rows()`](../../../src/snyk/outputs.py) (distinct codes across all rows).

The canonical spec at [`openspec/specs/three-stage-snyk-pipeline/spec.md`](../../../openspec/specs/three-stage-snyk-pipeline/spec.md) includes “Ambiguous APM per project fails discovery validation,” but Stage 1 does not implement that check; conflict enforcement lives only in Stages 2–3.

## Goals / Non-Goals

**Goals:**

- Introduce `repo_apm_map_from_rows(rows) -> dict[tuple[str, str], str]` keyed by `(project_key, repo_slug)` via existing [`row_repo_key()`](../../../src/common/output_state.py).
- Stage 2: emit `snyk-orgs.json` from `apm_codes_from_rows` only; no project-level conflict validation.
- Stage 3: resolve Snyk org name per target from `repo_apm[(projectKey, repoSlug)]`.
- Per-row `--default-org-id` and composite `target.name` for rows without `apm_code`.
- Remove conflict `ValueError`, `build_project_context_document`, and `parse_project_context_document`.

**Non-Goals:**

- New `snyk-project-context.json` file format or version bump.
- Stage 1 discovery changes.
- Broker stages (consume org names from `snyk-orgs.json` unchanged).

## Decisions

### 1. Routing key: `(projectKey, repoSlug)`

**Choice:** Map `(project_key, repo_slug)` → `apm_code` from discovery rows.

**Rationale:** Matches import `target` fields; same decomposition as `repository_path`.

### 2. Stage 2: no project-level validation

**Choice:** Delete `project_apm_map_from_rows(rows)` call from `snyk_orgs_cli.main`.

**Rationale:** `apm_codes_from_rows` already produces one org per distinct code; multi-APM per project is valid.

### 3. Stage 3 enrichment: repo-level lookup

**Choice:** Replace `project_apm: dict[str, str]` with `repo_apm: dict[tuple[str, str], str]` in `required_apm_codes_for_import`, `enrich_import_document`, and `summarize_enrichment_plan`.

**Rationale:** Each target must resolve org from its own row’s code, not siblings’ codes in the same project.

### 4. Default org and naming: per row

**Choice:** In `build_snyk_import_document`, use composite `target.name` when `default_org_id` is set **and** the row’s `apm_code` is null/empty; use display name (or slug) only when the row has an `apm_code`.

**Rationale:** Aligns with per-repo routing; allows mixed APM and default-org repos under one Bitbucket project.

### 5. Project context module

**Choice:** Refactor [`src/snyk/project_context.py`](../../../src/snyk/project_context.py) (optional rename to `repo_apm.py`); drop JSON document helpers used only in tests.

**Rationale:** User confirmed internal-only map; no CLI writes `snyk-project-context.json` today.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| **BREAKING** `--default-org-id` no longer applies to entire projects when some repos have APM | Document in README; mixed-project scenario in tests |
| Operators expect Stage 2 failure on “bad” multi-APM data | Spec explicitly allows; customer ACCP case is the intended fix |
| Same display name in one Snyk org across projects | Unchanged for APM-mapped targets; default-org rows still use composite names |

## Migration Plan

1. Ship code + README **BREAKING** note for `--default-org-id`.
2. Re-run Stage 2 on existing discovery (no rediscovery required).
3. Re-run Stage 3; repos in multi-APM projects route to correct orgs.
4. Archive OpenSpec change into main `three-stage-snyk-pipeline` spec.

## Open Questions

- None. Optional follow-up: rename `project_context.py` → `repo_apm.py` for clarity (implementation choice).
