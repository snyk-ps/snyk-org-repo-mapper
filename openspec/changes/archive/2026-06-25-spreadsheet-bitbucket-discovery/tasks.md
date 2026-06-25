## 1. Spreadsheet + Bitbucket discovery

- [x] 1.1 Add [`bb_repo_mapping.py`](../../../src/common/spreadsheet/bb_repo_mapping.py) + `iter_first_sheet_ab`
- [x] 1.2 Add `get_repository`, `repository_has_default_branch`; master fallback in `default_branch_tuple`
- [x] 1.3 Add `iter_mapping_for_repos` + no-default-branch empty handling
- [x] 1.4 Refactor [`spreadsheet_cli.py`](../../../src/commands/spreadsheet_cli.py) + [`discovery_helpers.py`](../../../src/commands/discovery_helpers.py)
- [x] 1.5 Remove legacy [`mapping.py`](../../../src/common/spreadsheet/mapping.py)

## 2. Stage 3 batching

- [x] 2.1 Add `--repos-per-batch`, `split_import_targets`, `batch_import_output_paths`
- [x] 2.2 Tests for batching and dry-run plan

## 3. Documentation and OpenSpec

- [x] 3.1 Update README
- [x] 3.2 OpenSpec proposal, design, spec delta, tasks
- [x] 3.3 `openspec validate spreadsheet-bitbucket-discovery`
