"""Offline tests for Micro-Sprint 3.5: fetch + persist + IngestionRun wiring.

Uses a fake adapter (no network) against the seeded in-memory SQLite setup.
"""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.data_sources.base import (
    BaseDataSourceAdapter,
    DataSourceError,
    DataSourceHTTPError,
    ObservationDTO,
)
from app.db import base
from app.db.seed import DEFAULT_DATA_FILE, seed
from app.models import IngestionRun, Observation
from app.services.ingestion_service import IngestionError, run_ingestion
from app.services.observation_service import ObservationPersistenceError

RETRIEVED_AT = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
SERIES = "NY.GDP.MKTP.KD.ZG"


class FakeAdapter(BaseDataSourceAdapter):
    source_key = "world_bank"

    def __init__(self, dtos=None, error=None):
        self.dtos = dtos or []
        self.error = error
        self.calls = []

    async def fetch_indicator(self, country_iso3, external_series_code,
                              start_year=None, end_year=None):
        self.calls.append((country_iso3, external_series_code, start_year, end_year))
        if self.error is not None:
            raise self.error
        return self.dtos


def _dto(year: int, value: float, country_iso3: str = "CHE") -> ObservationDTO:
    return ObservationDTO(
        country_iso3=country_iso3,
        indicator_code="GDP_GROWTH",
        external_series_code=SERIES,
        period=year,
        value=value,
        unit=None,
        source_key="world_bank",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"date": str(year), "value": value},
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


async def test_happy_path_persists_observations_and_records_run(session):
    adapter = FakeAdapter(dtos=[_dto(2021, 4.2), _dto(2022, 2.6)])
    outcome = await run_ingestion(session, adapter, "CHE", SERIES, start_year=2020)

    run = outcome.run
    assert run.status == "success"
    assert run.completed_at is not None
    assert run.rows_received == 2
    assert run.rows_inserted == 2
    assert run.rows_skipped == 0
    assert run.error_count == 0
    assert run.rows_revised == 0
    assert run.run_metadata["country_iso3"] == "CHE"
    assert run.run_metadata["external_series_code"] == SERIES

    observations = (await session.execute(select(Observation))).scalars().all()
    assert len(observations) == 2


async def test_second_run_is_idempotent(session):
    adapter = FakeAdapter(dtos=[_dto(2021, 4.2), _dto(2022, 2.6)])
    await run_ingestion(session, adapter, "CHE", SERIES)
    await session.commit()

    outcome = await run_ingestion(session, adapter, "CHE", SERIES)
    assert outcome.run.status == "success"
    assert outcome.persistence.inserted == 0
    assert outcome.persistence.skipped == 2

    runs = (await session.execute(select(IngestionRun))).scalars().all()
    assert len(runs) == 2


async def test_fetch_failure_records_failed_run(session):
    adapter = FakeAdapter(error=DataSourceHTTPError("boom", 503))
    outcome = await run_ingestion(session, adapter, "CHE", SERIES)

    assert outcome.persistence is None
    assert outcome.run.status == "failed"
    assert outcome.run.completed_at is not None
    assert outcome.run.error_count == 1
    assert outcome.run.errors[0]["type"] == "DataSourceHTTPError"

    observations = (await session.execute(select(Observation))).scalars().all()
    assert len(observations) == 0


async def test_unknown_source_key_raises_before_run_creation(session):
    adapter = FakeAdapter()
    adapter.source_key = "not_seeded"
    with pytest.raises(IngestionError):
        await run_ingestion(session, adapter, "CHE", SERIES)


async def test_persistence_error_propagates(session):
    adapter = FakeAdapter(dtos=[_dto(2021, 4.2, country_iso3="ZZZ")])
    with pytest.raises(ObservationPersistenceError):
        await run_ingestion(session, adapter, "CHE", SERIES)