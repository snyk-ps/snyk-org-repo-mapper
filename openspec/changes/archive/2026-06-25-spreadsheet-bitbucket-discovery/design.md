## Context

Stage 1 spreadsheet today maps offline APM from columns A/B/D. Customer format [`data/bb-repo-mapping.xlsx`](../../../data/bb-repo-mapping.xlsx) lists project keys and hundreds of repo slugs per row. Stage 3 emits a single large import file. Discovery can fail when Bitbucket returns no default branch.

## Goals / Non-Goals

**Goals:**

- Parse `ProjectKey` / `RepoName` (semicolon-separated slugs).
- `get_repository` + shared per-repo mapper (`iter_mapping_for_repos`).
- Discovery output `source: bitbucket` with full row fields.
- No default branch → `is_empty: true`, skip commits and YAML.
- `default_branch_tuple` synthetic fallback → `master`.
- `--repos-per-batch` on Stage 3.

**Non-goals:**

- Legacy apmcodes format.
- Parallel Bitbucket or Snyk HTTP.

## Decisions

### 1. Spreadsheet replaces offline format

Single format: row 1 headers, column B semicolon list. Duplicate `(project_key, slug)` → stderr warning, first wins.

### 2. Targeted Bitbucket API

`GET .../repos/{slug}` per pair; 404 → `ValueError`. No project-wide repo listing.

### 3. Shared discovery flush

[`discovery_helpers.py`](../../../src/commands/discovery_helpers.py) used by Bitbucket and spreadsheet CLIs.

### 4. No default branch

`repository_has_default_branch(repo)` false → empty row, no commit/YAML calls.

### 5. Stage 3 batching

One enrichment pass; slice `targets` into batches; write `{output_stem}-{NNN}.json`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Large semicolon lists → many HTTP calls | `--max-repos`, README |
| Batch file count surprises operators | Dry-run lists paths and counts |

## Migration Plan

1. Re-run `discover spreadsheet` with `bb-repo-mapping.xlsx`.
2. Use `--repos-per-batch` for large imports.

## Open Questions

- None for v1.
