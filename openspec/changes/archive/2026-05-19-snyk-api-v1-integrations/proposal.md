# Proposal: Snyk Stage 3 — V1 integrations default + `SNYK_API`

## Problem

- Stage 3 lists group organizations via the Snyk REST API, which remains appropriate.
- Listing org **integrations** via REST is not generally available for all customers; operators need the stable v1 integrations endpoint for Stage 3.
- `SNYK_API_BASE` requires callers to pass a path that includes `/rest`, which is easy to misconfigure when different API surfaces use `/rest` vs `/v1`.

## Proposal

1. Introduce **`SNYK_API`**: API origin only (e.g. `https://api.snyk.io`). Internally derive **`{SNYK_API}/rest`** for REST calls and **`{SNYK_API}/v1`** for v1 calls.
2. Default **integrations** listing to **v1** (`GET /v1/org/{orgId}/integrations`).
3. Add **`SNYK_INTEGRATIONS_API`**: `v1` (default) or `rest` to opt into REST integrations when available.
4. Deprecate **`SNYK_API_BASE`**: if `SNYK_API` is unset, derive origin by stripping a trailing `/rest` from `SNYK_API_BASE` for backward compatibility.

## Non-goals

- CLI UX beyond documentation (env table and migration notes).
