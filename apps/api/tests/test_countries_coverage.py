"""Coverage fields on GET /api/countries (latest-vintage-only counts)."""
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db import base
from app.db.session import get_session
from app.db.seed import DEFAULT_DATA_FILE, seed
from app.models import Country, Observation, SourceSeries
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture
async def client(tmp_path):
    data_file = tmp_path / "countries.json"
    data_file.write_text(DEFAULT_DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(base.Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    from app.db import session as session_module
    session_module._engine = engine
    session_module._sessionmaker = sessionmaker

    await seed(data_file)

    # CHE coverage: series[0] has 2023 (vintage 1) and 2024 with two vintages
    # (vintage 2 supersedes vintage 1); series[1] has 2024 (vintage 1).
    async with sessionmaker() as session:
        che = (
            await session.execute(select(Country).where(Country.iso3 == "CHE"))
        ).scalar_one()
        series = (await session.execute(select(SourceSeries))).scalars().all()
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)

        session.add(Observation(
            country_id=che.id, indicator_id=series[0].indicator_id,
            data_source_id=series[0].data_source_id,
            source_series_id=series[0].id,
            period_start=datetime(2023, 1, 1, tzinfo=timezone.utc),
            value=1.0, observation_date=now, retrieved_at=now,
        ))
        session.add(Observation(
            country_id=che.id, indicator_id=series[0].indicator_id,
            data_source_id=series[0].data_source_id,
            source_series_id=series[0].id,
            period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            value=1.3, observation_date=now, retrieved_at=now,
        ))
        session.add(Observation(
            country_id=che.id, indicator_id=series[0].indicator_id,
            data_source_id=series[0].data_source_id,
            source_series_id=series[0].id,
            period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            value=1.4, observation_date=now, retrieved_at=now,
            vintage_number=2,
        ))
        session.add(Observation(
            country_id=che.id, indicator_id=series[1].indicator_id,
            data_source_id=series[1].data_source_id,
            source_series_id=series[1].id,
            period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            value=90000.0, observation_date=now, retrieved_at=now,
        ))
        await session.commit()

    from app.main import app

    async def override_get_session():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_coverage_counts_latest_vintages_only(client):
    response = await client.get("/api/countries")
    assert response.status_code == 200
    by_iso3 = {c["iso3"]: c for c in response.json()}

    che = by_iso3["CHE"]
    # 4 latest-vintage observations: s1/2023, s1/2024 (vintage 2), s2/2024.
    # The superseded s1/2024 vintage 1 is not counted.
    assert che["observation_count"] == 3
    assert che["indicator_count"] == 2
    assert che["latest_observation_year"] == 2024

    usa = by_iso3["USA"]
    assert usa["observation_count"] is None
    assert usa["indicator_count"] is None
    assert usa["latest_observation_year"] is None