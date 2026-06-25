# bitbucket-org-repo-mapper

This project helps you onboard Bitbucket Server repositories into Snyk in **stages**: produce a single **discovery** JSON from Bitbucket or from a spreadsheet, derive **`snyk-orgs.json`** for org creation, optionally plan and apply **Universal Broker** org–connection assignments, build **`snyk-import.json`** and resolve Snyk `orgId` / `integrationId` via the Snyk REST API, then optionally run **post-import cleanup** across the whole Snyk group. Stages 3 and 4 never call Bitbucket.

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

After `pip install -e .`, the same flows are available as `repo-mapper-discover-bitbucket`, `repo-mapper-discover-spreadsheet`, `repo-mapper-snyk-orgs`, `repo-mapper-snyk-broker-plan`, `repo-mapper-snyk-broker-apply`, `repo-mapper-snyk-broker-integration-settings`, `repo-mapper-snyk-import`, and `repo-mapper-snyk-post-import-cleanup` on your `PATH`.

## Requirements

- **Python 3.12+** (see `pyproject.toml`).
- **Stage 1 (Bitbucket):** HTTPS reachability to Bitbucket Server and a PAT that can list projects/repos and read file content.
- **Stage 1 (spreadsheet):** `bb-repo-mapping.xlsx` plus the same `BITBUCKET_*` settings as Bitbucket discovery.
- **Stage 2:** Paths only; no API tokens. You may pass **`--group-id`** / **`--template-org-id`** on the CLI to embed those UUIDs in `snyk-orgs.json` (still no HTTP).
- **Stages 2.1–2.2 (Broker):** `SNYK_TOKEN`, `SNYK_TENANT_ID`, `SNYK_BROKER_INSTALL_ID`; `SNYK_GROUP_ID` recommended for org name → UUID resolution.
- **Stage 2.3 (integration settings):** `SNYK_TOKEN`; `SNYK_INTEGRATIONS_API` must be `v1` (default). Token needs permission to edit integrations.
- **Stage 3:** Snyk REST credentials (`SNYK_TOKEN`, `SNYK_GROUP_ID`); optional `--snyk-orgs` for a consistency check.
- **Stage 4 (post-import cleanup):** `SNYK_TOKEN`, `SNYK_GROUP_ID`; `SNYK_INTEGRATIONS_API` must be `v1`. Token needs permission to delete projects, edit integrations, and edit org language settings. Use `--dry-run` before the first live run.

## Installation

```bash
pip install -r requirements.txt
```

Application code lives under `src/`. Run with `PYTHONPATH=src` and `python src/main.py …`, or install in editable mode (includes pytest):

```bash
pip install -e ".[dev]"
```

## Workflow

### Stage 1 — `discover bitbucket` or `discover spreadsheet`

