# github-empty-repos Specification (change delta)

## ADDED Requirements

### Requirement: Empty-repos document version 1 for GitHub

The GitHub discovery command SHALL be able to write a JSON document with `version` 1, `source` `github`, and a `repositories` array. Each entry SHALL include `repository_path`, `project_key` (org login), `repo_slug` (repo name), `repository_name`, and `bitbucket_project_name` (org display name from the discovery row).

#### Scenario: Document lists only empty repositories

- **GIVEN** discovery rows where some have `is_empty` true and some false
- **WHEN** the empty-repos document is built for GitHub discovery
- **THEN** `repositories` SHALL contain only rows with `is_empty` true
- **AND** entries SHALL be sorted by `repository_path`

#### Scenario: No empty repositories

- **GIVEN** no discovery rows have `is_empty` true
- **WHEN** the empty-repos document is written
- **THEN** `repositories` SHALL be an empty array
