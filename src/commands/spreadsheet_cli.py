"""CLI: Stage 1 spreadsheet discovery (writes discovery JSON)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from common.discovery_document import build_discovery_document
from common.output_state import assert_safe_filesystem_path, atomic_write_json
from common.spreadsheet.mapping import mapping_rows_from_xlsx


def build_parser() -> argparse.ArgumentParser:
    """Construct the spreadsheet discovery CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Stage 1 (spreadsheet): build discovery JSON from an .xlsx "
            "(columns A/B/D). Does not call Bitbucket."
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
            "Write discovery JSON (versioned: source=spreadsheet, rows). "
            "If omitted, print a JSON array of rows to stdout."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run spreadsheet discovery CLI."""
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
            atomic_write_json(
                out_path,
                build_discovery_document(rows, "spreadsheet", last_completed=None),
            )
        else:
            text = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
            sys.stdout.write(text)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    return 0
