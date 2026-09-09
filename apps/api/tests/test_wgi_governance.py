"""Milestone 5.2 offline tests: WGI governance mappings, seeding, persistence,
force promotion (Rule of law + Corruption + Internal conflict), semantics, and
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
from app.models import DataSource, Indicator, Observation, SourceSeries
from app.services.force_coverage_service import get_force_coverage

RETRIEVED_AT = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)

WGI_RL = "GOV_WGI_RL_SC"
WGI_CC = "GOV_WGI_CC_SC"
WGI_PV = "GOV_WGI_PV_SC"

WGI_CODES = {
    "RULE_OF_LAW_WGI_SCORE": WGI_RL,
    "CONTROL_OF_CORRUPTION_WGI_SCORE": WGI_CC,
    "POLITICAL_STABILITY_WGI_SCORE": WGI_PV,
}

# Legacy pre-2025-revision WGI codes must never appear in the mapping registry
LEGACY_WGI_CODES = ("RL.EST", "CC.EST", "PV.EST")


def _dto(iso3: str, indicator: str, external: str, value: float) -> object:
    from app.data_sources.base import ObservationDTO

    return ObservationDTO(
        country_iso3=iso3,
        indicator_code=indicator,
        external_series_code=external,
        period=2024,
        value=value,
        unit="score 0-100",
        source_key="world_bank",
        observation_date=date(2024, 1, 1),
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


def _wgi_dtos(iso3: str) -> list:
    return [
        _dto(iso3, "RULE_OF_LAW_WGI_SCORE", WGI_RL, 87.32),
        _dto(iso3, "CONTROL_OF_CORRUPTION_WGI_SCORE", WGI_CC, 88.48),
        _dto(iso3, "POLITICAL_STABILITY_WGI_SCORE", WGI_PV, 82.65),
    ]


async def coverage_by_code(iso3: str) -> dict:
    from app.models import Country

    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        country_id = (
            await session.execute(select(Country.id).where(Country.iso3 == iso3))
        ).scalar_one()
        items = await get_force_coverage(session, country_id)
        return {item.definition.code: item for item in items}


# --- 1: current revised WGI mapping codes ---------------------------------------


async def test_wgi_mappings_use_current_revised_codes(client):
    by_indicator = {m.indicator_code: m for m in WORLD_BANK_MAPPINGS}
    for indicator_code, external_code in WGI_CODES.items():
        mapping = by_indicator.get(indicator_code)
        assert mapping is not None, f"{indicator_code} missing from WB mappings"
        assert mapping.external_code == external_code
        assert "Governance score (0-100)" in mapping.external_name
    external_codes = {m.external_code for m in WORLD_BANK_MAPPINGS}
    assert not (set(LEGACY_WGI_CODES) & external_codes)


# --- 2: 3 canonical WGI indicators seeded ---------------------------------------


async def test_wgi_canonical_indicators_seeded(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        rows = (
            await session.execute(select(Indicator).where(Indicator.code.in_(WGI_CODES)))
        ).scalars().all()
    assert {r.code for r in rows} == set(WGI_CODES)
    for row in rows:
        assert row.category == "Governance"
        assert row.unit == "score 0-100"
        assert row.frequency == "annual"
        assert row.strength_direction == "positive"
    by_code = {r.code: r for r in rows}
    assert "Absence of Violence/Terrorism" in by_code["POLITICAL_STABILITY_WGI_SCORE"].description


# --- 3: SourceSeries seed idempotency ---------------------------------------------


async def test_wgi_source_series_seeded_idempotently(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        total = (
            await session.execute(select(func.count()).select_from(SourceSeries))
        ).scalar_one()
        # 19 = 15 WB + 2 BIS + 2 OECD
        assert total == 19
        wgi_series = (
            await session.execute(
                select(SourceSeries.external_code)
                .join(DataSource, DataSource.id == SourceSeries.data_source_id)
                .where(DataSource.key == "world_bank")
            )
        ).scalars().all()
        assert set(WGI_CODES.values()) <= set(wgi_series)

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


# --- 4: WGI observation persistence ----------------------------------------------


async def test_wgi_observation_persisted_raw_value(client):
    await _persist([_dto("CHE", "RULE_OF_LAW_WGI_SCORE", WGI_RL, 87.32)])
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        row = (
            await session.execute(
                select(Observation)
                .join(SourceSeries, SourceSeries.id == Observation.source_series_id)
                .where(SourceSeries.external_code == WGI_RL)
                .limit(1)
            )
        ).scalar_one()
    assert row.value == 87.32  # stored raw, never transformed
    assert row.vintage_number == 1
    assert row.period_start.year == 2024


# --- 5–7: force promotions --------------------------------------------------------


async def test_rule_of_law_force_available_with_data(client):
    await _persist(_wgi_dtos("CHE"))
    coverage = await coverage_by_code("CHE")
    force = coverage["rule_of_law"]
    assert force.status == "available"
    live = {i.indicator_code: i for i in force.live_inputs}
    assert set(live) == {"RULE_OF_LAW_WGI_SCORE"}
    assert all(i.has_data and i.has_source_series for i in live.values())
    assert all(i.source == "world_bank" for i in live.values())


async def test_corruption_force_available_with_data(client):
    await _persist(_wgi_dtos("CHE"))
    coverage = await coverage_by_code("CHE")
    force = coverage["corruption"]
    assert force.status == "available"
    live = {i.indicator_code: i for i in force.live_inputs}
    assert set(live) == {"CONTROL_OF_CORRUPTION_WGI_SCORE"}
    assert all(i.has_data for i in live.values())


async def test_internal_conflict_force_partial_with_data(client):
    # Methodology correction (Milestone 5.3): the WGI series is an explicitly
    # incomplete proxy, so the force is capped at PARTIAL even with full data.
    await _persist(_wgi_dtos("CHE"))
    coverage = await coverage_by_code("CHE")
    force = coverage["internal_conflict"]
    assert force.status == "partial"
    live = {i.indicator_code: i for i in force.live_inputs}
    assert set(live) == {"POLITICAL_STABILITY_WGI_SCORE"}
    assert all(i.has_data for i in live.values())
    assert force.definition.coverage_ceiling == "partial"
    notes = force.definition.coverage_notes
    # the proxy caveat must not overclaim
    assert "Absence of Violence/Terrorism" in notes
    assert "does NOT measure every form" in notes
    assert "capped at PARTIAL" in notes


# --- 8: control-of-corruption semantics stay positive ----------------------------


async def test_control_of_corruption_semantics_positive_direction(client):
    force = force_definition_by_code("corruption")
    assert force.live_indicator_codes == ("CONTROL_OF_CORRUPTION_WGI_SCORE",)
    # the coverage note must explain that higher = healthier / lower corruption
    notes = force.coverage_notes
    assert "Control of Corruption" in notes
    assert "never reversed" in notes

    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        indicator = (
            await session.execute(
                select(Indicator).where(Indicator.code == "CONTROL_OF_CORRUPTION_WGI_SCORE")
            )
        ).scalar_one()
    assert indicator.strength_direction == "positive"

    # persisted raw values are never flipped or reinterpreted
    await _persist([_dto("CHN", "CONTROL_OF_CORRUPTION_WGI_SCORE", WGI_CC, 49.65)])
    coverage = await coverage_by_code("CHN")
    live = {i.indicator_code: i for i in coverage["corruption"].live_inputs}
    assert live["CONTROL_OF_CORRUPTION_WGI_SCORE"].has_data


# --- 9: country scoping -----------------------------------------------------------


async def test_wgi_coverage_is_country_scoped(client):
    await _persist(_wgi_dtos("CHE"))
    che = await coverage_by_code("CHE")
    usa = await coverage_by_code("USA")
    assert che["rule_of_law"].status == "available"
    assert usa["rule_of_law"].status == "defined_not_sourced"
    usa_live = {i.indicator_code: i for i in usa["rule_of_law"].live_inputs}
    assert all(not i.has_data for i in usa_live.values())


# --- 10: Global openness remains missing ------------------------------------------


async def test_global_openness_remains_missing_with_wgi_data(client):
    await _persist(_wgi_dtos("CHE"))
    coverage = await coverage_by_code("CHE")
    openness = coverage["global_openness"]
    assert openness.status == "missing"
    assert openness.live_inputs == []
    assert openness.candidate_inputs == []


# --- 11: no force score fields ------------------------------------------------------


async def test_wgi_api_payload_has_no_score_fields(client):
    await _persist(_wgi_dtos("CHE"))
    response = await client.get("/api/countries/CHE/force-coverage")
    assert response.status_code == 200
    data = response.json()

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

    keys = _keys(data)
    assert not ({"score", "force_score", "phase", "weight", "trend"} & keys)


# --- 12: force API remains 17 forces -------------------------------------------------


async def test_wgi_api_still_returns_17_forces(client):
    await _persist(_wgi_dtos("CHE"))
    response = await client.get("/api/countries/CHE/force-coverage")
    assert response.status_code == 200
    data = response.json()
    assert data["country"] == "CHE"
    assert len(data["forces"]) == 17
    by_code = {f["code"]: f for f in data["forces"]}
    assert by_code["rule_of_law"]["status"] == "available"
    assert by_code["corruption"]["status"] == "available"
    assert by_code["internal_conflict"]["status"] == "partial"