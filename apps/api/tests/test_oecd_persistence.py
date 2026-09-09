"""Offline Sprint 4.11–4.14 regression tests: OECD canonical seeding, annual +
quarterly persistence, ingestion happy path, no-data handling, and source
filtering.

Synthetic DTOs and httpx.MockTransport only — no live OECD calls.
"""
from datetime import date, datetime, timezone

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.data_sources.base import ObservationDTO
from app.data_sources.oecd import OECDAdapter
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

PROD_CODE = "DSD_PDB@DF_PDB/{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP"
ULC_CODE = "DSD_PDB@DF_PDB_ULC_Q/{cc}.Q.ULCE._T.PA.V.GY.S.NC"

PROD_HEADER = (
    "REF_AREA,FREQ,MEASURE,ACTIVITY,UNIT_MEASURE,PRICE_BASE,TRANSFORMATION,"
    "ASSET_CODE,CONVERSION_TYPE,TIME_PERIOD,OBS_VALUE,OBS_STATUS,UNIT_MULT,"
    "DECIMALS,BASE_PER"
)
ULC_HEADER = (
    "REF_AREA,FREQ,MEASURE,ACTIVITY,UNIT_MEASURE,PRICE_BASE,TRANSFORMATION,"
    "ADJUSTMENT,CONVERSION_TYPE,TIME_PERIOD,OBS_VALUE,OBS_STATUS,UNIT_MULT,"
    "DECIMALS"
)


def _prod_row(ref_area: str, time_period: str, value: str) -> str:
    return (
        f"{ref_area},A,GDPHRS,_T,USD_PPP_H,LR,N,_Z,PPP,{time_period},"
        f"{value},A,0,2,"
    )


def _ulc_row(ref_area: str, time_period: str, value: str) -> str:
    return f"{ref_area},Q,ULCE,_T,PA,V,GY,S,NC,{time_period},{value},A,0,2"


# --- Parts 1–2: canonical indicators + SourceSeries seeded --------------------


