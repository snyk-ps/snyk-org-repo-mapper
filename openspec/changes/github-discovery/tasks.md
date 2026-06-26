## 1. GitHub integration

- [x] 1.1 Add `src/integrations/github/client.py` — org repo pagination, contents fetch, latest commit, org metadata
- [x] 1.2 Add GitHub settings loader (`GITHUB_TOKEN`, `GITHUB_API_URL`, `GITHUB_FILE_PATH`, retry/flush env vars)
- [x] 1.3 Add GitHub mapping iterator (empty repo rules, YAML merge, committer/date fields)

## 2. CLI and discovery document

- [x] 2.1 Add `src/commands/github_cli.py` with required `--orgs`, mirror Bitbucket file-output flags
- [x] 2.2 Wire `discover github` in `dispatch.py`; add `repo-mapper-discover-github` entry point
- [x] 2.3 Extend `discovery_document.ALLOWED_SOURCES` with `github`
- [x] 2.4 Parameterize `discovery_helpers.flush_discovery` and empty-repos writer by `source`
- [x] 2.5 Default empty-repos filename `github-empty-repos.json` for GitHub runs

## 3. Tests and docs

- [x] 3.1 Unit tests: GitHub client (mock HTTP), mapper, CLI validation (`--orgs` required)
- [x] 3.2 Update README — Stage 1 GitHub section, env table, example command
- [x] 3.3 `openspec validate github-discovery`
