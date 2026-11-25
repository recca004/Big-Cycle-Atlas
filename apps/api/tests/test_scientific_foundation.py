import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db import session as session_module
from app.data_sources.alfred import AlfredAdapter
from app.data_sources.base import DataSourceCredentialError
from app.data_sources.jst_macrohistory import iter_jst_rows
from app.models import (
    DatasetRightsRegistry, EvidenceStatusEntry, HypothesisProtocol,
    PredictionLedgerEntry, TheoryRegistryEntry,
)
from app.research.h01 import build_samples
from app.research.scientific_registry import THEORY_ENTRIES, TIMESCALES


def _tiny_xlsx(path: Path) -> Path:
    sheet = """<?xml version='1.0' encoding='UTF-8'?>
<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'><sheetData>
<row r='1'><c r='A1' t='inlineStr'><is><t>year</t></is></c><c r='B1' t='inlineStr'><is><t>country</t></is></c><c r='C1' t='inlineStr'><is><t>iso</t></is></c><c r='D1' t='inlineStr'><is><t>ifs</t></is></c><c r='E1' t='inlineStr'><is><t>pop</t></is></c><c r='F1' t='inlineStr'><is><t>rgdpmad</t></is></c><c r='G1' t='inlineStr'><is><t>crisisJST</t></is></c></row>
<row r='2'><c r='A2'><v>1900</v></c><c r='B2' t='inlineStr'><is><t>Testland</t></is></c><c r='C2' t='inlineStr'><is><t>TST</t></is></c><c r='D2'><v>999</v></c><c r='E2'><v>42.5</v></c><c r='F2'><v>10</v></c><c r='G2'><v>1</v></c></row>
</sheetData></worksheet>"""
    workbook = """<workbook xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main' xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'><sheets><sheet name='Sheet1' sheetId='1' r:id='rId1'/></sheets></workbook>"""
    rels = """<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet' Target='worksheets/sheet1.xml'/></Relationships>"""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'><Default Extension='xml' ContentType='application/xml'/></Types>")
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    return path


async def test_scientific_registry_seed(client):
    async with session_module._sessionmaker() as session:
        theories = (await session.execute(select(TheoryRegistryEntry))).scalars().all()
        protocols = (await session.execute(select(HypothesisProtocol))).scalars().all()
        rights = (await session.execute(select(DatasetRightsRegistry))).scalars().all()
        evidence = (await session.execute(select(EvidenceStatusEntry))).scalars().all()
    assert len(theories) == len(THEORY_ENTRIES)
    assert {p.hypothesis_code for p in protocols} == {"H01", "H02", "H03", "H04"}
    assert any(r.source_key == "jst_macrohistory" and r.share_alike for r in rights)
    assert any(e.evidence_status == "unavailable_research_result" for e in evidence)


async def test_theory_registry_distinguishes_atlas_framework(client):
    stage = next(e for e in THEORY_ENTRIES if e.theory_code == "atlas_eight_stages")
    duration = next(e for e in THEORY_ENTRIES if e.theory_code == "cycle_duration_approximately_75_years")
    assert stage.atlas_operational is True
    assert "Not represented as the author's original" in stage.framework_differences
    assert duration.testable_status == "untestable_with_current_evidence"
    assert "does not use it to advance stages" in duration.atlas_interpretation
    assert {t["timescale_code"] for t in TIMESCALES} == {
        "short_economic_financial", "medium_institutional_financial", "long_historical_big_cycle"
    }


def test_jst_xlsx_reader(tmp_path):
    path = _tiny_xlsx(tmp_path / "jst.xlsx")
    rows = list(iter_jst_rows(path))
    assert len(rows) == 1
    assert rows[0].year == 1900
    assert rows[0].iso3 == "TST"
    assert rows[0].values == {"pop": 42.5, "rgdpmad": 10.0, "crisisJST": 1.0}


def test_h01_samples_respect_cutoff_and_unknown_coverage():
    panel = {
        ("AAA", 1996): {"debtgdp": 1.0},
        ("AAA", 2001): {"debtgdp": 2.0},
    }
    coverage = {("AAA", 2002)}
    events = {("AAA", 2002)}
    samples = build_samples(panel, coverage, events, horizon_years=1)
    assert len(samples) == 1
    assert samples[0].forecast_origin_year == 2001
    assert samples[0].outcome is True
    assert build_samples(panel, set(), set(), 1) == []


async def test_prediction_ledger_is_append_only(client):
    async with session_module._sessionmaker() as session:
        row = PredictionLedgerEntry(
            prediction_key="test:immutable", hypothesis_code="H01", protocol_version="H01-P1.0",
            model_id="m", model_version="v", entity_code="AAA",
            forecast_origin=datetime(2000, 12, 31, tzinfo=timezone.utc),
            info_cutoff=datetime(2000, 12, 31, tzinfo=timezone.utc),
            horizon_end=datetime(2001, 12, 31, tzinfo=timezone.utc),
            target_outcome="banking_crisis_onset", data_coverage={},
            input_vintage_ids={}, dataset_versions={}, recorded_at=datetime.now(timezone.utc),
            content_checksum="x",
        )
        session.add(row)
        await session.flush()
        row.evaluation_status = "evaluated"
        with pytest.raises(ValueError):
            await session.flush()
        await session.rollback()

        row = PredictionLedgerEntry(
            prediction_key="test:immutable-delete", hypothesis_code="H01",
            protocol_version="H01-P1.0", model_id="m", model_version="v",
            entity_code="AAA",
            forecast_origin=datetime(2000, 12, 31, tzinfo=timezone.utc),
            info_cutoff=datetime(2000, 12, 31, tzinfo=timezone.utc),
            horizon_end=datetime(2001, 12, 31, tzinfo=timezone.utc),
            target_outcome="banking_crisis_onset", data_coverage={},
            input_vintage_ids={}, dataset_versions={},
            recorded_at=datetime.now(timezone.utc), content_checksum="x",
        )
        session.add(row)
        await session.flush()
        await session.delete(row)
        with pytest.raises(ValueError):
            await session.flush()
        await session.rollback()


async def test_foundation_api_and_alfred_blocker(client):
    response = await client.get("/api/research/foundation/theory-registry")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == len(THEORY_ENTRIES)
    assert any(e["testable_status"] == "untestable_with_current_evidence" for e in payload["entries"])
    response = await client.get("/api/research/foundation/hypotheses")
    assert response.status_code == 200
    assert any(p["hypothesis_code"] == "H01" for p in response.json()["protocols"])
    with pytest.raises(DataSourceCredentialError):
        await AlfredAdapter(api_key=None).vintage_dates("GDP")
