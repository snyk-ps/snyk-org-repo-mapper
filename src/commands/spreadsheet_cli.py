"""CLI: Stage 1 spreadsheet-driven Bitbucket discovery (writes discovery JSON)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from commands.discovery_helpers import (
    flush_discovery,
    log_empty_repo_summary,
    resolve_empty_repos_path,
    run_discovery_with_file_output,
)
from common.empty_repos_document import write_empty_repos_document
from common.mapper import iter_mapping_for_repos
from common.spreadsheet.bb_repo_mapping import parse_bb_repo_mapping_sheet
from config import load_dotenv_file, load_settings
from integrations.bitbucket import BitbucketServerClient


def build_parser() -> argparse.ArgumentParser:
    """Construct the spreadsheet discovery CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Stage 1 (spreadsheet): read bb-repo-mapping.xlsx (ProjectKey + repo list), "
            "query Bitbucket for AppSec YAML per repo, and write discovery JSON."
        ),
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input_path",
        type=Path,
        metavar="PATH",
        help=(
            "Input .xlsx (row 1: ProjectKey, RepoName; column B is semicolon-delimited "
            "repo slugs). You may pass the same path as a positional argument."
        ),
    )
    parser.add_argument(
        "input_positional",
        nargs="?",
        type=Path,
        metavar="INPUT.xlsx",
        help="Same as -i/--input when you prefer a positional path.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Write discovery JSON (versioned: source=bitbucket, rows, optional checkpoint). "
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


def main(argv: Sequence[str] | None = None) -> int:
    """Run spreadsheet-driven Bitbucket discovery CLI."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    inp = args.input_path or args.input_positional
    if inp is None:
        parser.error(
            "input spreadsheet is required: use -i/--input PATH or pass INPUT.xlsx "
            "(run `python main.py discover spreadsheet …`)."
        )
    if (
        args.input_path is not None
        and args.input_positional is not None
        and Path(args.input_path).resolve() != Path(args.input_positional).resolve()
    ):
        parser.error("Conflicting paths: -i/--input and positional INPUT.xlsx differ.")

    inp = Path(inp)
    if not inp.is_file():
        print(f"Input file not found: {inp}", file=sys.stderr)
        return 2

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

    try:
        repo_targets = parse_bb_repo_mapping_sheet(inp)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    client = BitbucketServerClient(
        settings.bitbucket_url,
        settings.bitbucket_pat,
        http_max_attempts=settings.http_max_attempts,
        http_backoff_seconds=settings.http_backoff_seconds,
    )
    empty_repos_path = resolve_empty_repos_path(
        output_path=args.output,
        empty_repos_output=args.empty_repos_output,
        no_empty_repos_output=args.no_empty_repos_output,
    )

    try:
        if args.output:
            output_path = Path(args.output)

            def factory(completed: set[tuple[str, str]]) -> Any:
                return iter_mapping_for_repos(
                    client,
                    settings.file_path,
                    repo_targets,
                    completed_keys=completed,
                    max_repos=args.max_repos,
                )

            run_discovery_with_file_output(
                output_path=output_path,
                row_iter_factory=factory,
                flush_interval=flush_interval,
                empty_repos_path=empty_repos_path,
            )
        else:
            rows = list(
                iter_mapping_for_repos(
                    client,
                    settings.file_path,
                    repo_targets,
                    completed_keys=set(),
                    max_repos=args.max_repos,
                )
            )
            text = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
            sys.stdout.write(text)
            if empty_repos_path is not None:
                write_empty_repos_document(empty_repos_path, rows, source="bitbucket")
                log_empty_repo_summary(rows, empty_repos_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
