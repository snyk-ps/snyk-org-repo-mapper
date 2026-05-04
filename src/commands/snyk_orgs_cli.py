"""CLI Stage 2: write snyk-orgs.json from discovery JSON (no APIs)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from common.discovery_document import load_rows_from_stage1_file
from common.output_state import assert_safe_filesystem_path, atomic_write_json
from snyk.outputs import apm_codes_from_rows, build_snyk_orgs_document
from snyk.project_context import project_apm_map_from_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 2: write snyk-orgs.json (Snyk API Import orgs:create shape) from discovery JSON."
        ),
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
        help="Output path for snyk-orgs.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print snyk-orgs JSON to stdout; do not write --output.",
    )
    parser.add_argument(
        "--group-id",
        dest="group_id",
        default=None,
        metavar="UUID",
        help=(
            "Snyk Group ID for every org entry's groupId (default: placeholder string)."
        ),
    )
    parser.add_argument(
        "--template-org-id",
        dest="template_org_id",
        default=None,
        metavar="UUID",
        help=(
            "Snyk source/template organization ID for every org entry's sourceOrgId "
            "(default: placeholder string)."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        rows, _src = load_rows_from_stage1_file(args.discovery)
        project_apm_map_from_rows(rows)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    group_id = (args.group_id.strip() if isinstance(args.group_id, str) else None) or None
    template_org_id = (
        (args.template_org_id.strip() if isinstance(args.template_org_id, str) else None)
        or None
    )

    orgs_doc = build_snyk_orgs_document(
        apm_codes_from_rows(rows),
        group_id=group_id,
        template_org_id=template_org_id,
    )

    if args.dry_run:
        print(json.dumps(orgs_doc, indent=2, ensure_ascii=False))
        return 0

    try:
        assert_safe_filesystem_path(args.output)
        atomic_write_json(args.output, orgs_doc)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0
