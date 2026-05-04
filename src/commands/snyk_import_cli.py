"""CLI Stage 3: build snyk-import.json and resolve Snyk org/integration IDs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from common.discovery_document import load_rows_from_stage1_file
from common.output_state import assert_safe_filesystem_path, atomic_write_json
from config import load_dotenv_file
from config.snyk_settings import load_snyk_settings
from integrations.snyk.client import SnykRestClient
from snyk.enrichment import (
    build_name_to_org_id,
    enrich_import_document,
    integration_cache_for_orgs,
    load_json_object,
    org_names_from_snyk_orgs_document,
    required_apm_codes_for_import,
    summarize_enrichment_plan,
    validate_orgs_file_lists_codes,
)
from snyk.outputs import build_snyk_import_document
from snyk.project_context import project_apm_map_from_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 3: build snyk-import.json from discovery rows and resolve orgId / "
            "integrationId via Snyk REST API (no Bitbucket calls)."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional path to a .env file (defaults to ./.env if present).",
    )
    parser.add_argument(
        "--discovery",
        type=Path,
        required=True,
        metavar="PATH",
        help="Stage 1 discovery JSON (or legacy primary mapping).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        metavar="PATH",
        help="Output path for snyk-import.json.",
    )
    parser.add_argument(
        "--snyk-orgs",
        type=Path,
        default=None,
        metavar="PATH",
        help="Optional snyk-orgs.json for cross-check of expected org names.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Query Snyk API and print a plan; do not write --output.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    load_dotenv_file(args.env_file)

    try:
        rows, _src = load_rows_from_stage1_file(args.discovery)
        project_apm = project_apm_map_from_rows(rows)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    import_doc = build_snyk_import_document(rows)
    required = required_apm_codes_for_import(project_apm, import_doc)

    orgs_doc = None
    if args.snyk_orgs is not None:
        try:
            assert_safe_filesystem_path(args.snyk_orgs)
            orgs_doc = load_json_object(args.snyk_orgs)
            org_names = org_names_from_snyk_orgs_document(orgs_doc)
            validate_orgs_file_lists_codes(org_names_in_file=org_names, required_codes=required)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    try:
        settings = load_snyk_settings()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    client = SnykRestClient(settings)
    try:
        api_orgs = client.iter_group_orgs()
        name_to_id = build_name_to_org_id(api_orgs)
        for code in sorted(required):
            if code not in name_to_id:
                msg = f"No Snyk organization named {code!r} in group {settings.group_id}"
                raise ValueError(msg)
        org_ids = {name_to_id[c] for c in required}
        org_to_integration = integration_cache_for_orgs(client, org_ids)
        new_doc = enrich_import_document(
            import_doc,
            project_apm=project_apm,
            name_to_org_id=name_to_id,
            org_to_integration_id=org_to_integration,
        )
        plan = summarize_enrichment_plan(
            import_doc,
            project_apm,
            name_to_id,
            org_to_integration,
        )
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.dry_run:
        print(plan)
        return 0

    try:
        assert_safe_filesystem_path(args.output)
        atomic_write_json(args.output, new_doc)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0
