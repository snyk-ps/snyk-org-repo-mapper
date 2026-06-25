## Why

Empty Bitbucket repositories (zero commits) cannot be meaningfully imported into Snyk but are still discovered today and appear in `snyk-import.json`, causing failed or pointless import attempts. Detecting emptiness during Stage 1 (when Bitbucket is already contacted) records the fact once and lets Stage 3 exclude those repos without extra API calls.

## What Changes

- **Stage 1 (Bitbucket only):** After listing each repo, call the commits API (`limit=1`); set boolean **`is_empty: true`** on the discovery row when there are zero commits; still include the row in discovery (audit/resume), but **skip `appsec.yaml` fetch** when empty (saves HTTP).
- **Stage 1 artifact:** When discovery writes to `-o` / `--output`, also write **`bitbucket-empty-repos.json`** by default (override with `--empty-repos-output`); lists all empty repos for operator review.
- **Stage 3:** `build_snyk_import_document` skips rows with `is_empty === true`.
- **README:** Document `is_empty`, `bitbucket-empty-repos.json`, and Stage 3 omission behavior.
- **Spreadsheet Stage 1:** Unchanged (no Bitbucket API; rows omit `is_empty` and are treated as not empty in Stage 3).

**Out of scope:**

- Re-defining empty as “no branches” or “no files on default branch”.
- Removing empty repos from discovery `rows` entirely (identify + flag, do not drop).
- Stage 2 changes (empty repos rarely contribute `apm_code`; existing org builder already ignores null APM).
- Post-hoc empty detection in Stage 3 (would require Bitbucket HTTP, violating Stage 3 boundary).

## Capabilities

### New Capabilities

- `bitbucket-empty-repos`: Versioned JSON artifact (`bitbucket-empty-repos.json` v1) listing repositories with `is_empty: true`, written during Bitbucket file-output discovery.

### Modified Capabilities

- `three-stage-snyk-pipeline`: Stage 1 Bitbucket rows include `is_empty`; Stage 3 omits those rows from import targets; Stage 1 writes empty-repos artifact when `-o` is set.

## Impact

- **Code**: [`src/integrations/bitbucket/client.py`](../../../src/integrations/bitbucket/client.py), [`src/common/mapper.py`](../../../src/common/mapper.py), [`src/common/empty_repos_document.py`](../../../src/common/empty_repos_document.py), [`src/snyk/outputs.py`](../../../src/snyk/outputs.py), [`src/commands/bitbucket_cli.py`](../../../src/commands/bitbucket_cli.py).
- **Tests**: Bitbucket client, mapper, outputs, import CLI.
- **Docs**: [`README.md`](../../../README.md).
- **Dependencies**: None (existing Bitbucket REST client patterns).
