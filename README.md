# bitbucket-org-repo-mapper

This project helps you onboard Bitbucket Server repositories into Snyk in **stages**: produce a single **discovery** JSON from Bitbucket or from a spreadsheet, derive **`snyk-orgs.json`** for org creation, optionally plan and apply **Universal Broker** org–connection assignments, then build **`snyk-import.json`** and resolve Snyk `orgId` / `integrationId` via the Snyk REST API. Stage 3 never calls Bitbucket.

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

   Create orgs in Snyk (matching names in `snyk-orgs.json`) before Stage 2.2 — Broker Apply and Stage 3 if they do not exist yet.

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

5. **Stage 3 — import file + IDs** (Snyk API only):

   ```bash
   export SNYK_TOKEN='your-token'
   export SNYK_GROUP_ID='your-group-uuid'

   PYTHONPATH=src python src/main.py snyk-import \
     --discovery discovery.json \
     --output snyk-import.json \
     --snyk-orgs snyk-orgs.json
   ```

After `pip install -e .`, the same flows are available as `repo-mapper-discover-bitbucket`, `repo-mapper-discover-spreadsheet`, `repo-mapper-snyk-orgs`, `repo-mapper-snyk-broker-plan`, `repo-mapper-snyk-broker-apply`, and `repo-mapper-snyk-import` on your `PATH`.

## Requirements

- **Python 3.12+** (see `pyproject.toml`).
- **Stage 1 (Bitbucket):** HTTPS reachability to Bitbucket Server and a PAT that can list projects/repos and read file content.
- **Stage 1 (spreadsheet):** An `.xlsx` only; no Bitbucket.
- **Stage 2:** Paths only; no API tokens. You may pass **`--group-id`** / **`--template-org-id`** on the CLI to embed those UUIDs in `snyk-orgs.json` (still no HTTP).
- **Stages 2.1–2.2 (Broker):** `SNYK_TOKEN`, `SNYK_TENANT_ID`, `SNYK_BROKER_INSTALL_ID`; `SNYK_GROUP_ID` recommended for org name → UUID resolution.
- **Stage 3:** Snyk REST credentials (`SNYK_TOKEN`, `SNYK_GROUP_ID`); optional `--snyk-orgs` for a consistency check.

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

