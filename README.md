# bitbucket-org-repo-mapper

Enumerate all repositories on **Bitbucket Server (Data Center)**, read a configurable YAML file from each repo (same relative path everywhere), merge `appSec` fields with REST API metadata, and print or save a JSON mapping. Optional companion files target the **Snyk API Import Tool** (org creation and Bitbucket Server import payloads).

## Requirements

- **Python 3.12+**
- **pip** (for installing dependencies from `requirements.txt`)
- A Bitbucket Server instance reachable over HTTPS and a **personal access token (PAT)** with permission to list projects and repositories and read repository content via the REST API (for the Bitbucket mapper path only)

## Installation

From the repository root, install runtime dependencies:

```bash
pip install -r requirements.txt
```

This installs **PyYAML** and anything else listed in `requirements.txt`. The application code lives under `src/`; you run it with **Python** and `PYTHONPATH=src` (see [Usage](#usage)).

To run tests, install **pytest** as well (or use an editable install with dev extras: `pip install -e ".[dev]"` from this repo, which follows `pyproject.toml`).

## Configuration

Configuration is read from **environment variables**. Values already set in the environment are never overwritten by a `.env` file.

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BITBUCKET_URL` | Yes | Base URL of your Bitbucket Server instance (with or without a trailing slash; it is normalized). Example: `https://bitbucket.company.com` or `https://bitbucket.company.com/bitbucket`. |
| `BITBUCKET_PAT` | Yes | Personal access token. Sent as `Authorization: Bearer <token>`. Do not commit this value or log it. |
| `BITBUCKET_FILE_PATH` | No | Path to the YAML file **inside each repository**, identical for every repo. Default: `appsec.yaml`. |
| `BITBUCKET_HTTP_RETRIES` | No | Maximum number of **attempts** per HTTP call (including the first). Default: `5`. Used for transient failures (e.g. `429`, `5xx`, network errors). |
| `BITBUCKET_HTTP_BACKOFF_S` | No | Base delay in seconds for exponential backoff between retries. Default: `1.0`. |
| `BITBUCKET_FLUSH_INTERVAL` | No | When writing to `--output`, flush the primary file (and optional Snyk files) every **N** newly processed repositories. Default: `1`. Overridable with `--flush-interval`. |

### Optional `.env` file

If you do not pass `--env-file`, the CLI loads `.env` from the **current working directory** when that file exists. Lines are `KEY=value`; `#` comments and blank lines are ignored. Use `--env-file /path/to/.env` to load a specific file instead.

### YAML file format

The tool expects YAML like:

```yaml
appSec:
  apmCode: ABC1
  productionBranch: main   # optional; if omitted or empty, the repo default branch from the API is used
```

## Usage

From the **repository root**, set `PYTHONPATH=src` so Python can import packages under `src/` (`commands`, `common`, etc.). The entry point is **`src/main.py`**: the **first argument** chooses which CLI runs:

| First argument | Role |
|----------------|------|
| `bitbucket` | Same behavior as the **`bitbucket-repo-mapper`** console script (Bitbucket Server API + YAML in each repo). |
| `spreadsheet` | Same behavior as **`bitbucket-repo-mapper-from-spreadsheet`** (build JSON from an `.xlsx` only; no Bitbucket). |

```bash
# Show dispatcher usage
PYTHONPATH=src python src/main.py -h

# Bitbucket mapper (set BITBUCKET_* or use .env first)
PYTHONPATH=src python src/main.py bitbucket [OPTIONS]

# Spreadsheet-only path
PYTHONPATH=src python src/main.py spreadsheet [OPTIONS]
```

If you install this project in **editable** mode (`pip install -e .`), the same CLIs are also available as **`bitbucket-repo-mapper`** and **`bitbucket-repo-mapper-from-spreadsheet`** on your `PATH` without `PYTHONPATH`.

### Spreadsheet import (no Bitbucket API)

Use **`spreadsheet`** as the first argument (or `bitbucket-repo-mapper-from-spreadsheet` after `pip install -e .`) when you already have an **Excel mapping** (for example AppSec exports) and want the **same JSON outputs** as the mapper—including optional Snyk API Import Tool files—**without** querying Bitbucket or configuring `BITBUCKET_*` credentials.

- **Columns:** **A** = APM code, **B** = repository selector (`BB::<project_key>::<repo_slug>`), **D** = repository display name. Columns **C**, **E**, and **F** are ignored.
- **Filter:** Only rows whose column **B** starts with **`BB::`** are imported. Other prefixes (such as **`PG::`**) are skipped entirely.
- **Offline fields:** `production_branch` is always an empty string (no YAML or API). `bitbucket_project_name` is set to the parsed **project key** from column B.

Example from the repository root (same as `-i`; you can pass the path alone as a positional argument):

```bash
PYTHONPATH=src python src/main.py spreadsheet \
  --input "data/AppSec Repo to APM - Sample.xlsx" \
  -o mapping-from-sheet.json \
  --snyk-orgs-output snyk-orgs.json \
  --snyk-import-output snyk-import.json
```

With `-o`, the primary file uses the same **versioned wrapper** format as the Bitbucket mapper; without `-o`, the command prints a JSON **array** to stdout.

### CLI options

Options below apply to **`python src/main.py bitbucket`** (and the `bitbucket-repo-mapper` entry point). The spreadsheet command supports its own flags (e.g. `--input` / positional `.xlsx`); run `PYTHONPATH=src python src/main.py spreadsheet -h` for details.

| Option | Description |
|--------|-------------|
| `-o`, `--output` | Write the primary mapping to this file using the **resumable wrapper** format (see below). If omitted, a JSON array is written to **stdout** (no resume). |
| `--env-file` | Path to a `.env` file to load before reading configuration. |
| `--max-repos N` | Process at most **N** new repositories in this run (after skipping any already present in the output file). Useful for partial or stress-test runs. |
| `--flush-interval N` | Flush outputs every **N** new repositories when `--output` is set. Overrides `BITBUCKET_FLUSH_INTERVAL`. |
| `--snyk-orgs-output PATH` | Write Snyk org-creation JSON (`orgs` array, one entry per distinct non-null `apm_code`). |
| `--snyk-import-output PATH` | Write Snyk Bitbucket Server import JSON (`targets` array, one entry per repository processed into the primary mapping). |

### Examples

Write `mapping.json` with incremental saves and optional Snyk companion files:

```bash
export BITBUCKET_URL='https://bitbucket.example.com'
export BITBUCKET_PAT='your-token'
export BITBUCKET_FILE_PATH='security/appsec.yaml'   # optional

PYTHONPATH=src python src/main.py bitbucket \
  -o mapping.json \
  --snyk-orgs-output snyk-orgs.json \
  --snyk-import-output snyk-import.json
```

Print a JSON array to stdout (no resume; full run in memory):

```bash
PYTHONPATH=src python src/main.py bitbucket > mapping.json
```

Limit to 50 repositories in one run:

```bash
PYTHONPATH=src python src/main.py bitbucket -o mapping.json --max-repos 50
```

## Output

### Primary mapping (stdout)

When **no** `-o` is used, the command prints a **JSON array** of objects. Each object includes:

| Field | Source |
|-------|--------|
| `apm_code` | `appSec.apmCode` in the file, or `null` if missing or if the file is absent |
| `repository_path` | `<project key>/<repository slug>` |
| `repository_name` | Repository name from the API |
| `production_branch` | `appSec.productionBranch` when set and non-empty; otherwise the repository **default branch** from the API |
| `bitbucket_project_name` | Project name from the API |

Example:

```json
[
  {
    "apm_code": "ABC1",
    "repository_path": "MYPROJ/my-service",
    "repository_name": "my-service",
    "production_branch": "main",
    "bitbucket_project_name": "My Project"
  }
]
```

### Primary mapping (file, `-o`)

When `-o` is set, the file uses a **versioned wrapper** so runs can be **resumed** after interruption:

```json
{
  "version": 1,
  "rows": [ ... same objects as in the array above ... ],
  "checkpoint": {
    "project_key": "MYPROJ",
    "repo_slug": "my-service"
  }
}
```

- **`checkpoint`** reflects the last repository represented in `rows` after the most recent successful flush (omit if there are no rows yet).
- **Resume:** On the next run, repositories whose `(project key, slug)` already appear in `rows` are skipped. New rows are appended and the file is rewritten periodically according to `--flush-interval` / `BITBUCKET_FLUSH_INTERVAL`.
- **Legacy files:** If an existing output file is a **bare JSON array** (older format), it is read correctly; the next successful write upgrades it to the wrapper format.

### Snyk org creation (`--snyk-orgs-output`)

One org per **distinct** non-null `apm_code` seen in the accumulated primary `rows` (sorted by APM code). Placeholders are meant for find-and-replace before use with Snyk APIs:

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

### Snyk import (`--snyk-import-output`)

One import target per row in the primary mapping. `orgId` and `integrationId` are placeholders (`******`); replace with your Snyk org and Bitbucket Server integration IDs.

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

Exit codes: `0` success, `1` runtime error (e.g. API failure), `2` invalid or missing configuration, missing/invalid `main.py` subcommand, or usage error when invoking `src/main.py`.

## Testing

```bash
pip install -r requirements.txt
pip install pytest
pytest
```

`pytest` picks up `pythonpath = ["src"]` from `pyproject.toml`, so tests resolve imports the same way as `PYTHONPATH=src` at the command line.

## Project layout

Source layout follows the repository’s **project guidelines** (see `.cursor/rules/guidelines.mdc`):

| Path | Purpose |
|------|---------|
| `src/main.py` | Application entry: dispatches to `bitbucket` or `spreadsheet` (see [Usage](#usage)) |
| `src/commands/` | CLI command modules (`bitbucket_cli`, `spreadsheet_cli`) |
| `src/common/` | Shared domain logic: mapping rows, YAML/AppSec parsing, primary output files, spreadsheet `.xlsx` ingestion |
| `src/config/` | Settings loaded from environment variables and optional `.env` |
| `src/integrations/` | External integrations: HTTP retry helpers, Bitbucket Server REST client |
| `src/snyk/` | Snyk API Import Tool JSON builders |
| `tests/` | Unit tests |
