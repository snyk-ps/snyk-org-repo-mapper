## 1. Bitbucket API and parsing

- [x] 1.1 Add `parse_committer_identity(commit)` and `repository_latest_commit` to [`src/integrations/bitbucket/client.py`](../../../src/integrations/bitbucket/client.py); remove `repository_has_commits`
- [x] 1.2 Unit tests in [`tests/test_bitbucket_client_commits.py`](../../../tests/test_bitbucket_client_commits.py): empty page, committer present, author fallback, missing identity

## 2. Stage 1 mapper

- [x] 2.1 Extend `mapping_row` / `iter_mapping` with `last_committer_name` and `last_committer_email` in [`src/common/mapper.py`](../../../src/common/mapper.py)
- [x] 2.2 Unit tests in [`tests/test_mapper.py`](../../../tests/test_mapper.py): empty repo null fields, non-empty populated, fake client uses `repository_latest_commit`

## 3. Documentation

- [x] 3.1 Update [README.md](../../../README.md): discovery row fields and JSON example

## 4. OpenSpec alignment

- [x] 4.1 Run `openspec validate discovery-last-committer`
