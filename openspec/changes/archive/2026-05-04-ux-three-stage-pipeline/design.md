# Design: Three-stage UX pipeline

## Command names (proposed; implementer may adjust before merge)

| Stage | Proposed `main.py` subcommand | Role |
|-------|------------------------------|------|
| 1 | `discover` (or `stage1-discover`) | Bitbucket **or** spreadsheet → intermediate JSON |
| 2 | `snyk-orgs` (or `stage2-snyk-orgs`) | Intermediate → `snyk-orgs.json` |
| 3 | `snyk-import` (or `stage3-snyk-import`) | Intermediate (+ optional orgs file) → `snyk-import.json` + Snyk REST |

Legacy names (`bitbucket`, `spreadsheet`, `snyk-prepare-orgs`, `snyk-enrich-import`) MAY be removed or kept as thin aliases for one release; **README MUST NOT** present them as the primary path after implementation.

## Stage 1 intermediate artifact (canonical)

**Single file** (e.g. `discovery.json` — exact filename is a CLI flag, not normative here) to avoid drift between “primary mapping” and separate `snyk-project-context.json` unless implementation proves a split is still needed.

### Suggested JSON shape

```json
{
  "version": 1,
  "source": "bitbucket",
  "rows": [
    {
      "apm_code": "ABC1",
      "repository_path": "PROJ/slug",
      "repository_name": "My Service",
      "production_branch": "main",
      "bitbucket_project_name": "My Project"
    }
  ],
  "checkpoint": null
}
```

- **`source`:** `"bitbucket"` | `"spreadsheet"` (MUST be set for diagnostics and parity tests).
- **`rows`:** Same logical fields as today’s primary mapping rows produced by [`mapping_row`](../../../src/common/mapper.py) / spreadsheet mapping, so Stages 2 and 3 can reuse [`apm_codes_from_rows`](../../../src/snyk/outputs.py), [`build_snyk_orgs_document`](../../../src/snyk/outputs.py), [`build_snyk_import_document`](../../../src/snyk/outputs.py), and [`project_apm_map_from_rows`](../../../src/snyk/project_context.py) **without** a second file—**unless** implementation retains `snyk-project-context.json` as a derived cache; if so, document one canonical source of truth.

**Bitbucket path:** MUST enumerate projects and repos via existing REST client, read YAML at `BITBUCKET_FILE_PATH`, apply existing branch resolution rules.

**Spreadsheet path:** MUST produce **row-equivalent** objects; document known gaps (e.g. `bitbucket_project_name` may equal project **key** from selector, not display name from API).

**Conflict rule:** When deriving **one `apm_code` per `projectKey`**, the same rule as today applies: **more than one distinct non-empty `apm_code` under the same project key → validation failure** with actionable stderr (reuse [`project_apm_map_from_rows`](../../../src/snyk/project_context.py) semantics).

**Resume:** Bitbucket Stage 1 MAY retain optional resume/checkpoint behavior using the same wrapper pattern as [`build_primary_document`](../../../src/common/output_state.py); spreadsheet Stage 1 is typically single-shot.

## Stage 2 — `snyk-orgs.json`

- **Input:** Stage 1 intermediate only.
- **Output:** `orgs` array compatible with **Snyk API Import Tool** org creation (placeholders for `groupId` / `sourceOrgId` as today).
- **APIs:** None by default.

## Stage 3 — `snyk-import.json`

- **Input:** Stage 1 intermediate (required). **`snyk-orgs.json`** (optional but recommended) for **cross-check** of expected org names before Snyk calls.
- **Process:** Build targets from rows (same as [`build_snyk_import_document`](../../../src/snyk/outputs.py)); resolve `orgId` / `integrationId` via [`SnykRestClient`](../../../src/integrations/snyk/client.py) patterns (group org listing, per-org integrations, **`bitbucket-server`** type).
- **Output:** Atomic write to `snyk-import.json`.
- **Bitbucket:** No network calls in Stage 3 if intermediate is complete.

## Environment variables (by stage)

| Stage | Variables |
|-------|-----------|
| 1 (Bitbucket) | `BITBUCKET_URL`, `BITBUCKET_PAT`, optional `BITBUCKET_FILE_PATH`, HTTP retry / flush as today |
| 1 (Spreadsheet) | None (file paths only) |
| 2 | None |
| 3 | `SNYK_TOKEN`, `SNYK_GROUP_ID`, optional `SNYK_API_BASE`, `SNYK_API_VERSION`, HTTP retry envs |

## CLI / help UX

- Top-level `main.py -h` lists **three stages first**, then any auxiliary commands.
- Each stage has its own `--help` with **required** inputs/outputs spelled out.
- Exit codes: preserve `0` / `2` (validation/usage) / `1` (runtime/API) convention.

## Security

- Tokens only via env / `--env-file`; never log `Authorization` values (unchanged from current practice).

## Migration (for `tasks.md`)

Document one-time guidance: users replacing old flow run **Stage 1** to replace `mapping.json` + optional context files with the new intermediate; then Stage 2 / 3.
