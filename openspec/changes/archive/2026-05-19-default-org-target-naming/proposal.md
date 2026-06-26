## Why

Stage 3 (`snyk-import`) can route repositories from Bitbucket projects without YAML APM into a single **default Snyk organization** via `--default-org-id`. Today each import target’s `name` is only the repository display name (or slug). Repositories in **different** Bitbucket projects that share the same name (e.g. `api` in `ACCP` and `OTHER`) collide when imported into one org, even though `projectKey` and `repoSlug` differ. Operators need distinct, predictable `target.name` values so every default-org import remains addressable in Snyk.

## What Changes

- When building `snyk-import.json` targets that will use the default organization (project absent from `projectKey → apm_code` and `--default-org-id` supplied), set `target.name` to **`{projectKey}/{repository_name}`**, using repository slug when display name is absent.
- Targets resolved via APM mapping keep existing naming (`repository_name` or slug only; no project prefix).
- Document the naming rule in README Stage 3.
- Add unit and CLI tests for collision avoidance and unchanged APM behavior.

**Out of scope:**

- Per-repo default org within a project that has a project-level APM code.
- Renaming or migrating projects already imported under the old `target.name`.
- Sanitizing characters in names unless Snyk import rejects `/` (follow-up if needed).

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- `three-stage-snyk-pipeline`: Stage 3 import target naming for default-organization targets; new scenarios for composite names, APM unchanged behavior, and slug fallback.

## Impact

- **Code**: [`src/snyk/outputs.py`](../../../src/snyk/outputs.py) (`default_org_target_name`, `build_snyk_import_document`), [`src/commands/snyk_import_cli.py`](../../../src/commands/snyk_import_cli.py).
- **Tests**: [`tests/test_snyk_outputs.py`](../../../tests/test_snyk_outputs.py), [`tests/test_snyk_import_cli.py`](../../../tests/test_snyk_import_cli.py).
- **Docs**: [`README.md`](../../../README.md) Stage 3.
- **Dependencies**: None.
