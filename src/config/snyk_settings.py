"""Snyk API settings for import enrichment (Stage 3)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


DEFAULT_SNYK_API_ORIGIN = "https://api.snyk.io"
DEFAULT_SNYK_API_VERSION = "2024-10-15"

IntegrationsApi = Literal["v1", "rest"]


@dataclass(frozen=True)
class SnykSettings:
    """Runtime settings for Snyk HTTP calls (REST group orgs; v1 or REST integrations)."""

    token: str
    group_id: str
    api_origin: str
    rest_root: str
    v1_root: str
    integrations_api: IntegrationsApi
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


def _parse_integrations_api(raw: str | None) -> IntegrationsApi:
    if raw is None or not raw.strip():
        return "v1"
    value = raw.strip().lower()
    if value == "v1":
        return "v1"
    if value == "rest":
        return "rest"
    msg = "SNYK_INTEGRATIONS_API must be 'v1' or 'rest'"
    raise ValueError(msg)


def _derive_api_origin() -> str:
    """Resolve API origin (no /rest or /v1 suffix)."""
    explicit = os.environ.get("SNYK_API", "").strip()
    if explicit:
        origin = explicit.rstrip("/")
        while origin.endswith("/rest"):
            origin = origin[: -len("/rest")].rstrip("/")
        while origin.endswith("/v1"):
            origin = origin[: -len("/v1")].rstrip("/")
        return origin
    legacy = os.environ.get("SNYK_API_BASE", "").strip()
    if legacy:
        leg = legacy.rstrip("/")
        if leg.endswith("/rest"):
            leg = leg[: -len("/rest")]
        return leg.rstrip("/")
    return DEFAULT_SNYK_API_ORIGIN.rstrip("/")


def load_snyk_settings() -> SnykSettings:
    """Load settings from the environment (after optional ``load_dotenv_file``)."""
    token = os.environ.get("SNYK_TOKEN", "").strip()
    group_id = os.environ.get("SNYK_GROUP_ID", "").strip()
    api_origin = _derive_api_origin()
    rest_root = f"{api_origin}/rest"
    v1_root = f"{api_origin}/v1"
    integrations_api = _parse_integrations_api(os.environ.get("SNYK_INTEGRATIONS_API"))
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
        api_origin=api_origin,
        rest_root=rest_root,
        v1_root=v1_root,
        integrations_api=integrations_api,
        api_version=api_version,
        http_max_attempts=attempts,
        http_backoff_seconds=backoff,
    )


@dataclass(frozen=True)
class BrokerSettings:
    """Runtime settings for Universal Broker plan/apply (REST under ``/rest``)."""

    token: str
    api_origin: str
    rest_root: str
    api_version: str
    tenant_id: str
    install_id: str
    group_id: str | None
    http_max_attempts: int
    http_backoff_seconds: float


def load_broker_settings(
    *,
    tenant_id: str | None = None,
    install_id: str | None = None,
) -> BrokerSettings:
    """Load Broker settings from env and optional CLI overrides."""
    token = os.environ.get("SNYK_TOKEN", "").strip()
    api_origin = _derive_api_origin()
    rest_root = f"{api_origin}/rest"
    api_version = os.environ.get("SNYK_API_VERSION", "").strip()
    if not api_version:
        api_version = DEFAULT_SNYK_API_VERSION
    tid = (tenant_id or os.environ.get("SNYK_TENANT_ID", "")).strip()
    iid = (install_id or os.environ.get("SNYK_BROKER_INSTALL_ID", "")).strip()
    group_raw = os.environ.get("SNYK_GROUP_ID", "").strip()
    group_id = group_raw if group_raw else None
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
    if not tid:
        msg = "tenant_id is required (SNYK_TENANT_ID or --tenant-id)"
        raise ValueError(msg)
    if not iid:
        msg = "install_id is required (SNYK_BROKER_INSTALL_ID or --install-id)"
        raise ValueError(msg)
    return BrokerSettings(
        token=token,
        api_origin=api_origin,
        rest_root=rest_root,
        api_version=api_version,
        tenant_id=tid,
        install_id=iid,
        group_id=group_id,
        http_max_attempts=attempts,
        http_backoff_seconds=backoff,
    )
