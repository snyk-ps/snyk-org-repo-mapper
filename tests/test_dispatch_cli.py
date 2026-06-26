"""Tests for commands.dispatch main router."""

from __future__ import annotations

from commands.dispatch import main


def test_dispatch_help_returns_zero() -> None:
    assert main(["-h"]) == 0


def test_dispatch_discover_help() -> None:
    assert main(["discover", "-h"]) == 0


def test_dispatch_discover_github_help() -> None:
    assert main(["discover", "github", "-h"]) == 0


def test_dispatch_unknown_command() -> None:
    assert main(["unknown-cmd"]) == 2


def test_dispatch_unknown_discover_target() -> None:
    assert main(["discover", "gitlab"]) == 2
