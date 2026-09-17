## 1. Bitbucket API — latest active branch

- [x] 1.1 Add `iter_branches(project_key, repo_slug, *, details=True)` paginator to [`src/integrations/bitbucket/client.py`](../../../src/integrations/bitbucket/client.py)
- [x] 1.2 Add branch tip timestamp helper (prefer `committerTimestamp`, fall back to `authorTimestamp` from branch metadata)
- [x] 1.3 Add `resolve_latest_active_branch(client, project_key, repo_slug) -> tuple[str, str, dict] | None` returning `(at_ref, display_id, tip_commit)` with lexicographic tie-break on `displayId`
- [x] 1.4 Add `repository_latest_commit_on_ref(project_key, repo_slug, at_ref)` for branch-scoped `commits?until=&limit=1`
- [x] 1.5 Unit tests in [`tests/test_bitbucket_client_branches.py`](../../../tests/test_bitbucket_client_branches.py): pagination, newest branch wins, tie-break, empty branch list

## 2. Configuration and CLI

- [x] 2.1 Add `include_archived: bool` to [`Settings`](../../../src/config/__init__.py) from `BITBUCKET_INCLUDE_ARCHIVED` (default false; truthy: `1`, `true`, `yes`, case-insensitive)
- [x] 2.2 Add `--include-archived` to [`src/commands/bitbucket_cli.py`](../../../src/commands/bitbucket_cli.py) and [`src/commands/spreadsheet_cli.py`](../../../src/commands/spreadsheet_cli.py); CLI flag overrides env when set
- [x] 2.3 Unit tests in [`tests/test_config.py`](../../../tests/test_config.py) for `BITBUCKET_INCLUDE_ARCHIVED` parsing

## 3. Mapper — Bitbucket discovery rows

- [x] 3.1 Refactor [`_mapping_row_for_repository`](../../../src/common/mapper.py) to resolve `latest_active_branch`, fetch YAML at that ref, and populate new fields
- [x] 3.2 Emit `bitbucket_default_branch`, `latest_active_branch`, and `is_archived` on all emitted Bitbucket rows (including empty)
- [x] 3.3 Remove Bitbucket use of `resolve_production_branch` fallback; set `production_branch` from YAML only (null when missing)
- [x] 3.4 Scope commit metadata to tip commit on `latest_active_branch`
- [x] 3.5 Skip archived repositories when `include_archived` is false (no row yielded, no checkpoint)
- [x] 3.6 Pass `include_archived` through `iter_mapping` and `iter_mapping_for_repos`
- [x] 3.7 Update [`tests/test_mapper.py`](../../../tests/test_mapper.py) and [`tests/test_spreadsheet_cli.py`](../../../tests/test_spreadsheet_cli.py) for new client methods, fields, archived skip/include, and strict `production_branch`

## 4. AppSec YAML helper

- [x] 4.1 Confirm `resolve_production_branch` remains GitHub-only; adjust Bitbucket mapper tests that assumed default-branch fallback

## 5. Documentation

- [x] 5.1 Update [`README.md`](../../../README.md): Bitbucket Stage 1 behavior (latest active branch, new row fields, `--include-archived`, `BITBUCKET_INCLUDE_ARCHIVED`, breaking `production_branch` change)
- [x] 5.2 Update discovery JSON example with `bitbucket_default_branch`, `latest_active_branch`, and `is_archived`

## 6. OpenSpec alignment

- [x] 6.1 Run `openspec validate bitbucket-latest-active-branch`
