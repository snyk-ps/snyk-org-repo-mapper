## Context

Stage 1 Bitbucket discovery ([`iter_mapping`](../../../src/common/mapper.py)) lists every repository, fetches `appsec.yaml` on the default branch, and writes versioned discovery JSON. Stage 3 ([`build_snyk_import_document`](../../../src/snyk/outputs.py)) turns every row into a Snyk import target. Repositories with **no commits** exist in Bitbucket but have nothing to scan; they should be recorded in discovery for visibility yet excluded from import.

**Empty** (confirmed): **no commits at all** — `GET .../commits?limit=1` returns no commit entries.

## Goals / Non-Goals

**Goals:**

- Add `repository_has_commits(project_key, repo_slug)` to [`BitbucketServerClient`](../../../src/integrations/bitbucket/client.py).
- Set `is_empty` on each Bitbucket discovery row; skip YAML fetch when `is_empty` is true.
- Omit `is_empty: true` rows from `snyk-import.json` in Stage 3.
- Treat missing `is_empty` as false (legacy discovery, spreadsheet).
- Log empty-repo count at end of Bitbucket discovery.
- Write **`bitbucket-empty-repos.json`** (default path) when discovery uses `-o` / `--output`.

**Non-Goals:**

- Spreadsheet empty detection.
- Dropping empty rows from discovery `rows`.
- Optional `--skip-empty-check` (future optimization).
- Stage 2 behavior changes.

## Decisions

### 1. Commits API for emptiness

**Choice:** `GET rest/api/1.0/projects/{projectKey}/repos/{repoSlug}/commits?limit=1`

- No values / empty `values` → `is_empty: true`
- At least one commit object → `is_empty: false`
- API errors propagate (never default to empty on failure)

**Rationale:** Matches “no commits at all”; one extra GET per repo during discovery only.

### 2. Keep empty repos in discovery with a flag

**Choice:** `is_empty: true` on the row; do not remove from `rows`.

**Rationale:** Audit trail, resume/checkpoint compatibility, operator visibility.

### 3. Skip YAML when empty

**Choice:** Do not call `fetch_raw_file` when `is_empty` is true; `apm_code` and YAML branch remain null; `production_branch` still derived from API default branch metadata.

**Rationale:** Avoids pointless 404s and speeds large estates.

### 4. Stage 3 filter in `build_snyk_import_document`

**Choice:** `row_is_empty(row)` helper; `continue` at start of row loop.

**Rationale:** Single choke point; enrichment never sees omitted targets.

### 5. Backward compatibility

**Choice:** Missing or non-boolean `is_empty` → treat as not empty.

**Rationale:** Legacy discovery files and spreadsheet rows keep current behavior.

### 6. `bitbucket-empty-repos.json` artifact

**Choice:** Version 1 document with `repositories` array (subset of discovery fields), built from rows where `row_is_empty(row)` is true, sorted by `repository_path`.

**CLI:**

- When `--output` is set: default `--empty-repos-output` to `bitbucket-empty-repos.json`.
- Stdout-only discovery: no empty-repos file unless `--empty-repos-output` is explicitly provided.
- Rewrite on each discovery flush alongside `discovery.json`.

**Rationale:** Operators get a dedicated audit file without scanning full discovery; Stage 3 still reads only discovery.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| +1 HTTP call per repo in discovery | Document in README; acceptable for correctness |
| Commits API permission differs from browse | Fail discovery with clear error (same as other BB calls) |
| Edge case: commits only on non-default refs | Accepted; “no commits at all” is the product definition |

## Migration Plan

1. Ship OpenSpec + code; new discovery runs include `is_empty`.
2. Re-run Bitbucket discovery before Stage 3 to refresh flags on existing estates.
3. Old discovery without `is_empty`: Stage 3 still imports all rows until rediscovered.

## Open Questions

- None for v1.
