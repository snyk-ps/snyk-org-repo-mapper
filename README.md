# snyk-org-repo-mapper

This project helps you onboard Bitbucket Server and GitHub repositories into Snyk in **stages**: produce a single **discovery** JSON from Bitbucket, a spreadsheet, or GitHub orgs; derive **`snyk-orgs.json`** for org creation; optionally plan and apply **Universal Broker** org–connection assignments; build **`snyk-import.json`** and resolve Snyk `orgId` / `integrationId` via the Snyk REST API; then optionally run **post-import cleanup** across the whole Snyk group. Stages 3 and 4 never call the source SCM.

## Quick start

1. **Stage 1 — discovery** (pick one source):

   ```bash
   export BITBUCKET_URL='https://bitbucket.example.com'
   export BITBUCKET_PAT='your-token'

   PYTHONPATH=src python src/main.py discover bitbucket -o discovery.json
   ```

   Or from an AppSec-style `.xlsx`:

   ```bash
   PYTHONPATH=src python src/main.py discover spreadsheet \
     --input "data/AppSec Repo to APM - Sample.xlsx" \
     -o discovery.json
   ```

   Or from GitHub orgs:

   ```bash
   export GITHUB_TOKEN='your-token'

   PYTHONPATH=src python src/main.py discover github \
     --orgs "org-name-1,org-name-2" \
     -o discovery.json
   ```

2. **Stage 2 — org list** (no network):

   ```bash
   PYTHONPATH=src python src/main.py snyk-orgs \
     --discovery discovery.json \
     --output snyk-orgs.json
   ```

   Optional: pass **`--group-id`** and **`--template-org-id`** (UUIDs) so each org entry’s `groupId` and `sourceOrgId` are filled instead of placeholder strings.

   Create orgs in Snyk (matching names in `snyk-orgs.json`) before Stage 2.2 — Broker Apply, Stage 3, or Stage 4 if they do not exist yet.

3. **Stage 2.1 — Broker Plan** (optional; requires existing Broker deployments and `bitbucket-server` connections):

   ```bash
   export SNYK_TOKEN='your-token'
   export SNYK_TENANT_ID='your-tenant-uuid'
   export SNYK_BROKER_INSTALL_ID='your-broker-install-uuid'

   PYTHONPATH=src python src/main.py snyk-broker-plan \
     --snyk-orgs snyk-orgs.json \
     --output broker-org-plan.json
   ```

   Set `SNYK_GROUP_ID` so org names from `snyk-orgs.json` resolve to org UUIDs for pre-check.

4. **Stage 2.2 — Broker Apply** (optional; runs after Broker Plan):

   ```bash
   PYTHONPATH=src python src/main.py snyk-broker-apply \
     --plan broker-org-plan.json \
     --output broker-org-apply-report.json
   ```

5. **Stage 2.3 — Integration settings** (optional; runs after Broker Apply):

   ```bash
   export SNYK_TOKEN='your-token'
   export SNYK_INTEGRATIONS_API='v1'

   PYTHONPATH=src python src/main.py snyk-broker-integration-settings \
     --report broker-org-apply-report.json \
     --output broker-integration-settings-report.json
   ```

   Applies a predefined Bitbucket Server SCM settings profile to each org listed under `applied` in the apply report. Requires **Integrations v1** API (`SNYK_INTEGRATIONS_API=v1`, the default).

6. **Stage 3 — import file + IDs** (Snyk API only):

   ```bash
   export SNYK_TOKEN='your-token'
   export SNYK_GROUP_ID='your-group-uuid'

   PYTHONPATH=src python src/main.py snyk-import \
     --discovery discovery.json \
     --output snyk-import.json \
     --snyk-orgs snyk-orgs.json
   ```

7. **Stage 4 — post-import cleanup** (optional; runs after import):

   ```bash
   export SNYK_TOKEN='your-token'
   export SNYK_GROUP_ID='your-group-uuid'
   export SNYK_INTEGRATIONS_API='v1'

   PYTHONPATH=src python src/main.py snyk-post-import-cleanup \
     --output post-import-cleanup-report.json
   ```

   **Destructive:** deletes Dockerfile Snyk projects in every org in the group. Run with **`--dry-run`** first to review the report on stdout. Requires token permissions to delete projects, edit integrations, and edit org language settings. Existing Python projects may need a re-test before scan results reflect Python 3.12.

After `pip install -e .`, the **snyk-org-repo-mapper** console entry points are available on your `PATH`: `repo-mapper-discover-bitbucket`, `repo-mapper-discover-spreadsheet`, `repo-mapper-discover-github`, `repo-mapper-snyk-orgs`, `repo-mapper-snyk-broker-plan`, `repo-mapper-snyk-broker-apply`, `repo-mapper-snyk-broker-integration-settings`, `repo-mapper-snyk-import`, and `repo-mapper-snyk-post-import-cleanup`.

## Requirements

