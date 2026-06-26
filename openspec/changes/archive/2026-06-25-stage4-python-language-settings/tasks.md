## 1. Defaults module

- [x] 1.1 Add [`src/snyk/python_language_settings_defaults.py`](../../../src/snyk/python_language_settings_defaults.py) with `PYTHON_LANGUAGE_VERSION = "3.12"`, `PYTHON_LANGUAGE_SETTINGS_PROFILE_ID`, and `PYTHON_ORG_LANGUAGE_SETTINGS_PAYLOAD` (JSON:API PATCH body)
- [x] 1.2 Confirm JSON:API attribute keys against [Snyk LanguagesSettings docs](https://docs.snyk.io/developer-tools/snyk-api/reference/languagessettings) and lock shape in unit test

## 2. Client extension

- [x] 2.1 Add `SnykRestClient.patch_org_language_settings(org_id, language, payload)` in [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py) (REST PATCH, JSON:API headers, `version` query param, retries)
- [x] 2.2 Unit test PATCH URL, headers, and body in new or extended client test file (e.g. [`tests/test_snyk_client_python_language_settings.py`](../../../tests/test_snyk_client_python_language_settings.py))

## 3. Stage 4 orchestration

- [x] 3.1 Add step 4 to [`src/snyk/post_import_cleanup.py`](../../../src/snyk/post_import_cleanup.py): PATCH Python 3.12 per org after integration settings; record `python_language_settings` buckets
- [x] 3.2 Bump `POST_IMPORT_CLEANUP_REPORT_VERSION` to `2`; add `python_version` metadata to report dict
- [x] 3.3 Update [`src/commands/snyk_post_import_cleanup_cli.py`](../../../src/commands/snyk_post_import_cleanup_cli.py): include `python_language_settings.failed` in failure check; update CLI description

## 4. Tests

- [x] 4.1 Extend [`tests/test_post_import_cleanup.py`](../../../tests/test_post_import_cleanup.py): dry-run skips PATCH; live run records `python_language_settings.updated`; failure path; report `version: 2`

## 5. Docs and verification

- [x] 5.1 Update [`README.md`](../../../README.md) Stage 4 section: Python 3.12 org language normalization, re-test note for existing projects
- [x] 5.2 Run pytest for new and related tests (`test_post_import_cleanup`, client PATCH test)
