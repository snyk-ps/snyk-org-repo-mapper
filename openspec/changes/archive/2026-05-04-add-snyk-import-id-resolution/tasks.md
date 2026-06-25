# Tasks: Two-stage Snyk org preparation + import enrichment

## 1. CLI routing

- [x] Extend [`src/main.py`](../../../src/main.py) with **`snyk-prepare-orgs`** and **`snyk-enrich-import`** (names finalizable) and update top-level usage.
- [x] Add `commands/snyk_prepare_orgs_cli.py` (stage 1).
- [x] Add `commands/snyk_enrich_import_cli.py` (stage 2).
- [x] (Optional) Refactor [`pyproject.toml`](../../../pyproject.toml) scripts to dispatch through `main.py`.

## 2. Shared domain helpers

- [x] Implement `build_project_context_from_rows(rows)` → versioned JSON + conflict detection (shared by stage 1 and optional mapper flush).
- [x] Unit tests for conflicts and for spreadsheet/bitbucket row shapes.

## 3. Stage 1 — prepare orgs

- [x] Parse `--mapping` via [`parse_primary_json_payload`](../../../src/common/output_state.py).
- [x] Write [`build_snyk_orgs_document`](../../../src/snyk/outputs.py) + project-context atomically.
- [x] `--dry-run` without writes.

## 4. Stage 2 — configuration + Snyk client

- [x] Snyk settings loader (`SNYK_TOKEN`, `SNYK_GROUP_ID`, `SNYK_API_BASE`).
- [x] `--env-file` via [`load_dotenv_file`](../../../src/config/__init__.py).
- [x] REST client + list group orgs + list integrations + Bitbucket Server integration type resolution.

## 5. Stage 2 — enrich import

- [x] Load required `--snyk-orgs`, `--snyk-project-context`, `--snyk-import`.
- [x] Cross-check org names in orgs file vs required `apm_code` set.
- [x] Optional `--mapping` fallback path (same project map semantics).
- [x] Patch targets; atomic write; `--dry-run`.

## 6. Optional mapper integration

- [x] When flushing `snyk-orgs` from [`bitbucket_cli`](../../../src/commands/bitbucket_cli.py) / [`spreadsheet_cli`](../../../src/commands/spreadsheet_cli.py), optionally write project-context if `--snyk-project-context-output` is set—must match stage 1 byte-for-byte logic (shared function).

## 7. Tests + docs

- [x] Tests: stage 1 outputs, stage 2 with mocked Snyk HTTP, cross-check failures.
- [x] Update [`README.md`](../../../README.md) with two-stage workflow.
- [x] Archive OpenSpec change when done.
