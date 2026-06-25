# Delta spec: snyk-import-enrichment (superseded numbering)

## REMOVED Requirements

Superseded by **`three-stage-snyk-pipeline`**: user “Stage 1” is now **discovery** (Bitbucket/spreadsheet), not `snyk-prepare-orgs`; user “Stage 2/3” map to **`snyk-orgs`** and **`snyk-import`** commands. The following requirement sections are removed from the baseline when this change is archived.

### Requirement: Prepare Snyk orgs file and project context (stage 1)

### Requirement: Enrich import targets using orgs file and project context (stage 2)

### Requirement: Match Snyk organizations by APM code name

### Requirement: Cross-check orgs file against required APM codes

### Requirement: Bitbucket Server integration selection

### Requirement: Optional primary mapping fallback for stage 2

### Requirement: CLI routed through main dispatcher

### Requirement: Optional emission of project-context from mapper flush

## ADDED Requirements

### Requirement: Canonical Snyk onboarding specification

Normative requirements for discovery, org file generation, and import enrichment SHALL be defined in [`three-stage-snyk-pipeline`](../three-stage-snyk-pipeline/spec.md). This document SHALL remain a short pointer after archive so the rebuilt specification is never empty.

#### Scenario: Contributors locate the active journey

- **GIVEN** a reader consults `snyk-import-enrichment`
- **WHEN** they seek user-journey requirements for preparing Snyk org and import payloads
- **THEN** they SHALL use `three-stage-snyk-pipeline` as the source of truth

## Notes for archiver

After merge, either delete [`openspec/specs/snyk-import-enrichment/spec.md`](../../specs/snyk-import-enrichment/spec.md) if empty, or repoint its **Purpose** to state that behavioral requirements for Snyk file prep and enrichment now live under **`three-stage-snyk-pipeline`**, keeping `snyk-import-enrichment` only for historical reference until fully removed.
