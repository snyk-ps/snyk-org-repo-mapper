#!/usr/bin/env python3
"""Delete and reimport Snyk targets with mismatched branch references.

Reads a diff.json artifact (apm_code, repository_name, production_branch,
target_reference), deletes each mismatched target, and reimports via snyk-api-import.

Example::

    export SNYK_TOKEN='...'
    export SNYK_GROUP_ID='...'
    PYTHONPATH=src python scripts/reimport_mismatched_targets.py \\
        --input diff.json \\
        --dry-run \\
        --limit 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

# Allow running without pip install -e .
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from common.output_state import assert_safe_filesystem_path, atomic_write_json  # noqa: E402
from config import load_dotenv_file  # noqa: E402
from config.snyk_settings import load_snyk_settings  # noqa: E402
from integrations.snyk.client import SnykRestClient  # noqa: E402
from snyk.branch_mismatch_reimport import (  # noqa: E402
    BranchMismatchReimportOptions,
    load_diff_entries,
    run_branch_mismatch_reimport,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Delete Snyk targets with mismatched branch references and reimport "
            "with the correct production_branch from a diff.json artifact."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional path to a .env file (defaults to ./.env if present).",
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        metavar="PATH",
        help="diff.json file (array of branch mismatch entries).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("branch-reimport-report.json"),
        metavar="PATH",
        help="Output path for the reimport report JSON.",
    )
    parser.add_argument(
        "--import-batch-dir",
        type=Path,
        default=Path("."),
        metavar="PATH",
        help="Directory for branch-reimport-batch-*.json files (and snyk-api-import cwd).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and match targets only; no DELETE or snyk-api-import.",
    )
    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Delete matched targets but do not run snyk-api-import.",
    )
    parser.add_argument(
        "--repos-per-batch",
        type=int,
        default=50,
        metavar="N",
        help="Max targets per snyk-api-import batch file (default: 50).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N diff entries (for UAT smoke tests).",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=0,
        metavar="MS",
        help="Optional delay between delete operations in milliseconds.",
    )
    parser.add_argument(
        "--snyk-api-import-cmd",
        default="snyk-api-import",
        metavar="CMD",
        help=(
            "Command to invoke snyk-api-import (default: snyk-api-import). "
            "Use 'npx snyk-api-import' if not installed globally."
        ),
    )
    return parser


def _report_has_failures(report: dict[str, object]) -> bool:
    failed = report.get("failed")
    return isinstance(failed, list) and bool(failed)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    load_dotenv_file(args.env_file)

    try:
        settings = load_snyk_settings()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        assert_safe_filesystem_path(args.input)
        assert_safe_filesystem_path(args.output)
        assert_safe_filesystem_path(args.import_batch_dir)
        entries = load_diff_entries(args.input)
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    options = BranchMismatchReimportOptions(
        dry_run=args.dry_run,
        skip_import=args.skip_import,
        repos_per_batch=args.repos_per_batch,
        limit=args.limit,
        snyk_api_import_cmd=args.snyk_api_import_cmd,
        import_batch_dir=args.import_batch_dir,
        delay_ms=args.delay_ms,
    )

    client = SnykRestClient(settings)
    try:
        report = run_branch_mismatch_reimport(client, entries, options)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps(report, indent=2))
    else:
        atomic_write_json(args.output, report)
        print(f"Wrote report to {args.output}")

    if _report_has_failures(report):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
