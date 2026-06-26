# snyk-import-enrichment Specification

## Purpose

User-journey requirements for Bitbucket-to-Snyk discovery, org preparation, and import enrichment now live under **[`three-stage-snyk-pipeline`](../three-stage-snyk-pipeline/spec.md)**. This document is a pointer for historical context (legacy command names such as `snyk-prepare-orgs` / `snyk-enrich-import`).

## Requirements
### Requirement: Canonical Snyk onboarding specification

Normative requirements for discovery, org file generation, and import enrichment SHALL be defined in [`three-stage-snyk-pipeline`](../three-stage-snyk-pipeline/spec.md). This document SHALL remain a short pointer after archive so the rebuilt specification is never empty.

#### Scenario: Contributors locate the active journey

- **GIVEN** a reader consults `snyk-import-enrichment`
- **WHEN** they seek user-journey requirements for preparing Snyk org and import payloads
- **THEN** they SHALL use `three-stage-snyk-pipeline` as the source of truth

