"""CLI: build mapper JSON from a spreadsheet without calling Bitbucket."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from common.output_state import (
    assert_safe_filesystem_path,
    atomic_write_json,
    build_primary_document,
)
from common.spreadsheet.mapping import mapping_rows_from_xlsx
from snyk.outputs import (
    apm_codes_from_rows,
    build_snyk_import_document,
    build_snyk_orgs_document,
)


def build_parser() -> argparse.ArgumentParser:
    """Construct the spreadsheet import CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Build primary mapping and optional Snyk JSON files from an .xlsx "
            "spreadsheet (columns A/B/D). Does not call Bitbucket."
        ),
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input_path",
        type=Path,
        metavar="PATH",
        help=(
            "Input .xlsx file (first worksheet; columns A=APM, B=selector, D=repo name). "
            "You may pass the same path as a positional argument instead."
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
            "Write primary mapping JSON using the versioned wrapper format "
            "(same as bitbucket-repo-mapper). If omitted, print a JSON array to stdout."
        ),
    )
    parser.add_argument(
        "--snyk-orgs-output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write Snyk org-creation JSON (one org per distinct non-null apm_code).",
    )
    parser.add_argument(
        "--snyk-import-output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write Snyk Bitbucket Server import targets JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the spreadsheet import CLI."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    inp = args.input_path or args.input_positional
    if inp is None:
        parser.error(
            "input spreadsheet is required: use -i/--input PATH or pass INPUT.xlsx "
            "(run `bitbucket-repo-mapper-from-spreadsheet`, not `bitbucket-repo-mapper`)."
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

    rows: list[dict[str, Any]]
    try:
        rows = mapping_rows_from_xlsx(inp)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        if args.output:
            out_path = Path(args.output)
            assert_safe_filesystem_path(out_path)
            atomic_write_json(out_path, build_primary_document(rows, last_completed=None))
        else:
            text = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
            sys.stdout.write(text)

        if args.snyk_orgs_output is not None:
            so = Path(args.snyk_orgs_output)
            assert_safe_filesystem_path(so)
            atomic_write_json(so, build_snyk_orgs_document(apm_codes_from_rows(rows)))

        if args.snyk_import_output is not None:
            si = Path(args.snyk_import_output)
            assert_safe_filesystem_path(si)
            atomic_write_json(si, build_snyk_import_document(rows))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    return 0
