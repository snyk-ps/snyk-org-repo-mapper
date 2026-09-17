## Context

Stage 1 Bitbucket discovery ([`_mapping_row_for_repository`](../../../src/common/mapper.py)) resolves default branch metadata, fetches AppSec YAML at that ref, and writes versioned discovery JSON. Spreadsheet mode reuses the same mapper via [`iter_mapping_for_repos`](../../../src/common/mapper.py). GitHub discovery ([`github_mapper.py`](../../../src/common/github_mapper.py)) intentionally keeps default-branch YAML fetch and `production_branch` fallback — out of scope.

The configured YAML path remains **`BITBUCKET_FILE_PATH`** (default `appsec.yaml`) from [`load_settings()`](../../../src/config/__init__.py).

## Goals / Non-Goals

**Goals:**

- Add Bitbucket client support to resolve **`latest_active_branch`** (branch with newest tip commit).
- Fetch and parse YAML at `refs/heads/{latest_active_branch}` only.
- Emit `apm_code` and `production_branch` strictly from YAML (null when absent).
- Scope commit metadata to the latest commit on `latest_active_branch`.
- Emit `bitbucket_default_branch`, `latest_active_branch`, and `is_archived` on every Bitbucket row that is emitted.
- Skip archived repositories by default; opt in via `--include-archived` or `BITBUCKET_INCLUDE_ARCHIVED`.
- Preserve existing **`is_empty`** gate: zero commits repo-wide (and existing no-default-branch empty semantics).

**Non-Goals:**

- GitHub branch/YAML/archived semantics.
- Stage 3 validation of null `production_branch` (existing: null → empty string in import `target.branch`).
- Using tags or pull-request refs as active-branch candidates.
- Changing `BITBUCKET_FILE_PATH` defaults or YAML key parsing.

## Decisions

### 1. Latest active branch selection

**Choice:** Paginate `GET .../repos/{slug}/branches?details=true` and pick the branch whose latest-commit timestamp is maximal. Prefer `committerTimestamp`, fall back to `authorTimestamp` from branch metadata. Compare timestamps numerically.

**Tie-break:** Lexicographically smallest `displayId` when timestamps equal.

**Output:** `(at_ref, display_id, tip_commit)` for YAML fetch and commit metadata; `display_id` stored as `latest_active_branch`.

**Fallback when branch list is empty but commits exist:** Log warning; attempt repo-wide `commits?limit=1` to derive ref from commit metadata if available; otherwise set `latest_active_branch` to `null`.

**Alternatives considered:** Per-branch `commits?until=` for every branch (accurate but N+1 HTTP); default-branch-only (rejected — does not meet requirement).

### 2. Default branch capture (informational only)

**Choice:** Continue using [`resolve_repository_branch`](../../../src/integrations/bitbucket/client.py) to obtain configured default branch display id → **`bitbucket_default_branch`**. This ref is **not** used for YAML fetch or `production_branch`.

When no usable default branch exists, `bitbucket_default_branch` SHALL be `null`.

### 3. Remove production_branch fallback (Bitbucket only)

**Choice:** In Bitbucket [`mapping_row`](../../../src/common/mapper.py) path, set `production_branch` to parsed YAML value only (`null` if missing/blank). Do **not** call `resolve_production_branch(..., default_display)` for Bitbucket.

**Choice:** Keep `resolve_production_branch` for GitHub in [`github_mapper.py`](../../../src/common/github_mapper.py).

### 4. Commit metadata source

**Choice:** Use tip commit on `latest_active_branch`:

- Preferred: reuse tip commit object from branch listing metadata when complete.
- Otherwise: `GET .../commits?until={at_ref}&limit=1`.

Apply existing [`parse_committer_identity`](../../../src/integrations/bitbucket/client.py) and [`parse_commit_timestamp`](../../../src/integrations/bitbucket/client.py).

### 5. Archive status and filtering

**Choice:** Read boolean **`archived`** from Bitbucket repository object.

- **Default (`include_archived=false`):** Do not yield a row; repo is not checkpointed.
- **Override:** CLI `--include-archived` or env `BITBUCKET_INCLUDE_ARCHIVED` (truthy: `1`, `true`, `yes`, case-insensitive). CLI flag takes precedence when both are set.

When included, emit row with **`is_archived: true`**. Non-archived rows emit **`is_archived: false`**.

**Spreadsheet mode:** Same filter — archived repo listed in spreadsheet is skipped unless override enabled.

### 6. Empty repositories

**Choice:** When repository has zero commits repo-wide → `is_empty: true`:

- Skip branch scan and YAML fetch.
- `latest_active_branch`, commit metadata, `apm_code`, `production_branch` → `null`.
- Still emit `bitbucket_default_branch` and `is_archived` when row is emitted (archived empty repos still skipped unless `--include-archived`).

Existing no-default-branch empty semantics from baseline spec remain unchanged.

### 7. YAML file path

**Choice:** No change — `BITBUCKET_FILE_PATH`, default `appsec.yaml`.

### 8. Row field summary (Bitbucket)

| Field | Source |
|-------|--------|
| `bitbucket_default_branch` | Configured default branch display id (API) |
| `latest_active_branch` | Branch with newest tip commit |
| `is_archived` | `repo.archived` |
| `apm_code` | YAML on `latest_active_branch` only |
| `production_branch` | YAML on `latest_active_branch` only (no API fallback) |
| `last_commit_*` | Tip commit on `latest_active_branch` |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Extra HTTP per repo (branch pagination) | Use `details=true`; paginate with existing client patterns; document cost in README |
| Large repos (1000+ branches) | Paginate; future optimization out of scope |
| YAML only on default branch, not active branch | Intended behavior — operators maintain YAML on active branches |
| Null `production_branch` breaks import expectations | Document breaking change; Stage 3 maps null → `""` |
| Branch metadata missing timestamps | Fall back to `commits?until=` for winning branch only |
| Archived repos disappear from row counts | Document default skip; `--include-archived` for audit runs |

## Migration Plan

1. Ship OpenSpec + code; update README.
2. Re-run `discover bitbucket` / spreadsheet discovery for affected estates.
3. Review rows with `production_branch: null` before Stage 3 import.
4. Use `--include-archived` when archived repos must appear in discovery output.

## Open Questions

- None — tie-break (lexicographic `displayId`), archived skip default, and YAML path legacy behavior confirmed with stakeholders.
