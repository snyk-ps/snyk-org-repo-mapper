"""Load GitHub configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from config import _parse_float, _parse_int


DEFAULT_GITHUB_API_URL = "https://api.github.com"


@dataclass(frozen=True)
class GithubSettings:
    """Runtime settings for GitHub discovery."""

    token: str
    api_url: str
    file_path: str
    http_max_attempts: int
    http_backoff_seconds: float
    flush_interval: int


def load_github_settings() -> GithubSettings:
    """Build GitHub settings from the environment (after optional ``load_dotenv_file``)."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    api_url = os.environ.get("GITHUB_API_URL", DEFAULT_GITHUB_API_URL).strip().rstrip("/")
    file_path = os.environ.get("GITHUB_FILE_PATH", "appsec.yaml").strip()
    http_retries = _parse_int(
        "GITHUB_HTTP_RETRIES",
        os.environ.get("GITHUB_HTTP_RETRIES"),
        default=5,
        minimum=1,
    )
    http_backoff = _parse_float(
        "GITHUB_HTTP_BACKOFF_S",
        os.environ.get("GITHUB_HTTP_BACKOFF_S"),
        default=1.0,
        minimum=0.0,
    )
    flush_interval = _parse_int(
        "GITHUB_FLUSH_INTERVAL",
        os.environ.get("GITHUB_FLUSH_INTERVAL"),
        default=1,
        minimum=1,
    )
    if not token:
        msg = "GITHUB_TOKEN is required"
        raise ValueError(msg)
    if not api_url:
        msg = "GITHUB_API_URL must not be empty when set"
        raise ValueError(msg)
    if not file_path:
        msg = "GITHUB_FILE_PATH must not be empty when set"
        raise ValueError(msg)
    return GithubSettings(
        token=token,
        api_url=api_url,
        file_path=file_path,
        http_max_attempts=http_retries,
        http_backoff_seconds=http_backoff,
        flush_interval=flush_interval,
    )
