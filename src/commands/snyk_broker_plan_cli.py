"""CLI Stage 2.1 — Broker Plan: build broker-org-plan.json from snyk-orgs and Universal Broker."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from common.output_state import assert_safe_filesystem_path, atomic_write_json
from config import load_dotenv_file
from config.snyk_settings import BrokerSettings, load_broker_settings, load_snyk_settings
from integrations.snyk.broker_client import BrokerClient
from integrations.snyk.client import SnykRestClient
from snyk.broker_plan import build_broker_org_plan
from snyk.enrichment import load_json_object


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 2.1 — Broker Plan: build broker-org-plan.json from snyk-orgs.json and "
            "Universal Broker bitbucket-server connections (read-only API)."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional path to a .env file (defaults to ./.env if present).",
    )
    parser.add_argument(
        "--snyk-orgs",
        type=Path,
        required=True,
        metavar="PATH",
        help="snyk-orgs.json from Stage 2 (snyk-orgs).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("broker-org-plan.json"),
        metavar="PATH",
        help="Output path for broker-org-plan.json.",
    )
    parser.add_argument(
        "--tenant-id",
        default=None,
        metavar="UUID",
        help="Snyk tenant id (or SNYK_TENANT_ID).",
    )
    parser.add_argument(
        "--install-id",
        default=None,
        metavar="UUID",
        help="Universal Broker install id (or SNYK_BROKER_INSTALL_ID).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan JSON to stdout; do not write --output.",
    )
    return parser


def _snyk_client_for_group_resolve(settings: BrokerSettings) -> SnykRestClient | None:
    if not settings.group_id:
        return None
    return SnykRestClient(
        load_snyk_settings(),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    load_dotenv_file(args.env_file)

    try:
        assert_safe_filesystem_path(args.snyk_orgs)
        orgs_doc = load_json_object(args.snyk_orgs)
        broker_settings = load_broker_settings(
            tenant_id=args.tenant_id,
            install_id=args.install_id,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    broker = BrokerClient(broker_settings)
    snyk: SnykRestClient | None = None
    if broker_settings.group_id:
        try:
            snyk = _snyk_client_for_group_resolve(broker_settings)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    try:
        plan = build_broker_org_plan(orgs_doc=orgs_doc, broker=broker, snyk=snyk)
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0

    try:
        assert_safe_filesystem_path(args.output)
        atomic_write_json(args.output, plan)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0
