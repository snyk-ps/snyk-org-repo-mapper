## Default branch resolution

Discovery resolves the branch ref for YAML fetch in order:

1. **`defaultBranch` on repository object** — from list/get repository payloads.
2. **`GET /rest/api/1.0/projects/{key}/repos/{slug}/default-branch`** — when (1) is absent.
3. **204 No Content** — Bitbucket reports an empty repository → `is_empty: true` without commits/YAML calls.
4. **404 Not Found** — configured default ref not created:
   - If `commits?limit=1` returns a commit → synthetic **`refs/heads/master`** for YAML fetch.
   - If no commits → `is_empty: true`.

This preserves legacy deliverable behavior for repos like `DNCLBATCH/9f_dncl_batch` where list/get omits `defaultBranch` but commits and AppSec YAML exist on `master`.

## Gates (mapper)

| Gate | Check | Outcome when false |
|------|-------|-------------------|
| 1 | `repository_has_default_branch(repo)` | Try default-branch API |
| 2 | default-branch API | 204 → empty; 404 → defer to commits |
| 3 | `repository_latest_commit` | No commits → empty |
| 4 | YAML fetch at resolved ref | Normal row assembly |
