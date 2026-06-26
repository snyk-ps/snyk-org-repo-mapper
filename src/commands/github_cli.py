"""Command-line interface: Stage 1 GitHub discovery (writes discovery JSON)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from commands.discovery_helpers import (
    log_empty_repo_summary,
    resolve_empty_repos_path,
    run_discovery_with_file_output,
)
from common.empty_repos_document import write_empty_repos_document
from common.github_mapper import iter_github_mapping
from config import load_dotenv_file
from config.github_settings import load_github_settings
from integrations.github import GitHubClient


def parse_org_list(raw: str) -> list[str]:
    orgs = [part.strip() for part in raw.split(",")]
    orgs = [org for org in orgs if org]
    if not orgs:
        msg = "--orgs must include at least one organization login"
        raise ValueError(msg)
    return orgs


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Stage 1 (GitHub): list repositories for one or more orgs, read AppSec YAML "
            "per repo, and write discovery JSON for later snyk-orgs / snyk-import stages."
        ),
    )
    parser.add_argument(
        "--orgs",
        required=True,
        metavar="ORG1,ORG2",
        help="Comma-separated GitHub organization logins to crawl.",
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
            "Write discovery every N new repositories (default: GITHUB_FLUSH_INTERVAL "
            "or 1). Applies when --output is set."
        ),
    )
    parser.add_argument(
        "--empty-repos-output",
        default=None,
        metavar="PATH",
        help=(
            "Write empty-repository list JSON. Default: github-empty-repos.json "
            "when -o/--output is set."
        ),
    )
    parser.add_argument(
        "--no-empty-repos-output",
        action="store_true",
        help="Do not write github-empty-repos.json even when -o/--output is set.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run GitHub discovery CLI."""
    parser = build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 2
    load_dotenv_file(args.env_file)
    try:
        settings = load_github_settings()
        org_logins = parse_org_list(args.orgs)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    flush_interval = (
        args.flush_interval if args.flush_interval is not None else settings.flush_interval
    )
    if flush_interval < 1:
        print("flush interval must be >= 1", file=sys.stderr)
        return 2

    client = GitHubClient(
        settings.api_url,
        settings.token,
        http_max_attempts=settings.http_max_attempts,
        http_backoff_seconds=settings.http_backoff_seconds,
    )
    empty_repos_path = resolve_empty_repos_path(
        output_path=args.output,
        empty_repos_output=args.empty_repos_output,
        no_empty_repos_output=args.no_empty_repos_output,
        source="github",
    )
    try:
        if args.output:
            run_discovery_with_file_output(
                output_path=Path(args.output),
                row_iter_factory=lambda completed: iter_github_mapping(
                    client,
                    settings.file_path,
                    org_logins,
                    completed_keys=completed,
                    max_repos=args.max_repos,
                ),
                flush_interval=flush_interval,
                empty_repos_path=empty_repos_path,
                source="github",
            )
        else:
            rows = list(
                iter_github_mapping(
                    client,
                    settings.file_path,
                    org_logins,
                    completed_keys=set(),
                    max_repos=args.max_repos,
                )
            )
            text = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
            sys.stdout.write(text)
            if empty_repos_path is not None:
                write_empty_repos_document(empty_repos_path, rows, source="github")
                log_empty_repo_summary(rows, empty_repos_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
