## Context

Stage 1 Bitbucket discovery walks projects/repos (or a spreadsheet list), reads `appsec.yaml`, and writes versioned discovery JSON consumed by Stages 2–3. Row keys are derived from `repository_path` as `{scope}/{repo}`; resume/checkpoint reuse `project_key` + `repo_slug` parsed from that path ([`row_repo_key`](../../../src/common/output_state.py)). GitHub org login maps naturally to `project_key`; repo name to `repo_slug`.

## Goals / Non-Goals

**Goals:**

- `discover github --orgs "acme-corp,acme-labs" -o discovery.json`
- Paginate `GET /orgs/{org}/repos` per listed org; shared AppSec YAML parser ([`parse_appsec_yaml`](../../../src/common/appsec_yaml.py)).
- Row parity with Bitbucket discovery (including `is_empty`, committer fields, `last_commit_date`).
- Resumable file output via existing [`run_discovery_with_file_output`](../../../src/commands/discovery_helpers.py).
- `source: github` in discovery and empty-repos documents.

**Non-Goals:**

- Spreadsheet-driven GitHub discovery.
- Stage 3 GitHub import target shape / integration type selection.
- Org discovery beyond explicit `--orgs` list.
- GraphQL API (REST v3 only for v1).

## Decisions

### 1. Org scope via required CLI flag

`--orgs` accepts a comma-separated string of org **logins** (not display names). Whitespace around entries is trimmed; empty tokens rejected. At least one org required. Order determines crawl order (org A repos fully, then org B, …).

### 2. Authentication and API base

- **Auth:** `Authorization: Bearer {GITHUB_TOKEN}` (classic PAT or fine-grained token with `contents:read`, `metadata:read` on target orgs).
- **Base URL:** `GITHUB_API_URL` optional; default `https://api.github.com`. Trailing slashes stripped. GitHub Enterprise Server uses `{host}/api/v3`.

### 3. Repository iteration and row mapping

For each `(org_login, repo)` from paginated org repo list:

| Discovery field | GitHub source |
|-----------------|---------------|
| `repository_path` | `{org_login}/{repo.name}` |
| `repository_name` | `repo.name` |
| `bitbucket_project_name` | org display name from `GET /orgs/{org}` (fallback: org login) |
| `production_branch` | YAML `productionBranch`, else `repo.default_branch` |
| `apm_code` | YAML `security.apmCode` (same as Bitbucket) |
| `is_empty` | `true` when repo has **zero commits** on default branch (see below) |
| `last_committer_*`, `last_commit_date` | latest commit on default branch (`GET .../commits?per_page=1&sha={default_branch}`) |

Reuse existing checkpoint field names: `project_key` = org login, `repo_slug` = repo name.

### 4. Empty repository rules (parity with Bitbucket)

Mark `is_empty: true` when:

- `GET .../commits?per_page=1` returns an empty array, **or**
- `default_branch` is null/missing on the repo object.

When empty: skip YAML fetch; committer fields and `last_commit_date` are `null`. Row still appears in `rows` and in empty-repos sidecar.

**Note:** GitHub repos created with a README have one commit → `is_empty: false` (same as Bitbucket non-zero commits).

### 5. YAML file path

`GITHUB_FILE_PATH` env var, default `appsec.yaml`. Same YAML schema as Bitbucket ([README YAML format](../../../README.md#yaml-file-format-stage-1-bitbucket)).

### 6. Shared discovery flush with source parameter

Generalize `flush_discovery(..., source: DiscoverySource)` so GitHub CLI passes `"github"`. Empty-repos writer selects builder by source (`github-empty-repos.json` default filename).

### 7. HTTP retries and rate limits

Reuse [`run_with_retries`](../../../src/integrations/http_retry.py). On HTTP 403/429 with `Retry-After` or rate-limit headers, honor backoff. Env: `GITHUB_HTTP_RETRIES` (default 5), `GITHUB_HTTP_BACKOFF_S` (default 1.0), `GITHUB_FLUSH_INTERVAL` (default 1).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Large orgs → many API calls | `--max-repos`, `--flush-interval`, resume/checkpoint |
| Rate limiting on github.com | Retry + README guidance on token scopes / off-peak runs |
| `bitbucket_project_name` on GitHub rows | Document as legacy field name; value is GitHub org display name |
| Stage 3 still expects Bitbucket Server integration | Explicitly out of scope; discovery unblocks Stage 2 org list today |

## Migration Plan

1. Ship `discover github`; operators run discovery and `snyk-orgs` immediately.
2. Follow-on change: Stage 3 GitHub integration resolution + import target shape for Snyk GitHub import tool.

## Open Questions

- **GHE vs github.com:** Is `GITHUB_API_URL` sufficient for all enterprise customers, or do we need a separate `GITHUB_HOST` for HTML/raw URLs?
- **Archived repos:** Include with `is_empty` semantics unchanged, or skip archived repos by default?
- **Forks:** Include org forks in org repo list (GitHub API default) or filter `fork: false` only?
