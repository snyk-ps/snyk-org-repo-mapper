# snyk-post-import-cleanup Specification (change delta)

## MODIFIED Requirements

### Requirement: SnykRestClient project API support

The implementation SHALL add client methods for paginated org project listing, project deletion, and v1 project settings PUT, using the same HTTP retry behavior as existing client methods.

#### Scenario: List projects with type filter

- **WHEN** the stage requests dockerfile projects for an org
- **THEN** the client uses the v1 projects API with query parameter `types=dockerfile` (not `type`)
- **AND** pagination uses `from` and `to` as today

#### Scenario: Delete project via REST

- **WHEN** the stage deletes a project
- **THEN** the client issues a REST DELETE for that org and project id

#### Scenario: Update project settings via v1

- **WHEN** the stage sets recurring test frequency
- **THEN** the client issues a v1 PUT to `/org/{orgId}/project/{projectId}/settings`
