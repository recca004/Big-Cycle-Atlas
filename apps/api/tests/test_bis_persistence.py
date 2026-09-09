"""Offline Sprint 4.4–4.7 regression tests: BIS canonical seeding, quarterly
persistence, ingestion happy path, and source filtering.

Synthetic DTOs and httpx.MockTransport only — no live BIS calls.
"""
from datetime import date, datetime, timezone

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.data_sources.bis import BISAdapter
from app.data_sources.base import ObservationDTO
from app.db import session as session_module
from app.db.seed import DEFAULT_DATA_FILE, seed
from app.models import (
    DataSource,
    Indicator,
    IngestionRun,
    IngestionRunStatus,
    Observation,
    SourceSeries,
)
from app.services.ingestion_service import run_ingestion
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)

GAP_CODE = "WS_CREDIT_GAP/Q.{cc}.P.A.C"
DSR_CODE = "WS_DSR/Q.{cc}.P"

GAP_HEADER = (
    "FREQ,BORROWERS_CTY,TC_BORROWERS,TC_LENDERS,CG_DTYPE,COLLECTION,"
    "DECIMALS,UNIT_MEASURE,UNIT_MULT,TIME_FORMAT,TITLE_TS,TIME_PERIOD,"
    "OBS_VALUE,OBS_STATUS,OBS_CONF,OBS_PRE_BREAK"
)


def _gap_row(iso2: str, time_period: str, value: str) -> str:
    return f"Q,{iso2},P,A,C,E,1,770,0,,Test title,{time_period},{value},A,F,"


# --- Part 1: canonical indicators seeded ------------------------------------


