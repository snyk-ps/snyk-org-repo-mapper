## Why

After Stage 3 (Snyk import), organizations in the target group may contain Dockerfile Snyk projects, projects with non-disabled recurring test schedules, and integration settings that drift from the standard profile applied in Stage 2.3. Operators need a repeatable **Stage 4** that normalizes the whole Snyk group post-import—without manual per-org cleanup in the UI.

Stage 2.3 only processes orgs listed under `applied` in the broker apply report. Stage 4 extends integration settings reconciliation to **every org in `SNYK_GROUP_ID`**, and adds destructive project cleanup plus recurring-test tuning across all projects.

## What Changes

- Add **Stage 4** CLI `snyk-post-import-cleanup`: iterates all orgs in `SNYK_GROUP_ID` and, per org:
  1. **Deletes** all Snyk projects with type `dockerfile`
  2. **Sets** recurring test frequency to `never` on every listed project
  3. **PUT**s the Stage 2.3 integration settings profile (`bitbucket-server-default-v1`) to the org's **bitbucket-server** integration (always PUT, same semantics as Stage 2.3)
- Add `SnykRestClient` methods for project list, delete, and project settings PUT (v1).
- Add orchestration module, versioned `post-import-cleanup-report.json`, `--dry-run`, dispatcher wiring, and README pipeline step.
- Extract a shared integration-settings apply helper reused by Stage 2.3 and Stage 4.

**Out of scope:**

- Limiting scope to import/onboarding orgs only (whole group is intentional).
- GET/compare before integration settings PUT (always PUT).
- Configurable settings profile or external settings file.
- Changes to Stages 1–3 or broker stages 2.1–2.2.

## Capabilities

### New Capabilities

- `snyk-post-import-cleanup`: Stage 4 CLI, group-wide dockerfile delete, recurring test `never`, integration settings PUT, report v1.

### Modified Capabilities

- `three-stage-snyk-pipeline`: Document Stage 4 as the post-import normalization step in the pipeline (README / help ordering).

## Impact

- **Code**: [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py), new [`src/snyk/post_import_cleanup.py`](../../../src/snyk/post_import_cleanup.py), new [`src/snyk/integration_settings_apply.py`](../../../src/snyk/integration_settings_apply.py) (refactor from [`src/snyk/broker_integration_settings.py`](../../../src/snyk/broker_integration_settings.py)), [`src/commands/snyk_post_import_cleanup_cli.py`](../../../src/commands/snyk_post_import_cleanup_cli.py), [`src/commands/dispatch.py`](../../../src/commands/dispatch.py).
- **Tests**: new [`tests/test_post_import_cleanup.py`](../../../tests/test_post_import_cleanup.py), client tests for project APIs.
- **Docs**: [`README.md`](../../../README.md).
- **APIs**: Snyk v1 project list/settings; REST project delete; v1 integration settings PUT (existing).
