## Context

Stage 1 Bitbucket discovery ([`iter_mapping`](../../../src/common/mapper.py)) lists every repository, calls the commits API (`limit=1`) for emptiness, fetches `appsec.yaml` when not empty, and writes versioned discovery JSON. Operators want the **last committer** on each row for routing and audit without additional Bitbucket calls in Stages 2–3.

## Goals / Non-Goals

**Goals:**

- Replace `repository_has_commits` with a single method that returns the latest commit object or `None`.
- Parse `committer` (`name`, `emailAddress`) with fallback to `author` when committer is absent.
- Add `last_committer_name` and `last_committer_email` to Bitbucket discovery rows; `null` when `is_empty: true`.
- Consolidate to **one** `commits?limit=1` request per repo (no extra HTTP).

**Non-Goals:**

- Spreadsheet committer fields.
- Sidecar JSON artifacts for committers.
- Stage 2 / Stage 3 behavior changes.

## Decisions

### 1. Single commits API call

**Choice:** `repository_latest_commit(project_key, repo_slug) -> dict | None` replaces `repository_has_commits`.

- No values / empty page → `None` → `is_empty: true`, committer fields `null`.
- First commit in `values` → extract identity.
- API errors propagate (never default to empty on failure).

**Rationale:** Matches existing `is_empty` semantics; avoids doubling discovery HTTP.

### 2. Committer identity parsing

**Choice:** `parse_committer_identity(commit) -> tuple[str | None, str | None]` prefers `committer`, then `author`. Maps `emailAddress` to `last_committer_email`.

**Rationale:** Aligns with user request for “last committer”; author fallback covers API variants without committer.

### 3. Flat row fields

**Choice:** `last_committer_name` and `last_committer_email` (string or `null` on row JSON).

**Rationale:** User preference; consistent with other scalar row fields (`apm_code`, `is_empty`).

### 4. Spreadsheet and legacy discovery

**Choice:** Spreadsheet rows omit both fields. Missing keys in legacy discovery are ignored by Stages 2–3.

**Rationale:** No Bitbucket API in spreadsheet path; backward compatible.

### 5. Malformed commit payload

**Choice:** If commit exists but identity cannot be parsed, set both fields to `null` with `is_empty: false`.

**Rationale:** Do not fail discovery for partial API shapes; repo remains importable.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Commits list order not “latest on default branch” | Document same semantics as `is_empty` (repo-wide `commits?limit=1`) |
| Partial committer object | Author fallback; both null if neither yields strings |

## Migration Plan

1. Ship OpenSpec + code; new discovery runs include committer fields.
2. Re-run Bitbucket discovery to refresh existing estates.
3. Old discovery without committer keys: unchanged Stage 2–3 behavior.

## Open Questions

- None for v1.
