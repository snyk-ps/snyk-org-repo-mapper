"""CLI Stage 2.3 — Apply Bitbucket Server integration settings from Broker Apply report."""

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
from snyk.broker_integration_settings import apply_integration_settings, load_broker_apply_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 2.3 — Apply predefined Bitbucket Server integration settings for "
            "each org in broker-org-apply-report.json applied entries."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional path to a .env file (defaults to ./.env if present).",
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        metavar="PATH",
        help="broker-org-apply-report.json from Stage 2.2 — Broker Apply.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("broker-integration-settings-report.json"),
        metavar="PATH",
        help="Output path for settings apply report JSON.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated; do not PUT integration settings.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    load_dotenv_file(args.env_file)

    try:
        assert_safe_filesystem_path(args.report)
        apply_report = load_broker_apply_report(args.report)
        settings = load_snyk_settings()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if settings.integrations_api != "v1":
        print(
            "snyk-broker-integration-settings requires SNYK_INTEGRATIONS_API=v1 "
            "(integration settings PUT is not implemented for REST).",
            file=sys.stderr,
        )
        return 2

    client = SnykRestClient(settings)
    try:
        report = apply_integration_settings(
            apply_report,
            client=client,
            source_report_path=args.report,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1 if report.get("failed") else 0

    try:
        assert_safe_filesystem_path(args.output)
        atomic_write_json(args.output, report)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if report.get("failed"):
        print(
            f"Settings apply completed with {len(report['failed'])} failure(s); "
            f"see {args.output}",
            file=sys.stderr,
        )
        return 1
    return 0
