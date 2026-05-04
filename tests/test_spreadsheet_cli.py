"""CLI tests for spreadsheet import."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from commands.spreadsheet_cli import main


def test_main_stdout_json_array_long_option(tmp_path, capsys) -> None:
    inp = tmp_path / "mini.xlsx"
    inp.write_bytes(_minimal_two_row_xlsx())
    rc = main(["--input", str(inp)])
    assert rc == 0
    out = capsys.readouterr().out
    rows = json.loads(out)
    assert isinstance(rows, list)
    bb = next(r for r in rows if r["repository_path"] == "MYPROJ/my-repo")
    assert bb["apm_code"] == "APM1"


def test_main_stdout_json_array_short_i(tmp_path, capsys) -> None:
    inp = tmp_path / "mini.xlsx"
    inp.write_bytes(_minimal_two_row_xlsx())
    rc = main(["-i", str(inp)])
    assert rc == 0
    rows = json.loads(capsys.readouterr().out)
    assert any(r["repository_path"] == "MYPROJ/my-repo" for r in rows)


def test_main_positional_input(tmp_path, capsys) -> None:
    inp = tmp_path / "mini.xlsx"
    inp.write_bytes(_minimal_two_row_xlsx())
    rc = main([str(inp)])
    assert rc == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) >= 1


def test_main_requires_input() -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def _minimal_two_row_xlsx() -> bytes:
    """Duplicate of minimal builder for one BB data row."""
    import io as io_mod
    import zipfile

    strings = ["APM1", "BB::MYPROJ::my-repo", "My Repo"]
    ss_items = "".join(f"<si><t>{s}</t></si>" for s in strings)
    sheet_rows = (
        '<row r="1">'
        '<c r="A1" t="s"><v>0</v></c>'
        '<c r="B1" t="s"><v>1</v></c>'
        '<c r="D1" t="s"><v>2</v></c>'
        "</row>"
    )
    ns_main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ns_rel_pkg = "http://schemas.openxmlformats.org/package/2006/relationships"
    ns_rel_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ns_ct = "http://schemas.openxmlformats.org/package/2006/content-types"
    buf = io_mod.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            f'<?xml version="1.0"?><Types xmlns="{ns_ct}">'
            '<Default Extension="rels" '
            'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            f'<?xml version="1.0"?><Relationships xmlns="{ns_rel_pkg}">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/workbook.xml",
            f'<?xml version="1.0"?><workbook xmlns="{ns_main}" xmlns:r="{ns_rel_r}">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            f'<?xml version="1.0"?><Relationships xmlns="{ns_rel_pkg}">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            f'<?xml version="1.0"?><worksheet xmlns="{ns_main}">'
            f"<sheetData>{sheet_rows}</sheetData></worksheet>",
        )
        z.writestr(
            "xl/sharedStrings.xml",
            f'<?xml version="1.0"?><sst xmlns="{ns_main}" count="3" uniqueCount="3">'
            f"{ss_items}</sst>",
        )
    return buf.getvalue()


def test_main_missing_input(tmp_path) -> None:
    missing = tmp_path / "nope.xlsx"
    rc = main(["--input", str(missing)])
    assert rc == 2


def test_main_writes_discovery_json(tmp_path: Path) -> None:
    inp = tmp_path / "mini.xlsx"
    inp.write_bytes(_minimal_two_row_xlsx())
    out = tmp_path / "discovery.json"
    rc = main(["-i", str(inp), "-o", str(out)])
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["version"] == 1
    assert doc["source"] == "spreadsheet"
    assert doc["checkpoint"] is None
    assert any(r["repository_path"] == "MYPROJ/my-repo" for r in doc["rows"])
