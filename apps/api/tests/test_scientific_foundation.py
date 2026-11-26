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
    PredictionLedgerEntry, TheoryRegistryEntry, ValidationQuestion,
)
from app.research.h01 import build_samples
from app.research.scientific_registry import THEORY_ENTRIES, TIMESCALES
from app.research.validation_questions import (
    IMPLEMENTATION_STATUSES, VALIDATION_QUESTIONS, VALIDATION_REGISTRY_VERSION, VALIDATION_STATUSES,
)


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


async def test_validation_question_registry_is_complete_and_versioned(client):
    async with session_module._sessionmaker() as session:
        rows = (await session.execute(select(ValidationQuestion).where(
            ValidationQuestion.registry_version == VALIDATION_REGISTRY_VERSION
        ))).scalars().all()
    assert len(rows) == 50
    assert [q.question_code for q in VALIDATION_QUESTIONS] == [f"Q{i:02d}" for i in range(1, 51)]
    assert {q.category for q in VALIDATION_QUESTIONS} == {
        "core_theory", "debt_money", "internal_conflict", "external_rivalry", "technology_shocks"
    }
    assert all(q.implementation_status in IMPLEMENTATION_STATUSES for q in VALIDATION_QUESTIONS)
    assert all(q.research_validation_status in VALIDATION_STATUSES for q in VALIDATION_QUESTIONS)
    assert all(q.original_question.endswith("?") for q in VALIDATION_QUESTIONS)
    assert all(len(q.content_checksum) == 64 for q in rows)


async def test_validation_question_immutability(client):
    async with session_module._sessionmaker() as session:
        row = (await session.execute(select(ValidationQuestion).where(
            ValidationQuestion.question_code == "Q01",
            ValidationQuestion.registry_version == VALIDATION_REGISTRY_VERSION,
        ))).scalar_one()
        row.short_title = "changed"
        with pytest.raises(ValueError):
            await session.flush()
        await session.rollback()


async def test_validation_question_api(client):
    response = await client.get("/api/research/foundation/validation/questions")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 50
    assert payload["questions"][0]["question_code"] == "Q01"
    response = await client.get("/api/research/foundation/validation/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["count"] == 50
    assert summary["by_category"]["debt_money"] == 15
    assert summary["by_category"]["technology_shocks"] == 5
    response = await client.get("/api/research/foundation/validation/questions/Q11")
    assert response.status_code == 200
    detail = response.json()
    assert detail["question"]["original_question"].endswith("?")
    assert detail["stable_url"] == "/research/validation?question=Q11"
    assert "H01" in detail["question"]["related_hypotheses"]


def test_cofer_and_bis_fx_parsers_preserve_currency_scope_and_skip_nan():
    from app.data_sources.research_panels import parse_bis_fx_turnover_csv, parse_cofer_csv

    now = datetime(2026, 11, 26, tzinfo=timezone.utc)
    cofer_csv = (
        "DATAFLOW,COUNTRY,INDICATOR,FXR_CURRENCY,TYPE_OF_TRANSFORMATION,FREQUENCY,TIME_PERIOD,OBS_VALUE,PUBLICATION_DATE\n"
        "IMF.STA:COFER,G001,AFXRA,CI_USD,SHRO_PT,Q,2026-Q2,56.7047,2026-09-30T13:00:00Z\n"
        "IMF.STA:COFER,G001,AFXRA,CI_EUR,SHRO_PT,Q,2026-Q2,20.6017,2026-09-30T13:00:00Z\n"
        "IMF.STA:COFER,G001,AFXRA,CI_INR,SHRO_PT,Q,2026-Q2,,2026-09-30T13:00:00Z\n"
    )
    rows = parse_cofer_csv(cofer_csv, annual_pre_1999_only=False, retrieved_at=now)
    by_ccy = {r["entity_code"]: r for r in rows}
    assert "USD" in by_ccy and by_ccy["USD"]["entity_type"] == "currency"
    assert "EUR" in by_ccy and by_ccy["EUR"]["entity_type"] == "currency_area"
    # Unreported INR must never be zero-imputed
    assert "INR" not in by_ccy

    fx_csv = (
        "DER_TYPE,DER_INSTR,DER_RISK,DER_REP_CTY,DER_SECTOR_CPY,DER_CPC,DER_CURR_LEG1,DER_CURR_LEG2,DER_EX_METHOD,DER_BASIS,TIME_PERIOD,OBS_VALUE\n"
        "U,A,B,5J,A,5J,TO1,TO1,3,C,2024,NaN\n"
        "U,A,B,5J,A,5J,INR,TO1,3,C,2024,NaN\n"
        "U,A,B,5J,A,5J,TO1,TO1,3,C,2025,9510000\n"
        "U,A,B,5J,A,5J,INR,TO1,3,C,2025,185445\n"
    )
    fx_rows = parse_bis_fx_turnover_csv(fx_csv, retrieved_at=now)
    # Non-survey 2024 NaN rows skipped; 2025 INR turnover + 200%-sum share preserved
    assert all(r["period_start"].year == 2025 for r in fx_rows)
    inr_share = next(
        r for r in fx_rows
        if r["entity_code"] == "INR" and r["variable_code"] == "FX_TURNOVER_SHARE_200PCT"
    )
    assert pytest.approx(inr_share["value"], rel=1e-4) == 1.95

