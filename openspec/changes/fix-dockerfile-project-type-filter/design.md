## Context

Stage 4 lists Dockerfile projects via `SnykRestClient.iter_org_projects(org_id, project_type="dockerfile")` before issuing REST DELETE calls. The original Stage 4 design assumed the v1 filter query parameter was `type`; [Snyk API documentation](https://docs.snyk.io/snyk-api/api-endpoints-index-and-tips) documents it as **`types`** (plural).

Current broken request:

```
GET {v1_root}/org/{orgId}/projects?from=1&to=100&type=dockerfile
```

Correct request:

```
GET {v1_root}/org/{orgId}/projects?from=1&to=100&types=dockerfile
```

Other Stage 4 APIs were reviewed and are correct:

| Operation | Endpoint | Status |
|-----------|----------|--------|
| List all projects | `GET /v1/org/{orgId}/projects?from=&to=` | OK |
| Delete project | `DELETE /rest/orgs/{orgId}/projects/{projectId}?version=` | OK |
| Update settings | `PUT /v1/org/{orgId}/project/{projectId}/settings` | OK |

## Goals / Non-Goals

**Goals:**

- Unblock Stage 4 Dockerfile listing with the documented Snyk v1 `types` query parameter.
- Keep `project_type` as the Python method argument name (internal API unchanged).
- Update tests to lock in the correct URL shape.

**Non-Goals:**

- Refactoring Stage 4 to one project list per org.
- Switching Dockerfile filtering to client-side-only (works but adds API volume).
- Changing REST delete or v1 settings payloads.

## Decisions

### 1. Fix query parameter name only

**Choice:** Change `&type=` to `&types=` in `iter_org_projects`.

**Rationale:** Minimal, matches Snyk v1 API; restores intended Stage 4 behavior without API surface changes.

**Alternative:** List all projects and filter `project["type"] == "dockerfile"` client-side — rejected for this change (more API traffic; server filter is documented and preferred).

### 2. No change to `delete_org_project` or `update_project_settings`

**Choice:** Leave REST DELETE and v1 settings PUT unchanged.

**Rationale:** Customer failure occurs before delete; audit confirms URLs and payloads match Snyk docs.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Snyk changes v1 `types` semantics | Requirement and test assert exact query string; monitor API errors in `dockerfile_projects.failed` |
| Regressions in unfiltered list | Unfiltered path unchanged; existing tests cover pagination |
