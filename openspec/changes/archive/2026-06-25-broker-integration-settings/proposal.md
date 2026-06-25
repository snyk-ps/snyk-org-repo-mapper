## Why

After Stage 2.2 (Broker Apply), orgs have Bitbucket Server integrations linked via Universal Broker, but SCM settings (PR checks, dependency upgrade, remediation PRs) remain at Snyk defaults. Operators need a repeatable stage to apply a standard integration settings profile across every org in the apply report—without editing each org in the UI.

## What Changes

- Add **Stage 2.3** CLI `snyk-broker-integration-settings`: reads `broker-org-apply-report.json`, processes each entry in `applied` with `org_id`, resolves the **bitbucket-server** integration id, and **PUT**s a predefined settings payload via Snyk **Integrations v1** (`/org/{orgId}/integrations/{integrationId}/settings`).
- Add `SnykRestClient.update_org_integration_settings`, defaults module, apply logic, and `broker-integration-settings-report.json` output.
- Register command in dispatcher and `pyproject.toml`; document README pipeline step.

**Out of scope:**

- Broker Plan / Apply behavior changes.
- Processing `skipped` or `failed` rows from the apply report.
- REST integrations API for settings (v1 required).
- Configurable `pullRequestAssignment` assignee (literal `"username"` in baked-in JSON).
- External settings file or credential/broker field updates.

## Capabilities

### New Capabilities

- `broker-integration-settings`: Stage 2.3 CLI, v1 settings PUT, report v1.

### Modified Capabilities

- _(none — README pipeline ordering only)_

## Impact

- **Code**: [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py), new [`src/snyk/integration_settings_defaults.py`](../../../src/snyk/integration_settings_defaults.py), [`src/snyk/broker_integration_settings.py`](../../../src/snyk/broker_integration_settings.py), [`src/commands/snyk_broker_integration_settings_cli.py`](../../../src/commands/snyk_broker_integration_settings_cli.py), [`src/commands/dispatch.py`](../../../src/commands/dispatch.py).
- **Tests**: new [`tests/test_broker_integration_settings.py`](../../../tests/test_broker_integration_settings.py), client PUT test.
- **Docs**: [`README.md`](../../../README.md).
