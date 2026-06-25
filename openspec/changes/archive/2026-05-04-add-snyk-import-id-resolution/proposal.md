# Proposal: Snyk org file preparation and import ID resolution (two stages)

## Why

Today `snyk-import.json` is generated with placeholder `orgId` and `integrationId` values, and `snyk-orgs.json` is emitted alongside the primary mapping. Operators create orgs out-of-band, then must resolve IDs manually. This change defines **two explicit stages**—each a separate `main.py` command—so workflows stay clear: first materialize the org-creation file (and a tiny intermediate derived from the same mapping pass), then resolve import targets using that orgs file after orgs exist, **without placing additional Bitbucket API traffic on stage two**.

## What Changes

### Stage 1 — Prepare orgs (`snyk-prepare-orgs`, name TBD)

From an existing **primary mapping** JSON (Bitbucket or spreadsheet pipeline output):

1. Emit **`snyk-orgs.json`** using the same rules as today ([`build_snyk_orgs_document`](../../../src/snyk/outputs.py)): one org entry per distinct non-null `apm_code`, placeholders for group/source org.
2. Emit a **`snyk-project-context.json`** (intermediate, see [design.md](./design.md)): a deterministic **`projectKey → apm_code`** map with the same conflict rules as downstream enrichment (one `apm_code` per Bitbucket project key).

**No Snyk API** in stage 1. **No Bitbucket API** if the user passes an already-built mapping file (typical: run Bitbucket or spreadsheet mapper once, then run stage 1).

### Stage 2 — Enrich import (`snyk-enrich-import`, name TBD)

**Assumes Snyk orgs already exist** (names align with `apm_code` per existing convention).

1. **Requires** `snyk-orgs.json` as input (expected org names; optional future fields such as resolved ids if operators annotate the file). Same shape as emitted by [`build_snyk_orgs_document`](../../../src/snyk/outputs.py).
2. **Requires** `snyk-import.json` (placeholders for ids). Same shape as [`build_snyk_import_document`](../../../src/snyk/outputs.py).
3. **Requires** **`snyk-project-context.json`** from stage 1 so **`projectKey → apm_code`** is resolved **without** re-reading the full primary mapping or calling Bitbucket.
4. Queries **Snyk API** only: orgs in group, integrations per org; writes resolved `orgId` / `integrationId` atomically.

Optional **`--mapping`** fallback (same semantics as today) may be specified for ad-hoc use but is **discouraged** when project-context exists, to keep the “single mapping pass → frozen context” workflow obvious.

## CLI shape

- **Single dispatcher:** `main.py snyk-prepare-orgs …` and `main.py snyk-enrich-import …` (exact names implementer may finalize).
- Stage 1: mapping in, orgs + project-context out; optional `--dry-run`.
- Stage 2: orgs + project-context + snyk-import in; **`SNYK_*`** env; **no `BITBUCKET_*`** required.
- Thin setuptools wrappers may prepend argv; no standalone argparse roots bypassing [`main.py`](../../../src/main.py).

See [design.md](./design.md) for flags, intermediate schema, and API notes.

## Impact

- Two command modules under `src/commands/` (or one module with subcommands if preferred later).
- New JSON schema/version for intermediate file; shared conflict detection between stage 1 output and stage 2 consumption.
- Snyk HTTP client used **only** in stage 2.

## Success criteria

- Stage 1 produces valid `snyk-orgs.json` and `snyk-project-context.json` from any supported primary mapping shape (wrapper or legacy array).
- Stage 2 resolves import ids using orgs file + project-context + Snyk API with **zero Bitbucket calls**.
- Ambiguous `apm_code` per project fails in stage 1 (and stage 2 rejects inconsistent context if validated).
- `--dry-run` supported where specified; exit codes `0` / `2` / `1` aligned with existing CLIs.

## Non-goals

- Creating Snyk orgs or integrations via API (read-only Snyk usage in stage 2 plus local JSON writes).
- Matching Snyk orgs by Bitbucket **project display name** as the default (**APM code ↔ org name** remains the contract).

## Related artifacts

- Companion generators: [`src/snyk/outputs.py`](../../../src/snyk/outputs.py).
- Primary mapping parse: [`src/common/output_state.py`](../../../src/common/output_state.py).
