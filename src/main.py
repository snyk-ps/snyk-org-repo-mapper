"""Application entry point (see project guidelines: ``src/main.py``).

Delegates to the Bitbucket mapper CLI—the same behavior as the
``bitbucket-repo-mapper`` console script.
"""

from __future__ import annotations

from commands.bitbucket_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
