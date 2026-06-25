## 1. Client extensions

- [x] 1.1 Add `SnykRestClient.iter_org_targets(org_id, *, display_name=None)` with REST pagination in [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py)
- [x] 1.2 Add `SnykRestClient.get_org_target(org_id, target_id)` in [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py)
- [x] 1.3 Add `SnykRestClient.delete_org_target(org_id, target_id)` (REST DELETE) in [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py)
- [x] 1.4 Unit tests for new target client methods in [`tests/test_snyk_client_targets.py`](../../../tests/test_snyk_client_targets.py)

## 2. Branch mismatch reimport logic

- [x] 2.1 Add [`src/snyk/branch_mismatch_reimport.py`](../../../src/snyk/branch_mismatch_reimport.py) with diff loader/validator, target matching, delete orchestration, import batch build, and `snyk-api-import` subprocess invocation
- [x] 2.2 Tests in [`tests/test_branch_mismatch_reimport.py`](../../../tests/test_branch_mismatch_reimport.py) (matching, dry-run, batch building, mocked subprocess)

## 3. Scripts entrypoint

- [x] 3.1 Add [`scripts/reimport_mismatched_targets.py`](../../../scripts/reimport_mismatched_targets.py) CLI (`--input`, `--output`, `--dry-run`, `--repos-per-batch`, `--limit`, `--skip-import`, `--snyk-api-import-cmd`)

## 4. Documentation

- [x] 4.1 Update [`README.md`](../../../README.md) with `scripts/` section, operational notes (`imported-targets.log`, UAT dry-run)

## 5. Verification

- [x] 5.1 Run pytest for new and related tests
