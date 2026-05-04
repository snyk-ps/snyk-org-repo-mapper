"""Snyk REST API settings for import enrichment (stage 2)."""

from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_SNYK_REST_BASE = "https://api.snyk.io/rest"
DEFAULT_SNYK_API_VERSION = "2024-10-15"


@dataclass(frozen=True)
class SnykSettings:
    """Runtime settings for Snyk REST calls."""

    token: str
    group_id: str
    rest_api_base: str
    api_version: str
    http_max_attempts: int
    http_backoff_seconds: float


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


def load_snyk_settings() -> SnykSettings:
    """Load settings from the environment (after optional ``load_dotenv_file``)."""
    token = os.environ.get("SNYK_TOKEN", "").strip()
    group_id = os.environ.get("SNYK_GROUP_ID", "").strip()
    rest_base = os.environ.get("SNYK_API_BASE", "").strip().rstrip("/")
    if not rest_base:
        rest_base = DEFAULT_SNYK_REST_BASE.rstrip("/")
    api_version = os.environ.get("SNYK_API_VERSION", "").strip()
    if not api_version:
        api_version = DEFAULT_SNYK_API_VERSION
    attempts = _parse_int(
        "SNYK_HTTP_MAX_ATTEMPTS",
        os.environ.get("SNYK_HTTP_MAX_ATTEMPTS"),
        default=5,
        minimum=1,
    )
    backoff = _parse_float(
        "SNYK_HTTP_BACKOFF_S",
        os.environ.get("SNYK_HTTP_BACKOFF_S"),
        default=1.0,
        minimum=0.0,
    )
    if not token:
        msg = "SNYK_TOKEN is required"
        raise ValueError(msg)
    if not group_id:
        msg = "SNYK_GROUP_ID is required"
        raise ValueError(msg)
    return SnykSettings(
        token=token,
        group_id=group_id,
        rest_api_base=rest_base,
        api_version=api_version,
        http_max_attempts=attempts,
        http_backoff_seconds=backoff,
    )