- **Python 3.12+** (see `pyproject.toml`).
- **Stage 1 (Bitbucket):** HTTPS reachability to Bitbucket Server and a PAT that can list projects/repos and read file content.
- **Stage 1 (spreadsheet):** `bb-repo-mapping.xlsx` plus the same `BITBUCKET_*` settings as Bitbucket discovery.
- **Stage 1 (GitHub):** `GITHUB_TOKEN` (see [Stage 1 (GitHub)](#stage-1-github) for required scopes); `--orgs` with comma-separated org logins.
- **Stage 2:** Paths only; no API tokens. You may pass **`--group-id`** / **`--template-org-id`** on the CLI to embed those UUIDs in `snyk-orgs.json` (still no HTTP).
- **Stages 2.1–2.2 (Broker):** `SNYK_TOKEN`, `SNYK_TENANT_ID`, `SNYK_BROKER_INSTALL_ID`; `SNYK_GROUP_ID` recommended for org name → UUID resolution.
- **Stage 2.3 (integration settings):** `SNYK_TOKEN`; `SNYK_INTEGRATIONS_API` must be `v1` (default). Token needs permission to edit integrations.
- **Stage 3:** Snyk REST credentials (`SNYK_TOKEN`, `SNYK_GROUP_ID`); optional `--snyk-orgs` for a consistency check.
- **Stage 4 (post-import cleanup):** `SNYK_TOKEN`, `SNYK_GROUP_ID`, `SNYK_USER_ID`; `SNYK_INTEGRATIONS_API` must be `v1`. Set `SNYK_API` to your tenant API origin on single-tenant instances (e.g. `https://api.example.my.snyk.io`, no `/rest` or `/v1` suffix). Token needs permission to delete projects, edit integrations, and edit org language settings. Use `--dry-run` before the first live run.

## Installation

The Python package name is **`snyk-org-repo-mapper`** (formerly `bitbucket-org-repo-mapper`).

```bash
pip install -r requirements.txt
```

Application code lives under `src/`. Run with `PYTHONPATH=src` and `python src/main.py …`, or install in editable mode (includes pytest):

```bash
pip install -e ".[dev]"
```

## Workflow

### Stage 1 — `discover bitbucket`, `discover spreadsheet`, or `discover github`

**Bitbucket** walks projects and repositories, checks each repo for commits (zero commits → `is_empty: true`), records **`last_committer_name`** and **`last_committer_email`** from the latest commit when not empty (API `committer`, falling back to `author`), **`last_commit_date`** as UTC ISO-8601 from `committerTimestamp` (falling back to `authorTimestamp`), reads a YAML file from non-empty repos (see [YAML format](#yaml-file-format)), merges AppSec fields with API metadata, and either prints a JSON **array of rows** to stdout or writes **discovery JSON** with `-o` / `--output`. With `-o`, also writes **`bitbucket-empty-repos.json`** by default listing empty repositories (override with `--empty-repos-output`; disable with `--no-empty-repos-output`).

**Spreadsheet** reads `bb-repo-mapping.xlsx` (project keys + semicolon-delimited repo slugs), queries Bitbucket per repo for YAML-derived APM and full row metadata (see [Stage 1 (spreadsheet)](#stage-1-spreadsheet)), and writes discovery JSON with `source: bitbucket`.

**GitHub** lists repositories for each org in **`--orgs`** (comma-separated logins), applies the same empty-repo and committer rules via the GitHub REST API, reads AppSec YAML from non-empty repos for **`production_branch`** only, derives **`apm_code`** from repository topics (default: topic `apm-ABC1` → `ABC1`), and writes discovery JSON with **`source: github`**. With `-o`, also writes **`github-empty-repos.json`** by default (same override/disable flags as Bitbucket). There is no spreadsheet ingress for GitHub.

Discovery is the handoff artifact for Stages 2 and 3. Shape: `version`, `source` (`bitbucket`, `spreadsheet`, or `github`), `rows`, and optional `checkpoint` for resume (file output). Legacy **primary mapping** files (wrapper without `source`, or a bare array) are still accepted as `--discovery` input in Stages 2–3; `source` is treated as `bitbucket` for compatibility.

### Stage 2 — `snyk-orgs`

Reads `--discovery`, writes **`snyk-orgs.json`** in the shape expected for Snyk org creation / import tooling (one org per distinct non-null `apm_code`). No Snyk or Bitbucket HTTP calls. Optional **`--group-id`** and **`--template-org-id`** set `groupId` and `sourceOrgId` on every row instead of placeholders (each flag is independent). See [Snyk REST — Organizations](https://docs.snyk.io/snyk-api/rest-api/endpoints/organizations) for how you apply this payload in your process.

### Stage 2.1 — Broker Plan (`snyk-broker-plan`)

Reads `snyk-orgs.json`, lists Universal Broker **deployments** and **connections** for `SNYK_TENANT_ID` + `SNYK_BROKER_INSTALL_ID`, keeps `bitbucket-server` connections only (SCM type from `attributes.integrationType` or `integration_type`, not JSON:API resource `type`), pre-checks orgs already integrated per connection, and writes **`broker-org-plan.json`** with round-robin **assignments**. **GET only** (no Broker mutations).

### Stage 2.2 — Broker Apply (`snyk-broker-apply`)

Reads `broker-org-plan.json` and **POST**s org–connection integrations for each `assignments` entry (skips `already_integrated`). Writes **`broker-org-apply-report.json`**. Does **not** create deployments or connections. Orgs must already exist in Snyk; use `SNYK_GROUP_ID` when `org_id` is missing from the plan.

### Stage 2.3 — Integration settings (`snyk-broker-integration-settings`)

Reads **`broker-org-apply-report.json`**, processes each entry in **`applied`** with an `org_id`, resolves the **bitbucket-server** integration id (same rules as Stage 3), and **PUT**s a fixed SCM settings profile via Snyk Integrations v1 (`/org/{orgId}/integrations/{integrationId}/settings`). Writes **`broker-integration-settings-report.json`**. Does **not** process `skipped` or `failed` apply rows. **`--dry-run`** lists intended updates without PUT. Requires `SNYK_INTEGRATIONS_API=v1`.

### Stage 3 — `snyk-import`

Reads `--discovery`, builds import targets (skips rows with **`is_empty: true`**), then calls the **Snyk REST API** to resolve `orgId` and `integrationId` per repository using that row’s `apm_code` (Snyk org **name** = APM code). Repositories in the same Bitbucket project may have different APM codes. Optional **`--repos-per-batch N`** writes multiple import files (`snyk-import-001.json`, …) with at most **N** targets each for the API Import Tool. Optional `--snyk-orgs` cross-checks that org names cover the APM codes needed by the import. Optional **`--default-org-id`** routes targets whose discovery row has no `apm_code` into one org; their `target.name` is **`{projectKey}/{repository_name}`** (repository slug when display name is absent). Rows with an `apm_code` keep unprefixed display names even when siblings in the same project use the default org. **No Bitbucket HTTP** in this stage.

### Stage 4 — Post-import cleanup (`snyk-post-import-cleanup`)

Iterates **every org** in `SNYK_GROUP_ID` and, per org: **lists** projects via the REST Projects API (type `dockerfile` filtered client-side), **deletes** those Dockerfile projects, **PATCH**es recurring test frequency to `never` on all remaining projects (REST PATCH requires `SNYK_USER_ID` in `relationships.owner`), **remediates project ownership** so pre-PATCH owners are preserved (unassigned projects stay unassigned; other owners are restored), **PUT**s the Stage 2.3 Bitbucket Server integration settings profile (v1 integrations API), and **PATCH**es org Python language settings to **3.12** (Pip). Writes **`post-import-cleanup-report.json`** (version 3). **`--dry-run`** prints the report to stdout without DELETE, PUT, or PATCH. Requires `SNYK_INTEGRATIONS_API=v1` for integration settings only. On single-tenant Snyk, set `SNYK_API` to your tenant origin (not `https://api.snyk.io`). **Destructive** — run dry-run first. Existing Python projects may need a re-test for scan results to reflect the new version.

## Configuration by stage

### Stage 1 (Bitbucket)

| Variable | Required | Description |
|----------|----------|-------------|
| `BITBUCKET_URL` | Yes | Base URL of Bitbucket Server (trailing slash optional; normalized). |
| `BITBUCKET_PAT` | Yes | Personal access token; sent as `Authorization: Bearer …`. Do not commit or log. |
| `BITBUCKET_FILE_PATH` | No | YAML path **inside each repo**; default `appsec.yaml`. |
| `BITBUCKET_HTTP_RETRIES` | No | Max attempts per HTTP call (including first). Default `5`. |
| `BITBUCKET_HTTP_BACKOFF_S` | No | Base seconds for exponential backoff. Default `1.0`. |
| `BITBUCKET_FLUSH_INTERVAL` | No | When using `-o`, flush discovery every **N** new repos. Default `1`; overridable with `--flush-interval`. |

| Flag | Description |
|------|-------------|
| `--empty-repos-output PATH` | Write empty-repository list JSON (default: `bitbucket-empty-repos.json` when `-o` is set). |
| `--no-empty-repos-output` | Do not write the empty-repos file even when `-o` is set. |

### Stage 1 (spreadsheet)

Uses the same **`BITBUCKET_*`** variables as Bitbucket discovery (see above), including `--empty-repos-output`, `--max-repos`, and `--flush-interval` when writing `-o`.

- **Format:** Row 1 headers **`ProjectKey`** / **`RepoName`**. Column **A** = Bitbucket project key; column **B** = semicolon-delimited repository slugs (e.g. `repo-a;repo-b`).
- **APM:** Read from each repo’s AppSec YAML via Bitbucket (not from the spreadsheet).
- **Empty repos:** Zero commits, or **no default branch** in Bitbucket metadata → `is_empty: true` (skipped in Stage 3).
- **Synthetic default branch ref** (when normalizing API metadata only): **`master`**, not `main`.

### Stage 1 (GitHub)

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | Personal access token; sent as `Authorization: Bearer …`. Do not commit or log. |
| `GITHUB_API_URL` | No | GitHub REST API base URL. Default `https://api.github.com`. GitHub Enterprise Server: `{host}/api/v3`. |
| `GITHUB_FILE_PATH` | No | YAML path **inside each repo**; default `appsec.yaml`. |
| `GITHUB_HTTP_RETRIES` | No | Max attempts per HTTP call (including first). Default `5`. |
| `GITHUB_HTTP_BACKOFF_S` | No | Base seconds for exponential backoff. Default `1.0`. |
| `GITHUB_FLUSH_INTERVAL` | No | When using `-o`, flush discovery every **N** new repos. Default `1`; overridable with `--flush-interval`. |

| Flag | Description |
|------|-------------|
| `--orgs ORG1,ORG2` | **Required.** Comma-separated GitHub organization logins to crawl. |
| `--apm-topic-regex REGEX` | Regex with one capture group to extract `apm_code` from repository topics (default: `^apm-(.+)$`; e.g. `apm-ABC1` → `ABC1`). |
| `--empty-repos-output PATH` | Write empty-repository list JSON (default: `github-empty-repos.json` when `-o` is set). |
| `--no-empty-repos-output` | Do not write the empty-repos file even when `-o` is set. |

- **Empty repos:** Zero commits, or **no default branch** in GitHub metadata → `is_empty: true` (skipped in Stage 3).
- **Row paths:** `repository_path` is `{org_login}/{repo_name}`; **`github_org`** is the org login (same as the path prefix).
- **APM:** `apm_code` comes from repository **topics** matching `--apm-topic-regex`, not from AppSec YAML.

**Token permissions:** Discovery is read-only. It calls `GET /orgs/{org}`, `GET /orgs/{org}/repos`, `GET /repos/{owner}/{repo}/commits`, `GET /repos/{owner}/{repo}/topics`, and `GET /repos/{owner}/{repo}/contents/{path}`. The token owner must be a **member** of each org in `--orgs` with access to the repositories being crawled.

**Fine-grained PAT (GitHub.com):** Grant access to the target org(s). Repository permissions: **Contents** (Read-only) and **Metadata** (Read-only). No write or admin permissions are required.

**Classic PAT:**

| Scope | When needed |
|-------|-------------|
| `repo` | Private repositories in the org |
| `read:org` | Listing org repositories via the API |
| `public_repo` | Public repositories only |

For a typical private-org crawl, use **`repo`** and **`read:org`**. Do not commit or log the token.

### Stage 2

| Flag | Description |
|------|-------------|
| `--group-id UUID` | Snyk Group ID written as `groupId` on each org entry (default: placeholder). |
| `--template-org-id UUID` | Template/source organization ID written as `sourceOrgId` on each org entry (default: placeholder). |

`--dry-run` prints JSON to stdout instead of writing `--output`.

### Stages 2.1–2.2 (Universal Broker)

| Variable / flag | Required | Description |
|-----------------|----------|-------------|
| `SNYK_TOKEN` | Yes | Snyk API token. |
| `SNYK_TENANT_ID` / `--tenant-id` | Yes | Tenant UUID for Broker API paths. |
| `SNYK_BROKER_INSTALL_ID` / `--install-id` | Yes | Broker app install UUID (plan only). |
| `SNYK_GROUP_ID` | Recommended | Resolve org **names** to org **UUIDs** for pre-check and apply. |
| `SNYK_API`, `SNYK_API_VERSION` | No | Same as Stage 3 (REST base and version query param). |

Apply reads `tenant_id` and `install_id` from the plan file; orgs must exist in Snyk before `snyk-broker-apply`.

### Stage 2.3 (integration settings)

| Flag | Description |
|------|-------------|
| `--report PATH` | **Required.** `broker-org-apply-report.json` from Stage 2.2. |
| `--output PATH` | Settings apply report (default: `broker-integration-settings-report.json`). |
| `--dry-run` | Print report JSON to stdout; no settings PUT. |

Uses `SNYK_TOKEN` and **`SNYK_INTEGRATIONS_API=v1`** (required). Processes only `applied` entries with `org_id`.

### Stage 3

| Variable | Required | Description |
|----------|----------|-------------|
| `SNYK_TOKEN` | Yes | Snyk API token (`Authorization: token …`). |
| `SNYK_GROUP_ID` | Yes | UUID of the Snyk **Group** used to list orgs for name matching. |
| `SNYK_API` | No | Snyk API **origin** only (scheme + host), e.g. `https://api.snyk.io`. The tool appends `/rest` for REST calls and `/v1` for v1 integrations. Default `https://api.snyk.io`. |
| `SNYK_API_BASE` | No | **Deprecated.** Used only if `SNYK_API` is unset; a trailing `/rest` is stripped to derive the origin (migration from the old “REST base URL” style). |
| `SNYK_INTEGRATIONS_API` | No | Which API lists org integrations: `v1` (default) or `rest`. Use `rest` when the REST integrations endpoint is available for your tenant. |
| `SNYK_API_VERSION` | No | REST API version query parameter for group org listing (date string). Default `2024-10-15`. |
| `SNYK_HTTP_MAX_ATTEMPTS` | No | HTTP retry attempts. Default `5`. |
| `SNYK_HTTP_BACKOFF_S` | No | Base backoff between retries. Default `1.0`. |

| Flag | Description |
|------|-------------|
| `--discovery PATH` | **Required.** Discovery JSON from Stage 1. |
| `--output PATH` | **Required.** Import document (e.g. `snyk-import.json`). |
| `--snyk-orgs PATH` | Optional cross-check against `snyk-orgs.json`. |
| `--repos-per-batch N` | Split output into multiple files with at most N targets each. |
| `--default-org-id UUID` | Snyk org id for import targets whose discovery row has no `apm_code` (null/empty). Sets composite `target.name` = `{projectKey}/{repository_name}` for those rows only. |
| `--dry-run` | Print resolution plan; do not overwrite `--output`. |

### Stage 4 (post-import cleanup)

| Variable | Required | Description |
|----------|----------|-------------|
| `SNYK_TOKEN` | Yes | Snyk API token. |
| `SNYK_GROUP_ID` | Yes | UUID of the Snyk **Group** whose orgs are normalized. |
| `SNYK_USER_ID` | Yes | Snyk user UUID **required in the PATCH body** for recurring-test updates (`relationships.owner`). Not the intended permanent owner — Stage 4 restores prior ownership after PATCH. |
| `SNYK_INTEGRATIONS_API` | Yes | Must be `v1` (default). Integration settings PUT is not implemented for REST. |
| `SNYK_API` | No | Snyk API **origin** only (scheme + host), e.g. `https://api.snyk.io` or `https://api.example.my.snyk.io` on single-tenant. Required for REST project list/delete/settings and org language PATCH. |
| `SNYK_API_VERSION` | No | REST API version query parameter (date string). Default `2024-10-15`. |
| `SNYK_HTTP_MAX_ATTEMPTS`, `SNYK_HTTP_BACKOFF_S` | No | Same as Stage 3. |

| Flag | Description |
|------|-------------|
| `--output PATH` | Cleanup report (default: `post-import-cleanup-report.json`). |
| `--dry-run` | Print report JSON to stdout; no DELETE, PUT, or PATCH. |
| `--user-id UUID` | Override `SNYK_USER_ID` transition user for project settings PATCH. |

**Dry-run vs live:** `--dry-run` skips DELETE, PUT, and PATCH — it will not surface HTTP 400 from project-settings PATCH. Live runs require `SNYK_USER_ID` (REST PATCH needs `relationships.owner`). After each successful frequency PATCH, Stage 4 clears or restores project ownership so `SNYK_USER_ID` is not left as permanent owner on previously unassigned or differently owned projects. PATCH HTTP 404 on a project already deleted in the dockerfile step is recorded as `recurring_test_frequency.skipped` with `reason: project_not_found`.

Processes **every org** in the group. **Destructive** — deletes Dockerfile Snyk projects; run `--dry-run` first.

### Optional `.env`

If you omit `--env-file`, the CLI loads `.env` from the **current working directory** when present (`KEY=value`; `#` comments and blank lines ignored). Stages 3 and 4 accept `--env-file` for Snyk settings.

## Commands reference

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `discover bitbucket` | Bitbucket → discovery or stdout rows | `-o`, `--empty-repos-output`, `--no-empty-repos-output`, `--env-file`, `--max-repos`, `--flush-interval` |
| `discover spreadsheet` | `bb-repo-mapping.xlsx` + Bitbucket → discovery | `-i`, `-o`, `--env-file`, `--max-repos`, `--flush-interval`, empty-repos flags |
| `discover github` | GitHub orgs → discovery | `--orgs`, `--apm-topic-regex`, `-o`, `--env-file`, `--max-repos`, `--flush-interval`, empty-repos flags |
| `snyk-orgs` | discovery → `snyk-orgs.json` | `--discovery`, `--output`, `--group-id`, `--template-org-id`, `--dry-run` |
| `snyk-broker-plan` | snyk-orgs → broker-org-plan.json | `--snyk-orgs`, `--output`, `--tenant-id`, `--install-id`, `--env-file`, `--dry-run` |
| `snyk-broker-apply` | plan → broker-org-apply-report.json | `--plan`, `--output`, `--env-file`, `--dry-run` |
| `snyk-broker-integration-settings` | apply report → settings report | `--report`, `--output`, `--env-file`, `--dry-run` |
| `snyk-import` | discovery → `snyk-import.json` + Snyk IDs | `--discovery`, `--output`, `--repos-per-batch` (optional), `--snyk-orgs`, `--default-org-id`, `--env-file`, `--dry-run` |
| `snyk-post-import-cleanup` | group-wide post-import normalization | `--output`, `--env-file`, `--dry-run`, `--user-id` |

```bash
PYTHONPATH=src python src/main.py -h
PYTHONPATH=src python src/main.py discover -h
PYTHONPATH=src python src/main.py discover bitbucket -h
PYTHONPATH=src python src/main.py discover github -h
PYTHONPATH=src python src/main.py snyk-orgs -h
PYTHONPATH=src python src/main.py snyk-import -h
PYTHONPATH=src python src/main.py snyk-post-import-cleanup -h
```

## File formats

### Discovery JSON (Stage 1 file output)

```json
{
  "version": 1,
  "source": "bitbucket",
  "rows": [
    {
      "apm_code": "ABC1",
      "repository_path": "MYPROJ/my-service",
      "repository_name": "my-service",
      "production_branch": "main",
      "bitbucket_project_name": "My Project",
      "is_empty": false,
      "last_committer_name": "charlie",
      "last_committer_email": "charlie@example.com",
      "last_commit_date": "2024-03-15T10:30:00+00:00"
    }
  ],
  "checkpoint": {
    "project_key": "MYPROJ",
    "repo_slug": "my-service"
  }
}
```

GitHub rows use **`github_org`** (org login) instead of `bitbucket_project_name`, and **`apm_code`** from repository topics:

```json
{
  "version": 1,
  "source": "github",
  "rows": [
    {
      "apm_code": "ABC1",
      "repository_path": "acme-corp/my-service",
      "repository_name": "my-service",
      "production_branch": "main",
      "github_org": "acme-corp",
      "is_empty": false,
      "last_committer_name": "charlie",
      "last_committer_email": "charlie@example.com",
      "last_commit_date": "2024-03-15T10:30:00+00:00"
    }
  ]
}
```

`checkpoint` may be `null` when empty or not yet written. **Stdout** (no `-o`) is still a **bare array** of the same row objects. Bitbucket rows include **`is_empty`** (`true` when the repo has zero commits), **`last_committer_name`** / **`last_committer_email`** (`null` when empty; from the latest commit otherwise), and **`last_commit_date`** (`null` when empty; UTC ISO-8601 from the latest commit otherwise). Spreadsheet rows omit `is_empty` and committer fields; Stage 3 treats missing `is_empty` as not empty. Stages 2–3 do not use committer or commit-date metadata.

### `bitbucket-empty-repos.json` (Stage 1 Bitbucket, with `-o`)

Written by default alongside discovery (see `--empty-repos-output`). Lists repositories with `is_empty: true`:

```json
{
  "version": 1,
  "source": "bitbucket",
  "repositories": [
    {
      "repository_path": "MYPROJ/new-repo",
      "project_key": "MYPROJ",
      "repo_slug": "new-repo",
      "repository_name": "new-repo",
      "bitbucket_project_name": "My Project"
    }
  ]
}
```

### Primary mapping (legacy)

Older **wrapper** files used `version` + `rows` + optional `checkpoint` without `source`. Stages 2–3 treat those rows as Bitbucket-shaped. A **bare JSON array** of rows is also accepted.

### `snyk-orgs.json` (Stage 2)

One org per distinct non-null `apm_code` (sorted). By default, `groupId` and `sourceOrgId` use placeholder strings for manual substitution; pass **`--group-id`** and/or **`--template-org-id`** to `snyk-orgs` to emit real UUIDs instead. Example with placeholders:

```json
{
  "orgs": [
    {
      "groupId": "<public_snyk_group_id>",
      "name": "ABC1",
      "sourceOrgId": "<public_snyk_organization_id>"
    }
  ]
}
```

### `snyk-import.json` (Stage 3)

After enrichment, targets include resolved `orgId` and `integrationId` where the API lookup succeeded. Placeholders apply until Stage 3 runs:

```json
{
  "targets": [
    {
      "orgId": "******",
      "integrationId": "******",
      "target": {
        "projectKey": "MYPROJ",
        "repoSlug": "my-service",
        "name": "my-service",
        "branch": "main"
      }
    }
  ]
}
```

### `post-import-cleanup-report.json` (Stage 4)

Version 3 report with per-org outcomes under `dockerfile_projects`, `recurring_test_frequency`, `project_owner_remediation`, `integration_settings`, and `python_language_settings` (each with `deleted`/`updated`/`cleared`/`restored`, `skipped`, and `failed` arrays as applicable). Metadata includes `group_id`, `transition_user_id` (the `SNYK_USER_ID` used for PATCH), `settings_profile` (`bitbucket-server-default-v1`), and `python_version` (`3.12`).

`project_owner_remediation` records ownership restore after recurring-test PATCH: `cleared` (previously unassigned), `restored` (prior owner UUID), `skipped` (e.g. `already_transition_user`, `dry_run`, `frequency_patch_failed`), and `failed`.

## YAML file format (Stage 1 Bitbucket)

The tool expects YAML like:

```yaml
security:
  apmCode: ABC1
  productionBranch: main
```

If `productionBranch` is omitted or empty, the repository default branch from the API is used in the row.

## Examples

Resumable Bitbucket discovery with periodic flush:

```bash
export BITBUCKET_URL='https://bitbucket.example.com'
export BITBUCKET_PAT='your-token'
export BITBUCKET_FILE_PATH='security/appsec.yaml'

PYTHONPATH=src python src/main.py discover bitbucket \
  -o discovery.json \
  --flush-interval 10
```

Print rows only (no resume file):

```bash
PYTHONPATH=src python src/main.py discover bitbucket > rows.json
```

Spreadsheet-driven discovery (requires `BITBUCKET_*` in `.env`):

```bash
PYTHONPATH=src python src/main.py discover spreadsheet \
  -i data/bb-repo-mapping.xlsx \
  -o discovery.json \
  --env-file .env
```

GitHub org discovery:

```bash
export GITHUB_TOKEN='your-token'
export GITHUB_FILE_PATH='security/appsec.yaml'

PYTHONPATH=src python src/main.py discover github \
  --orgs "org-name-1,org-name-2" \
  -o discovery.json \
  --flush-interval 10
```

Batched import (250 targets, 100 per file → three JSON files):

```bash
PYTHONPATH=src python src/main.py snyk-import \
  --discovery discovery.json \
  --output snyk-import.json \
  --repos-per-batch 100 \
  --env-file .env
```

Post-import cleanup (dry run first):

```bash
export SNYK_TOKEN='your-token'
export SNYK_GROUP_ID='your-group-uuid'
export SNYK_USER_ID='your-user-uuid'

PYTHONPATH=src python src/main.py snyk-post-import-cleanup --dry-run

PYTHONPATH=src python src/main.py snyk-post-import-cleanup \
  --output post-import-cleanup-report.json \
  --env-file .env
```

**Exit codes:** `0` success, `1` runtime error (e.g. API failure), `2` configuration / usage / validation error.

## Scripts

### Branch mismatch reimport (`scripts/reimport_mismatched_targets.py`)

Operational script for Scotia-style branch remediation: reads a `diff.json` artifact (output of a Bitbucket-vs-Snyk branch comparison), deletes each mismatched Snyk target, and reimports it with the correct `production_branch` via [`snyk-api-import`](https://docs.snyk.io/developer-tools/snyk-apps/tool-snyk-api-import).

Each diff entry requires `apm_code` (Snyk org name), `repository_name` (target **display name** from the Snyk Targets API, e.g. `BB/my-service`), `production_branch` (desired branch after reimport), and `target_reference` (current branch on the **target** resource — must match `attributes.target_reference` exactly).

**Diff field provenance:** Generate `diff.json` with [`scripts/lookup_target_reference.py`](scripts/lookup_target_reference.py) (or equivalent). That script lists Bitbucket Server targets per org and sets `target_reference` from the **target** resource (`attributes.target_reference`), not from project attributes alone. Using project-level `target_reference` in the diff causes false `target_not_found` when project and target disagree (seen on Scotia single-tenant UAT). Merge with your security.yaml comparison to add `production_branch`.

Target lookup lists **all** targets in the org via REST (`GET /rest/orgs/{org_id}/targets?exclude_empty=false`) and matches client-side on `display_name` + `target_reference`. Empty targets (no projects) are included; the API omits them by default without `exclude_empty=false`.

**Destructive** — deletes targets and all associated projects before reimport. Run `--dry-run` in UAT first.

| Variable / flag | Required | Description |
|-----------------|----------|-------------|
| `SNYK_TOKEN` | Yes | Snyk API token. |
| `SNYK_GROUP_ID` | Yes | Group UUID for org name → id resolution. |
| `--input PATH` | Yes | `diff.json` array file. |
| `--output PATH` | No | Report JSON (default: `branch-reimport-report.json`). |
| `--dry-run` | No | Match targets only; no DELETE or import. |
| `--skip-import` | No | Delete only; skip `snyk-api-import`. |
| `--repos-per-batch N` | No | Targets per import batch file (default: `50`). |
| `--limit N` | No | Process first N entries (UAT smoke tests). |
| `--snyk-api-import-cmd CMD` | No | Default `snyk-api-import`; use `npx snyk-api-import` if not global. |
| `--import-batch-dir PATH` | No | Directory for batch JSON and `snyk-api-import` cwd (default: `.`). |

**Operational notes:**

- Install `snyk-api-import` globally or pass `--snyk-api-import-cmd 'npx snyk-api-import'`.
- Do **not** delete or move `imported-targets.log` while an import is running — doing so causes skipped imports and 404 errors.
- Custom branching must be enabled in the target Snyk environment before reimport.
- Empty-target cleanup after import is handled separately in Snyk (not by this script).
- On single-tenant Snyk, set `SNYK_API` to your tenant API origin (not `https://api.snyk.io`).

**Report diagnostics (`target_not_found`):**

When a target is not matched, the report includes:

| Field | Meaning |
|-------|---------|
| `candidates_returned` | Targets returned for the org (after `exclude_empty=false`) |
| `same_display_name_branches` | Branches seen on targets whose `display_name` matches `repository_name` but `target_reference` differed — diff may be stale |
| `near_match_display_names` | Other target display names containing the repo slug — `repository_name` in diff may be wrong |

**UAT re-test checklist (Scotia-style):**

1. Regenerate `diff.json` with `lookup_target_reference.py` using tenant `SNYK_API` and `SNYK_TOKEN`.
2. Dry-run reimport on a known mismatch, e.g. `BB/uat-bitbucket-java-sample` with `--limit 5`; confirm match or actionable diagnostics (not silent `target_not_found`).
3. Live reimport on 1–2 repos; verify Snyk target `target_reference` equals `production_branch` after import.
4. Stage 4: set `SNYK_USER_ID`, run `--dry-run`, then live on one org; confirm recurring-test PATCH succeeds (dry-run skips PATCH — live run validates transition `user_id`). After live run, confirm a project with a pre-existing owner still has that owner, and a previously unassigned project remains unassigned (check `project_owner_remediation` in the report).

UAT dry-run example:

```bash
export SNYK_TOKEN='your-token'
export SNYK_GROUP_ID='your-group-uuid'

PYTHONPATH=src python scripts/reimport_mismatched_targets.py \
  --input diff.json \
  --dry-run \
  --limit 5 \
  --env-file .env
```

Live run (after UAT validation):

```bash
PYTHONPATH=src python scripts/reimport_mismatched_targets.py \
  --input diff.json \
  --output branch-reimport-report.json \
  --repos-per-batch 50 \
  --env-file .env
```

### Clear project owners (`scripts/clear_project_owners.py`)

**Legacy / bulk tool.** Stage 4 now preserves project ownership automatically after recurring-test PATCH (see Stage 4 above). Use this script only to revert owners from **older Stage 4 runs** (before built-in remediation) or to clear **all** owners in a group or org list regardless of prior state.

The script clears every project owner in scope with v1 `PUT /v1/org/{orgId}/project/{projectId}` and body `{"owner": null}` — it does not selectively restore prior owners.

**Not destructive to projects** — only clears the owner field. Run `--dry-run` first.

| Variable / flag | Required | Description |
|-----------------|----------|-------------|
| `SNYK_TOKEN` | Yes | Snyk API token with permission to edit projects. |
| `SNYK_GROUP_ID` | Group scope only | Group UUID when using `--group` without an explicit id. |
| `--group GROUP_ID` | One of `--group` / `--orgs` | List all orgs in the group and clear owner on every project. |
| `--orgs ORG_IDS` | One of `--group` / `--orgs` | Comma-separated org UUIDs; `SNYK_GROUP_ID` not required. |
| `--output PATH` | No | Report JSON (default: `clear-project-owner-report.json`). |
| `--dry-run` | No | List projects that would be updated; no PUT requests. |
| `--limit N` | No | Process first N projects across all orgs (UAT smoke tests). |

Group dry-run example:

```bash
export SNYK_TOKEN='your-token'
export SNYK_GROUP_ID='your-group-uuid'

PYTHONPATH=src python scripts/clear_project_owners.py \
  --group "$SNYK_GROUP_ID" \
  --dry-run \
  --env-file .env
```

Explicit orgs (no group env required):

```bash
PYTHONPATH=src python scripts/clear_project_owners.py \
  --orgs org-uuid-1,org-uuid-2 \
  --output clear-project-owner-report.json \
  --env-file .env
```

## Testing

```bash
pip install -r requirements.txt
pip install pytest
pytest
```

`pytest` uses `pythonpath = ["src"]` from `pyproject.toml` (same as `PYTHONPATH=src`).

## Project layout

| Path | Purpose |
|------|---------|
| `src/main.py` | Entry: dispatches pipeline stage commands |
| `src/commands/dispatch.py` | Router and console-script entrypoints |
| `src/commands/bitbucket_cli.py` | Stage 1 Bitbucket |
| `src/commands/github_cli.py` | Stage 1 GitHub |
| `src/commands/spreadsheet_cli.py` | Stage 1 spreadsheet |
| `src/commands/snyk_orgs_cli.py` | Stage 2 |
| `src/commands/snyk_broker_plan_cli.py` | Stage 2.1 Broker Plan |
| `src/commands/snyk_broker_apply_cli.py` | Stage 2.2 Broker Apply |
| `src/commands/snyk_broker_integration_settings_cli.py` | Stage 2.3 integration settings |
| `src/commands/snyk_import_cli.py` | Stage 3 |
| `src/commands/snyk_post_import_cleanup_cli.py` | Stage 4 post-import cleanup |
| `src/common/` | Discovery document, mapper, output state, spreadsheet ingestion |
| `src/config/` | Environment and optional `.env` |
| `src/integrations/` | HTTP retry, Bitbucket client, GitHub client, Snyk REST client |
| `src/snyk/` | Org/import builders, enrichment helpers, branch mismatch reimport, project owner cleanup |
| `scripts/` | Operational scripts (branch mismatch reimport, clear project owners) |
| `tests/` | Unit tests |
