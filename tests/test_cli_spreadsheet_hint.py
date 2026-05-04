"""Regression: Bitbucket discovery should hint when spreadsheet flags are used."""

from __future__ import annotations

import pytest

from commands.bitbucket_cli import main


def test_bitbucket_mapper_stderr_hints_when_using_spreadsheet_flags(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["-i", "foo.xlsx"])
    err = capsys.readouterr().err
    assert "discover spreadsheet" in err
