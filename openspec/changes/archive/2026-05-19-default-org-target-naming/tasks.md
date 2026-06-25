## 1. Import target naming

- [x] 1.1 Add `default_org_target_name(project_key, repository_name, repo_slug)` in [`src/snyk/outputs.py`](../../../src/snyk/outputs.py)
- [x] 1.2 Extend `build_snyk_import_document` with optional `project_apm` and `default_org_id`; apply composite name when project has no APM entry and default org is set
- [x] 1.3 Pass `project_apm` and `default_org` from [`src/commands/snyk_import_cli.py`](../../../src/commands/snyk_import_cli.py) into `build_snyk_import_document`

## 2. Tests

- [x] 2.1 Unit test: two projects, same display name, default org → distinct `P1/foo` and `P2/foo` in [`tests/test_snyk_outputs.py`](../../../tests/test_snyk_outputs.py)
- [x] 2.2 Unit test: APM-mapped project → unprefixed name unchanged
- [x] 2.3 Unit test: default-org target with null `repository_name` → `{projectKey}/{repoSlug}`
- [x] 2.4 CLI test: existing default-org fixture asserts `target.name == "NOPM/r1"` in [`tests/test_snyk_import_cli.py`](../../../tests/test_snyk_import_cli.py)

## 3. Documentation

- [x] 3.1 Update [README.md](../../../README.md) Stage 3: document `target.name` = `{projectKey}/{repository_name}` for `--default-org-id` targets
