"""Tests for HTTP retry helpers."""

import pytest

from integrations.http_retry import (
    run_with_retries,
    sleep_backoff_seconds,
)


def test_run_with_retries_succeeds_first_call() -> None:
    assert run_with_retries(lambda: 42, max_attempts=3, base_backoff_s=0.01, retry=lambda e: False) == 42


def test_run_with_retries_retries_then_succeeds() -> None:
    n = {"i": 0}

    def flaky() -> str:
        n["i"] += 1
        if n["i"] < 2:
            raise OSError("transient")
        return "ok"

    assert (
        run_with_retries(
            flaky,
            max_attempts=5,
            base_backoff_s=0.01,
            retry=lambda e: isinstance(e, OSError),
        )
        == "ok"
    )


def test_run_with_retries_exhausts() -> None:
    def always_fail() -> None:
        raise ValueError("nope")

    with pytest.raises(ValueError, match="nope"):
        run_with_retries(
            always_fail,
            max_attempts=2,
            base_backoff_s=0.01,
            retry=lambda e: isinstance(e, ValueError),
        )


def test_run_with_retries_requires_positive_attempts() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        run_with_retries(lambda: 1, max_attempts=0, base_backoff_s=0.01, retry=lambda e: True)


def test_sleep_backoff_seconds_noop_for_non_positive_base() -> None:
    sleep_backoff_seconds(3, 0.0)
