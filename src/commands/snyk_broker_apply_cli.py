"""CLI Stage 2.2 — Broker Apply: apply broker-org-plan.json via Universal Broker integration POST."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from common.output_state import assert_safe_filesystem_path, atomic_write_json
from config import load_dotenv_file
from config.snyk_settings import load_broker_settings, load_snyk_settings
from integrations.snyk.broker_client import BrokerClient
from integrations.snyk.client import SnykRestClient
from snyk.broker_apply import load_and_apply_plan_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 2.2 — Broker Apply: create org–broker connection integrations from "
            "broker-org-plan.json assignments."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional path to a .env file (defaults to ./.env if present).",
    )
    parser.add_argument(
        "--plan",
        type=Path,
        required=True,
        metavar="PATH",
        help="broker-org-plan.json from Stage 2.1 — Broker Plan.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("broker-org-apply-report.json"),
        metavar="PATH",
        help="Output path for apply report JSON.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be POSTed; do not create integrations.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    load_dotenv_file(args.env_file)

    try:
        assert_safe_filesystem_path(args.plan)
        plan_doc = json.loads(args.plan.read_text(encoding="utf-8"))
        tenant_id = plan_doc.get("tenant_id") if isinstance(plan_doc, dict) else None
        install_id = plan_doc.get("install_id") if isinstance(plan_doc, dict) else None
        broker_settings = load_broker_settings(
            tenant_id=tenant_id if isinstance(tenant_id, str) else None,
            install_id=install_id if isinstance(install_id, str) else None,
        )
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    broker = BrokerClient(broker_settings)
    snyk: SnykRestClient | None = None
    if broker_settings.group_id:
        try:
            snyk = SnykRestClient(load_snyk_settings())
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    try:
        report = load_and_apply_plan_file(
            args.plan,
            broker=broker,
            snyk=snyk,
            dry_run=args.dry_run,
        )
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

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
            f"Apply completed with {len(report['failed'])} failure(s); see {args.output}",
            file=sys.stderr,
        )
        return 1
    return 0
