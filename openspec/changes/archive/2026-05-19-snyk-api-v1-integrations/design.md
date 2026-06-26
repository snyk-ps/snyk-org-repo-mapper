## Configuration

| Variable | Role |
|----------|------|
| `SNYK_API` | Canonical API origin (scheme + host [+ port]). Default `https://api.snyk.io`. |
| `SNYK_API_BASE` | Deprecated. Used only when `SNYK_API` is empty; trailing `/rest` is stripped to obtain the origin. |
| `SNYK_INTEGRATIONS_API` | `v1` (default) or `rest` — which API lists integrations per org. |
| `SNYK_API_VERSION` | Unchanged — REST `version` query param for group org listing. |

## URL layout

- REST root: `{origin}/rest`
- V1 root: `{origin}/v1`

## HTTP behavior

- **Group orgs:** existing JSON:API GET with `Accept: application/vnd.api+json`, pagination via `links.next`.
- **Integrations (v1):** GET `{origin}/v1/org/{orgId}/integrations` with `Accept: application/json`; normalize body to a list of integration dicts (array root or common wrapper keys).
- **Integrations (rest):** existing REST path and pagination when `SNYK_INTEGRATIONS_API=rest`.

## Integration type resolution

Extend type slug extraction for v1 flat fields (`integrationType`, etc.) while preserving JSON:API `attributes` behavior.
