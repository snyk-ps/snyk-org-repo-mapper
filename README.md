# bitbucket-org-repo-mapper

This project helps you onboard Bitbucket Server repositories into Snyk in **three stages**: produce a single **discovery** JSON from Bitbucket or from a spreadsheet, derive **`snyk-orgs.json`** for org creation, then build **`snyk-import.json`** and resolve Snyk `orgId` / `integrationId` via the Snyk REST API. Stage 3 never calls Bitbucket.

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

3. **Stage 3 — import file + IDs** (Snyk API only):

   ```bash
   export SNYK_TOKEN='your-token'
   export SNYK_GROUP_ID='your-group-uuid'

   PYTHONPATH=src python src/main.py snyk-import \
     --discovery discovery.json \
     --output snyk-import.json \
     --snyk-orgs snyk-orgs.json
   ```

   Create orgs and integrations in Snyk (matching names in `snyk-orgs.json`) before Stage 3 if they do not exist yet.

After `pip install -e .`, the same flows are available as `repo-mapper-discover-bitbucket`, `repo-mapper-discover-spreadsheet`, `repo-mapper-snyk-orgs`, and `repo-mapper-snyk-import` on your `PATH` (each is a thin wrapper around `main.py` with the first arguments filled in).

## Requirements

- **Python 3.12+** (see `pyproject.toml`).
- **Stage 1 (Bitbucket):** HTTPS reachability to Bitbucket Server and a PAT that can list projects/repos and read file content.
- **Stage 1 (spreadsheet):** An `.xlsx` only; no Bitbucket.
- **Stage 2:** Paths only; no tokens.
- **Stage 3:** Snyk REST credentials (`SNYK_TOKEN`, `SNYK_GROUP_ID`); optional `--snyk-orgs` for a consistency check.

## Installation

```bash
pip install -r requirements.txt
```

Application code lives under `src/`. Run with `PYTHONPATH=src` and `python src/main.py …`, or install in editable mode (includes pytest):

```bash
pip install -e ".[dev]"
```

## Three-stage workflow

### Stage 1 — `discover bitbucket` or `discover spreadsheet`

**Bitbucket** walks projects and repositories, reads a YAML file from each repo (see [YAML format](#yaml-file-format)), merges AppSec fields with API metadata, and either prints a JSON **array of rows** to stdout or writes **discovery JSON** with `-o` / `--output`.

**Spreadsheet** maps columns A/B/D into the same row shape (see [Stage 1 (spreadsheet)](#stage-1-spreadsheet)) and writes the same discovery format with `-o`.

Discovery is the handoff artifact for Stages 2 and 3. Shape: `version`, `source` (`bitbucket` or `spreadsheet`), `rows`, and optional `checkpoint` for resume (Bitbucket file output). Legacy **primary mapping** files (wrapper without `source`, or a bare array) are still accepted as `--discovery` input in Stages 2–3; `source` is treated as `bitbucket` for compatibility.

### Stage 2 — `snyk-orgs`

Reads `--discovery`, writes **`snyk-orgs.json`** in the shape expected for Snyk org creation / import tooling (one org per distinct non-null `apm_code`). No Snyk or Bitbucket HTTP calls. See [Snyk REST — Organizations](https://docs.snyk.io/snyk-api/rest-api/endpoints/organizations) for how you apply this payload in your process.

### Stage 3 — `snyk-import`

Reads `--discovery`, builds import targets, then calls the **Snyk REST API** to resolve `orgId` and `integrationId`. Optional `--snyk-orgs` cross-checks that org names cover the APM codes needed by the import. **No Bitbucket HTTP** in this stage.

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

### Stage 1 (spreadsheet)

No `BITBUCKET_*` variables.

- **Columns:** **A** = APM code, **B** = repository selector (`BB::<project_key>::<repo_slug>`), **D** = display name. **C**, **E**, **F** ignored.
- **Filter:** Only rows whose **B** starts with **`BB::`** are imported; other prefixes (e.g. **`PG::`**) are skipped.
- **Offline fields:** `production_branch` is empty; `bitbucket_project_name` is the parsed project key from **B**.

### Stage 2

None beyond file paths. `--dry-run` prints JSON to stdout instead of writing `--output`.

### Stage 3

| Variable | Required | Description |
|----------|----------|-------------|
| `SNYK_TOKEN` | Yes | Snyk API token (`Authorization: token …`). |
| `SNYK_GROUP_ID` | Yes | UUID of the Snyk **Group** used to list orgs for name matching. |
| `SNYK_API_BASE` | No | REST base including `/rest`, e.g. `https://api.snyk.io/rest`. Default `https://api.snyk.io/rest`. |
| `SNYK_API_VERSION` | No | API version query (date string). Default `2024-10-15`. |
| `SNYK_HTTP_MAX_ATTEMPTS` | No | HTTP retry attempts. Default `5`. |
| `SNYK_HTTP_BACKOFF_S` | No | Base backoff between retries. Default `1.0`. |

### Optional `.env`

If you omit `--env-file`, the CLI loads `.env` from the **current working directory** when present (`KEY=value`; `#` comments and blank lines ignored). Stage 3 accepts `--env-file` for Snyk settings.

## Commands reference

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `discover bitbucket` | Bitbucket → discovery or stdout rows | `-o`, `--env-file`, `--max-repos`, `--flush-interval` |
| `discover spreadsheet` | `.xlsx` → discovery or stdout rows | `-i` / `--input`, `-o` |
| `snyk-orgs` | discovery → `snyk-orgs.json` | `--discovery`, `--output`, `--dry-run` |
| `snyk-import` | discovery → `snyk-import.json` + Snyk IDs | `--discovery`, `--output`, `--snyk-orgs` (optional), `--env-file`, `--dry-run` |

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
      "bitbucket_project_name": "My Project"
    }
  ],
  "checkpoint": {
    "project_key": "MYPROJ",
    "repo_slug": "my-service"
  }
}
```

`checkpoint` may be `null` when empty or not yet written. **Stdout** (no `-o`) is still a **bare array** of the same row objects.

### Primary mapping (legacy)

Older **wrapper** files used `version` + `rows` + optional `checkpoint` without `source`. Stages 2–3 treat those rows as Bitbucket-shaped. A **bare JSON array** of rows is also accepted.

### `snyk-orgs.json` (Stage 2)

One org per distinct non-null `apm_code` (sorted). Placeholders are intended for substitution before use with Snyk APIs:

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
appSec:
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
