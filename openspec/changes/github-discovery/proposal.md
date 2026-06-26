## Why

Customers onboarding **GitHub.com** (or GitHub Enterprise) repositories into Snyk need the same Stage 1 **discovery** artifact as Bitbucket: a versioned JSON file that downstream stages consume for org planning and import. Today only Bitbucket Server (full crawl or spreadsheet-driven list) can produce that document. Operators with one or more GitHub orgs need a targeted crawl scoped by org login, without a spreadsheet ingress path.

## What Changes

- **Stage 1 (GitHub):** New `discover github` command that lists repositories under one or more GitHub orgs (from `--orgs`), reads AppSec YAML per repo, and writes **discovery JSON** with `source: github`.
- **CLI:** Required `--orgs "<org-1>,<org-2>"` (comma-separated org logins). Same file-output ergonomics as Bitbucket: `-o discovery.json`, resume/checkpoint, `--flush-interval`, `--max-repos`, empty-repos sidecar.
- **Configuration:** `GITHUB_TOKEN` (required), optional `GITHUB_FILE_PATH`, HTTP retry/flush env vars mirroring Bitbucket naming.
- **Output shape:** Same document wrapper and row semantics as README Discovery JSON: `version`, `source`, `rows`, optional `checkpoint`; rows include `apm_code`, `repository_path`, `repository_name`, `production_branch`, `bitbucket_project_name` (populated with GitHub org display name for schema stability), `is_empty`, `last_committer_name`, `last_committer_email`, `last_commit_date`.
- **Empty repos sidecar:** Default `github-empty-repos.json` when `-o` is set (override/disable same flags as Bitbucket).
- **README / CLI help** updated; console script `repo-mapper-discover-github`.

**Out of scope:**

- `discover spreadsheet` equivalent for GitHub.
- Stages 2–4 GitHub-specific behavior (Broker `github` connections, `snyk-import` GitHub integration resolution, post-import cleanup profiles). Discovery rows SHALL be consumable by existing Stage 2 (`snyk-orgs`) for APM extraction only; Stage 3+ GitHub support is a follow-on change.
- GitHub App / installation-token auth (PAT only for v1).
- User-owned repos outside the listed orgs.
- Renaming legacy row fields (`bitbucket_project_name`, checkpoint `project_key` / `repo_slug`).

## Capabilities

### New Capabilities

- `github-empty-repos`: empty-repository sidecar for GitHub discovery (`source: github`).

### Modified Capabilities

- `three-stage-snyk-pipeline`: Stage 1 adds GitHub org-scoped discovery ingress; `source` enum includes `github`.

## Impact

- **Code**: new `src/commands/github_cli.py`, `src/integrations/github/client.py`, GitHub mapping in `src/common/mapper.py` (or dedicated module), `src/config/` GitHub settings loader, `src/commands/dispatch.py`, `src/common/discovery_document.py` (`ALLOWED_SOURCES`), `src/commands/discovery_helpers.py` (parameterize `source` on flush), `src/common/empty_repos_document.py`, `pyproject.toml` console script.
- **Tests**: GitHub client (pagination, empty repo, YAML fetch, committer), CLI/dispatch, discovery document parse with `source: github`.
- **Docs**: README Stage 1 section, commands reference.
- **Dependencies**: None (stdlib HTTP + existing retry helper).
