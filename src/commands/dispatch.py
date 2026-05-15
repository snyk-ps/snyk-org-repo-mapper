"""Unified CLI dispatcher: discover → snyk-orgs → broker plan/apply → snyk-import."""

from __future__ import annotations

import sys
from typing import Sequence

from commands.bitbucket_cli import main as bitbucket_main
from commands.snyk_broker_apply_cli import main as snyk_broker_apply_main
from commands.snyk_broker_plan_cli import main as snyk_broker_plan_main
from commands.snyk_import_cli import main as snyk_import_main
from commands.snyk_orgs_cli import main as snyk_orgs_main
from commands.spreadsheet_cli import main as spreadsheet_main


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch to pipeline stage CLIs (1, 2, 2.1, 2.2, 3)."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(
            "Usage: python main.py <command> [options...]\n\n"
            "Snyk onboarding (run in order):\n"
            "  discover bitbucket       Stage 1 — Bitbucket Server → discovery.json\n"
            "  discover spreadsheet     Stage 1 — .xlsx → discovery.json\n"
            "  snyk-orgs                Stage 2 — discovery.json → snyk-orgs.json\n"
            "  snyk-broker-plan         Stage 2.1 — Broker Plan → broker-org-plan.json\n"
            "  snyk-broker-apply        Stage 2.2 — Broker Apply → broker integrations (POST)\n"
            "  snyk-import              Stage 3 — discovery.json → snyk-import.json (Snyk API)\n",
            file=sys.stderr,
        )
        return 0 if args and args[0] in ("-h", "--help") else 2

    cmd, *rest = args
    if cmd == "discover":
        if not rest or rest[0] in ("-h", "--help"):
            print(
                "Usage: python main.py discover {bitbucket|spreadsheet} [options...]\n"
                "  discover bitbucket      — same flags as before (see --help)\n"
                "  discover spreadsheet    — same flags as before (see --help)",
                file=sys.stderr,
            )
            return 0 if rest and rest[0] in ("-h", "--help") else 2
        target, *tail = rest
        if target == "bitbucket":
            return bitbucket_main(tail)
        if target == "spreadsheet":
            return spreadsheet_main(tail)
        print(f"Unknown discover target {target!r}. Use bitbucket or spreadsheet.", file=sys.stderr)
        return 2

    if cmd == "snyk-orgs":
        return snyk_orgs_main(rest)

    if cmd == "snyk-broker-plan":
        return snyk_broker_plan_main(rest)

    if cmd == "snyk-broker-apply":
        return snyk_broker_apply_main(rest)

    if cmd == "snyk-import":
        return snyk_import_main(rest)

    print(f"Unknown command {cmd!r}. Use -h for usage.", file=sys.stderr)
    return 2


def main_discover_bitbucket() -> int:
    """Console script: ``repo-mapper-discover-bitbucket``."""
    return main(["discover", "bitbucket"] + sys.argv[1:])


def main_discover_spreadsheet() -> int:
    """Console script: ``repo-mapper-discover-spreadsheet``."""
    return main(["discover", "spreadsheet"] + sys.argv[1:])


def main_snyk_orgs() -> int:
    """Console script: ``repo-mapper-snyk-orgs``."""
    return main(["snyk-orgs"] + sys.argv[1:])


def main_snyk_import() -> int:
    """Console script: ``repo-mapper-snyk-import``."""
    return main(["snyk-import"] + sys.argv[1:])


def main_snyk_broker_plan() -> int:
    """Console script: ``repo-mapper-snyk-broker-plan``."""
    return main(["snyk-broker-plan"] + sys.argv[1:])


def main_snyk_broker_apply() -> int:
    """Console script: ``repo-mapper-snyk-broker-apply``."""
    return main(["snyk-broker-apply"] + sys.argv[1:])
