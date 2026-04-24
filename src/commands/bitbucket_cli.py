"""Command-line interface for the Bitbucket org repo mapper."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from common.mapper import iter_mapping
from common.output_state import (
    atomic_write_json,
    build_primary_document,
    completed_keys_from_rows,
    load_primary_output_file,
    row_repo_key,
)
from config import load_dotenv_file, load_settings
from integrations.bitbucket import BitbucketServerClient
from snyk.outputs import (
    apm_codes_from_rows,
    build_snyk_import_document,
    build_snyk_orgs_document,
)


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "List all Bitbucket Server repositories and map AppSec YAML to JSON."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Write primary mapping JSON to this file (resumable wrapper format). "
            "If omitted, print a JSON array to stdout."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Optional path to a .env file (defaults to ./.env if present).",
    )
    parser.add_argument(
        "--max-repos",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Process at most N new repositories in this run (after resume skips). "
            "Useful for stress tests or partial runs."
        ),
    )
    parser.add_argument(
        "--snyk-orgs-output",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Write Snyk org-creation JSON (one org per distinct APM code) to this path."
        ),
    )
    parser.add_argument(
        "--snyk-import-output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write Snyk Bitbucket Server import targets JSON to this path.",
    )
    parser.add_argument(
        "--flush-interval",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Write outputs every N new repositories (default: BITBUCKET_FLUSH_INTERVAL "
            "or 1). Applies when --output is set."
        ),
    )
    return parser


def _last_checkpoint_key(rows: list[dict[str, Any]]) -> tuple[str, str] | None:
    for row in reversed(rows):
        k = row_repo_key(row)
        if k is not None:
            return k
    return None


def _flush_artifacts(
    primary_path: Path,
    rows: list[dict[str, Any]],
    snyk_orgs: Path | None,
    snyk_import: Path | None,
) -> None:
    """Persist primary and optional Snyk companion files atomically."""
    ck = _last_checkpoint_key(rows)
    atomic_write_json(primary_path, build_primary_document(rows, last_completed=ck))
    if snyk_orgs is not None:
        atomic_write_json(
            snyk_orgs,
            build_snyk_orgs_document(apm_codes_from_rows(rows)),
        )
    if snyk_import is not None:
        atomic_write_json(
            snyk_import,
            build_snyk_import_document(rows),
        )


def _run_with_file_output(
    *,
    output_path: Path,
    client: BitbucketServerClient,
    file_path: str,
    max_repos: int | None,
    flush_interval: int,
    snyk_orgs: Path | None,
    snyk_import: Path | None,
) -> None:
    """Incremental mapping with resume and periodic flush."""
    try:
        existing_rows, _legacy = load_primary_output_file(output_path)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    completed = completed_keys_from_rows(existing_rows)
    rows_accum: list[dict[str, Any]] = list(existing_rows)
    pending_flush = 0
    try:
        for row in iter_mapping(
            client,
            file_path,
            completed_keys=completed,
            max_repos=max_repos,
        ):
            rows_accum.append(row)
            key = row_repo_key(row)
            if key is not None:
                completed.add(key)
            pending_flush += 1
            if pending_flush >= flush_interval:
                _flush_artifacts(output_path, rows_accum, snyk_orgs, snyk_import)
                pending_flush = 0
    finally:
        _flush_artifacts(output_path, rows_accum, snyk_orgs, snyk_import)


def _run_stdout(
    *,
    client: BitbucketServerClient,
    file_path: str,
    max_repos: int | None,
    snyk_orgs: Path | None,
    snyk_import: Path | None,
) -> None:
    """Write a JSON array to stdout; optional Snyk files are still written when set."""
    rows = list(
        iter_mapping(
            client,
            file_path,
            completed_keys=set(),
            max_repos=max_repos,
        )
    )
    text = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    sys.stdout.write(text)
    if snyk_orgs is not None:
        atomic_write_json(
            snyk_orgs,
            build_snyk_orgs_document(apm_codes_from_rows(rows)),
        )
    if snyk_import is not None:
        atomic_write_json(snyk_import, build_snyk_import_document(rows))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the mapper CLI."""
    raw = list(argv) if argv is not None else sys.argv[1:]
    if "-i" in raw or "--input" in raw:
        print(
            "Spreadsheet import uses a different command: "
            "`uv run bitbucket-repo-mapper-from-spreadsheet -i FILE.xlsx` "
            "(or pass FILE.xlsx as the only positional argument). "
            "`bitbucket-repo-mapper` talks to Bitbucket and has no --input.",
            file=sys.stderr,
        )
    parser = build_parser()
    args = parser.parse_args(raw)
    load_dotenv_file(args.env_file)
    try:
        settings = load_settings()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    flush_interval = (
        args.flush_interval if args.flush_interval is not None else settings.flush_interval
    )
    if flush_interval < 1:
        print("flush interval must be >= 1", file=sys.stderr)
        return 2

    client = BitbucketServerClient(
        settings.bitbucket_url,
        settings.bitbucket_pat,
        http_max_attempts=settings.http_max_attempts,
        http_backoff_seconds=settings.http_backoff_seconds,
    )
    try:
        if args.output:
            _run_with_file_output(
                output_path=Path(args.output),
                client=client,
                file_path=settings.file_path,
                max_repos=args.max_repos,
                flush_interval=flush_interval,
                snyk_orgs=args.snyk_orgs_output,
                snyk_import=args.snyk_import_output,
            )
        else:
            _run_stdout(
                client=client,
                file_path=settings.file_path,
                max_repos=args.max_repos,
                snyk_orgs=args.snyk_orgs_output,
                snyk_import=args.snyk_import_output,
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
