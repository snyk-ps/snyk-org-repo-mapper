## Why

Long Bitbucket discovery runs against some networks or proxies can fail with `http.client.RemoteDisconnected` because the server closes the connection before an HTTP status line is received; today that exception is not classified as retriable, so the first drop aborts the whole run. Separately, Stage 3 import enrichment fails when every repository under a Bitbucket project has null `apm_code` in discovery (no YAML APM): those projects never enter `projectKey → apm_code`, and the enricher raises before org resolution. Operators need an optional escape hatch: a fixed Snyk organization UUID for those targets.

## What Changes

- Classify **`http.client.RemoteDisconnected`** as a **retriable** transport failure for Bitbucket Server and Snyk REST clients that use `urllib` with the existing exponential backoff and `max_attempts` settings; after retries are exhausted, Bitbucket paths SHALL surface the same style of wrapped network error as `URLError` / `TimeoutError` today.
- Add an optional Stage 3 CLI flag (e.g. **`--default-org-id`**) accepting a **Snyk organization id** (UUID). When a target’s `projectKey` is missing from the Stage 1–derived APM map, use that org id and resolve its Bitbucket Server integration id via the Snyk API; validate the id is a member of the configured group. When the flag is omitted, preserve the current hard error.

## Capabilities

### New Capabilities

- `http-transport-retries`: Normative behavior for retriable `urllib` transport failures (including `RemoteDisconnected`) on Bitbucket Server and Snyk REST HTTP clients, aligned with existing `run_with_retries` helpers.

### Modified Capabilities

- `three-stage-snyk-pipeline`: Stage 3 (`snyk-import`) SHALL support optional default Snyk organization id when `projectKey` has no APM-derived mapping; existing scenarios for dry-run, optional orgs file, and no Bitbucket HTTP remain valid with clarified resolution rules.

## Impact

- **Code**: [`src/integrations/bitbucket/client.py`](src/integrations/bitbucket/client.py), [`src/integrations/snyk/client.py`](src/integrations/snyk/client.py), [`src/snyk/enrichment.py`](src/snyk/enrichment.py), [`src/commands/snyk_import_cli.py`](src/commands/snyk_import_cli.py), tests under [`tests/`](tests/).
- **Dependencies**: None (stdlib `http.client.RemoteDisconnected`).
- **Docs / UX**: Stage 3 help text; optional note that `--snyk-orgs` validates names for required APM codes only (targets using the default org id do not add an APM name to that set).
