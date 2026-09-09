"""Offline tests for Micro-Sprint 3.4: DTO canonical identity + Observation persistence.

Synthetic DTOs only — no network calls. Uses the seeded SQLite `client` fixture.
"""
from datetime import date, datetime, timezone

import httpx
import pytest
from sqlalchemy import select

from app.data_sources.base import DataSourceError, ObservationDTO, SeriesMappingError
from app.data_sources.world_bank import WorldBankAdapter
from app.data_sources.world_bank_mappings import get_world_bank_mapping_by_external_code
from app.db import session as session_module
from app.models import DataSource, Indicator, Observation, SourceSeries
from app.services.observation_service import (
    ObservationPersistenceError,
    persist_observations,
)

RETRIEVED_AT = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)

WB_RECORDS = {
    "NY.GDP.MKTP.KD.ZG": [
        {"indicator": {"id": "NY.GDP.MKTP.KD.ZG", "value": "GDP growth (annual %)"},
         "date": str(y), "value": v, "unit": "", "countryiso3code": "CHE"}
        for y, v in [(2021, 6.18), (2022, 2.6), (2023, 1.2)]
    ],
}


def _parse(payload, series: str = "NY.GDP.MKTP.KD.ZG"):
    adapter = WorldBankAdapter(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[{}, []]))
    )
    return adapter.parse_response(payload, "CHE", series)


def _dto(year: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3="CHE",
        indicator_code="GDP_GROWTH",
        external_series_code="NY.GDP.MKTP.KD.ZG",
        period=year,
        value=value,
        unit=None,
        source_key="world_bank",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"date": str(year), "value": value,
                     "indicator": {"id": "NY.GDP.MKTP.KD.ZG"}},
    )


async def _observation_count(session) -> int:
    return len((await session.execute(select(Observation))).scalars().all())


# --- DTO identity (sprint items 1–3) ---------------------------------------


def test_parse_maps_external_series_to_canonical_indicator_code():
    payload = [{"page": 1, "pages": 1, "per_page": "20000", "total": 1},
               WB_RECORDS["NY.GDP.MKTP.KD.ZG"]]
    observations = _parse(payload)
    assert observations[0].indicator_code == "GDP_GROWTH"
    assert observations[0].external_series_code == "NY.GDP.MKTP.KD.ZG"


def test_reverse_mapping_lookup():
    mapping = get_world_bank_mapping_by_external_code("NY.GDP.MKTP.KD.ZG")
    assert mapping is not None
    assert mapping.indicator_code == "GDP_GROWTH"
    assert mapping.source_key == "world_bank"
    assert get_world_bank_mapping_by_external_code("SP.POP.TOTL") is None


def test_unknown_external_series_raises_mapping_error():
    payload = [{"page": 1, "pages": 1, "per_page": "20000", "total": 1},
               WB_RECORDS["NY.GDP.MKTP.KD.ZG"]]
    with pytest.raises(SeriesMappingError):
        _parse(payload, series="SP.POP.TOTL")


# --- Persistence (sprint items 4–9) ----------------------------------------


@pytest.mark.asyncio
async def test_persist_three_dtos_inserts_all(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        result = await persist_observations(
            session, [_dto(2021, 6.18), _dto(2022, 2.6), _dto(2023, 1.2)]
        )

    assert (result.received, result.inserted, result.skipped, result.revised) == (3, 3, 0, 0)


@pytest.mark.asyncio
async def test_persisted_values_raw_payload_and_relationships(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2021, 6.18)])
        obs = (await session.execute(select(Observation))).scalars().all()
        assert len(obs) == 1
        row = obs[0]
        assert row.value == 6.18
        assert row.raw_payload["date"] == "2021"
        assert row.raw_payload["value"] == 6.18
        assert row.release_date is None
        # SQLite round trip drops tzinfo — compare wall-clock time
        assert row.retrieved_at.replace(tzinfo=timezone.utc) == RETRIEVED_AT

        await session.refresh(row, ["country", "indicator", "data_source", "source_series"])
        assert row.country.iso3 == "CHE"
        assert row.indicator.code == "GDP_GROWTH"
        assert row.data_source.key == "world_bank"
        assert row.source_series.external_code == "NY.GDP.MKTP.KD.ZG"
        assert row.source_series.indicator_id == row.indicator.id
        assert row.source_series.data_source_id == row.data_source.id


@pytest.mark.asyncio
async def test_second_identical_import_skips_duplicates(client):
    sessionmaker = session_module._sessionmaker
    dtos = [_dto(2021, 6.18), _dto(2022, 2.6), _dto(2023, 1.2)]
    async with sessionmaker() as session:
        first = await persist_observations(session, dtos)
        assert (first.inserted, first.skipped, first.revised) == (3, 0, 0)
        await session.commit()  # caller owns the transaction

    async with sessionmaker() as session:
        second = await persist_observations(session, dtos)
        assert (second.received, second.inserted, second.skipped, second.revised) == (3, 0, 3, 0)
        assert await _observation_count(session) == 3


@pytest.mark.asyncio
async def test_changed_value_creates_new_vintage_and_revision(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        await persist_observations(session, [_dto(2023, 1.2)])
        await session.commit()  # caller owns the transaction

    async with sessionmaker() as session:
        result = await persist_observations(session, [_dto(2023, 1.4)])
        assert (result.inserted, result.skipped, result.revised) == (0, 0, 1)
        rows = (await session.execute(select(Observation))).scalars().all()
        assert len(rows) == 2
        assert {r.value for r in rows} == {1.2, 1.4}  # old row preserved


@pytest.mark.asyncio
async def test_mismatched_indicator_and_series_rejected(client):
    sessionmaker = session_module._sessionmaker
    # NY.GDP.MKTP.CD belongs to GDP_CURRENT_USD, not GDP_GROWTH
    dto = ObservationDTO(
        country_iso3="CHE",
        indicator_code="GDP_GROWTH",
        external_series_code="NY.GDP.MKTP.CD",
        period=2021,
        value=6.18,
        unit=None,
        source_key="world_bank",
        observation_date=date(2021, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"date": "2021", "value": 6.18},
    )
    async with sessionmaker() as session:
        with pytest.raises(ObservationPersistenceError):
            await persist_observations(session, [dto])
        assert await _observation_count(session) == 0


@pytest.mark.asyncio
async def test_unknown_country_fails_safely(client):
    sessionmaker = session_module._sessionmaker
    bad = _dto(2021, 6.18)
    bad.country_iso3 = "XYZ"
    async with sessionmaker() as session:
        with pytest.raises(ObservationPersistenceError):
            await persist_observations(session, [bad])
        assert await _observation_count(session) == 0


def test_mismatched_error_is_a_data_source_error():
    # SeriesMappingError sits in the DataSourceError hierarchy so callers can
    # catch adapter failures uniformly.
    assert issubclass(SeriesMappingError, DataSourceError)