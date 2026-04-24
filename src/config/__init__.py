"""Load configuration from environment variables and optional ``.env`` files."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the mapper."""

    bitbucket_url: str
    bitbucket_pat: str
    file_path: str
    http_max_attempts: int
    http_backoff_seconds: float
    flush_interval: int


def load_dotenv_file(path: Path | None = None) -> None:
    """Load ``KEY=value`` pairs from a ``.env`` file into the process environment.

    Existing environment variables are not overwritten. Lines starting with ``#``
    and blank lines are ignored.

    Args:
        path: File to read. Defaults to ``.env`` in the current working directory.
    """
    env_path = path if path is not None else Path.cwd() / ".env"
    if not env_path.is_file():
        return
    text = env_path.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
            value = value[1:-1]
        os.environ[key] = value


def _parse_int(name: str, raw: str | None, default: int, *, minimum: int = 1) -> int:
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip(), 10)
    except ValueError as exc:
        msg = f"{name} must be an integer"
        raise ValueError(msg) from exc
    if value < minimum:
        msg = f"{name} must be >= {minimum}"
        raise ValueError(msg)
    return value


def _parse_float(name: str, raw: str | None, default: float, *, minimum: float = 0.0) -> float:
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw.strip())
    except ValueError as exc:
        msg = f"{name} must be a number"
        raise ValueError(msg) from exc
    if value < minimum:
        msg = f"{name} must be >= {minimum}"
        raise ValueError(msg)
    return value


def load_settings() -> Settings:
    """Build settings from the environment (after optional ``load_dotenv_file``)."""
    base = os.environ.get("BITBUCKET_URL", "").strip().rstrip("/")
    pat = os.environ.get("BITBUCKET_PAT", "").strip()
    file_path = os.environ.get("BITBUCKET_FILE_PATH", "appsec.yaml").strip()
    http_retries = _parse_int(
        "BITBUCKET_HTTP_RETRIES",
        os.environ.get("BITBUCKET_HTTP_RETRIES"),
        default=5,
        minimum=1,
    )
    http_backoff = _parse_float(
        "BITBUCKET_HTTP_BACKOFF_S",
        os.environ.get("BITBUCKET_HTTP_BACKOFF_S"),
        default=1.0,
        minimum=0.0,
    )
    flush_interval = _parse_int(
        "BITBUCKET_FLUSH_INTERVAL",
        os.environ.get("BITBUCKET_FLUSH_INTERVAL"),
        default=1,
        minimum=1,
    )
    if not base:
        msg = "BITBUCKET_URL is required"
        raise ValueError(msg)
    if not pat:
        msg = "BITBUCKET_PAT is required"
        raise ValueError(msg)
    if not file_path:
        msg = "BITBUCKET_FILE_PATH must not be empty when set"
        raise ValueError(msg)
    return Settings(
        bitbucket_url=base,
        bitbucket_pat=pat,
        file_path=file_path,
        http_max_attempts=http_retries,
        http_backoff_seconds=http_backoff,
        flush_interval=flush_interval,
    )
