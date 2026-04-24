"""Tests for Bitbucket REST helpers."""

from integrations.bitbucket import (
    default_branch_tuple,
    iter_paged_values,
)


def test_iter_paged_values_yields_dicts() -> None:
    payload = {"values": [{"k": 1}, "skip", {"k": 2}]}
    rows = list(iter_paged_values(payload))
    assert rows == [{"k": 1}, {"k": 2}]


def test_iter_paged_values_non_list() -> None:
    assert list(iter_paged_values({"values": None})) == []


def test_default_branch_tuple_from_string_ref() -> None:
    at, disp = default_branch_tuple({"defaultBranch": "refs/heads/main"})
    assert at == "refs/heads/main"
    assert disp == "main"


def test_default_branch_tuple_from_object() -> None:
    at, disp = default_branch_tuple(
        {"defaultBranch": {"id": "refs/heads/develop", "displayId": "develop"}}
    )
    assert at == "refs/heads/develop"
    assert disp == "develop"


def test_default_branch_tuple_missing_uses_main() -> None:
    at, disp = default_branch_tuple({})
    assert at == "refs/heads/main"
    assert disp == "main"
