## 1. Client extensions

- [x] 1.1 Add `SnykRestClient.iter_org_projects(org_id, *, project_type=None)` with v1 pagination in [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py)
- [x] 1.2 Add `SnykRestClient.delete_org_project(org_id, project_id)` (REST DELETE) in [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py)
- [x] 1.3 Add `SnykRestClient.update_project_settings(org_id, project_id, settings)` (v1 PUT) in [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py)
- [x] 1.4 Unit tests for new client methods in [`tests/test_snyk_client_post_import_cleanup.py`](../../../tests/test_snyk_client_post_import_cleanup.py)

## 2. Shared integration settings helper

- [x] 2.1 Add [`src/snyk/integration_settings_apply.py`](../../../src/snyk/integration_settings_apply.py) with `apply_bitbucket_integration_settings_to_org(client, org_id, org_name, *, dry_run) -> outcome dict`
- [x] 2.2 Refactor [`src/snyk/broker_integration_settings.py`](../../../src/snyk/broker_integration_settings.py) to use the shared helper; ensure existing Stage 2.3 tests still pass

## 3. Stage 4 logic and CLI

- [x] 3.1 Add [`src/snyk/post_import_cleanup.py`](../../../src/snyk/post_import_cleanup.py) with `run_post_import_cleanup(client, *, dry_run) -> report dict` (group org iteration, three steps, report v1)
- [x] 3.2 Add [`src/commands/snyk_post_import_cleanup_cli.py`](../../../src/commands/snyk_post_import_cleanup_cli.py) (`SNYK_TOKEN`, `SNYK_GROUP_ID`, v1 integrations gate, `--dry-run`, `--output`)
- [x] 3.3 Tests in [`tests/test_post_import_cleanup.py`](../../../tests/test_post_import_cleanup.py) (dry-run, report shape, partial failure exit semantics)

## 4. Wiring and docs

- [x] 4.1 Register in [`src/commands/dispatch.py`](../../../src/commands/dispatch.py) and [`pyproject.toml`](../../../pyproject.toml) as `repo-mapper-snyk-post-import-cleanup`
- [x] 4.2 Update [`README.md`](../../../README.md) with Stage 4 after Stage 3, env requirements, destructive-operation warning, and `--dry-run` guidance

## 5. Verification

- [x] 5.1 Run pytest for new and related tests (`test_post_import_cleanup`, `test_snyk_client_post_import_cleanup`, `test_broker_integration_settings`)
