"""JST Macrohistory Database R6 reader/importer."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator
from xml.etree import ElementTree as ET
from zipfile import ZipFile

JST_R6_URL = "https://www.macrohistory.net/app/download/9834512569/JSTdatasetR6.xlsx"
JST_DATASET_VERSION = "R6"
JST_RELEASE_DATE = date(2022, 7, 1)
JST_SOURCE_KEY = "jst_macrohistory"
JST_LICENSE = "CC-BY-NC-SA-4.0"
JST_CRISIS_DEFINITION = (
    "crisisJST is 1 in the first year a country experiences a systemic banking "
    "crisis, 0 otherwise; systemic distress means major bank failures, banking "
    "panics, substantial losses, significant recapitalization, and/or "
    "significant government intervention."
)
_IDENTIFIER_COLUMNS = {"year", "country", "iso", "ifs"}
_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_CELL_RE = re.compile(r"^([A-Z]+)([0-9]+)$")


@dataclass(frozen=True)
class JstRow:
    year: int
    country: str
    iso3: str
    ifs_code: str | None
    values: dict[str, float]


def _column_index(ref: str) -> int:
    match = _CELL_RE.match(ref)
    if match is None:
        raise ValueError(f"invalid XLSX cell reference {ref!r}")
    idx = 0
    for char in match.group(1):
        idx = idx * 26 + ord(char) - 64
    return idx - 1


def _shared_strings(zf: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    out = []
    for item in root.findall("a:si", _NS):
        out.append("".join(t.text or "" for t in item.iter(f"{{{_NS['a']}}}t")))
    return out


def _cell_value(cell: ET.Element, shared: list[str]) -> str | None:
    value = cell.find("a:v", _NS)
    if cell.attrib.get("t") == "inlineStr":
        return "".join(t.text or "" for t in cell.iter(f"{{{_NS['a']}}}t"))
    if value is None or value.text is None:
        return None
    if cell.attrib.get("t") == "s":
        return shared[int(value.text)]
    return value.text


def iter_jst_rows(path: Path) -> Iterator[JstRow]:
    with ZipFile(path) as zf:
        shared = _shared_strings(zf)
        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        rows = sheet.findall("a:sheetData/a:row", _NS)
        parsed: list[list[str | None]] = []
        for row in rows:
            values: list[str | None] = []
            for cell in row.findall("a:c", _NS):
                idx = _column_index(cell.attrib["r"])
                while len(values) < idx:
                    values.append(None)
                values.append(_cell_value(cell, shared))
            parsed.append(values)
    if not parsed:
        raise ValueError(f"{path}: empty workbook")
    headers = [str(v).strip() if v is not None else "" for v in parsed[0]]
    if not {"year", "country", "iso"}.issubset(set(headers)):
        raise ValueError(f"{path}: missing required JST columns")
    for row in parsed[1:]:
        record = {headers[i]: row[i] for i in range(min(len(headers), len(row))) if headers[i]}
        if not record.get("year") or not record.get("iso"):
            continue
        values = {}
        for key, value in record.items():
            if key in _IDENTIFIER_COLUMNS or value in (None, ""):
                continue
            try:
                values[key] = float(value)
            except (TypeError, ValueError):
                continue
        yield JstRow(
            year=int(float(record["year"])), country=str(record["country"]),
            iso3=str(record["iso"]).upper(),
            ifs_code=str(record["ifs"]) if record.get("ifs") else None,
            values=values,
        )


def research_observation_payload(row: JstRow, variable: str, value: float, retrieved_at: datetime) -> dict:
    return {
        "source_key": JST_SOURCE_KEY,
        "dataset_version": JST_DATASET_VERSION,
        "entity_code": row.iso3,
        "entity_name": row.country,
        "entity_type": "country",
        "variable_code": variable,
        "variable_name": variable,
        "period_start": datetime(row.year, 1, 1, tzinfo=timezone.utc),
        "period_end": datetime(row.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "value": value,
        "unit": None,
        "vintage_date": JST_RELEASE_DATE,
        "release_date": datetime(2022, 7, 1, tzinfo=timezone.utc),
        "release_evidence_type": "dataset_release",
        "retrieved_at": retrieved_at,
        "source_version": "JST Macrohistory Database Release 6",
        "source_url": JST_R6_URL,
        "license_code": JST_LICENSE,
        "raw_payload": {"country": row.country, "ifs": row.ifs_code},
    }
