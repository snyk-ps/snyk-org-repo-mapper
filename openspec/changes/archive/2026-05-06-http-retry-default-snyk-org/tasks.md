## 1. HTTP transport retries

- [x] 1.1 Extend Bitbucket client `_is_retriable_request_failure` (and outer network-error handling after `run_with_retries`) to treat `http.client.RemoteDisconnected` like other retriable transport failures per spec.
- [x] 1.2 Extend Snyk client `_is_retriable_request_failure` consistently for `RemoteDisconnected`.
- [x] 1.3 Add unit tests (predicate and/or mocked `urlopen` retry) proving `RemoteDisconnected` is retried until success or exhaustion.

## 2. Stage 3 default Snyk organization id

- [x] 2.1 Add `--default-org-id` (or equivalent) to Stage 3 argument parser with help text describing UUID / org id semantics.
- [x] 2.2 Thread optional default org id through `required_apm_codes_for_import`, `enrich_import_document`, and `summarize_enrichment_plan`; ensure `integration_cache_for_orgs` receives the default id when any target needs it.
- [x] 2.3 After `iter_group_orgs()`, validate the default org id is present in the group; fail with clear stderr if not.
- [x] 2.4 Add tests for enrichment and/or CLI covering null-APM project + default org success and missing-default failure paths.

## 3. Verification

- [x] 3.1 Run the project test suite and fix any regressions.
