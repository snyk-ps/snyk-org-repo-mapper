"""Command-line interface: Stage 1 Bitbucket discovery (writes discovery JSON)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from common.discovery_document import build_discovery_document, load_resume_rows
from common.empty_repos_document import DEFAULT_EMPTY_REPOS_FILENAME, write_empty_repos_document
from common.mapper import iter_mapping, row_is_empty
from common.output_state import atomic_write_json, completed_keys_from_rows, row_repo_key
from config import load_dotenv_file, load_settings
from integrations.bitbucket import BitbucketServerClient


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Stage 1 (Bitbucket): list projects and repositories, read AppSec YAML per repo, "
            "and write discovery JSON for later snyk-orgs / snyk-import stages."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Write discovery JSON (versioned: source, rows, optional checkpoint). "
            "If omitted, print a JSON array of rows to stdout."
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
        "--flush-interval",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Write discovery every N new repositories (default: BITBUCKET_FLUSH_INTERVAL "
            "or 1). Applies when --output is set."
        ),
    )
    parser.add_argument(
        "--empty-repos-output",
        default=None,
        metavar="PATH",
        help=(
            "Write empty-repository list JSON. Default: bitbucket-empty-repos.json "
            "when -o/--output is set."
        ),
    )
    parser.add_argument(
        "--no-empty-repos-output",
        action="store_true",
        help="Do not write bitbucket-empty-repos.json even when -o/--output is set.",
    )
    return parser


def _last_checkpoint_key(rows: list[dict[str, Any]]) -> tuple[str, str] | None:
    for row in reversed(rows):
        k = row_repo_key(row)
        if k is not None:
            return k
    return None


def _resolve_empty_repos_path(
    *,
    output_path: str | None,
    empty_repos_output: str | None,
    no_empty_repos_output: bool,
) -> Path | None:
    if no_empty_repos_output:
        return None
    if empty_repos_output is not None:
        return Path(empty_repos_output)
    if output_path:
        return Path(DEFAULT_EMPTY_REPOS_FILENAME)
    return None


def _flush_discovery(
    output_path: Path,
    rows: list[dict[str, Any]],
    *,
    empty_repos_path: Path | None,
) -> None:
    """Persist discovery JSON atomically."""
    ck = _last_checkpoint_key(rows)
    atomic_write_json(
        output_path,
        build_discovery_document(rows, "bitbucket", last_completed=ck),
    )
    if empty_repos_path is not None:
        write_empty_repos_document(empty_repos_path, rows)


def _log_empty_repo_summary(rows: list[dict[str, Any]], empty_repos_path: Path | None) -> None:
    n_empty = sum(1 for row in rows if row_is_empty(row))
    if empty_repos_path is not None:
        print(
            f"{n_empty} empty repositories (is_empty=true); see {empty_repos_path}",
            file=sys.stderr,
        )


def _run_with_file_output(
    *,
    output_path: Path,
    client: BitbucketServerClient,
    file_path: str,
    max_repos: int | None,
    flush_interval: int,
    empty_repos_path: Path | None,
) -> None:
    """Incremental discovery with resume and periodic flush."""
    try:
        existing_rows = load_resume_rows(output_path)
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
                _flush_discovery(
                    output_path,
                    rows_accum,
                    empty_repos_path=empty_repos_path,
                )
                pending_flush = 0
    finally:
        _flush_discovery(
            output_path,
            rows_accum,
            empty_repos_path=empty_repos_path,
        )
        _log_empty_repo_summary(rows_accum, empty_repos_path)


def _run_stdout(
    *,
    client: BitbucketServerClient,
    file_path: str,
    max_repos: int | None,
) -> list[dict[str, Any]]:
    """Write a JSON array of rows to stdout (no discovery wrapper)."""
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
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    """Run Bitbucket discovery CLI."""
    raw = list(argv) if argv is not None else sys.argv[1:]
    if "-i" in raw or "--input" in raw:
        print(
            "Spreadsheet discovery uses: `python main.py discover spreadsheet …` "
            "(or the `repo-mapper-discover-spreadsheet` console script). "
            "This command is Bitbucket-only and has no --input.",
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
    empty_repos_path = _resolve_empty_repos_path(
        output_path=args.output,
        empty_repos_output=args.empty_repos_output,
        no_empty_repos_output=args.no_empty_repos_output,
    )
    try:
        if args.output:
            _run_with_file_output(
                output_path=Path(args.output),
                client=client,
                file_path=settings.file_path,
                max_repos=args.max_repos,
                flush_interval=flush_interval,
                empty_repos_path=empty_repos_path,
            )
        else:
            rows = _run_stdout(
                client=client,
                file_path=settings.file_path,
                max_repos=args.max_repos,
            )
            if empty_repos_path is not None:
                write_empty_repos_document(empty_repos_path, rows)
                _log_empty_repo_summary(rows, empty_repos_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
