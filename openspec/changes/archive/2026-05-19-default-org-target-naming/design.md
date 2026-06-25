## Context

Stage 3 builds `snyk-import.json` from discovery rows in [`src/snyk/outputs.py`](../../../src/snyk/outputs.py). Each target includes `target.projectKey`, `target.repoSlug`, and `target.name`. Org resolution lives in [`src/snyk/enrichment.py`](../../../src/snyk/enrichment.py); [`--default-org-id`](../../../src/commands/snyk_import_cli.py) assigns a fixed org UUID when the Bitbucket project has no `apm_code` in the Stage 1–derived `projectKey → apm_code` map.

Today `target.name` is always `repository_name` or repo slug. Multiple projects without APM can share one default org; identical display names then collide in Snyk import even though Bitbucket keys differ.

## Goals / Non-Goals

**Goals:**

- Set `target.name` to `{projectKey}/{repository_name}` (slash separator) for default-org targets only.
- Use repo slug when `repository_name` is absent (same fallback as today).
- Leave APM-mapped targets unchanged (`repository_name` or slug only).
- Apply naming when building the import document so written `snyk-import.json` matches enriched output.

**Non-Goals:**

- Changing `enrich_import_document` org/integration logic.
- Per-repo default org within an APM-mapped project.
- Migrating existing Snyk projects imported under old names.

## Decisions

### 1. Composite name format: `projectKey/repository_part`

**Choice:** `{projectKey}/{repository_name}` with `/` separator (e.g. `ACCP/my-service`).

**Rationale:** Mirrors `repository_path` (`projectKey/repoSlug`); user confirmed this format. `projectKey` and `repoSlug` on the target object stay unchanged for Bitbucket API identification.

**Alternatives considered:**

- `projectKey-repository_name` — rejected (less aligned with path conventions).
- Prefix only on collision — rejected (non-deterministic, harder to test).

### 2. Apply naming in `build_snyk_import_document`, not enrichment

**Choice:** Add optional `project_apm` and `default_org_id` to `build_snyk_import_document`; introduce `default_org_target_name(project_key, repository_name, repo_slug)`.

**Rationale:** Naming is a property of the import payload, not API resolution. `enrich_import_document` already copies `target` unchanged for default-org rows.

**Condition:** Apply composite name when `default_org_id` is non-empty **and** `project_key not in project_apm`.

### 3. CLI wires context into build

**Choice:** After `project_apm_map_from_rows(rows)` and parsing `--default-org-id`, pass both into `build_snyk_import_document`.

**Rationale:** Single place produces correct names before enrichment and file write.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Snyk import rejects `/` in `target.name` | Document format; add validation or alternate delimiter in follow-up if integration fails |
| Operators expect short names in default org | README documents composite rule; re-import may be needed for existing projects |
| Callers of `build_snyk_import_document` without new kwargs | Optional parameters default to `None`; behavior unchanged when omitted |

## Migration Plan

1. Ship code + README update.
2. New runs with `--default-org-id` emit prefixed names automatically.
3. Existing imports under unprefixed names: operational re-import or manual rename in Snyk (out of tool scope).

## Open Questions

- None for v1. Confirm `/` is accepted by Snyk API Import Tool in customer environment if issues arise.
