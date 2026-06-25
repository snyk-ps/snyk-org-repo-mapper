## Context

Stage 4 ([`snyk-post-import-cleanup`](../../../src/commands/snyk_post_import_cleanup_cli.py)) already normalizes every org in `SNYK_GROUP_ID`: delete dockerfile projects, set recurring test frequency to `never`, and PUT Bitbucket Server integration settings ([`src/snyk/post_import_cleanup.py`](../../../src/snyk/post_import_cleanup.py)).

Customers standardize on **Python 3.12** (matching [`pyproject.toml`](../../../pyproject.toml)). Snyk org-level Python language settings (Org Settings → Languages → Python → Pip) default to older versions unless configured. The Snyk REST API exposes this via **LanguagesSettings**:

```
PATCH {rest_root}/orgs/{orgId}/settings/open_source/languages/python?version={api_version}
```

[`SnykRestClient`](../../../src/integrations/snyk/client.py) has v1 PUT helpers and REST GET/DELETE but **no REST PATCH** yet. Hard-coded defaults follow the pattern in [`integration_settings_defaults.py`](../../../src/snyk/integration_settings_defaults.py).

## Goals / Non-Goals

**Goals:**

- After integration settings (step 3), PATCH org Python language settings to **3.12** for every org in the group.
- Hard-code version and JSON:API payload in a defaults module; no env/CLI configuration.
- Record outcomes under `python_language_settings` in report **version 2**; include `python_version: "3.12"` metadata.
- `--dry-run`, partial-failure continue, non-zero exit if any `failed` entry (consistent with existing Stage 4 semantics).
- Unit test locks PATCH URL, headers, and body shape.

**Non-Goals:**

- Configurable Python version.
- Project-level `.snyk` overrides or filtering to pip/python projects only.
- Other language ecosystems.
- GET/compare before PATCH (always PATCH, idempotent overwrite).

## Decisions

### 1. Org-level REST PATCH (not project-level)

**Choice:** One PATCH per org via LanguagesSettings REST API.

**Rationale:** User confirmed org-level scope; matches Snyk UI "Languages → Python"; affects all pip/requirements.txt imports in the org without per-project iteration.

**Alternative:** Project-level v1 settings or `.snyk` files — rejected; more API calls and repo changes.

### 2. Hard-coded Python 3.12

**Choice:** Constants in new [`python_language_settings_defaults.py`](../../../src/snyk/python_language_settings_defaults.py):

- `PYTHON_LANGUAGE_VERSION = "3.12"`
- `PYTHON_LANGUAGE_SETTINGS_PROFILE_ID = "python-org-default-3.12"`
- `PYTHON_ORG_LANGUAGE_SETTINGS_PAYLOAD` — JSON:API envelope for PATCH body

**Rationale:** Same pattern as integration settings profile; aligns with repo Python minimum.

### 3. Client method: `patch_org_language_settings`

**Choice:** Add `SnykRestClient.patch_org_language_settings(org_id, language, payload)`:

- URL: `{rest_root}/orgs/{orgId}/settings/open_source/languages/{language}?version={api_version}`
- Method: PATCH
- Headers: `Authorization`, `Accept: application/vnd.api+json`, `Content-Type: application/vnd.api+json`
- Body: JSON-encoded payload dict
- Retries: `run_with_retries` with existing HTTP error handling

**Rationale:** First REST PATCH in client; mirrors PUT patterns from v1 helpers.

**Implementation note:** Exact `data.type` and `data.attributes` keys must be confirmed against [Snyk LanguagesSettings docs](https://docs.snyk.io/developer-tools/snyk-api/reference/languagessettings) during implementation. Lock shape in unit test.

### 4. Processing order: step 4 after integration settings

**Choice:** Per org: (1) delete dockerfile → (2) recurring test never → (3) integration settings PUT → (4) Python language PATCH.

**Rationale:** Keeps existing steps unchanged; language settings are org-level metadata applied last.

### 5. Report schema v2

**Choice:** Bump `POST_IMPORT_CLEANUP_REPORT_VERSION` to `2`. Add:

```json
{
  "version": 2,
  "python_version": "3.12",
  "python_language_settings": {
    "updated": [...],
    "skipped": [...],
    "failed": [...]
  }
}
```

Existing buckets unchanged. CLI `_report_has_failures` includes `python_language_settings.failed`.

**Alternative:** Keep report v1 and add fields — rejected; version bump makes schema evolution explicit.

### 6. Partial failure semantics unchanged

**Choice:** Continue to next org after PATCH failure; record under `python_language_settings.failed`.

**Rationale:** Consistent with dockerfile delete and integration settings behavior.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| JSON:API attribute names unclear from docs alone | Confirm during implementation; unit test asserts exact PATCH body |
| Token lacks org settings edit permission | README permission note; HTTP errors in `failed` |
| Existing projects retain old scan metadata until re-test | Document in README (Snyk behavior for org language changes) |
| Report consumers expect version 1 | Document v2 in README; version field signals schema |

## Migration Plan

1. Deploy after existing Stage 4 steps are stable.
2. First run with `--dry-run` to review intended PATCH operations per org.
3. Safe to re-run: PATCH is idempotent overwrite to 3.12.
4. Operators may need to re-test existing Python projects for scan results to reflect 3.12.

## Open Questions

- Confirm exact JSON:API `data.attributes` field name for Pip Python version during implementation (validate with GET or Snyk API reference before merging).
