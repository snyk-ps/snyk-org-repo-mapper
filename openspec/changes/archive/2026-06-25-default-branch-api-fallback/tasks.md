## 1. Bitbucket client

- [x] 1.1 Add `get_default_branch` (200 / 204 / 404 handling)
- [x] 1.2 Add `resolve_repository_branch` fallback chain
- [x] 1.3 Document gate matrix in `test_bitbucket_helpers.py`

## 2. Mapper

- [x] 2.1 Wire `_mapping_row_for_repository` to resolver
- [x] 2.2 Apply 404 + commits → synthetic master policy

## 3. Tests and docs

- [x] 3.1 Unit tests for API fallback and DNCLBATCH-like shapes
- [x] 3.2 Update README default-branch section
- [x] 3.3 OpenSpec delta for default-branch resolution
