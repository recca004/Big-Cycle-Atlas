"""Sprint 6.6.2 Part 5 — WID raw-preservation persistence regression.

Proves a finite out-of-[0,1] DTO can be persisted unchanged as an
Observation.value via the mocked in-memory SQLite path. No live DB writes.
"""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.data_sources.base import BaseDataSourceAdapter, ObservationDTO
from app.db import base
from app.db.seed import DEFAULT_DATA_FILE, seed
from app.models import Observation
from app.services.ingestion_service import run_ingestion

RETRIEVED_AT = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
WEALTH_CODE = "WID/shwealj992/p90p100"


class FakeWidAdapter(BaseDataSourceAdapter):
    source_key = "wid"

    def __init__(self, dtos=None):
        self.dtos = dtos or []

    async def fetch_indicator(self, country_iso3, external_series_code,
                              start_year=None, end_year=None):
        return self.dtos


def _wealth_dto(year: int, value: float, country_iso3: str = "USA") -> ObservationDTO:
    return ObservationDTO(
        country_iso3=country_iso3,
        indicator_code="WEALTH_SHARE_TOP_10",
        external_series_code=WEALTH_CODE,
        period=year,
        value=value,
        unit="share (0-1)",
        source_key="wid",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"value": str(value)},
    )


@pytest.fixture
async def session(tmp_path):
    data_file = tmp_path / "countries.json"
    data_file.write_text(DEFAULT_DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(base.Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    from app.db import session as session_module
    session_module._engine = engine
    session_module._sessionmaker = maker

    await seed(data_file)
    async with maker() as s:
        yield s
    await engine.dispose()


async def test_out_of_range_value_persisted_unchanged(session):
    """A finite provider value > 1 (e.g. 1.03) is persisted unchanged as
    Observation.value — no clipping, no zero, no None."""
    adapter = FakeWidAdapter(dtos=[_wealth_dto(2020, 1.03)])
    outcome = await run_ingestion(session, adapter, "USA", WEALTH_CODE)
    assert outcome.run.status == "success"
    assert outcome.run.rows_inserted == 1

    observations = (await session.execute(select(Observation))).scalars().all()
    assert len(observations) == 1
    assert observations[0].value == 1.03


async def test_negative_value_persisted_unchanged(session):
    """A finite negative provider value is persisted unchanged."""
    adapter = FakeWidAdapter(dtos=[_wealth_dto(2020, -0.05)])
    outcome = await run_ingestion(session, adapter, "USA", WEALTH_CODE)
    assert outcome.run.status == "success"
    assert outcome.run.rows_inserted == 1

    observations = (await session.execute(select(Observation))).scalars().all()
    assert len(observations) == 1
    assert observations[0].value == -0.05


async def test_ordinary_value_persisted_unchanged(session):
    """An ordinary in-[0,1] value is persisted unchanged."""
    adapter = FakeWidAdapter(dtos=[_wealth_dto(2020, 0.72)])
    outcome = await run_ingestion(session, adapter, "USA", WEALTH_CODE)
    assert outcome.run.status == "success"

    observations = (await session.execute(select(Observation))).scalars().all()
    assert len(observations) == 1
    assert observations[0].value == 0.72
