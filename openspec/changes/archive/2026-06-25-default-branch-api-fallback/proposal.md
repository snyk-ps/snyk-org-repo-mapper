## Why

Bitbucket repository list/GET payloads often omit `defaultBranch` even when a default is configured. Discovery incorrectly marked such repos `is_empty: true` and skipped YAML/committer fetch (regression vs prior deliverables, e.g. `DNCLBATCH/9f_dncl_batch`).

## What Changes

- Call `GET .../repos/{slug}/default-branch` when `defaultBranch` is missing on the repository object.
- **204** → empty repository (`is_empty: true`).
- **404** + commits exist → synthetic `master` ref for YAML fetch (legacy behavior).
- **404** + no commits → `is_empty: true`.
- Document resolution matrix in tests and README.

**Out of scope:** Deprecated `/branches/default` endpoint; changing YAML key parsing.

## Capabilities

### Modified Capabilities

- `three-stage-snyk-pipeline`: default-branch resolution and empty-repo gates.

## Impact

- **Code**: [`src/integrations/bitbucket/client.py`](../../../src/integrations/bitbucket/client.py), [`src/common/mapper.py`](../../../src/common/mapper.py).
- **Tests / docs**: Bitbucket helper and mapper tests; README.
