"""Application entry point (see project guidelines: ``src/main.py``).

Routes to either the Bitbucket mapper CLI or the spreadsheet-only CLI based on the
first argument: ``bitbucket`` or ``spreadsheet``.
"""

from __future__ import annotations

import sys
from typing import Sequence

from commands.bitbucket_cli import main as bitbucket_main
from commands.spreadsheet_cli import main as spreadsheet_main

_MODES = frozenset({"bitbucket", "spreadsheet"})


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch to ``bitbucket_cli`` or ``spreadsheet_cli``."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(
            "Usage: python main.py {bitbucket|spreadsheet} [CLI options...]\n"
            "  bitbucket    — Bitbucket Server mapper (bitbucket-repo-mapper)\n"
            "  spreadsheet  — Build mapping from .xlsx (bitbucket-repo-mapper-from-spreadsheet)",
            file=sys.stderr,
        )
        return 0 if args and args[0] in ("-h", "--help") else 2

    mode, *rest = args
    if mode not in _MODES:
        print(
            f"Unknown mode {mode!r}. Use bitbucket or spreadsheet "
            f"(or run with -h for usage).",
            file=sys.stderr,
        )
        return 2
    if mode == "bitbucket":
        return bitbucket_main(rest)
    return spreadsheet_main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
