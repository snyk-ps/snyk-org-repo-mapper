"""CLI Stage 4 — Post-import group cleanup and normalization."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from common.output_state import assert_safe_filesystem_path, atomic_write_json
from config import load_dotenv_file
from config.snyk_settings import load_snyk_settings
from integrations.snyk.client import SnykRestClient
from snyk.post_import_cleanup import run_post_import_cleanup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 4 — Delete Dockerfile projects, set recurring test frequency to never, "
            "and apply integration settings for every org in SNYK_GROUP_ID."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional path to a .env file (defaults to ./.env if present).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("post-import-cleanup-report.json"),
        metavar="PATH",
        help="Output path for post-import cleanup report JSON.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change; do not DELETE projects or issue PUT requests.",
    )
    return parser


def _report_has_failures(report: dict[str, object]) -> bool:
    for section in (
        "dockerfile_projects",
        "recurring_test_frequency",
        "integration_settings",
    ):
        bucket = report.get(section)
        if not isinstance(bucket, dict):
            continue
        failed = bucket.get("failed")
        if isinstance(failed, list) and failed:
            return True
    return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    load_dotenv_file(args.env_file)

    try:
        settings = load_snyk_settings()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if settings.integrations_api != "v1":
        print(
            "snyk-post-import-cleanup requires SNYK_INTEGRATIONS_API=v1 "
            "(integration settings PUT is not implemented for REST).",
            file=sys.stderr,
        )
        return 2

    client = SnykRestClient(settings)
    report = run_post_import_cleanup(client, dry_run=args.dry_run)

    if args.dry_run:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1 if _report_has_failures(report) else 0

    try:
        assert_safe_filesystem_path(args.output)
        atomic_write_json(args.output, report)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if _report_has_failures(report):
        print(
            f"Post-import cleanup completed with failures; see {args.output}",
            file=sys.stderr,
        )
        return 1
    return 0