**Bitbucket** walks projects and repositories, checks each repo for commits (zero commits → `is_empty: true`), reads a YAML file from non-empty repos (see [YAML format](#yaml-file-format)), merges AppSec fields with API metadata, and either prints a JSON **array of rows** to stdout or writes **discovery JSON** with `-o` / `--output`. With `-o`, also writes **`bitbucket-empty-repos.json`** by default listing empty repositories (override with `--empty-repos-output`; disable with `--no-empty-repos-output`).

**Spreadsheet** maps columns A/B/D into the same row shape (see [Stage 1 (spreadsheet)](#stage-1-spreadsheet)) and writes the same discovery format with `-o`.

Discovery is the handoff artifact for Stages 2 and 3. Shape: `version`, `source` (`bitbucket` or `spreadsheet`), `rows`, and optional `checkpoint` for resume (Bitbucket file output). Legacy **primary mapping** files (wrapper without `source`, or a bare array) are still accepted as `--discovery` input in Stages 2–3; `source` is treated as `bitbucket` for compatibility.

### Stage 2 — `snyk-orgs`

Reads `--discovery`, writes **`snyk-orgs.json`** in the shape expected for Snyk org creation / import tooling (one org per distinct non-null `apm_code`). No Snyk or Bitbucket HTTP calls. Optional **`--group-id`** and **`--template-org-id`** set `groupId` and `sourceOrgId` on every row instead of placeholders (each flag is independent). See [Snyk REST — Organizations](https://docs.snyk.io/snyk-api/rest-api/endpoints/organizations) for how you apply this payload in your process.

### Stage 2.1 — Broker Plan (`snyk-broker-plan`)

Reads `snyk-orgs.json`, lists Universal Broker **deployments** and **connections** for `SNYK_TENANT_ID` + `SNYK_BROKER_INSTALL_ID`, keeps `bitbucket-server` connections only, pre-checks orgs already integrated per connection, and writes **`broker-org-plan.json`** with round-robin **assignments**. **GET only** (no Broker mutations).

### Stage 2.2 — Broker Apply (`snyk-broker-apply`)

Reads `broker-org-plan.json` and **POST**s org–connection integrations for each `assignments` entry (skips `already_integrated`). Writes **`broker-org-apply-report.json`**. Does **not** create deployments or connections. Orgs must already exist in Snyk; use `SNYK_GROUP_ID` when `org_id` is missing from the plan.

### Stage 3 — `snyk-import`

Reads `--discovery`, builds import targets (skips rows with **`is_empty: true`**), then calls the **Snyk REST API** to resolve `orgId` and `integrationId`. Optional `--snyk-orgs` cross-checks that org names cover the APM codes needed by the import. Optional **`--default-org-id`** routes targets from Bitbucket projects with no `apm_code` into one org; their `target.name` is **`{projectKey}/{repository_name}`** (repository slug when display name is absent) so repos with the same name in different projects stay unique. **No Bitbucket HTTP** in this stage.

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

No `BITBUCKET_*` variables.

- **Columns:** **A** = APM code, **B** = repository selector (`BB::<project_key>::<repo_slug>`), **D** = display name. **C**, **E**, **F** ignored.
- **Filter:** Only rows whose **B** starts with **`BB::`** are imported; other prefixes (e.g. **`PG::`**) are skipped.
- **Offline fields:** `production_branch` is empty; `bitbucket_project_name` is the parsed project key from **B**.

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
| `--default-org-id UUID` | Snyk org id for import targets whose Bitbucket project has no `apm_code`. Sets composite `target.name` = `{projectKey}/{repository_name}`. |

### Optional `.env`

If you omit `--env-file`, the CLI loads `.env` from the **current working directory** when present (`KEY=value`; `#` comments and blank lines ignored). Stage 3 accepts `--env-file` for Snyk settings.

## Commands reference

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `discover bitbucket` | Bitbucket → discovery or stdout rows | `-o`, `--empty-repos-output`, `--no-empty-repos-output`, `--env-file`, `--max-repos`, `--flush-interval` |
| `discover spreadsheet` | `.xlsx` → discovery or stdout rows | `-i` / `--input`, `-o` |
| `snyk-orgs` | discovery → `snyk-orgs.json` | `--discovery`, `--output`, `--group-id`, `--template-org-id`, `--dry-run` |
| `snyk-import` | discovery → `snyk-import.json` + Snyk IDs | `--discovery`, `--output`, `--snyk-orgs` (optional), `--default-org-id` (optional), `--env-file`, `--dry-run` |

```bash
PYTHONPATH=src python src/main.py -h
PYTHONPATH=src python src/main.py discover -h
PYTHONPATH=src python src/main.py discover bitbucket -h
PYTHONPATH=src python src/main.py snyk-orgs -h
PYTHONPATH=src python src/main.py snyk-import -h
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
      "is_empty": false
    }
  ],
  "checkpoint": {
    "project_key": "MYPROJ",
    "repo_slug": "my-service"
  }
}
```

`checkpoint` may be `null` when empty or not yet written. **Stdout** (no `-o`) is still a **bare array** of the same row objects. Bitbucket rows include **`is_empty`** (`true` when the repo has zero commits). Spreadsheet rows omit `is_empty`; Stage 3 treats missing `is_empty` as not empty.

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

Spreadsheet to discovery:

```bash
PYTHONPATH=src python src/main.py discover spreadsheet \
  --input "data/AppSec Repo to APM - Sample.xlsx" \
  -o discovery.json
```

**Exit codes:** `0` success, `1` runtime error (e.g. API failure), `2` configuration / usage / validation error.

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
| `src/main.py` | Entry: dispatches to `discover`, `snyk-orgs`, `snyk-import` |
| `src/commands/dispatch.py` | Router and console-script entrypoints |
| `src/commands/bitbucket_cli.py` | Stage 1 Bitbucket |
| `src/commands/spreadsheet_cli.py` | Stage 1 spreadsheet |
| `src/commands/snyk_orgs_cli.py` | Stage 2 |
| `src/commands/snyk_import_cli.py` | Stage 3 |
| `src/common/` | Discovery document, mapper, output state, spreadsheet ingestion |
| `src/config/` | Environment and optional `.env` |
| `src/integrations/` | HTTP retry, Bitbucket client, Snyk REST client |
| `src/snyk/` | Org/import builders, enrichment helpers |
| `tests/` | Unit tests |
