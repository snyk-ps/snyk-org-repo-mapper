## Why

Operators need ownership and contact hints during discovery (for example routing repos without APM or broker hygiene) without re-querying Bitbucket in later stages. The commits API is already called once per repository for `is_empty`; the same response can supply committer identity at no extra HTTP cost.

## What Changes

- **Stage 1 (Bitbucket only):** From `GET .../commits?limit=1`, set flat **`last_committer_name`** and **`last_committer_email`** on each discovery row (prefer API `committer`, fall back to `author`); both **`null`** when `is_empty: true`.
- **README:** Document the new row fields and discovery JSON example.
- **Stages 2–3:** No logic changes; committer fields are pass-through metadata only.

**Out of scope:**

- Spreadsheet column mapping for committer.
- `last_commit_id`, timestamps, or an author-vs-committer CLI toggle.
- Filtering or routing in Stages 2–3 based on committer.
- Default-branch-scoped commits (same repo-wide `commits?limit=1` semantics as `is_empty` today).

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `three-stage-snyk-pipeline`: Stage 1 Bitbucket rows include `last_committer_name` and `last_committer_email`; Stages 2–3 do not consume them.

## Impact

- **Code**: [`src/integrations/bitbucket/client.py`](../../../src/integrations/bitbucket/client.py), [`src/common/mapper.py`](../../../src/common/mapper.py).
- **Tests**: Bitbucket client commits, mapper.
- **Docs**: [`README.md`](../../../README.md).
- **Dependencies**: None (existing Bitbucket REST client patterns).
