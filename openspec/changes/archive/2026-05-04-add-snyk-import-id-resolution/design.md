# Design: Two-stage Snyk org file + import enrichment

## Commands (both via [`src/main.py`](../../../src/main.py))

| Stage | Command (proposed) | Bitbucket API | Snyk API |
|-------|-------------------|---------------|----------|
| 1 | `snyk-prepare-orgs` | No (reads mapping from disk) | No |
| 2 | `snyk-enrich-import` | No | Yes |

Bitbucket API cost is incurred only when the user runs **`bitbucket-repo-mapper`** (or future variants) to **produce** the primary mapping. Stage 1 reads that file once and derives both outputs; stage 2 never contacts Bitbucket.

## Intermediate format: `snyk-project-context.json`

**Purpose:** Freeze **`projectKey → apm_code`** in one small file so stage 2 does not need the full primary mapping or a second derivation pass over thousands of rows—while keeping **zero** Bitbucket calls for enrichment.

**Suggested shape** (versioned):

```json
{
  "version": 1,
  "derived_from": "primary_mapping",
  "projects": {
    "MYPROJ": { "apm_code": "ABC1" }
  }
}
```

- **`projects`:** keys are Bitbucket **project keys**; each value MUST contain **`apm_code`** (non-empty string). Omit projects with no non-empty `apm_code` on any row, or document explicit behavior for “missing yaml” projects (recommend: omit project key; stage 2 fails if import targets reference it).

**Construction rules (stage 1):** identical conflict policy as enrichment:

1. Group primary mapping rows by `repository_path` prefix before first `/` (`projectKey`).
2. Collect non-empty `apm_code` values per project.
3. If more than one distinct value → **fail** with project key and conflicting slugs/codes in stderr.

**Atomic writes:** use [`atomic_write_json`](../../../src/common/output_state.py) and [`assert_safe_filesystem_path`](../../../src/common/output_state.py).

## Stage 1 — `snyk-prepare-orgs`

**Inputs**

- `--mapping PATH` — primary mapping JSON (required); parsed with [`parse_primary_json_payload`](../../../src/common/output_state.py).

**Outputs**

- `--snyk-orgs PATH` — same semantic content as [`build_snyk_orgs_document`](../../../src/snyk/outputs.py).
- `--snyk-project-context PATH` — intermediate JSON above (required output for this command).

**Logic**

- Reuse [`apm_codes_from_rows`](../../../src/snyk/outputs.py) for org list.
- New helper: `build_project_context_document(rows)` → versioned dict + conflict detection.

**Flags:** `--dry-run` (print distinct apm codes + project count + conflicts; no writes), `--env-file` optional only if future placeholders read env (not required initially).

## Stage 2 — `snyk-enrich-import`

**Inputs**

- `--snyk-orgs PATH` — **required**; validates expected org **names** (APM codes) against needs derived from project-context + import targets (behavior: warn or strict—default strict fail if org name missing from file’s `orgs[]` list when cross-checking).
- `--snyk-project-context PATH` — **required** default path; ties each `targets[].target.projectKey` to `apm_code`.
- `--snyk-import PATH` — read/write import JSON.
- Optional `--mapping PATH` — fallback only: rebuild project map from mapping instead of context file (same conflict rules); document that this duplicates derivation and does not reduce Bitbucket calls (Bitbucket still unused).

**Snyk API flow:** unchanged from prior design: list orgs in group → match org **name** to `apm_code` → per org resolve Bitbucket Server **integration id**.

**Configuration:** `SNYK_TOKEN`, `SNYK_GROUP_ID`, optional `SNYK_API_BASE`; `--env-file`; **no** `BITBUCKET_*`.

**Flags:** `--dry-run`, atomic write to import path.

### Cross-check: orgs file vs targets

Stage 2 SHOULD verify that every `apm_code` required by `(project-context ∪ import targets)` appears as an `orgs[].name` in the input orgs file (after normalize/trim), and fail with a clear message if not—catching typos before API calls.

## Optional optimization (same Bitbucket run as mapping)

When [`bitbucket_cli`](../../../src/commands/bitbucket_cli.py) or [`spreadsheet_cli`](../../../src/commands/spreadsheet_cli.py) already has `rows` in memory, they **may** also write `snyk-project-context.json` in the same flush as `snyk-orgs.json` to skip a separate stage-1 invocation. That is an implementation shortcut only; behavior MUST match `snyk-prepare-orgs` output for the same rows. Spec treats **`snyk-prepare-orgs`** as the canonical definition.

## Snyk REST API (reference)

Same as before—implementers verify against current docs:

- [List all organizations in a group](https://docs.snyk.io/reference/groups-v1#group-groupid-orgs)
- [Org integrations](https://docs.snyk.io/reference/integrations-v1#org-orgid-integrations-1)
- [Import targets](https://docs.snyk.io/reference/import-projects-v1#org-orgid-integrations-integrationid-import)

## Security

- Stage 2: token in env only; never log secrets (see team security skill).
- HTTPS via stdlib defaults.

## Atomicity

Stage 2: complete all API reads, build full updated import document, single atomic write.

## Open questions

- Org name field in Snyk API vs trim/case normalization.
- Pagination for large groups.
- Whether stage 2 **requires** orgs file to list **only** needed codes or allows extras (recommended: allow extras).