async def test_approved_bis_indicators_seeded(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        codes = dict(
            (await session.execute(select(Indicator.code, Indicator.id))).all()
        )
        assert len(codes) == 25
        for code in ("CREDIT_TO_GDP_GAP", "DEBT_SERVICE_RATIO"):
            assert code in codes
        gap = (await session.execute(
            select(Indicator).where(Indicator.code == "CREDIT_TO_GDP_GAP")
        )).scalar_one()
        assert gap.name == "Credit-to-GDP gap (private non-financial sector)"
        assert gap.unit == "percentage of GDP"
        assert gap.frequency == "quarterly"
        assert gap.category == "Debt & Credit"
        dsr = (await session.execute(
            select(Indicator).where(Indicator.code == "DEBT_SERVICE_RATIO")
        )).scalar_one()
        assert dsr.unit == "per cent"
        assert dsr.frequency == "quarterly"


async def test_bis_source_series_seeded_idempotently(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        bis_source = (await session.execute(
            select(DataSource).where(DataSource.key == "bis")
        )).scalar_one()
        series = (await session.execute(
            select(SourceSeries).where(SourceSeries.data_source_id == bis_source.id)
        )).scalars().all()
        assert {s.external_code for s in series} == {GAP_CODE, DSR_CODE}
        # country-independent identity: the {cc} placeholder must survive seeding
        assert all("{cc}" in s.external_code for s in series)

    # re-running the seed updates, never duplicates
    await seed(DEFAULT_DATA_FILE)
    async with sessionmaker() as session:
        bis_source = (await session.execute(
            select(DataSource).where(DataSource.key == "bis")
        )).scalar_one()
        count = (await session.execute(
            select(func.count()).select_from(SourceSeries)
            .where(SourceSeries.data_source_id == bis_source.id)
        )).scalar_one()
        assert count == 2


# --- Part 3: quarterly persistence ------------------------------------------


def _bis_dto(year: int, quarter: int, value: float) -> ObservationDTO:
    month = 1 + (quarter - 1) * 3
    return ObservationDTO(
        country_iso3="CHE",
        indicator_code="CREDIT_TO_GDP_GAP",
        external_series_code=GAP_CODE,
        period=year,
        value=value,
        unit="percentage of GDP",
        source_key="bis",
        observation_date=date(year, month, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"TIME_PERIOD": f"{year}-Q{quarter}", "OBS_VALUE": value},
    )


@pytest.mark.asyncio
async def test_quarters_persist_as_distinct_observations(client):
    sessionmaker = session_module._sessionmaker
    dtos = [_bis_dto(2025, q, -17.0 - q) for q in (1, 2, 3, 4)]
    async with sessionmaker() as session:
        result = await persist_observations(session, dtos)
        assert (result.received, result.inserted, result.skipped) == (4, 4, 0)

        rows = (await session.execute(
            select(Observation).order_by(Observation.period_start)
        )).scalars().all()
        assert [r.period_start.date() for r in rows] == [
            date(2025, 1, 1),
            date(2025, 4, 1),
            date(2025, 7, 1),
            date(2025, 10, 1),
        ]
        assert all(r.period_start.date().day == 1 for r in rows)
        assert [r.value for r in rows] == [-18.0, -19.0, -20.0, -21.0]


@pytest.mark.asyncio
async def test_quarterly_reimport_skips_duplicates(client):
    sessionmaker = session_module._sessionmaker
    dtos = [_bis_dto(2025, q, -17.0 - q) for q in (1, 2, 3, 4)]
    async with sessionmaker() as session:
        first = await persist_observations(session, dtos)
        assert first.inserted == 4
        await session.commit()

    async with sessionmaker() as session:
        second = await persist_observations(session, dtos)
        assert (second.inserted, second.skipped, second.revised) == (0, 4, 0)
        count = (await session.execute(
            select(func.count()).select_from(Observation)
        )).scalar_one()
        assert count == 4


# --- Part 4/15: BIS run_ingestion happy path --------------------------------


@pytest.mark.asyncio
async def test_bis_run_ingestion_happy_path(client):
    body = "\n".join(
        [
            GAP_HEADER,
            _gap_row("CH", "2025-Q1", "-15.76"),
            _gap_row("CH", "2025-Q2", "-19.21"),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert "/data/WS_CREDIT_GAP/Q.CH.P.A.C/all" in str(request.url)
        return httpx.Response(200, text=body)

    adapter = BISAdapter(
        transport=httpx.MockTransport(handler),
        retrieved_at=RETRIEVED_AT.isoformat(),
    )
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        outcome = await run_ingestion(
            session, adapter, "CHE", GAP_CODE, start_year=2025, end_year=2025
        )
        assert outcome.error is None
        assert outcome.run.status.value == "success"
        assert outcome.persistence.received == 2
        assert outcome.persistence.inserted == 2
        run = outcome.run
        await session.commit()

    async with sessionmaker() as session:
        recorded = (await session.execute(
            select(IngestionRun).where(IngestionRun.id == run.id)
        )).scalar_one()
        assert recorded.status == IngestionRunStatus.success
        assert recorded.rows_inserted == 2
        assert recorded.run_metadata["external_series_code"] == GAP_CODE

        rows = (await session.execute(
            select(Observation).options(selectinload(Observation.source_series))
        )).scalars().all()
        assert len(rows) == 2
        assert all(row.source_series.external_code == GAP_CODE for row in rows)
        assert {row.period_start.date() for row in rows} == {
            date(2025, 1, 1),
            date(2025, 4, 1),
        }


# --- Part 8/15: source filtering --------------------------------------------


async def _seed_wb_and_bis_observations():
    """CHE with WB GDP_GROWTH (annual) + BIS credit gap (quarterly)."""
    sessionmaker = session_module._sessionmaker
    wb = ObservationDTO(
        country_iso3="CHE",
        indicator_code="GDP_GROWTH",
        external_series_code="NY.GDP.MKTP.KD.ZG",
        period=2025,
        value=1.3,
        unit="percent",
        source_key="world_bank",
        observation_date=date(2025, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"date": "2025"},
    )
    bis_dtos = [_bis_dto(2025, q, -17.0 - q) for q in (1, 2, 3, 4)]
    usa_bis = _bis_dto(2025, 4, -11.5)
    usa_bis.country_iso3 = "USA"
    async with sessionmaker() as session:
        await persist_observations(session, [wb, *bis_dtos, usa_bis])
        await session.commit()


@pytest.mark.asyncio
async def test_source_filter_returns_only_requested_source(client):
    await _seed_wb_and_bis_observations()
    response = await client.get("/api/countries/CHE/observations?source=bis&limit=1000")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 4
    assert all(item["source_key"] == "bis" for item in payload["items"])
    assert all(item["indicator_code"] == "CREDIT_TO_GDP_GAP" for item in payload["items"])
    # no World Bank rows leaked
    assert not any(item["indicator_code"] == "GDP_GROWTH" for item in payload["items"])

    wb_response = await client.get(
        "/api/countries/CHE/observations?source=world_bank&limit=1000"
    )
    wb_payload = wb_response.json()
    assert wb_payload["count"] == 1
    assert wb_payload["items"][0]["indicator_code"] == "GDP_GROWTH"
    assert wb_payload["items"][0]["source_key"] == "world_bank"


@pytest.mark.asyncio
async def test_country_and_source_isolation(client):
    await _seed_wb_and_bis_observations()
    # USA's BIS rows must never appear in the CHE response
    response = await client.get("/api/countries/CHE/observations?source=bis&limit=1000")
    values = [item["value"] for item in response.json()["items"]]
    assert -11.5 not in values  # USA's Q4 value must never leak into CHE
    assert len(values) == 4


@pytest.mark.asyncio
async def test_country_indicator_and_source_combine_safely(client):
    await _seed_wb_and_bis_observations()
    response = await client.get(
        "/api/countries/CHE/observations?source=bis&indicator=CREDIT_TO_GDP_GAP&start=2025&end=2025&limit=1000"
    )
    payload = response.json()
    assert payload["count"] == 4
    assert all(item["source_key"] == "bis" for item in payload["items"])

    year_response = await client.get(
        "/api/countries/CHE/observations?source=bis&start=2025&end=2025-06-30&limit=1000"
    )
    year_payload = year_response.json()
    assert year_payload["count"] == 2  # Q1 and Q2 only


@pytest.mark.asyncio
async def test_latest_vintage_behavior_with_bis(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        await persist_observations(session, [_bis_dto(2025, 4, -17.04)])
        await session.commit()
    async with sessionmaker() as session:
        result = await persist_observations(session, [_bis_dto(2025, 4, -18.5)])
        assert result.revised == 1
        await session.commit()

    response = await client.get(
        "/api/countries/CHE/observations?source=bis&start=2025&end=2025&limit=1000"
    )
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["value"] == -18.5  # latest vintage, not the original
    assert items[0]["vintage_number"] == 2