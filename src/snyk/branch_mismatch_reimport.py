"""Delete and reimport Snyk targets with mismatched branch references."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from integrations.snyk.client import SnykRestClient
from snyk.enrichment import build_name_to_org_id
from snyk.outputs import APP_TYPE_PREFIX, batch_import_output_paths


REPORT_VERSION = 1

_REQUIRED_DIFF_KEYS = ("apm_code", "repository_name", "production_branch", "target_reference")


@dataclass(frozen=True)
class DiffEntry:
    """One row from a branch-mismatch diff artifact."""

    apm_code: str
    repository_name: str
    production_branch: str
    target_reference: str


@dataclass(frozen=True)
class BranchMismatchReimportOptions:
    """Runtime options for branch mismatch reimport."""

    dry_run: bool = False
    skip_import: bool = False
    repos_per_batch: int = 50
    limit: int | None = None
    snyk_api_import_cmd: str = "snyk-api-import"
    import_batch_dir: Path | None = None
    delay_ms: int = 0


def load_diff_entries(path: Path) -> list[DiffEntry]:
    """Load and validate diff.json entries."""
    raw_text = path.read_text(encoding="utf-8")
    parsed = json.loads(raw_text)
    if not isinstance(parsed, list):
        msg = "diff file must be a JSON array"
        raise ValueError(msg)
    out: list[DiffEntry] = []
    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            msg = f"diff[{i}] must be an object"
            raise ValueError(msg)
        values: dict[str, str] = {}
        for key in _REQUIRED_DIFF_KEYS:
            raw = item.get(key)
            if not isinstance(raw, str) or not raw.strip():
                msg = f"diff[{i}] missing or empty {key!r}"
                raise ValueError(msg)
            values[key] = raw.strip()
        out.append(DiffEntry(**values))
    return out


def _attr_str(attrs: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        raw = attrs.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def target_display_name(target: dict[str, Any]) -> str | None:
    attrs = target.get("attributes")
    if not isinstance(attrs, dict):
        return None
    return _attr_str(attrs, "display_name", "displayName", "name")


def target_branch_reference(target: dict[str, Any]) -> str | None:
    attrs = target.get("attributes")
    if not isinstance(attrs, dict):
        return None
    return _attr_str(attrs, "target_reference", "targetReference", "branch")


def target_integration_id(target: dict[str, Any]) -> str | None:
    rel = target.get("relationships")
    if not isinstance(rel, dict):
        return None
    integration = rel.get("integration")
    if not isinstance(integration, dict):
        return None
    data = integration.get("data")
    if not isinstance(data, dict):
        return None
    raw_id = data.get("id")
    if isinstance(raw_id, str) and raw_id.strip():
        return raw_id.strip()
    return None


def target_project_key_and_slug(target: dict[str, Any]) -> tuple[str, str] | None:
    attrs = target.get("attributes")
    if not isinstance(attrs, dict):
        return None
    project_key = _attr_str(attrs, "project_key", "projectKey")
    repo_slug = _attr_str(attrs, "repo_slug", "repoSlug")
    if project_key and repo_slug:
        return project_key, repo_slug
    remote = attrs.get("remote_repo_url") or attrs.get("remoteRepoUrl")
    if isinstance(remote, str) and "/" in remote:
        _, _, tail = remote.rstrip("/").rpartition("/")
        if tail and project_key:
            return project_key, tail
    return None


def import_target_name(repository_name: str) -> str:
    """Build ``target.name`` for snyk-api-import (Stage 3 ``BB/`` convention)."""
    if repository_name.startswith(APP_TYPE_PREFIX):
        base = repository_name[len(APP_TYPE_PREFIX) :]
    else:
        base = repository_name
    return f"{APP_TYPE_PREFIX}{base}"


def build_import_payload(
    *,
    org_id: str,
    integration_id: str,
    project_key: str,
    repo_slug: str,
    repository_name: str,
    production_branch: str,
) -> dict[str, Any]:
    return {
        "orgId": org_id,
        "integrationId": integration_id,
        "target": {
            "projectKey": project_key,
            "repoSlug": repo_slug,
            "name": import_target_name(repository_name),
            "branch": production_branch,
        },
    }


def _entry_record(entry: DiffEntry, **extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "apm_code": entry.apm_code,
        "repository_name": entry.repository_name,
        "production_branch": entry.production_branch,
        "target_reference": entry.target_reference,
    }
    base.update(extra)
    return base


def _find_matching_targets(
    targets: list[dict[str, Any]],
    entry: DiffEntry,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for target in targets:
        display = target_display_name(target)
        branch = target_branch_reference(target)
        if display == entry.repository_name and branch == entry.target_reference:
            matches.append(target)
    return matches


def _empty_report_buckets() -> dict[str, list[dict[str, Any]]]:
    return {
        "deleted": [],
        "reimported": [],
        "skipped": [],
        "not_found": [],
        "ambiguous": [],
        "failed": [],
    }


def run_snyk_api_import(
    cmd: str,
    batch_file: Path,
    *,
    token: str,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    parts = shlex.split(cmd)
    if not parts:
        msg = "snyk-api-import command must not be empty"
        raise ValueError(msg)
    env = dict(os.environ)
    env["SNYK_TOKEN"] = token
    return subprocess.run(
        [*parts, "import", f"--file={batch_file}"],
        env=env,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )


def check_snyk_api_import_available(cmd: str) -> None:
    parts = shlex.split(cmd)
    if not parts:
        msg = "snyk-api-import command must not be empty"
        raise ValueError(msg)
    executable = parts[0]
    if executable == "npx":
        if shutil.which("npx") is None:
            msg = "npx not found on PATH; install Node.js or set --snyk-api-import-cmd"
            raise ValueError(msg)
        return
    if shutil.which(executable) is None:
        msg = (
            f"{executable!r} not found on PATH; install snyk-api-import "
            "or set --snyk-api-import-cmd (e.g. 'npx snyk-api-import')"
        )
        raise ValueError(msg)


def run_branch_mismatch_reimport(
    client: SnykRestClient,
    entries: list[DiffEntry],
    options: BranchMismatchReimportOptions,
    *,
    import_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    """Process diff entries: match targets, delete, and reimport via snyk-api-import."""
    if options.repos_per_batch < 1:
        msg = "repos_per_batch must be >= 1"
        raise ValueError(msg)

    if not options.dry_run and not options.skip_import:
        check_snyk_api_import_available(options.snyk_api_import_cmd)

    if options.limit is not None:
        if options.limit < 1:
            msg = "limit must be >= 1 when set"
            raise ValueError(msg)
        entries = entries[: options.limit]

    name_to_org_id = build_name_to_org_id(client.iter_group_orgs())
    buckets = _empty_report_buckets()
    import_queue: list[tuple[DiffEntry, dict[str, Any]]] = []
    org_targets_cache: dict[str, list[dict[str, Any]]] = {}

    def targets_for_org(org_id: str, display_name: str) -> list[dict[str, Any]]:
        if org_id not in org_targets_cache:
            org_targets_cache[org_id] = client.iter_org_targets(
                org_id,
                display_name=display_name,
            )
        return org_targets_cache[org_id]

    for entry in entries:
        if entry.production_branch == entry.target_reference:
            buckets["skipped"].append(
                _entry_record(entry, reason="already_correct"),
            )
            continue

        org_id = name_to_org_id.get(entry.apm_code)
        if org_id is None:
            buckets["not_found"].append(
                _entry_record(entry, reason="org_not_found"),
            )
            continue

        try:
            candidates = targets_for_org(org_id, entry.repository_name)
            matches = _find_matching_targets(candidates, entry)
        except RuntimeError as exc:
            buckets["failed"].append(
                _entry_record(entry, org_id=org_id, error=str(exc)),
            )
            continue

        if not matches:
            buckets["not_found"].append(
                _entry_record(entry, org_id=org_id, reason="target_not_found"),
            )
            continue
        if len(matches) > 1:
            buckets["ambiguous"].append(
                _entry_record(
                    entry,
                    org_id=org_id,
                    target_ids=[m.get("id") for m in matches],
                ),
            )
            continue

        target = matches[0]
        target_id = target.get("id")
        if not isinstance(target_id, str) or not target_id.strip():
            buckets["failed"].append(
                _entry_record(entry, org_id=org_id, error="target missing id"),
            )
            continue
        target_id = target_id.strip()

        if options.dry_run:
            buckets["skipped"].append(
                _entry_record(
                    entry,
                    org_id=org_id,
                    target_id=target_id,
                    reason="dry_run",
                ),
            )
            continue

        try:
            detail = client.get_org_target(org_id, target_id)
            integration_id = target_integration_id(detail)
            repo_keys = target_project_key_and_slug(detail)
            if integration_id is None:
                msg = "target missing integration id"
                raise ValueError(msg)
            if repo_keys is None:
                msg = "target missing projectKey/repoSlug"
                raise ValueError(msg)
            project_key, repo_slug = repo_keys
            client.delete_org_target(org_id, target_id)
            payload = build_import_payload(
                org_id=org_id,
                integration_id=integration_id,
                project_key=project_key,
                repo_slug=repo_slug,
                repository_name=entry.repository_name,
                production_branch=entry.production_branch,
            )
            import_queue.append((entry, payload))
            buckets["deleted"].append(
                _entry_record(entry, org_id=org_id, target_id=target_id),
            )
        except (RuntimeError, ValueError) as exc:
            buckets["failed"].append(
                _entry_record(entry, org_id=org_id, target_id=target_id, error=str(exc)),
            )

        if options.delay_ms > 0:
            time.sleep(options.delay_ms / 1000.0)

    import_batches: list[dict[str, Any]] = []
    if import_queue and not options.skip_import:
        batch_dir = options.import_batch_dir or Path(".")
        batch_dir.mkdir(parents=True, exist_ok=True)
        payloads = [payload for _, payload in import_queue]
        batch_size = options.repos_per_batch
        num_batches = (len(payloads) + batch_size - 1) // batch_size
        paths = batch_import_output_paths(
            batch_dir / "branch-reimport-batch.json",
            num_batches,
        )
        runner = import_runner or run_snyk_api_import
        entry_by_key = {
            (
                p["orgId"],
                p["target"]["projectKey"],
                p["target"]["repoSlug"],
                p["target"]["branch"],
            ): entry
            for entry, p in import_queue
        }

        for batch_index, batch_path in enumerate(paths):
            start = batch_index * batch_size
            batch_payloads = payloads[start : start + batch_size]
            batch_doc = {"targets": batch_payloads}
            batch_path.write_text(json.dumps(batch_doc, indent=2), encoding="utf-8")
            batch_info: dict[str, Any] = {
                "file": str(batch_path),
                "target_count": len(batch_payloads),
            }
            if options.dry_run:
                batch_info["status"] = "skipped_dry_run"
                import_batches.append(batch_info)
                continue

            result = runner(
                options.snyk_api_import_cmd,
                batch_path,
                token=client.token,
                cwd=batch_dir,
            )
            batch_info["returncode"] = result.returncode
            if result.stdout:
                batch_info["stdout"] = result.stdout[-2000:]
            if result.stderr:
                batch_info["stderr"] = result.stderr[-2000:]
            import_batches.append(batch_info)

            if result.returncode == 0:
                for payload in batch_payloads:
                    tgt = payload["target"]
                    key = (
                        payload["orgId"],
                        tgt["projectKey"],
                        tgt["repoSlug"],
                        tgt["branch"],
                    )
                    entry = entry_by_key.get(key)
                    if entry is not None:
                        buckets["reimported"].append(
                            _entry_record(
                                entry,
                                org_id=payload["orgId"],
                                import_file=str(batch_path),
                            ),
                        )
            else:
                for payload in batch_payloads:
                    tgt = payload["target"]
                    key = (
                        payload["orgId"],
                        tgt["projectKey"],
                        tgt["repoSlug"],
                        tgt["branch"],
                    )
                    entry = entry_by_key.get(key)
                    if entry is not None:
                        buckets["failed"].append(
                            _entry_record(
                                entry,
                                org_id=payload["orgId"],
                                error=f"snyk-api-import exit {result.returncode}",
                                import_file=str(batch_path),
                            ),
                        )

    return {
        "version": REPORT_VERSION,
        "group_id": client.group_id,
        "dry_run": options.dry_run,
        "skip_import": options.skip_import,
        "entries_processed": len(entries),
        "import_batches": import_batches,
        **buckets,
    }
