# Proposal: Three-stage UX pipeline (Bitbucket + spreadsheet)

## Why

The product currently mixes **Bitbucket mapping**, **spreadsheet import**, and **Snyk companion** steps with overlapping “stage” language in documentation and multiple optional flags. Operators must infer the correct order of operations and which artifacts depend on which inputs. This change defines a **single linear UX**: discover repository metadata once → emit Snyk org-creation JSON → emit Snyk import JSON with resolved Snyk IDs—while still supporting **both** Bitbucket Server and spreadsheet as **Stage 1** ingresses.

## What Changes

1. **Stage 1 — Discover (Bitbucket or spreadsheet)**  
   Gather preliminary data: projects, repositories, YAML-derived **`apm_code`** and **production branch** (with Bitbucket default branch fallback where applicable). Write one **versioned intermediate artifact** consumable by Stages 2 and 3 (see [design.md](./design.md)).

2. **Stage 2 — Snyk orgs file**  
   Read **only** the Stage 1 artifact. Emit **`snyk-orgs.json`** in the shape required by the **Snyk API Import Tool `orgs:create`** flow (same semantics as [`build_snyk_orgs_document`](../../../src/snyk/outputs.py) today). No Bitbucket calls; **no Snyk HTTP** unless the design explicitly adds optional validation.

3. **Stage 3 — Snyk import file**  
   Read the Stage 1 artifact (and optionally **`snyk-orgs.json`** for cross-check). **Build** `snyk-import.json` targets for the import tool and **query the Snyk REST API** for **`orgId`** and **`integrationId`** per target (Bitbucket Server integration type). **No Bitbucket HTTP** in Stage 3 when the intermediate is sufficient.

4. **CLI and entry points**  
   The CLI **may be rewritten** (new subcommand names, removal of legacy commands and console script names). **Backwards compatibility is not required**; [`pyproject.toml`](../../../pyproject.toml) and [`README.md`](../../../README.md) SHALL be updated to match the final command surface.

5. **README**  
   Restructure documentation so the **three-stage workflow** is the primary narrative; configuration and examples grouped **by stage** (see [tasks.md](./tasks.md)).

6. **Specifications**  
   Add capability **`three-stage-snyk-pipeline`** with behavioral requirements. **Remove** superseded requirements from [`openspec/specs/snyk-import-enrichment/spec.md`](../../specs/snyk-import-enrichment/spec.md) via delta (that spec’s “stage 1/2” wording conflicts with this model).

## Non-goals

- Implementing **`orgs:create`** or the import **HTTP** execution inside this repository (file generation and Snyk **read** APIs for id resolution remain in scope for Stage 3 as today).
- Changing the on-disk **YAML schema** consumed from repositories (`appSec` / `apmCode`).

## Success criteria

- A new reader can follow **Stage 1 → 2 → 3** from README alone.
- Stage 1 outputs validate against the documented intermediate schema.
- Stage 2 output matches Snyk org-creation expectations; Stage 3 output matches import tool target expectations with resolved ids.
- Legacy `snyk-prepare-orgs` / `snyk-enrich-import` / combined mapper Snyk flags are either removed or clearly deprecated in favor of the new surface (per implementation tasks).

## Related code (current baseline)

- Bitbucket path: [`commands/bitbucket_cli.py`](../../../src/commands/bitbucket_cli.py), [`common/mapper.py`](../../../src/common/mapper.py)  
- Spreadsheet path: [`commands/spreadsheet_cli.py`](../../../src/commands/spreadsheet_cli.py)  
- Snyk helpers: [`snyk/outputs.py`](../../../src/snyk/outputs.py), [`snyk/project_context.py`](../../../src/snyk/project_context.py), [`snyk/enrichment.py`](../../../src/snyk/enrichment.py), [`integrations/snyk/client.py`](../../../src/integrations/snyk/client.py)  
- Dispatch: [`commands/dispatch.py`](../../../src/commands/dispatch.py), [`main.py`](../../../src/main.py)
