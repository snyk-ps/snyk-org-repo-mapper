## Why

Customers assign different APM codes (Snyk organization names) to repositories within the same Bitbucket project—for example project `ACCP` with repos mapped to `ABCD`, `ABCE`, and `ABCF`. Discovery already records `apm_code` per row from each repo’s AppSec YAML, but Stages 2–3 enforce a false rule of one APM code per `projectKey`, failing Stage 2 with conflicting-apm errors and (if that check were removed) mis-routing all repos in a project to a single Snyk org. The tool should map **APM code → Snyk org per repository**, not **Bitbucket project → single APM**.

## What Changes

- Remove Stage 2 validation that rejects multiple non-empty `apm_code` values under the same Bitbucket `projectKey`.
- Stage 3: resolve `orgId` and `integrationId` per import target using that repository’s discovery `apm_code` (lookup by `projectKey` + `repoSlug`).
- **BREAKING:** `--default-org-id` applies to targets whose **discovery row** has null or empty `apm_code`, not to whole projects absent from a project-level map.
- **BREAKING:** Composite `target.name` (`{projectKey}/{repository_name}`) when **that row** uses the default org, not when the project lacks a project-level APM entry.
- Replace `project_apm_map_from_rows` with `repo_apm_map_from_rows`; remove unused `snyk-project-context.json` build/parse helpers (internal/test-only today).
- Update README Stage 2–3 and `--default-org-id` documentation.

**Out of scope:**

- Stage 1 discovery row shape or mapper behavior (already per-repo).
- Broker Plan / Broker Apply (2.1 / 2.2).
- Re-import or migration for repos previously routed under project-level assumptions.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- `three-stage-snyk-pipeline`: Remove one-APM-per-project validation; Stage 2 and Stage 3 route by per-repository `apm_code`; update default-org semantics and scenarios.

## Impact

- **Code**: [`src/snyk/project_context.py`](../../../src/snyk/project_context.py), [`src/snyk/enrichment.py`](../../../src/snyk/enrichment.py), [`src/snyk/outputs.py`](../../../src/snyk/outputs.py), [`src/commands/snyk_orgs_cli.py`](../../../src/commands/snyk_orgs_cli.py), [`src/commands/snyk_import_cli.py`](../../../src/commands/snyk_import_cli.py).
- **Tests**: [`tests/test_project_context.py`](../../../tests/test_project_context.py), [`tests/test_snyk_orgs_cli.py`](../../../tests/test_snyk_orgs_cli.py), [`tests/test_snyk_enrichment.py`](../../../tests/test_snyk_enrichment.py), [`tests/test_snyk_outputs.py`](../../../tests/test_snyk_outputs.py).
- **Docs**: [`README.md`](../../../README.md).
- **Dependencies**: None.
