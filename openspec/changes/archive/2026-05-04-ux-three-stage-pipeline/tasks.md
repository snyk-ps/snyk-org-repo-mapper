# Tasks: Three-stage UX pipeline

## 1. Intermediate schema and parsing

- [x] Document and implement Stage 1 JSON `version` / `source` / `rows` (and optional `checkpoint`) per [design.md](./design.md).
- [x] Add `parse_discovery_document` (or equivalent) next to [`parse_primary_json_payload`](../../../src/common/output_state.py) or in a dedicated module; reject unknown versions.
- [x] Unit tests: Bitbucket-shaped and spreadsheet-shaped rows round-trip through Stage 2/3 helpers.

## 2. Stage 1 CLI (`discover`)

- [x] Bitbucket ingress: refactor [`bitbucket_cli`](../../../src/commands/bitbucket_cli.py) logic so default output is the **intermediate** (not mixed snyk sidecars unless explicitly deprecated flags removed).
- [x] Spreadsheet ingress: align [`spreadsheet_cli`](../../../src/commands/spreadsheet_cli.py) to emit the **same** intermediate schema.
- [x] Update [`commands/dispatch.py`](../../../src/commands/dispatch.py) subcommand table and help text.

## 3. Stage 2 CLI (`snyk-orgs`)

- [x] Replace [`snyk_prepare_orgs_cli`](../../../src/commands/snyk_prepare_orgs_cli.py) behavior: read intermediate only; write `snyk-orgs.json` via [`build_snyk_orgs_document`](../../../src/snyk/outputs.py).
- [x] Remove standalone `snyk-project-context` output from user-facing Stage 2 unless retained as optional derived file (design decision locked in implementation).

## 4. Stage 3 CLI (`snyk-import`)

- [x] Merge generation + enrichment: read intermediate, build targets, call Snyk REST ([`integrations/snyk/client.py`](../../../src/integrations/snyk/client.py), [`snyk/enrichment.py`](../../../src/snyk/enrichment.py)), optional orgs-file cross-check; write `snyk-import.json`.
- [x] Remove or redirect [`snyk_enrich_import_cli`](../../../src/commands/snyk_enrich_import_cli.py) entry points per proposal.

## 5. Packaging and cleanup

- [x] Update [`pyproject.toml`](../../../pyproject.toml) `[project.scripts]` to new names; drop legacy script names **or** document one-release aliases.
- [x] Delete dead code paths (old flags `--snyk-orgs-output` on mapper, etc.) once Stage 1 no longer emits Snyk files.

## 6. Tests

- [x] End-to-end style tests with fixtures for three stages (mock Snyk HTTP for Stage 3).
- [x] Update or replace tests tied to `snyk-prepare-orgs` / `snyk-enrich-import` / old dispatcher strings.

## 7. README rewrite (structure and content)

Apply the following **target outline** to [`README.md`](../../../README.md) (replace overlapping sections; keep accurate technical detail):

1. **Title + one-paragraph overview** — What the tool does in three sentences (discover → orgs file → import file).
2. **Quick start (happy path)** — Numbered 1–3 with concrete `main.py` / installed script examples and file names.
3. **Requirements** — Python version, network, tokens (brief pointer to per-stage config).
4. **Installation** — `pip install -e ".[dev]"` or `requirements.txt`; how to get `main.py` on `PATH`.
5. **Three-stage workflow (primary narrative)**  
   - Stage 1: inputs/outputs, Bitbucket vs spreadsheet, intermediate schema pointer.  
   - Stage 2: inputs/outputs, link to Snyk `orgs:create` docs.  
   - Stage 3: inputs/outputs, Snyk REST reads, no Bitbucket in Stage 3.
6. **Configuration by stage** — Three subsubsections or tables:  
   - **Stage 1 (Bitbucket):** `BITBUCKET_URL`, `BITBUCKET_PAT`, `BITBUCKET_FILE_PATH`, retries, flush.  
   - **Stage 1 (Spreadsheet):** column rules (`BB::` selector), no `BITBUCKET_*`.  
   - **Stage 2:** (none or “paths only”).  
   - **Stage 3:** `SNYK_TOKEN`, `SNYK_GROUP_ID`, `SNYK_API_BASE`, `SNYK_API_VERSION`, retry envs.
7. **Commands reference** — Table: command → purpose → key flags (link to `--help`).
8. **File formats** — Subsections: intermediate JSON, `snyk-orgs.json`, `snyk-import.json` (minimal examples).
9. **YAML format** — Keep current `appSec` example (still used in Stage 1 Bitbucket path).
10. **Testing** — `pytest` + `PYTHONPATH=src`.
11. **Project layout** — Update table to reflect new command modules and removed legacy names.

**Remove / relocate from current README**

- [x] Remove the table row pair that labels `snyk-prepare-orgs` as “Stage 1” and `snyk-enrich-import` as “Stage 2” (superseded numbering).
- [x] Remove the standalone “Snyk two-stage workflow” subsection that documents `snyk-prepare-orgs` + `snyk-enrich-import`; replace with **three-stage** section.
- [x] Collapse duplicate `BITBUCKET_*` / `SNYK_*` prose if split by stage above.
- [x] Update “Project layout” if `src/main.py` or `commands/*` names change.

## 8. OpenSpec archive

- [x] After implementation, archive this change and merge deltas into `openspec/specs/` per team workflow; **replace** [`openspec/specs/snyk-import-enrichment/spec.md`](../../specs/snyk-import-enrichment/spec.md) Purpose (still “TBD”) with a sentence pointing to `three-stage-snyk-pipeline` as the user-journey source of truth, or fold requirements if consolidating capabilities.
