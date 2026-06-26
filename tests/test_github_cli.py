"""Tests for GitHub discovery CLI."""

from __future__ import annotations

from commands.github_cli import main, parse_org_list


def test_parse_org_list_trims_and_splits() -> None:
    assert parse_org_list(" acme , labs ") == ["acme", "labs"]


def test_parse_org_list_rejects_empty() -> None:
    try:
        parse_org_list(" , ")
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_github_cli_requires_orgs() -> None:
    assert main([]) == 2


def test_github_cli_requires_token(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert main(["--orgs", "acme"]) == 2
