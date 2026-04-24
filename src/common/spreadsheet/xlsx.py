"""Read column values from the first worksheet of an ``.xlsx`` file (Office Open XML).

Only the subset needed for spreadsheet import is implemented: shared strings,
cached values, and the first worksheet in workbook order.
"""

from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path


NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS_MAIN = f"{{{NS_MAIN}}}"
_NS_REL_PKG = f"{{{NS_REL_PKG}}}"


def _split_cell_ref(ref: str) -> tuple[str, int]:
    """Split ``A1``-style reference into column letters and 1-based row index."""
    col = "".join(c for c in ref if c.isalpha())
    row_s = "".join(c for c in ref if c.isdigit())
    if not col or not row_s:
        msg = f"Invalid cell reference: {ref!r}"
        raise ValueError(msg)
    return col.upper(), int(row_s)


def _parse_shared_strings(root: ET.Element) -> list[str]:
    """Build shared string table from ``sharedStrings.xml`` root."""
    strings: list[str] = []
    for si in root.findall(f"{_NS_MAIN}si"):
        parts: list[str] = []
        for t in si.findall(f".//{_NS_MAIN}t"):
            if t.text:
                parts.append(t.text)
            if t.tail:
                parts.append(t.tail)
        strings.append("".join(parts))
    return strings


def _cell_display(
    c: ET.Element,
    shared_strings: list[str],
) -> str | None:
    """Resolve a ``<c>`` element to a text or numeric string."""
    v_el = c.find(f"{_NS_MAIN}v")
    if v_el is None or v_el.text is None:
        is_el = c.find(f"{_NS_MAIN}is")
        if is_el is not None:
            parts: list[str] = []
            for t in is_el.findall(f".//{_NS_MAIN}t"):
                if t.text:
                    parts.append(t.text)
            return "".join(parts) if parts else None
        return None
    raw = v_el.text
    if c.get("t") == "s":
        idx = int(raw)
        if idx < 0 or idx >= len(shared_strings):
            msg = f"Shared string index out of range: {idx}"
            raise ValueError(msg)
        return shared_strings[idx]
    return raw


def _first_worksheet_part_path(z: zipfile.ZipFile) -> str:
    """Return zip path (e.g. ``xl/worksheets/sheet1.xml``) for the first sheet."""
    wb_data = z.read("xl/workbook.xml")
    wb_root = ET.fromstring(wb_data)
    first_rid: str | None = None
    for sheet in wb_root.iter():
        if sheet.tag != f"{_NS_MAIN}sheet":
            continue
        first_rid = sheet.get(f"{{{NS_REL}}}id")
        break
    if first_rid is None:
        msg = "Workbook has no worksheets"
        raise ValueError(msg)
    rels_data = z.read("xl/_rels/workbook.xml.rels")
    rels_root = ET.fromstring(rels_data)
    target: str | None = None
    for rel in rels_root.findall(f"{_NS_REL_PKG}Relationship"):
        if rel.get("Id") == first_rid:
            target = rel.get("Target")
            break
    if not target:
        msg = "Could not resolve first worksheet path"
        raise ValueError(msg)
    target = target.replace("\\", "/")
    if target.startswith("/"):
        target = target.lstrip("/")
    if not target.startswith("xl/"):
        target = "xl/" + target
    return target


def _sheet_max_row(sheet_root: ET.Element) -> int:
    """Infer last row index from ``dimension`` and cell references."""
    max_row = 0
    dim = sheet_root.find(f"{_NS_MAIN}dimension")
    if dim is not None:
        ref = dim.get("ref")
        if ref and ":" in ref:
            _, end = ref.split(":", 1)
            _, max_row = _split_cell_ref(end)
        elif ref:
            _, max_row = _split_cell_ref(ref)
    for c in sheet_root.findall(f".//{_NS_MAIN}c"):
        r = c.get("r")
        if not r:
            continue
        _, row = _split_cell_ref(r)
        max_row = max(max_row, row)
    return max_row


def iter_first_sheet_abd(path: Path) -> Iterator[tuple[int, str | None, str | None, str | None]]:
    """Yield ``(row_index_1based, col_a, col_b, col_d)`` for each row of the first sheet.

    Rows are emitted from 1 through the maximum row seen in columns A/B/D or the
    sheet dimension. Missing cells appear as ``None``.
    """
    path = Path(path)
    if path.suffix.lower() != ".xlsx":
        msg = f"Expected .xlsx file, got {path.suffix!r}"
        raise ValueError(msg)
    with zipfile.ZipFile(path) as z:
        strings: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss_root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            strings = _parse_shared_strings(ss_root)
        sheet_path = _first_worksheet_part_path(z)
        sheet_root = ET.fromstring(z.read(sheet_path))
        grid: dict[tuple[int, str], str] = {}
        for c in sheet_root.findall(f".//{_NS_MAIN}c"):
            ref = c.get("r")
            if not ref:
                continue
            col_letters, row_idx = _split_cell_ref(ref)
            if col_letters not in {"A", "B", "D"}:
                continue
            val = _cell_display(c, strings)
            grid[row_idx, col_letters] = val
        max_row = _sheet_max_row(sheet_root)
        if max_row < 1:
            return
        for row_idx in range(1, max_row + 1):
            a = grid.get((row_idx, "A"))
            b = grid.get((row_idx, "B"))
            d = grid.get((row_idx, "D"))
            yield row_idx, a, b, d
