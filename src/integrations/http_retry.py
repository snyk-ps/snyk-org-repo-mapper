"""Retry helpers for transient HTTP and network failures."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def sleep_backoff_seconds(attempt: int, base_s: float) -> None:
    """Sleep with exponential backoff and small jitter.

    Args:
        attempt: Zero-based attempt index after the first failure.
        base_s: Base delay in seconds before exponential growth.
    """
    if base_s <= 0:
        return
    delay = base_s * (2**attempt)
    jitter = random.random() * 0.25 * base_s
    time.sleep(delay + jitter)


def run_with_retries(
    fn: Callable[[], T],
    *,
    max_attempts: int,
    base_backoff_s: float,
    retry: Callable[[BaseException], bool],
) -> T:
    """Run ``fn`` until success or non-retriable error / attempts exhausted.

    Args:
        fn: Callable to invoke (typically a closure over HTTP I/O).
        max_attempts: Minimum 1; total tries including the first.
        base_backoff_s: Base backoff for :func:`sleep_backoff_seconds`.
        retry: Return True if the exception should trigger another attempt.

    Returns:
        The return value of ``fn``.

    Raises:
        The last exception if attempts are exhausted or ``retry`` returns False.
    """
    if max_attempts < 1:
        msg = "max_attempts must be at least 1"
        raise ValueError(msg)
    last: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except BaseException as exc:
            last = exc
            if attempt >= max_attempts - 1 or not retry(exc):
                raise
            sleep_backoff_seconds(attempt, base_backoff_s)
    assert last is not None
    raise last
