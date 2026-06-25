## 1. Repo APM map

- [x] 1.1 Add `repo_apm_map_from_rows` in [`src/snyk/project_context.py`](../../../src/snyk/project_context.py) (or rename module); remove `project_apm_map_from_rows` conflict raise
- [x] 1.2 Remove `build_project_context_document` and `parse_project_context_document`
- [x] 1.3 Update [`tests/test_project_context.py`](../../../tests/test_project_context.py): multi-APM same project succeeds; ACCP-style fixture

## 2. Stage 2

- [x] 2.1 Remove `project_apm_map_from_rows` validation from [`src/commands/snyk_orgs_cli.py`](../../../src/commands/snyk_orgs_cli.py)
- [x] 2.2 Add test in [`tests/test_snyk_orgs_cli.py`](../../../tests/test_snyk_orgs_cli.py): multi-APM `ACCP` discovery → exit 0, three org names in output

## 3. Stage 3 enrichment

- [x] 3.1 Change [`src/snyk/enrichment.py`](../../../src/snyk/enrichment.py) to `repo_apm: dict[tuple[str, str], str]` lookups and error messages per repository
- [x] 3.2 Update [`src/snyk/outputs.py`](../../../src/snyk/outputs.py) `build_snyk_import_document`: per-row default-org composite naming
- [x] 3.3 Wire [`src/commands/snyk_import_cli.py`](../../../src/commands/snyk_import_cli.py) to `repo_apm_map_from_rows`
- [x] 3.4 Tests in [`tests/test_snyk_enrichment.py`](../../../tests/test_snyk_enrichment.py) and [`tests/test_snyk_outputs.py`](../../../tests/test_snyk_outputs.py): same project two APM codes → two orgs; mixed default-org row

## 4. Documentation

- [x] 4.1 Update [`README.md`](../../../README.md) Stages 2–3 and `--default-org-id` (**BREAKING** semantics)

## 5. Verification

- [x] 5.1 Run full pytest suite
