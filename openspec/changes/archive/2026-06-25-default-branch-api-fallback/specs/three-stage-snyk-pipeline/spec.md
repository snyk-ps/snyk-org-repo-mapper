# three-stage-snyk-pipeline Specification (change delta)

## MODIFIED Requirements

### Requirement: Stage 1 discovery produces a versioned intermediate document

The discovery command SHALL support **two** ingress modes—Bitbucket Server and spreadsheet—and SHALL write a single **versioned** JSON document containing `rows` equivalent to the primary mapping semantics needed for Snyk Stages 2 and 3, including `apm_code`, `repository_path`, `repository_name`, `production_branch`, and `bitbucket_project_name` where applicable. For **Bitbucket** discovery (full crawl or spreadsheet-driven targeted list), each row SHALL include a boolean **`is_empty`**. A repository SHALL be marked `is_empty: true` when it has zero commits (`GET .../commits?limit=1` returns none) **or** when `GET .../default-branch` returns **204 No Content** (empty repository). When the repository list/GET payload omits `defaultBranch`, the implementation SHALL call `GET .../repos/{slug}/default-branch` to resolve the configured default. When that endpoint returns **404** (configured branch ref not created) but commits exist, the implementation SHALL fall back to synthetic **`refs/heads/master`** for AppSec YAML fetch. When synthesizing a default branch ref from incomplete API metadata, the implementation SHALL use **`master`** (not `main`) as the fallback display/ref. For non-empty rows, the row SHALL include **`last_committer_name`** and **`last_committer_email`** from the latest commit when commits exist.

#### Scenario: Repository list omits defaultBranch but default-branch API succeeds

- **GIVEN** a Bitbucket repository whose list/GET payload has no `defaultBranch` field
- **AND** `GET .../default-branch` returns a branch object
- **WHEN** Stage 1 discovery processes that repository
- **THEN** the row SHALL NOT be marked empty solely because `defaultBranch` was omitted on the repository object
- **AND** AppSec YAML SHALL be fetched at the resolved branch ref when commits exist

#### Scenario: Default-branch API 404 with commits uses master fallback

- **GIVEN** a Bitbucket repository with commits
- **AND** `defaultBranch` is absent on the repository object
- **AND** `GET .../default-branch` returns 404
- **WHEN** Stage 1 discovery processes that repository
- **THEN** the row SHALL have `is_empty` set to `false`
- **AND** YAML fetch SHALL use synthetic `refs/heads/master`

#### Scenario: Default-branch API 204 marks empty repository

- **GIVEN** a Bitbucket repository where `GET .../default-branch` returns 204
- **WHEN** Stage 1 discovery processes that repository
- **THEN** the row SHALL have `is_empty` set to `true`
- **AND** the implementation SHALL NOT fetch AppSec YAML

#### Scenario: Repository without default branch marked empty

- **REMOVED** — replaced by scenarios above; repos are no longer marked empty solely because list/GET omitted `defaultBranch`.
