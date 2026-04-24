"""Tests for minimal ``.xlsx`` reading (first sheet, columns A/B/D)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from common.spreadsheet.xlsx import iter_first_sheet_abd


def _write_minimal_xlsx(buf: io.BytesIO, row_triples: list[tuple[str, str, str]]) -> None:
    """Build a minimal workbook with one sheet and shared strings.

    ``row_triples`` lists (A, B, D) string values per row starting at row 1.
    """
    strings: list[str] = []
    index: dict[str, int] = {}

    def si(s: str) -> int:
        if s not in index:
            index[s] = len(strings)
            strings.append(s)
        return index[s]

    row_xml_parts: list[str] = []
    for i, (a, b, d) in enumerate(row_triples, start=1):
        ia, ib, id_ = si(a), si(b), si(d)
        row_xml_parts.append(
            f'<row r="{i}">'
            f'<c r="A{i}" t="s"><v>{ia}</v></c>'
            f'<c r="B{i}" t="s"><v>{ib}</v></c>'
            f'<c r="D{i}" t="s"><v>{id_}</v></c>'
            f"</row>"
        )
    sheet_rows = "".join(row_xml_parts)
    ss_items = "".join(f"<si><t>{_xml_escape(s)}</t></si>" for s in strings)
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<sst xmlns="{_NS_MAIN}" count="{len(strings)}" uniqueCount="{len(strings)}">'
        f"{ss_items}</sst>"
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<worksheet xmlns="{_NS_MAIN}">'
        f"<sheetData>{sheet_rows}</sheetData>"
        "</worksheet>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<workbook xmlns="{_NS_MAIN}" xmlns:r="{_REL_R}">'
        "<sheets>"
        '<sheet name="Sheet1" sheetId="1" r:id="rId1"/>'
        "</sheets></workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Relationships xmlns="{_REL_PKG}">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Relationships xmlns="{_REL_PKG}">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Types xmlns="{_CT}">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        z.writestr("xl/sharedStrings.xml", shared_xml)


_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
_REL_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def test_iter_first_sheet_abd_minimal_roundtrip(tmp_path: Path) -> None:
    buf = io.BytesIO()
    _write_minimal_xlsx(
        buf,
        [
            ("APM1", "BB::MYPROJ::my-repo", "My Repo"),
            ("APM2", "PG::OTHER::x", "ignored"),
        ],
    )
    path = tmp_path / "minimal.xlsx"
    path.write_bytes(buf.getvalue())
    rows = list(iter_first_sheet_abd(path))
    assert rows == [
        (1, "APM1", "BB::MYPROJ::my-repo", "My Repo"),
        (2, "APM2", "PG::OTHER::x", "ignored"),
    ]


def test_iter_first_sheet_abd_rejects_non_xlsx(tmp_path: Path) -> None:
    p = tmp_path / "not.txt"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match=".xlsx"):
        list(iter_first_sheet_abd(p))
