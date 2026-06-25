# three-stage-snyk-pipeline Specification (change delta)

## MODIFIED Requirements

### Requirement: Stage 3 emits snyk-import.json with resolved Snyk identifiers

The snyk-import command SHALL read the Stage 1 intermediate document, SHALL build import `targets` compatible with the Snyk import tool, and SHALL query the **Snyk REST API** to set **`orgId`** and **`integrationId`** on each target. For each target, when the Bitbucket `projectKey` appears in the Stage 1–derived `projectKey → apm_code` map with a non-empty `apm_code`, the command SHALL resolve the Snyk organization whose **name** equals that `apm_code` and SHALL select the **Bitbucket Server** integration for that org. When the `projectKey` has **no** entry in that map (including when every repository row under the project has null or empty `apm_code`), the command SHALL fail with a clear validation error **unless** the user supplies an optional **default Snyk organization identifier**; when supplied, the command SHALL verify that identifier refers to an organization in the configured Snyk group, SHALL assign that value as **`orgId`**, and SHALL assign the **Bitbucket Server** **`integrationId`** for that organization.

#### Scenario: Stage 3 performs no Bitbucket HTTP

- **GIVEN** a complete Stage 1 intermediate
- **WHEN** Stage 3 runs
- **THEN** it SHALL NOT contact Bitbucket over the network

#### Scenario: Optional orgs file cross-check

- **GIVEN** a `snyk-orgs.json` path is supplied
- **WHEN** Stage 3 validates required APM names against that file before calling Snyk
- **THEN** missing expected names SHALL fail with a validation exit code and clear stderr

#### Scenario: Dry run for Stage 3

- **WHEN** the user passes `--dry-run` to Stage 3
- **THEN** the command SHALL NOT overwrite the output import file
- **AND** SHALL print a reviewable plan of org and integration resolution

#### Scenario: Default organization id for projects without APM mapping

- **GIVEN** at least one import target whose `projectKey` is absent from the `projectKey → apm_code` map derived from Stage 1 rows
- **AND** the user passes a valid default Snyk organization identifier flag recognized by the implementation
- **WHEN** Stage 3 completes successfully
- **THEN** every such target SHALL have `orgId` set to that identifier
- **AND** SHALL have `integrationId` set to the Bitbucket Server integration for that org
- **AND** the identifier SHALL have been validated as belonging to the configured Snyk group

#### Scenario: Missing APM mapping without default org id

- **GIVEN** at least one import target whose `projectKey` is absent from the `projectKey → apm_code` map
- **AND** the user does not supply the default organization identifier option
- **WHEN** Stage 3 runs validation
- **THEN** the command SHALL fail with a clear error naming the affected project key
