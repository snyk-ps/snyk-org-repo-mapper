## 1. Defaults and client

- [x] 1.1 Add [`src/snyk/integration_settings_defaults.py`](../../../src/snyk/integration_settings_defaults.py) with `BITBUCKET_SERVER_INTEGRATION_SETTINGS` and `SETTINGS_PROFILE_ID`
- [x] 1.2 Add `SnykRestClient.update_org_integration_settings` in [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py)
- [x] 1.3 Unit test PUT URL and body in [`tests/test_snyk_client_integration_settings.py`](../../../tests/test_snyk_client_integration_settings.py)

## 2. Stage logic and CLI

- [x] 2.1 Add [`src/snyk/broker_integration_settings.py`](../../../src/snyk/broker_integration_settings.py) (`load_apply_report`, `apply_integration_settings`)
- [x] 2.2 Add [`src/commands/snyk_broker_integration_settings_cli.py`](../../../src/commands/snyk_broker_integration_settings_cli.py)
- [x] 2.3 Tests in [`tests/test_broker_integration_settings.py`](../../../tests/test_broker_integration_settings.py)

## 3. Wiring and docs

- [x] 3.1 Register in [`src/commands/dispatch.py`](../../../src/commands/dispatch.py) and [`pyproject.toml`](../../../pyproject.toml)
- [x] 3.2 Update [`README.md`](../../../README.md) Stage 2.3 and configuration table

## 4. Verification

- [x] 4.1 Run pytest for new and related tests
