"""Milestone 5.3 offline tests: WB Gini + CPI mappings, seeding, irregular-year
persistence, coverage ceiling (proxy-only forces), force promotions (Wealth /
opportunity / values gaps PARTIAL via Gini; Cost competitiveness ULC + CPI), and
API shape.

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

WB_GINI = "SI.POV.GINI"
WB_CPI = "FP.CPI.TOTL.ZG"
OECD_ULC = "DSD_PDB@DF_PDB_ULC_Q/{cc}.Q.ULCE._T.PA.V.GY.S.NC"


def _dto(iso3: str, indicator: str, external: str, value: float, year: int) -> object:
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


def _ulc_dto(iso3: str, value: float) -> object:
    from app.data_sources.base import ObservationDTO

    return ObservationDTO(
        country_iso3=iso3,
        indicator_code="UNIT_LABOUR_COST_GROWTH",
        external_series_code=OECD_ULC,
        period=2025,
        value=value,
        unit="percent per annum",
        source_key="oecd",
        observation_date=date(2025, 10, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


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


# --- 1 + 8: verified WB mappings -------------------------------------------------


async def test_gini_and_cpi_mappings_verified(client):
    by_indicator = {m.indicator_code: m for m in WORLD_BANK_MAPPINGS}
    gini = by_indicator.get("GINI_INDEX")
    assert gini is not None
    assert gini.external_code == WB_GINI
    assert gini.external_name == "Gini index"
    assert "never rescaled" in gini.transform_notes
    assert "forward-filled" in gini.transform_notes

    cpi = by_indicator.get("INFLATION_CPI")
    assert cpi is not None
    assert cpi.external_code == WB_CPI
    assert cpi.external_name == "Inflation, consumer prices (annual %)"
    assert "Domestic price-pressure" in cpi.transform_notes


# --- 2: Gini canonical indicator seeded ------------------------------------------


async def test_gini_indicator_seeded(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        row = (
            await session.execute(select(Indicator).where(Indicator.code == "GINI_INDEX"))
        ).scalar_one()
    assert row.name == "Gini index"
    assert row.category == "Inequality"
    assert row.unit == "index (0-100)"
    assert row.frequency == "irregular"
    assert row.strength_direction == "negative"
    assert "missing years are gaps" in row.description


async def test_inflation_cpi_frequency_corrected_to_annual(client):
    # Semantic correction (M5.3): the catalog's aspirational 'monthly' placeholder
    # was corrected to 'annual' to match the verified WB series FP.CPI.TOTL.ZG.
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        row = (
            await session.execute(select(Indicator).where(Indicator.code == "INFLATION_CPI"))
        ).scalar_one()
    assert row.frequency == "annual"
    assert row.unit == "percent"
    assert row.strength_direction == "contextual"


# --- 3: SourceSeries seeding idempotency ------------------------------------------


async def test_gini_cpi_source_series_seeded_idempotently(client):
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
        assert WB_GINI in wb_series
        assert WB_CPI in wb_series

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


# --- 4: irregular-year persistence (no fill, raw values) ---------------------------


async def test_gini_irregular_years_persisted_no_fill(client):
    # Real CHE shape: sparse/irregular years — 2008, 2012, 2022 only
    await _persist(
        [
            _dto("CHE", "GINI_INDEX", WB_GINI, 33.8, 2022),
            _dto("CHE", "GINI_INDEX", WB_GINI, 32.2, 2012),
            _dto("CHE", "GINI_INDEX", WB_GINI, 30.5, 2008),
        ]
    )
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        rows = (
            await session.execute(
                select(Observation.period_start, Observation.value)
                .join(SourceSeries, SourceSeries.id == Observation.source_series_id)
                .where(SourceSeries.external_code == WB_GINI)
                .order_by(Observation.period_start)
            )
        ).all()
    years = [r.period_start.year for r in rows]
    # gap years are absent — never forward-filled, never zero-filled
    assert years == [2008, 2012, 2022]
    assert [r.value for r in rows] == [30.5, 32.2, 33.8]


# --- 5–6: wealth-gap force is PARTIAL, never AVAILABLE, via the ceiling ------------


async def test_wealth_gap_force_partial_never_available_with_gini(client):
    await _persist([_dto("CHE", "GINI_INDEX", WB_GINI, 33.8, 2022)])
    coverage = await coverage_by_code("CHE")
    force = coverage["wealth_opportunity_values_gaps"]
    assert force.status == "partial"
    live = {i.indicator_code: i for i in force.live_inputs}
    assert set(live) == {"GINI_INDEX"}
    assert live["GINI_INDEX"].has_data
    assert live["GINI_INDEX"].source == "world_bank"
    # the ceiling is the reason — and the note explains the conceptual gap
    assert force.definition.coverage_ceiling == "partial"
    notes = force.definition.coverage_notes
    assert "income inequality only" in notes
    assert "Wealth inequality" in notes
    assert "opportunity gaps" in notes


async def test_proxy_ceiling_does_not_cap_undefined_forces(client):
    # the ceiling is opt-in per force; existing forces keep the default None
    for code in ("rule_of_law", "corruption", "productivity_output_growth", "indebtedness"):
        force = force_definition_by_code(code)
        assert force.coverage_ceiling is None
    # only the explicitly proxy-only forces carry the ceiling
    wealth = force_definition_by_code("wealth_opportunity_values_gaps")
    conflict = force_definition_by_code("internal_conflict")
    assert wealth.coverage_ceiling == "partial"
    assert conflict.coverage_ceiling == "partial"


async def test_wealth_gap_without_data_is_defined_not_sourced(client):
    coverage = await coverage_by_code("CHE")
    force = coverage["wealth_opportunity_values_gaps"]
    assert force.status == "defined_not_sourced"
    live = {i.indicator_code: i for i in force.live_inputs}
    assert not live["GINI_INDEX"].has_data


# --- 9–11: CPI persistence + Cost competitiveness promotion -------------------------


async def test_cpi_observation_persisted_raw(client):
    await _persist([_dto("CHE", "INFLATION_CPI", WB_CPI, 0.15, 2024)])
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        row = (
            await session.execute(
                select(Observation)
                .join(SourceSeries, SourceSeries.id == Observation.source_series_id)
                .where(SourceSeries.external_code == WB_CPI)
                .limit(1)
            )
        ).scalar_one()
    assert row.value == 0.15  # stored raw, never transformed
    assert row.vintage_number == 1
    assert row.period_start.year == 2024


async def test_cost_competitiveness_available_with_ulc_and_cpi(client):
    # OECD-6 shape: both live inputs have data → AVAILABLE (no ceiling on this force)
    await _persist(
        [
            _ulc_dto("CHE", -0.11),
            _dto("CHE", "INFLATION_CPI", WB_CPI, 0.15, 2024),
        ]
    )
    coverage = await coverage_by_code("CHE")
    force = coverage["cost_competitiveness"]
    assert force.status == "available"
    assert force.definition.coverage_ceiling is None
    live = {i.indicator_code: i for i in force.live_inputs}
    assert live["UNIT_LABOUR_COST_GROWTH"].has_data
    assert live["UNIT_LABOUR_COST_GROWTH"].source == "oecd"
    assert live["INFLATION_CPI"].has_data
    assert live["INFLATION_CPI"].source == "world_bank"
    assert force.candidate_inputs == []  # promoted — no longer a candidate


async def test_chn_cost_competitiveness_partial_with_cpi_only(client):
    # CHN/IND shape: CPI live but OECD ULC unavailable → PARTIAL, never AVAILABLE
    await _persist([_dto("CHN", "INFLATION_CPI", WB_CPI, 0.06, 2024)])
    coverage = await coverage_by_code("CHN")
    force = coverage["cost_competitiveness"]
    assert force.status == "partial"
    live = {i.indicator_code: i for i in force.live_inputs}
    assert live["INFLATION_CPI"].has_data
    assert not live["UNIT_LABOUR_COST_GROWTH"].has_data


# --- 12: country scoping -------------------------------------------------------------


async def test_gini_coverage_is_country_scoped(client):
    await _persist([_dto("CHE", "GINI_INDEX", WB_GINI, 33.8, 2022)])
    che = await coverage_by_code("CHE")
    usa = await coverage_by_code("USA")
    assert che["wealth_opportunity_values_gaps"].status == "partial"
    assert usa["wealth_opportunity_values_gaps"].status == "defined_not_sourced"
    usa_live = {i.indicator_code: i for i in usa["wealth_opportunity_values_gaps"].live_inputs}
    assert not usa_live["GINI_INDEX"].has_data


# --- 13–14: API shape -----------------------------------------------------------------


async def test_api_still_returns_17_forces_with_gini_cpi(client):
    await _persist(
        [
            _dto("CHE", "GINI_INDEX", WB_GINI, 33.8, 2022),
            _dto("CHE", "INFLATION_CPI", WB_CPI, 0.15, 2024),
        ]
    )
    response = await client.get("/api/countries/CHE/force-coverage")
    assert response.status_code == 200
    data = response.json()
    assert data["country"] == "CHE"
    assert len(data["forces"]) == 17
    by_code = {f["code"]: f for f in data["forces"]}
    assert by_code["wealth_opportunity_values_gaps"]["status"] == "partial"
    assert by_code["cost_competitiveness"]["status"] == "partial"  # CPI only, no ULC


async def test_api_payload_has_no_score_fields(client):
    await _persist([_dto("CHE", "GINI_INDEX", WB_GINI, 33.8, 2022)])
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