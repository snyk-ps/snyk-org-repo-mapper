## 1. Client fix

- [x] 1.1 In `SnykRestClient.iter_org_projects`, change the type-filter query parameter from `type=` to `types=` in [`src/integrations/snyk/client.py`](../../../src/integrations/snyk/client.py)

## 2. Tests

- [x] 2.1 Update `test_iter_org_projects_pagination_and_type_filter` expected URL to `types=dockerfile` in [`tests/test_snyk_client_post_import_cleanup.py`](../../../tests/test_snyk_client_post_import_cleanup.py)
- [x] 2.2 Run `pytest tests/test_snyk_client_post_import_cleanup.py tests/test_post_import_cleanup.py -q`

## 3. Verification

- [ ] 3.1 Confirm Stage 4 dry-run completes without HTTP 400 on Dockerfile listing (manual or customer re-test)
