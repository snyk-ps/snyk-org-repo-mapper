## Why

Scotia identified 896 Snyk targets where the stored branch (`target_reference`) does not match the AppSec YAML `productionBranch` because Bitbucket's default branch overrode the value during import before custom branching was enabled. Operators need a repeatable script that surgically deletes and reimports only the affected targets using the existing `diff.json` comparison artifact.

## What Changes

- Add **`scripts/reimport_mismatched_targets.py`**: operational CLI that reads a `diff.json` file, deletes mismatched targets, and reimports them with the correct `production_branch`.
- Extend **`SnykRestClient`** with REST Targets API methods (list, get, delete).
- Add **`src/snyk/branch_mismatch_reimport.py`**: orchestration (org resolution, target matching, delete, import batch build, `snyk-api-import` invocation).
- Add versioned **`branch-reimport-report.json`** output with per-entry outcomes.
- Document operational cautions (`imported-targets.log`, UAT dry-run) in README.

**Out of scope:**

- Generating `diff.json` (external comparison script).
- Full rediscovery, broker changes, or Stage 4 cleanup.
- Adding a `repo-mapper-*` console script entry.

## Capabilities

### New Capabilities

- `branch-mismatch-target-reimport`: Script and library code to delete mismatched Snyk targets and reimport with correct branch via `snyk-api-import`.

### Modified Capabilities

- (none)

## Impact

- **Code**: [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py), new [`src/snyk/branch_mismatch_reimport.py`](../../../src/snyk/branch_mismatch_reimport.py), new [`scripts/reimport_mismatched_targets.py`](../../../scripts/reimport_mismatched_targets.py).
- **Tests**: new [`tests/test_branch_mismatch_reimport.py`](../../../tests/test_branch_mismatch_reimport.py).
- **Docs**: [`README.md`](../../../README.md) scripts section.
- **APIs**: Snyk REST Targets (GET list, GET detail, DELETE); external `snyk-api-import` for reimport.
- **Dependencies**: `snyk-api-import` must be on PATH (or via `npx`).
