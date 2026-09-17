## Why

Bitbucket repositories often carry meaningful AppSec YAML on feature or release branches, not on the configured default branch. Discovery currently reads YAML from the default branch and backfills `production_branch` from Bitbucket when YAML omits it. Operators need YAML-derived routing (`apm_code`, `production_branch`) and commit metadata aligned to the branch that is actually active (most recent commit), while still recording Bitbucket's configured default branch and archive status for audit and remediation.

## What Changes

- **Stage 1 (Bitbucket + spreadsheet Bitbucket paths only):** Determine **`latest_active_branch`** as the branch whose tip has the most recent commit across the repository; parse the configured AppSec YAML file from that branch only.
- **`apm_code` and `production_branch`:** Both SHALL come strictly from parsed YAML on `latest_active_branch`. **BREAKING:** Remove Bitbucket default-branch fallback for `production_branch` (null when YAML omits or blanks `productionBranch`).
- **Commit metadata:** `last_commit_date`, `last_committer_name`, and `last_committer_email` SHALL reflect the latest commit on `latest_active_branch` (not repo-wide `commits?limit=1`).
- **New discovery row fields (Bitbucket rows):** `bitbucket_default_branch`, `latest_active_branch`, `is_archived`.
- **Archived repositories:** Skip archived Bitbucket repos by default (no row emitted). Include them when **`--include-archived`** is set or **`BITBUCKET_INCLUDE_ARCHIVED`** is truthy. Applies to `discover bitbucket` and spreadsheet-driven Bitbucket discovery.
- **YAML file path:** Unchanged — `BITBUCKET_FILE_PATH` env var, default `appsec.yaml`.
- **Docs:** Update README discovery JSON examples and Bitbucket Stage 1 description.

**Out of scope:**

- GitHub discovery (unchanged: default branch + YAML fallback remains).
- New ingress modes.
- Stage 2–4 logic changes (new fields are pass-through metadata unless already consumed).
- Changing YAML key parsing (`security.apmCode`, `security.productionBranch`).
- Renaming or changing `BITBUCKET_FILE_PATH` semantics.
- GitHub archived-repo handling.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `three-stage-snyk-pipeline`: Bitbucket Stage 1 branch selection, YAML sourcing, `production_branch` semantics, commit metadata scope, archived-repo filtering, and new row fields.

## Impact

- **Code:** [`src/integrations/bitbucket/client.py`](../../../src/integrations/bitbucket/client.py), [`src/common/mapper.py`](../../../src/common/mapper.py), [`src/config/__init__.py`](../../../src/config/__init__.py), [`src/commands/bitbucket_cli.py`](../../../src/commands/bitbucket_cli.py), [`src/commands/spreadsheet_cli.py`](../../../src/commands/spreadsheet_cli.py).
- **Tests:** Bitbucket client branch listing, mapper integration tests, CLI/config tests.
- **Docs:** [`README.md`](../../../README.md).
- **Breaking:** Discovery rows may have `production_branch: null` where YAML omits `productionBranch` (previously defaulted to Bitbucket default branch). Archived repos omitted by default. Re-run discovery before Stage 3 import planning.
