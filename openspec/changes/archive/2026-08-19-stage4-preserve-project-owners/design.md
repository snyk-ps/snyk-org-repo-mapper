## Context

Stage 4 ([`snyk-post-import-cleanup`](../../../src/commands/snyk_post_import_cleanup_cli.py)) lists projects via REST ([`normalize_rest_project`](../../../src/integrations/snyk/client.py) already exposes `owner_id` from `relationships.owner`). Recurring-test updates call `update_project_settings`, which always embeds `SNYK_USER_ID` in `relationships.owner` ([`_build_project_patch_body`](../../../src/integrations/snyk/client.py)).

The archived change `2026-08-12-clear-project-owner-script` added [`scripts/clear_project_owners.py`](../../../scripts/clear_project_owners.py) and [`run_clear_project_owners`](../../../src/snyk/clear_project_owners.py), which clear **every** owner in scope. This change is **selective**: remediation runs only for projects Stage 4 PATCHed, and the action depends on **pre-PATCH** `owner_id`.

## Goals / Non-Goals

**Goals:**

- Preserve ownership that existed before Stage 4.
- Revert unintended `SNYK_USER_ID` assignment on previously unassigned projects.
- Record remediation outcomes in the Stage 4 report.
- Document clearly that `SNYK_USER_ID` is a PATCH technical requirement, not the desired end-state owner.

**Non-Goals:**

- Avoid PATCH entirely for projects with existing owners (PATCH is still required to set frequency).
- Bulk clear all owners (the standalone script remains for that operational case).
- Change Stage 4 org scope or add `--orgs` filtering.

## Decisions

### 1. Pre-PATCH snapshot drives remediation

**Choice:** Read `owner_id` from the same REST list iteration used for frequency PATCH; store `prior_owner_id: str | None` per project.

**Rationale:** REST list already normalized; no extra GET per project.

**Alternatives considered:** Re-fetch project after PATCH to detect current owner — rejected (extra API call, still wouldn't recover prior owner without snapshot).

### 2. Remediation immediately after successful frequency PATCH

| `prior_owner_id` | Action after PATCH |
|------------------|-------------------|
| `None` | `clear_project_owner` (v1 PUT `{"owner": null}`) |
| UUID ≠ `user_id` | `set_project_owner(org, project, prior_owner_id)` (new v1 PUT wrapper) |
| UUID = `user_id` | skip (`reason: already_transition_user`) |

**Rationale:** PATCH always sets owner to `SNYK_USER_ID`; remediation restores intended state.

**Alternatives considered:** Skip PATCH for projects with existing owners — rejected (frequency would not be updated).

### 3. No remediation when frequency PATCH fails or is skipped

**Choice:** Record under `project_owner_remediation.skipped` with reason `frequency_patch_failed` or inherit dry-run / `project_not_found` skip paths from the frequency step.

**Rationale:** Avoid owner PUT when settings were not successfully updated.

### 4. Failure handling

**Choice:** Remediation failure is recorded under `project_owner_remediation.failed` but does **not** roll back a successful frequency PATCH. CLI non-zero exit if any remediation failed (consistent with other Stage 4 buckets).

### 5. Report version 3

Add top-level `transition_user_id` and:

```json
"project_owner_remediation": {
  "cleared": [...],
  "restored": [...],
  "skipped": [...],
  "failed": [...]
}
```

Skip reasons: `dry_run`, `already_transition_user`, `frequency_patch_failed`, `frequency_patch_skipped`.

### 6. Reuse script library patterns, not the script itself

**Choice:** Share skip/report entry shape with [`run_clear_project_owners`](../../../src/snyk/clear_project_owners.py) where practical; implement remediation inline in [`post_import_cleanup.py`](../../../src/snyk/post_import_cleanup.py) or a small helper module.

**Rationale:** Stage 4 has different per-project logic (clear vs restore vs skip); the script's "clear all" semantics do not apply.

## Risks / Trade-offs

- **[Extra v1 PUT per project]** → Doubles write load on recurring-test step for unassigned/other-owner projects. Acceptable for post-import batch; same HTTP retry behavior as existing client.
- **[Owner not returned in REST list]** → Treat as unassigned; may clear when operator expected an owner. Document that remediation assumes REST `relationships.owner` is authoritative at list time.
- **[Race if owner changes during run]** → Same as any batch job; out of scope.

## Migration Plan

1. Ship Stage 4 with built-in remediation; bump report to version 3.
2. Update README: `SNYK_USER_ID` is transition UUID; owners preserved automatically.
3. Retain `clear_project_owners.py` for legacy Stage 4 runs and bulk all-owner clear; update docs to say it is not required after this change for normal operation.
4. No rollback of frequency PATCH on remediation failure — operators re-run Stage 4 or use the script for manual fix.

## Open Questions

_None._
