"""Application entry point (see project guidelines: ``src/main.py``).

Routes CLI commands via ``commands.dispatch``.
"""

from __future__ import annotations

from commands.dispatch import main


if __name__ == "__main__":
    raise SystemExit(main())