async def test_approved_oecd_indicators_seeded(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        codes = dict(
            (await session.execute(select(Indicator.code, Indicator.id))).all()
        )
        assert len(codes) == 25
        prod = (await session.execute(
            select(Indicator).where(Indicator.code == "LABOUR_PRODUCTIVITY_PER_HOUR")
        )).scalar_one()
        assert prod.name == "Labour productivity — GDP per hour worked"
        assert prod.category == "Productivity"
        assert prod.unit == "US dollars per hour, PPP converted"
        assert prod.frequency == "annual"
        assert prod.strength_direction == "positive"
        ulc = (await session.execute(
            select(Indicator).where(Indicator.code == "UNIT_LABOUR_COST_GROWTH")
        )).scalar_one()
        assert ulc.name == "Unit labour cost growth"
        assert ulc.category == "Cost Competitiveness"
        assert ulc.unit == "percent per annum"
        assert ulc.frequency == "quarterly"
        assert ulc.strength_direction == "contextual"


async def test_oecd_source_series_seeded_idempotently(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        oecd_source = (await session.execute(
            select(DataSource).where(DataSource.key == "oecd")
        )).scalar_one()
        series = (await session.execute(
            select(SourceSeries).where(SourceSeries.data_source_id == oecd_source.id)
        )).scalars().all()
        assert {s.external_code for s in series} == {PROD_CODE, ULC_CODE}
        # country-independent identity: the {cc} placeholder must survive seeding
        assert all("{cc}" in s.external_code for s in series)
        total = (await session.execute(
            select(func.count()).select_from(SourceSeries)
        )).scalar_one()
        assert total == 19  # 15 WB + 2 BIS + 2 OECD

    # re-running the seed updates, never duplicates
    await seed(DEFAULT_DATA_FILE)
    async with sessionmaker() as session:
        oecd_source = (await session.execute(
            select(DataSource).where(DataSource.key == "oecd")
        )).scalar_one()
        count = (await session.execute(
            select(func.count()).select_from(SourceSeries)
            .where(SourceSeries.data_source_id == oecd_source.id)
        )).scalar_one()
        assert count == 2
        total = (await session.execute(
            select(func.count()).select_from(SourceSeries)
        )).scalar_one()
        assert total == 19


# --- Parts 4–5: annual + quarterly persistence --------------------------------


def _prod_dto(country: str, year: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=country,
        indicator_code="LABOUR_PRODUCTIVITY_PER_HOUR",
        external_series_code=PROD_CODE,
        period=year,
        value=value,
        unit="US dollars per hour, PPP converted",
        source_key="oecd",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"TIME_PERIOD": str(year), "OBS_VALUE": value},
    )


def _ulc_dto(country: str, year: int, quarter: int, value: float) -> ObservationDTO:
    month = 1 + (quarter - 1) * 3
    return ObservationDTO(
        country_iso3=country,
        indicator_code="UNIT_LABOUR_COST_GROWTH",
        external_series_code=ULC_CODE,
        period=year,
        value=value,
        unit="percent per annum",
        source_key="oecd",
        observation_date=date(year, month, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"TIME_PERIOD": f"{year}-Q{quarter}", "OBS_VALUE": value},
    )


@pytest.mark.asyncio
async def test_annual_productivity_persists_one_row_per_year(client):
    sessionmaker = session_module._sessionmaker
    dtos = [_prod_dto("CHE", year, 80.0 + year - 2019) for year in (2019, 2024, 2025)]
    async with sessionmaker() as session:
        result = await persist_observations(session, dtos)
        assert (result.received, result.inserted, result.skipped) == (3, 3, 0)
        rows = (await session.execute(
            select(Observation).order_by(Observation.period_start)
        )).scalars().all()
        assert [r.period_start.date() for r in rows] == [
            date(2019, 1, 1),
            date(2024, 1, 1),
            date(2025, 1, 1),
        ]


@pytest.mark.asyncio
async def test_quarterly_ulc_persists_distinct_quarters(client):
    sessionmaker = session_module._sessionmaker
    dtos = [_ulc_dto("CHE", 2025, q, 0.5 + q) for q in (1, 2, 3, 4)]
    async with sessionmaker() as session:
        result = await persist_observations(session, dtos)
        assert result.inserted == 4
        rows = (await session.execute(
            select(Observation).order_by(Observation.period_start)
        )).scalars().all()
        assert [r.period_start.date() for r in rows] == [
            date(2025, 1, 1),
            date(2025, 4, 1),
            date(2025, 7, 1),
            date(2025, 10, 1),
        ]


@pytest.mark.asyncio
async def test_oecd_reimport_skips_duplicates(client):
    sessionmaker = session_module._sessionmaker
    dtos = [_prod_dto("CHE", 2025, 90.5178)]
    async with sessionmaker() as session:
        first = await persist_observations(session, dtos)
        assert first.inserted == 1
        await session.commit()
    async with sessionmaker() as session:
        second = await persist_observations(session, dtos)
        assert (second.inserted, second.skipped, second.revised) == (0, 1, 0)
        count = (await session.execute(
            select(func.count()).select_from(Observation)
        )).scalar_one()
        assert count == 1


# --- Part 6: OECD run_ingestion happy path ------------------------------------


@pytest.mark.asyncio
async def test_oecd_run_ingestion_happy_path(client):
    body = "\n".join(
        [
            PROD_HEADER,
            _prod_row("CHE", "2024", "88.9551"),
            _prod_row("CHE", "2025", "90.5178"),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert (
            "/data/OECD.SDD.TPS,DSD_PDB@DF_PDB,2.0/CHE.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP"
            in str(request.url)
        )
        return httpx.Response(200, text=body)

    adapter = OECDAdapter(
        transport=httpx.MockTransport(handler),
        retrieved_at=RETRIEVED_AT.isoformat(),
    )
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        outcome = await run_ingestion(
            session, adapter, "CHE", PROD_CODE, start_year=2024, end_year=2025
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
        assert recorded.run_metadata["external_series_code"] == PROD_CODE
        rows = (await session.execute(
            select(Observation).options(selectinload(Observation.source_series))
        )).scalars().all()
        assert all(row.source_series.external_code == PROD_CODE for row in rows)


# --- Part 7: no-data handling ---------------------------------------------------


@pytest.mark.asyncio
async def test_oecd_run_ingestion_no_data_is_clean_not_failed(client):
    # OECD's verified answer for a no-coverage country (404 NoRecordsFound):
    # the run is recorded as a zero-data success, never a failed run.
    adapter = OECDAdapter(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(404, text="NoRecordsFound")
        ),
        retrieved_at=RETRIEVED_AT.isoformat(),
    )
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        outcome = await run_ingestion(
            session, adapter, "CHN", PROD_CODE, start_year=1990, end_year=2025
        )
        assert outcome.error is None
        assert outcome.run.status.value == "success"
        assert outcome.persistence.received == 0
        assert outcome.run.run_metadata.get("no_data") is True
        run = outcome.run
        await session.commit()

    async with sessionmaker() as session:
        recorded = (await session.execute(
            select(IngestionRun).where(IngestionRun.id == run.id)
        )).scalar_one()
        assert recorded.status == IngestionRunStatus.success
        assert recorded.error_count == 0
        assert recorded.run_metadata["no_data"] is True
        count = (await session.execute(
            select(func.count()).select_from(Observation)
        )).scalar_one()
        assert count == 0


@pytest.mark.asyncio
async def test_oecd_empty_success_response_is_also_zero_data(client):
    # A 200 with a header-only CSV is equally a legitimate no-coverage case.
    adapter = OECDAdapter(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=PROD_HEADER + "\n")
        ),
        retrieved_at=RETRIEVED_AT.isoformat(),
    )
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        outcome = await run_ingestion(
            session, adapter, "CHN", PROD_CODE, start_year=1990, end_year=2025
        )
        assert outcome.error is None
        assert outcome.persistence.received == 0
        assert outcome.run.status.value == "success"


# --- Parts 8–10: source filtering, isolation, latest vintage --------------------


async def _seed_oecd_observations():
    sessionmaker = session_module._sessionmaker
    dtos = [
        _prod_dto("CHE", 2025, 90.52),
        _ulc_dto("CHE", 2025, 4, 0.4),
        _ulc_dto("USA", 2025, 4, 1.9),  # must never leak into CHE responses
    ]
    async with sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


@pytest.mark.asyncio
async def test_source_filter_returns_only_oecd_rows(client):
    await _seed_oecd_observations()
    response = await client.get("/api/countries/CHE/observations?source=oecd&limit=1000")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert all(item["source_key"] == "oecd" for item in payload["items"])
    assert {item["indicator_code"] for item in payload["items"]} == {
        "LABOUR_PRODUCTIVITY_PER_HOUR",
        "UNIT_LABOUR_COST_GROWTH",
    }


@pytest.mark.asyncio
async def test_oecd_indicator_filter_combines_with_source(client):
    await _seed_oecd_observations()
    prod = await client.get(
        "/api/countries/CHE/observations"
        "?source=oecd&indicator=LABOUR_PRODUCTIVITY_PER_HOUR&limit=1000"
    )
    assert prod.status_code == 200
    payload = prod.json()
    assert payload["count"] == 1
    assert payload["items"][0]["value"] == 90.52

    ulc = await client.get(
        "/api/countries/CHE/observations"
        "?source=oecd&indicator=UNIT_LABOUR_COST_GROWTH&limit=1000"
    )
    assert ulc.json()["count"] == 1
    assert ulc.json()["items"][0]["value"] == 0.4


@pytest.mark.asyncio
async def test_country_and_oecd_source_isolation(client):
    await _seed_oecd_observations()
    response = await client.get("/api/countries/CHE/observations?source=oecd&limit=1000")
    values = [item["value"] for item in response.json()["items"]]
    assert 1.9 not in values  # USA's ULC value must never leak into CHE
    assert sorted(values) == [0.4, 90.52]


@pytest.mark.asyncio
async def test_latest_vintage_behavior_with_oecd(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        await persist_observations(session, [_prod_dto("CHE", 2025, 90.5178)])
        await session.commit()
    async with sessionmaker() as session:
        result = await persist_observations(session, [_prod_dto("CHE", 2025, 91.1)])
        assert result.revised == 1
        await session.commit()

    response = await client.get(
        "/api/countries/CHE/observations"
        "?source=oecd&indicator=LABOUR_PRODUCTIVITY_PER_HOUR&limit=1000"
    )
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["value"] == 91.1  # latest vintage, not the original
    assert items[0]["vintage_number"] == 2