**Bitbucket** walks projects and repositories, checks each repo for commits (zero commits → `is_empty: true`), records **`last_committer_name`** and **`last_committer_email`** from the latest commit when not empty (API `committer`, falling back to `author`), **`last_commit_date`** as UTC ISO-8601 from `committerTimestamp` (falling back to `authorTimestamp`), reads a YAML file from non-empty repos (see [YAML format](#yaml-file-format)), merges AppSec fields with API metadata, and either prints a JSON **array of rows** to stdout or writes **discovery JSON** with `-o` / `--output`. With `-o`, also writes **`bitbucket-empty-repos.json`** by default listing empty repositories (override with `--empty-repos-output`; disable with `--no-empty-repos-output`).

**Spreadsheet** reads `bb-repo-mapping.xlsx` (project keys + semicolon-delimited repo slugs), queries Bitbucket per repo for YAML-derived APM and full row metadata (see [Stage 1 (spreadsheet)](#stage-1-spreadsheet)), and writes discovery JSON with `source: bitbucket`.

Discovery is the handoff artifact for Stages 2 and 3. Shape: `version`, `source` (`bitbucket` or `spreadsheet`), `rows`, and optional `checkpoint` for resume (Bitbucket file output). Legacy **primary mapping** files (wrapper without `source`, or a bare array) are still accepted as `--discovery` input in Stages 2–3; `source` is treated as `bitbucket` for compatibility.

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

Iterates **every org** in `SNYK_GROUP_ID` and, per org: **deletes** Snyk projects with type `dockerfile`, **PUT**s recurring test frequency to `never` on all remaining projects, **PUT**s the Stage 2.3 Bitbucket Server integration settings profile, and **PATCH**es org Python language settings to **3.12** (Pip). Writes **`post-import-cleanup-report.json`** (version 2). **`--dry-run`** prints the report to stdout without DELETE, PUT, or PATCH. Requires `SNYK_INTEGRATIONS_API=v1`. **Destructive** — run dry-run first. Existing Python projects may need a re-test for scan results to reflect the new version.

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
| `SNYK_INTEGRATIONS_API` | Yes | Must be `v1` (default). Integration settings PUT is not implemented for REST. |
| `SNYK_API`, `SNYK_API_VERSION` | No | Same as Stage 3 (REST base and version query param). |
| `SNYK_HTTP_MAX_ATTEMPTS`, `SNYK_HTTP_BACKOFF_S` | No | Same as Stage 3. |

| Flag | Description |
|------|-------------|
| `--output PATH` | Cleanup report (default: `post-import-cleanup-report.json`). |
| `--dry-run` | Print report JSON to stdout; no DELETE, PUT, or PATCH. |

Processes **every org** in the group. **Destructive** — deletes Dockerfile Snyk projects; run `--dry-run` first.

### Optional `.env`

If you omit `--env-file`, the CLI loads `.env` from the **current working directory** when present (`KEY=value`; `#` comments and blank lines ignored). Stages 3 and 4 accept `--env-file` for Snyk settings.

## Commands reference

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `discover bitbucket` | Bitbucket → discovery or stdout rows | `-o`, `--empty-repos-output`, `--no-empty-repos-output`, `--env-file`, `--max-repos`, `--flush-interval` |
| `discover spreadsheet` | `bb-repo-mapping.xlsx` + Bitbucket → discovery | `-i`, `-o`, `--env-file`, `--max-repos`, `--flush-interval`, empty-repos flags |
| `snyk-orgs` | discovery → `snyk-orgs.json` | `--discovery`, `--output`, `--group-id`, `--template-org-id`, `--dry-run` |
| `snyk-broker-plan` | snyk-orgs → broker-org-plan.json | `--snyk-orgs`, `--output`, `--tenant-id`, `--install-id`, `--env-file`, `--dry-run` |
| `snyk-broker-apply` | plan → broker-org-apply-report.json | `--plan`, `--output`, `--env-file`, `--dry-run` |
| `snyk-broker-integration-settings` | apply report → settings report | `--report`, `--output`, `--env-file`, `--dry-run` |
| `snyk-import` | discovery → `snyk-import.json` + Snyk IDs | `--discovery`, `--output`, `--repos-per-batch` (optional), `--snyk-orgs`, `--default-org-id`, `--env-file`, `--dry-run` |
| `snyk-post-import-cleanup` | group-wide post-import normalization | `--output`, `--env-file`, `--dry-run` |

```bash
PYTHONPATH=src python src/main.py -h
PYTHONPATH=src python src/main.py discover -h
PYTHONPATH=src python src/main.py discover bitbucket -h
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

Version 2 report with per-org outcomes under `dockerfile_projects`, `recurring_test_frequency`, `integration_settings`, and `python_language_settings` (each with `deleted`/`updated`, `skipped`, and `failed` arrays as applicable). Metadata includes `group_id`, `settings_profile` (`bitbucket-server-default-v1`), and `python_version` (`3.12`).

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

PYTHONPATH=src python src/main.py snyk-post-import-cleanup --dry-run

PYTHONPATH=src python src/main.py snyk-post-import-cleanup \
  --output post-import-cleanup-report.json \
  --env-file .env
```

**Exit codes:** `0` success, `1` runtime error (e.g. API failure), `2` configuration / usage / validation error.

## Scripts

### Branch mismatch reimport (`scripts/reimport_mismatched_targets.py`)

Operational script for Scotia-style branch remediation: reads a `diff.json` artifact (output of a Bitbucket-vs-Snyk branch comparison), deletes each mismatched Snyk target, and reimports it with the correct `production_branch` via [`snyk-api-import`](https://docs.snyk.io/developer-tools/snyk-apps/tool-snyk-api-import).

Each diff entry requires `apm_code` (Snyk org name), `repository_name` (target display name, e.g. `BB/my-service`), `production_branch` (desired branch), and `target_reference` (current wrong branch).

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
| `src/commands/spreadsheet_cli.py` | Stage 1 spreadsheet |
| `src/commands/snyk_orgs_cli.py` | Stage 2 |
| `src/commands/snyk_broker_plan_cli.py` | Stage 2.1 Broker Plan |
| `src/commands/snyk_broker_apply_cli.py` | Stage 2.2 Broker Apply |
| `src/commands/snyk_broker_integration_settings_cli.py` | Stage 2.3 integration settings |
| `src/commands/snyk_import_cli.py` | Stage 3 |
| `src/commands/snyk_post_import_cleanup_cli.py` | Stage 4 post-import cleanup |
| `src/common/` | Discovery document, mapper, output state, spreadsheet ingestion |
| `src/config/` | Environment and optional `.env` |
| `src/integrations/` | HTTP retry, Bitbucket client, Snyk REST client |
| `src/snyk/` | Org/import builders, enrichment helpers, branch mismatch reimport |
| `scripts/` | Operational scripts (branch mismatch reimport) |
| `tests/` | Unit tests |
