## Why

After Stage 3 import, Snyk orgs in the target group often retain default Python language settings (typically 3.7 or org-specific drift) that do not match the customer's Python 3.12 estate. Incorrect Python version settings cause pip/requirements.txt scans to omit incompatible dependencies or produce inaccurate results. Stage 4 already normalizes dockerfile projects, recurring tests, and integration settings group-wide; operators need the same repeatable treatment for **org-level Python language settings** without editing each org in the Snyk UI.

## What Changes

- Extend **Stage 4** (`snyk-post-import-cleanup`) with a fourth step per org: **PATCH** org Python language settings to hard-coded **3.12** via the Snyk REST LanguagesSettings API.
- Add `SnykRestClient.patch_org_language_settings` (REST PATCH, JSON:API).
- Add hard-coded Python language defaults module (version `3.12`, profile id, JSON:API payload).
- Bump `post-import-cleanup-report.json` to **version 2** with `python_version` metadata and `python_language_settings` outcome buckets (`updated`, `skipped`, `failed`).
- Update CLI failure detection, help text, and README Stage 4 documentation.

**Out of scope:**

- Configurable Python version via env var or CLI flag.
- Project-level `.snyk` file overrides or per-project language settings.
- Other language ecosystems (npm, maven, etc.).
- GET/compare before PATCH (always PATCH, idempotent overwrite — same as integration settings).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `snyk-post-import-cleanup`: Add org-level Python 3.12 language settings step, REST PATCH client support, and report schema v2.

## Impact

- **Code**: [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py), new [`src/snyk/python_language_settings_defaults.py`](../../../src/snyk/python_language_settings_defaults.py), [`src/snyk/post_import_cleanup.py`](../../../src/snyk/post_import_cleanup.py), [`src/commands/snyk_post_import_cleanup_cli.py`](../../../src/commands/snyk_post_import_cleanup_cli.py).
- **Tests**: extend [`tests/test_post_import_cleanup.py`](../../../tests/test_post_import_cleanup.py); new or extended client test for REST PATCH.
- **Docs**: [`README.md`](../../../README.md) Stage 4 section.
- **APIs**: Snyk REST `PATCH /orgs/{orgId}/settings/open_source/languages/python` (new); existing Stage 4 APIs unchanged.
