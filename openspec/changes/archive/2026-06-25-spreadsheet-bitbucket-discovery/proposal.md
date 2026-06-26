## Why

Operators maintain a curated repo list in `bb-repo-mapping.xlsx` (project keys + many slugs per row) and need APM codes from each repo’s AppSec YAML without crawling all of Bitbucket. Large imports also need multiple `snyk-import.json` files for the API Import Tool. Repos without a default branch should not fail discovery.

## What Changes

- **Stage 1 (spreadsheet):** Replace offline `apmcodes.xlsx` (A/B/D) with `bb-repo-mapping.xlsx` (`ProjectKey`, semicolon-delimited `RepoName`); call Bitbucket per listed repo for YAML, `is_empty`, and committer fields; write discovery with `source: bitbucket`.
- **Stage 1 (all Bitbucket paths):** Repos with no default branch → `is_empty: true` (no error); synthetic ref fallback `master` (not `main`).
- **Stage 3:** Optional `--repos-per-batch N` writes `snyk-import-001.json`, … with at most N targets each.
- **README / CLI help** updated; legacy spreadsheet format removed.

**Out of scope:**

- Keeping apmcodes A/B/D offline mode.
- Automatic Snyk Import Tool upload.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `three-stage-snyk-pipeline`: spreadsheet ingress, no-default-branch empty, master fallback, Stage 3 batch output.

## Impact

- **Code**: [`src/common/spreadsheet/bb_repo_mapping.py`](../../../src/common/spreadsheet/bb_repo_mapping.py), [`src/commands/spreadsheet_cli.py`](../../../src/commands/spreadsheet_cli.py), [`src/common/mapper.py`](../../../src/common/mapper.py), [`src/integrations/bitbucket/client.py`](../../../src/integrations/bitbucket/client.py), [`src/commands/snyk_import_cli.py`](../../../src/commands/snyk_import_cli.py), [`src/snyk/outputs.py`](../../../src/snyk/outputs.py).
- **Removed**: [`src/common/spreadsheet/mapping.py`](../../../src/common/spreadsheet/mapping.py).
- **Tests / docs**: README, spreadsheet and import tests.
