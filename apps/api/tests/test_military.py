"""Milestone 5.4 offline tests: SIPRI-derived WB military-expenditure mappings,
seeding, persistence, and the Military strength force promotion (PARTIAL via the
DEC-009 coverage ceiling — spending is an input proxy, never capability).

Synthetic DTOs persisted via the real persistence layer against seeded SQLite;
no external World Bank calls. Coverage is data availability only — no scores.
"""
from datetime import date, datetime, timezone

from sqlalchemy import func, select

from app.cycle.force_definitions import force_definition_by_code
from app.data_sources.world_bank_mappings import WORLD_BANK_MAPPINGS
from app.db import session as session_module
from app.db.seed import DEFAULT_DATA_FILE, seed
from app.models import Country, DataSource, Indicator, Observation, SourceSeries
from app.services.force_coverage_service import get_force_coverage

RETRIEVED_AT = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)

WB_MIL_USD = "MS.MIL.XPND.CD"
WB_MIL_GDP = "MS.MIL.XPND.GD.ZS"


def _mil_dto(iso3: str, indicator: str, external: str, value: float, year: int) -> object:
    from app.data_sources.base import ObservationDTO

    return ObservationDTO(
        country_iso3=iso3,
        indicator_code=indicator,
        external_series_code=external,
        period=year,
        value=value,
        unit="test unit",
        source_key="world_bank",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


def _mil_usd_dto(iso3: str, value: float, year: int = 2024) -> object:
    return _mil_dto(iso3, "MILITARY_EXPENDITURE_USD", WB_MIL_USD, value, year)


def _mil_gdp_dto(iso3: str, value: float, year: int = 2024) -> object:
    return _mil_dto(iso3, "MILITARY_EXPENDITURE_GDP", WB_MIL_GDP, value, year)


async def _persist(dtos) -> None:
    from app.services.observation_service import persist_observations

    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


async def coverage_by_code(iso3: str) -> dict:
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        country_id = (
            await session.execute(select(Country.id).where(Country.iso3 == iso3))
        ).scalar_one()
        items = await get_force_coverage(session, country_id)
        return {item.definition.code: item for item in items}


# --- 1–2: verified WB (SIPRI-derived) mappings ---------------------------------------


async def test_military_usd_mapping_verified(client):
    by_indicator = {m.indicator_code: m for m in WORLD_BANK_MAPPINGS}
    usd = by_indicator.get("MILITARY_EXPENDITURE_USD")
    assert usd is not None
    assert usd.external_code == WB_MIL_USD
    assert usd.external_name == "Military expenditure (current USD)"
    assert usd.external_unit == "current US$"
    assert "SIPRI" in usd.transform_notes
    assert "input" in usd.transform_notes
    assert "not a capability measure" in usd.transform_notes


async def test_military_gdp_mapping_verified(client):
    by_indicator = {m.indicator_code: m for m in WORLD_BANK_MAPPINGS}
    gdp = by_indicator.get("MILITARY_EXPENDITURE_GDP")
    assert gdp is not None
    assert gdp.external_code == WB_MIL_GDP
    assert gdp.external_name == "Military expenditure (% of GDP)"
    assert gdp.external_unit == "% of GDP"
    assert "SIPRI" in gdp.transform_notes


# --- 3: canonical indicator seeding -------------------------------------------------


async def test_military_indicators_seeded(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        usd = (
            await session.execute(
                select(Indicator).where(Indicator.code == "MILITARY_EXPENDITURE_USD")
            )
        ).scalar_one()
        gdp = (
            await session.execute(
                select(Indicator).where(Indicator.code == "MILITARY_EXPENDITURE_GDP")
            )
        ).scalar_one()
    assert usd.name == "Military expenditure"
    assert usd.category == "Military"
    assert usd.unit == "current US$"
    assert usd.frequency == "annual"
    assert usd.strength_direction == "contextual"  # spending != capability
    assert "SIPRI" in usd.description

    assert gdp.name == "Military expenditure (% of GDP)"
    assert gdp.category == "Military"
    assert gdp.unit == "percent of GDP"
    assert gdp.frequency == "annual"
    assert gdp.strength_direction == "contextual"
    assert "SIPRI" in gdp.description


# --- 4: SourceSeries seeding + idempotency -------------------------------------------


async def test_military_source_series_seeded_idempotently(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        total = (
            await session.execute(select(func.count()).select_from(SourceSeries))
        ).scalar_one()
        # 19 = 15 WB + 2 BIS + 2 OECD
        assert total == 19
        wb_series = (
            await session.execute(
                select(SourceSeries.external_code)
                .join(DataSource, DataSource.id == SourceSeries.data_source_id)
                .where(DataSource.key == "world_bank")
            )
        ).scalars().all()
        assert WB_MIL_USD in wb_series
        assert WB_MIL_GDP in wb_series

    await seed(DEFAULT_DATA_FILE)

    async with sessionmaker() as session:
        total = (
            await session.execute(select(func.count()).select_from(SourceSeries))
        ).scalar_one()
        assert total == 19
        dup = (
            await session.execute(
                select(func.count())
                .select_from(SourceSeries)
                .group_by(SourceSeries.data_source_id, SourceSeries.indicator_id)
                .having(func.count() > 1)
            )
        ).all()
        assert dup == []


# --- 5: observation persistence (raw values, annual periods) --------------------------


async def test_military_observations_persisted_raw(client):
    await _persist(
        [
            _mil_usd_dto("CHE", 6_722_303_543.87),
            _mil_gdp_dto("CHE", 0.72),
        ]
    )
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        rows = (
            await session.execute(
                select(Observation, SourceSeries.external_code)
                .join(SourceSeries, SourceSeries.id == Observation.source_series_id)
                .where(SourceSeries.external_code.in_([WB_MIL_USD, WB_MIL_GDP]))
            )
        ).all()
    by_external = {external: obs for obs, external in rows}
    assert by_external[WB_MIL_USD].value == 6_722_303_543.87  # stored raw
    assert by_external[WB_MIL_GDP].value == 0.72
    assert all(obs.vintage_number == 1 for obs in by_external.values())
    assert all(obs.period_start.year == 2024 for obs in by_external.values())


# --- 6: Military strength becomes PARTIAL with data ----------------------------------


async def test_military_strength_partial_with_data(client):
    await _persist(
        [
            _mil_usd_dto("CHE", 6_722_303_543.87),
            _mil_gdp_dto("CHE", 0.72),
        ]
    )
    coverage = await coverage_by_code("CHE")
    force = coverage["military_strength"]
    assert force.status == "partial"
    live = {i.indicator_code: i for i in force.live_inputs}
    assert set(live) == {"MILITARY_EXPENDITURE_USD", "MILITARY_EXPENDITURE_GDP"}
    assert all(i.has_data for i in live.values())
    assert all(i.source == "world_bank" for i in live.values())


# --- 7: Military strength never AVAILABLE from spending alone -----------------------


async def test_military_strength_never_available_even_with_complete_data(client):
    # Full history for both inputs — the force still cannot report AVAILABLE:
    # spending is an INPUT proxy (SIPRI), capped by the DEC-009 ceiling.
    await _persist(
        [_mil_usd_dto("CHE", 5_000_000_000.0, year) for year in range(1990, 2025)]
        + [_mil_gdp_dto("CHE", 0.7, year) for year in range(1990, 2025)]
    )
    coverage = await coverage_by_code("CHE")
    force = coverage["military_strength"]
    assert force.status == "partial"
    assert force.status != "available"
    assert force.definition.coverage_ceiling == "partial"
    notes = force.definition.coverage_notes
    assert "SIPRI" in notes
    assert "INPUT measure" in notes
    assert "not a measure of military capability" in notes or "never" in notes


# --- 8: ceiling behaviour remains correct across all forces ---------------------------


async def test_coverage_ceiling_set_only_on_proxy_forces(client):
    for code in ("rule_of_law", "corruption", "productivity_output_growth",
                 "cost_competitiveness", "indebtedness", "trade_capital_flows",
                 "infrastructure_investment"):
        force = force_definition_by_code(code)
        assert force.coverage_ceiling is None, code
    for code in ("wealth_opportunity_values_gaps", "internal_conflict", "military_strength"):
        force = force_definition_by_code(code)
        assert force.coverage_ceiling == "partial", code


# --- 9: country scoping ---------------------------------------------------------------


async def test_military_coverage_is_country_scoped(client):
    await _persist(
        [
            _mil_usd_dto("CHE", 6_722_303_543.87),
            _mil_gdp_dto("CHE", 0.72),
        ]
    )
    che = await coverage_by_code("CHE")
    usa = await coverage_by_code("USA")
    assert che["military_strength"].status == "partial"
    assert usa["military_strength"].status == "defined_not_sourced"
    usa_live = {i.indicator_code: i for i in usa["military_strength"].live_inputs}
    assert not any(i.has_data for i in usa_live.values())


# --- 10: API still returns exactly 17 forces ------------------------------------------


async def test_api_still_returns_17_forces_with_military(client):
    await _persist(
        [
            _mil_usd_dto("CHE", 6_722_303_543.87),
            _mil_gdp_dto("CHE", 0.72),
        ]
    )
    response = await client.get("/api/countries/CHE/force-coverage")
    assert response.status_code == 200
    data = response.json()
    assert data["country"] == "CHE"
    assert len(data["forces"]) == 17
    by_code = {f["code"]: f for f in data["forces"]}
    assert by_code["military_strength"]["status"] == "partial"
    live = {i["indicator_code"]: i for i in by_code["military_strength"]["live_inputs"]}
    assert set(live) == {"MILITARY_EXPENDITURE_USD", "MILITARY_EXPENDITURE_GDP"}


# --- 11: no score fields ---------------------------------------------------------------


async def test_api_payload_has_no_score_fields(client):
    await _persist([_mil_usd_dto("CHE", 6_722_303_543.87)])
    data = (await client.get("/api/countries/CHE/force-coverage")).json()

    def _keys(obj) -> set:
        keys = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                keys.add(k)
                keys |= _keys(v)
        elif isinstance(obj, list):
            for item in obj:
                keys |= _keys(item)
        return keys

    assert not ({"score", "force_score", "phase", "weight", "trend"} & _keys(data))