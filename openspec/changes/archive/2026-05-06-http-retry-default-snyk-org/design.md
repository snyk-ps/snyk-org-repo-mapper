## Context

The repo uses stdlib `urllib.request.urlopen` inside [`run_with_retries`](src/integrations/http_retry.py). Retriability is decided by duplicated `_is_retriable_request_failure` helpers in the Bitbucket and Snyk clients. `http.client.RemoteDisconnected` is not a `urllib.error.URLError`; it inherits from `ConnectionResetError` and currently fails the predicate, so no retries run.

Stage 3 builds `project_apm` via [`project_apm_map_from_rows`](src/snyk/project_context.py), which skips null/empty `apm_code`. [`required_apm_codes_for_import`](src/snyk/enrichment.py) then requires every import target’s `projectKey` to exist in that map.

## Goals / Non-Goals

**Goals:**

- Retry `RemoteDisconnected` (and optionally document whether broader `ConnectionError` is in scope) with existing backoff parameters on both HTTP clients.
- After Bitbucket retries are exhausted, wrap `RemoteDisconnected` in the same user-facing `RuntimeError` pattern as other network errors on Bitbucket paths.
- Allow Stage 3 to proceed for targets whose `projectKey` is absent from `project_apm` when `--default-org-id` is supplied and validated against `iter_group_orgs()`.
- Include the default org id in the set passed to `integration_cache_for_orgs` so `integrationId` is populated.

**Non-Goals:**

- Changing spreadsheet Stage 1 semantics or project-context JSON parser (`parse_project_context_document`) for this change.
- Adding a default **APM name** string (org name) instead of org UUID; the operator explicitly asked for org id.
- New third-party HTTP libraries.

## Decisions

1. **Retriable type**: Start with `http.client.RemoteDisconnected` explicitly in `_is_retriable_request_failure` (and Bitbucket outer `except` tuple). Optionally extend to a small documented set (e.g. `ConnectionResetError`, `BrokenPipeError`) in the same predicate if the team wants fewer follow-up tickets; the spec can mandate only `RemoteDisconnected` for a minimal first ship.

2. **Predicate location**: Keep duplicate predicates in Bitbucket and Snyk clients for the smallest diff, or extract one shared function under `integrations/` in a follow-up refactor (non-blocking).

3. **Default org resolution**: Pass `default_org_id: str | None` through `required_apm_codes_for_import`, `enrich_import_document`, and `summarize_enrichment_plan`. Missing map + flag set → use `name_to_org_id` is irrelevant; use the provided id directly and read `org_to_integration_id[default_org_id]`.

4. **`--snyk-orgs`**: Do not require a synthetic org **name** for default-org targets; document that the optional file still validates only the APM-derived name set.

## Risks / Trade-offs

- **[Risk]** Retrying on very persistent server faults delays failure. **→ Mitigation:** Same `max_attempts` cap as today; operators can tune env/settings if present.

- **[Risk]** Wrong `--default-org-id` sends imports to the wrong Snyk org. **→ Mitigation:** Validate membership in listed group orgs before writing output; clear stderr message.

- **[Trade-off]** Projects with mixed null and non-null APM across repos already resolve to the single non-null code per existing rules; default org applies only when the project key is **absent** from the map.

## Migration Plan

No data migration. After deploy, users may add `--default-org-id` to Stage 3 invocations where discovery contains null APM projects. Rollback is revert binary / package version.

## Open Questions

- Whether to broaden retriable exceptions beyond `RemoteDisconnected` in v1 (see Decisions).
