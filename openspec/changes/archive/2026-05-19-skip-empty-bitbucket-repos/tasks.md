## 1. Bitbucket API and Stage 1

- [x] 1.1 Add `repository_has_commits(project_key, repo_slug)` to [`src/integrations/bitbucket/client.py`](../../../src/integrations/bitbucket/client.py) + unit tests (mocked `urlopen`)
- [x] 1.2 Add `row_is_empty(row)` helper; extend `mapping_row` / `iter_mapping` to set `is_empty` and skip YAML fetch when empty
- [x] 1.3 Add [`src/common/empty_repos_document.py`](../../../src/common/empty_repos_document.py); bitbucket CLI `--empty-repos-output` default + flush + stderr

## 2. Stage 3

- [x] 2.1 Skip `is_empty: true` rows in [`build_snyk_import_document`](../../../src/snyk/outputs.py)
- [x] 2.2 Unit tests: empty row excluded from targets; missing `is_empty` still included

## 3. Documentation

- [x] 3.1 Update [README.md](../../../README.md): discovery `is_empty`, `bitbucket-empty-repos.json`, Stage 3 omission

## 4. OpenSpec alignment

- [x] 4.1 Update proposal/design/spec/tasks for empty-repos artifact
