"""Offline tests for Micro-Sprint 3.6: observation revision handling.

Changed values must create immutable new vintages + IndicatorRevision rows;
history is never overwritten. Synthetic DTOs, seeded SQLite, no network.
"""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.data_sources.base import ObservationDTO
from app.db import base
from app.db import session as session_module
from app.db.seed import DEFAULT_DATA_FILE, seed
from app.models import IndicatorRevision, Observation
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
SERIES = "NY.GDP.MKTP.KD.ZG"


def _dto(year: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3="CHE",
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
async def client(tmp_path):
    data_file = tmp_path / "countries.json"
    data_file.write_text(DEFAULT_DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(base.Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    session_module._engine = engine
    session_module._sessionmaker = maker

    await seed(data_file)
    yield maker
    await engine.dispose()


async def _observations(session):
    return list((await session.execute(select(Observation).order_by(Observation.vintage_number))).scalars().all())


async def _revisions(session):
    return list((await session.execute(select(IndicatorRevision))).scalars().all())


async def test_changed_value_creates_second_observation(client):
    sessionmaker = client
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.2)])
        await session.commit()
    async with sessionmaker() as session:
        result = await persist_observations(session, [_dto(2023, 1.4)])
        assert result.revised == 1
        assert result.inserted == 0
        rows = await _observations(session)
        assert len(rows) == 2


async def test_old_value_remains_unchanged(client):
    sessionmaker = client
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.2)])
        await session.commit()
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.4)])
        rows = await _observations(session)
        old = rows[0]
        assert old.value == 1.2
        assert old.vintage_number == 1
        assert old.supersedes_observation_id is None


async def test_vintage_number_increments(client):
    sessionmaker = client
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.2)])
        await session.commit()
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.4)])
        rows = await _observations(session)
        assert [r.vintage_number for r in rows] == [1, 2]


async def test_supersedes_observation_id_is_correct(client):
    sessionmaker = client
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.2)])
        await session.commit()
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.4)])
        rows = await _observations(session)
        assert rows[1].supersedes_observation_id == rows[0].id


async def test_indicator_revision_row_created(client):
    sessionmaker = client
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.2)])
        await session.commit()
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.4)])
        rows = await _observations(session)
        revisions = await _revisions(session)
        assert len(revisions) == 1
        rev = revisions[0]
        assert rev.prior_observation_id == rows[0].id
        assert rev.new_observation_id == rows[1].id
        assert rev.old_value == 1.2
        assert rev.new_value == 1.4


async def test_delta_is_correct(client):
    sessionmaker = client
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.2)])
        await session.commit()
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.4)])
        revisions = await _revisions(session)
        assert revisions[0].delta == pytest.approx(0.2)


async def test_third_revision_becomes_vintage_three(client):
    sessionmaker = client
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.2)])
        await session.commit()
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.4)])
        await session.commit()
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.5)])
        rows = await _observations(session)
        assert [r.vintage_number for r in rows] == [1, 2, 3]
        assert rows[2].supersedes_observation_id == rows[1].id
        revisions = await _revisions(session)
        assert len(revisions) == 2
        assert revisions[-1].prior_observation_id == rows[1].id
        assert revisions[-1].old_value == 1.4


async def test_identical_latest_value_is_skipped(client):
    sessionmaker = client
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.2)])
        await session.commit()
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.4)])
        await session.commit()
    async with sessionmaker() as session:
        result = await persist_observations(session, [_dto(2023, 1.4)])
        assert result.skipped == 1
        assert result.revised == 0
        assert len(await _observations(session)) == 2


async def test_revision_is_part_of_same_transaction(client):
    sessionmaker = client
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.2)])
        await session.commit()
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.4)])
        await session.rollback()  # caller aborted — nothing persisted

    async with sessionmaker() as session:
        assert len(await _observations(session)) == 1
        assert len(await _revisions(session)) == 0