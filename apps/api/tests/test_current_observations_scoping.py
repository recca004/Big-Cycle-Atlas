"""Regression: GET /countries/{iso3}/observations must be scoped to the
requested country, indicator, and latest vintage.

Found during Milestone 3 verification: SourceSeries rows are shared across
countries, so the latest-vintage join needs the country filter on the outer
query too — otherwise every country page got a global mix of rows.
"""
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import base
from app.db.session import get_session
from app.db.seed import DEFAULT_DATA_FILE, seed
from app.models import Country, Observation, SourceSeries
from app.models.indicator import Indicator

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


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

    async with sessionmaker() as session:
        countries = {
            c.iso3: c
            for c in (await session.execute(select(Country))).scalars().all()
        }
        indicators = {
            i.code: i
            for i in (await session.execute(select(Indicator))).scalars().all()
        }
        series = {
            s.indicator_id: s
            for s in (await session.execute(select(SourceSeries))).scalars().all()
        }
        growth = indicators["GDP_GROWTH"]
        gdp_usd = indicators["GDP_CURRENT_USD"]

        def obs(country, indicator, value, year, vintage=1):
            return Observation(
                country_id=country.id,
                indicator_id=indicator.id,
                data_source_id=series[indicator.id].data_source_id,
                source_series_id=series[indicator.id].id,
                period_start=datetime(year, 1, 1, tzinfo=timezone.utc),
                value=value,
                observation_date=NOW,
                retrieved_at=NOW,
                vintage_number=vintage,
            )

        # USA GDP_GROWTH 2025: vintage 1 = 3.0 superseded by vintage 2 = 2.1
        session.add(obs(countries["USA"], growth, 3.0, 2025, vintage=1))
        session.add(obs(countries["USA"], growth, 2.1, 2025, vintage=2))
        # USA second indicator in an older period, so no-filter order is deterministic
        session.add(obs(countries["USA"], gdp_usd, 30000.0, 2024))
        # CHE same series/period as USA's GDP_GROWTH — the leak case
        session.add(obs(countries["CHE"], growth, 1.3, 2025))
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
async def test_observations_scoped_to_requested_country(client):
    usa = await client.get("/api/countries/USA/observations")
    assert usa.status_code == 200
    usa_data = usa.json()
    # 2025 growth (latest vintage) first, then 2024 GDP current — USA only
    assert [i["value"] for i in usa_data["items"]] == [2.1, 30000.0]
    assert usa_data["count"] == len(usa_data["items"]) == 2
    usa_ids = {i["country_id"] for i in usa_data["items"]}
    assert len(usa_ids) == 1

    che = await client.get("/api/countries/CHE/observations")
    assert che.status_code == 200
    che_data = che.json()
    che_values = [i["value"] for i in che_data["items"]]
    assert che_values == [1.3]
    assert che_data["count"] == 1
    assert 2.1 not in che_values
    assert 30000.0 not in che_values


@pytest.mark.asyncio
async def test_observations_filtered_by_indicator(client):
    response = await client.get(
        "/api/countries/USA/observations?indicator=GDP_GROWTH"
    )
    assert response.status_code == 200
    data = response.json()
    assert [i["value"] for i in data["items"]] == [2.1]
    assert data["count"] == len(data["items"]) == 1
    assert all(i["indicator_code"] == "GDP_GROWTH" for i in data["items"])


@pytest.mark.asyncio
async def test_observations_return_latest_vintage_only(client):
    response = await client.get(
        "/api/countries/USA/observations?indicator=GDP_GROWTH"
    )
    data = response.json()
    values = [i["value"] for i in data["items"]]
    assert values == [2.1]
    assert 3.0 not in values  # superseded vintage stays in DB but is not served
    assert [i["vintage_number"] for i in data["items"]] == [2]