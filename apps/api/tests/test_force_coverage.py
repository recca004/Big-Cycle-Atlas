"""Milestone 5.0 offline tests: 17-force definitions, indicator→force mapping,
per-country deterministic coverage, force-coverage API.

Synthetic DTOs persisted via the real persistence layer, seeded SQLite, no
external API calls. Coverage is data availability only — no scores exist.
"""
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.cycle.force_definitions import (
    FORCE_DEFINITIONS,
    force_definition_by_code,
)
from app.data_sources.base import ObservationDTO
from app.db import session as session_module
from app.models import Country
from app.services.force_coverage_service import get_force_coverage
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)

WB_GDP_GROWTH = "NY.GDP.MKTP.KD.ZG"
WB_CPI = "FP.CPI.TOTL.ZG"
OECD_PROD = "DSD_PDB@DF_PDB/{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP"
OECD_ULC = "DSD_PDB@DF_PDB_ULC_Q/{cc}.Q.ULCE._T.PA.V.GY.S.NC"
BIS_GAP = "WS_CREDIT_GAP/Q.{cc}.P.A.C"
BIS_DSR = "WS_DSR/Q.{cc}.P"

EXPECTED_17 = [
    "leadership_capabilities",
    "education",
    "character_determination",
    "rule_of_law",
    "corruption",
    "resource_allocation_efficiency",
    "global_openness",
    "productivity_output_growth",
    "cost_competitiveness",
    "trade_capital_flows",
    "infrastructure_investment",
    "indebtedness",
    "military_strength",
    "wealth_opportunity_values_gaps",
    "internal_conflict",
    "geography",
    "acts_of_nature",
]


def _dto(
    iso3: str,
    indicator: str,
    external: str,
    source: str,
    value: float,
    day: date,
) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code=indicator,
        external_series_code=external,
        period=day.year,
        value=value,
        unit="test unit",
        source_key=source,
        observation_date=day,
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


async def _persist(dtos: list[ObservationDTO]) -> None:
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


async def _coverage(iso3: str) -> dict[str, object]:
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        country_id = (
            await session.execute(select(Country.id).where(Country.iso3 == iso3))
        ).scalar_one()
        items = await get_force_coverage(session, country_id)
        return {item.definition.code: item for item in items}


def _che_full_dtos() -> list[ObservationDTO]:
    return [
        _dto("CHE", "GDP_GROWTH", WB_GDP_GROWTH, "world_bank", 1.4, date(2025, 1, 1)),
        _dto("CHE", "INFLATION_CPI", WB_CPI, "world_bank", 0.15, date(2025, 1, 1)),
        _dto(
            "CHE",
            "LABOUR_PRODUCTIVITY_PER_HOUR",
            OECD_PROD,
            "oecd",
            90.52,
            date(2025, 1, 1),
        ),
        _dto(
            "CHE",
            "UNIT_LABOUR_COST_GROWTH",
            OECD_ULC,
            "oecd",
            -0.11,
            date(2025, 10, 1),
        ),
        _dto("CHE", "CREDIT_TO_GDP_GAP", BIS_GAP, "bis", -17.04, date(2025, 10, 1)),
        _dto("CHE", "DEBT_SERVICE_RATIO", BIS_DSR, "bis", 15.4, date(2025, 10, 1)),
    ]


# --- 1–4: definitions and known mappings -------------------------------------


async def test_exactly_17_force_definitions(client):
    assert len(FORCE_DEFINITIONS) == 17
    codes = [f.code for f in FORCE_DEFINITIONS]
    assert codes == EXPECTED_17  # packages/shared FORCES ordering
    assert len(set(codes)) == 17
    for force in FORCE_DEFINITIONS:
        assert force.name
        assert force.description


async def test_productivity_mapping_known(client):
    force = force_definition_by_code("productivity_output_growth")
    assert force is not None
    assert set(force.live_indicator_codes) == {
        "GDP_GROWTH",
        "LABOUR_PRODUCTIVITY_PER_HOUR",
    }


async def test_cost_competitiveness_mapping_known(client):
    force = force_definition_by_code("cost_competitiveness")
    assert force is not None
    assert set(force.live_indicator_codes) == {
        "UNIT_LABOUR_COST_GROWTH",
        "INFLATION_CPI",
    }


async def test_indebtedness_mapping_known(client):
    force = force_definition_by_code("indebtedness")
    assert force is not None
    assert set(force.live_indicator_codes) == {
        "CREDIT_TO_GDP_GAP",
        "DEBT_SERVICE_RATIO",
        "GOVERNMENT_DEBT_GDP",
    }


# --- 5–8: coverage statuses ---------------------------------------------------


async def test_che_coverage_full(client):
    await _persist(_che_full_dtos())
    coverage = await _coverage("CHE")

    assert coverage["productivity_output_growth"].status == "available"
    assert coverage["cost_competitiveness"].status == "available"
    # Indebtedness: 2 of 3 live inputs have data (GOVERNMENT_DEBT_GDP has no
    # observation in this fixture) → partial, not available.
    assert coverage["indebtedness"].status == "partial"

    live = {
        i.indicator_code: i
        for i in coverage["productivity_output_growth"].live_inputs
    }
    assert live["GDP_GROWTH"].has_data
    assert live["GDP_GROWTH"].source == "world_bank"
    assert live["LABOUR_PRODUCTIVITY_PER_HOUR"].has_data
    assert live["LABOUR_PRODUCTIVITY_PER_HOUR"].source == "oecd"


async def test_chn_partial_productivity_because_oecd_absent(client):
    # CHN has WB GDP growth but no OECD labour productivity (real-world no-data)
    await _persist(
        [_dto("CHN", "GDP_GROWTH", WB_GDP_GROWTH, "world_bank", 5.0, date(2025, 1, 1))]
    )
    coverage = await _coverage("CHN")

    productivity = coverage["productivity_output_growth"]
    assert productivity.status == "partial"
    by_code = {i.indicator_code: i for i in productivity.live_inputs}
    assert by_code["GDP_GROWTH"].has_data
    assert not by_code["LABOUR_PRODUCTIVITY_PER_HOUR"].has_data
    # ULC is sourced globally but CHN has no observations → defined, not sourced
    assert coverage["cost_competitiveness"].status == "defined_not_sourced"
    # BIS covers all 8 countries in reality, but no rows persisted here


async def test_catalog_only_indicator_does_not_count_as_live(client):
    coverage = await _coverage("CHE")

    education = coverage["education"]
    # Education now has TERTIARY_ATTAINMENT_25_34 as a live input (Sprint 5.20)
    # but with no observations persisted → defined_not_sourced.
    # PARTIAL ceiling (one tertiary series cannot make Education AVAILABLE).
    assert education.status == "defined_not_sourced"
    live_codes = {i.indicator_code for i in education.live_inputs}
    assert "TERTIARY_ATTAINMENT_25_34" in live_codes
    # TERTIARY_ENROLLMENT is now a candidate (not live)
    candidate_codes = {i.indicator_code for i in education.candidate_inputs}
    assert "TERTIARY_ENROLLMENT" in candidate_codes


async def test_completely_missing_force_stays_missing(client):
    await _persist(_che_full_dtos())
    coverage = await _coverage("CHE")
    # no live or candidate catalog inputs defined for these forces
    assert coverage["leadership_capabilities"].status == "missing"
    assert coverage["geography"].status == "missing"
    # military_strength now has live inputs (M5.4) but no data in this fixture
    assert coverage["military_strength"].status == "defined_not_sourced"


# --- 9–11: API -----------------------------------------------------------------


async def test_api_returns_all_17_forces(client):
    await _persist(_che_full_dtos())
    response = await client.get("/api/countries/CHE/force-coverage")
    assert response.status_code == 200
    data = response.json()
    assert data["country"] == "CHE"
    assert len(data["forces"]) == 17
    assert [f["code"] for f in data["forces"]] == EXPECTED_17

    by_code = {f["code"]: f for f in data["forces"]}
    assert by_code["productivity_output_growth"]["status"] == "available"
    assert by_code["cost_competitiveness"]["status"] == "available"
    assert by_code["indebtedness"]["status"] == "partial"
    assert by_code["education"]["status"] == "defined_not_sourced"
    assert by_code["trade_capital_flows"]["status"] == "defined_not_sourced"
    assert by_code["military_strength"]["status"] == "defined_not_sourced"  # M5.4 promotion, no data in this fixture

    prod_live = by_code["productivity_output_growth"]["live_inputs"]
    sources = {i["indicator_code"]: i["source"] for i in prod_live}
    assert sources["GDP_GROWTH"] == "world_bank"
    assert sources["LABOUR_PRODUCTIVITY_PER_HOUR"] == "oecd"


async def test_api_country_scoping_no_leak(client):
    # OECD productivity exists for USA only; CHE must not see it (ISSUE-004 discipline)
    await _persist(
        [
            _dto(
                "USA",
                "LABOUR_PRODUCTIVITY_PER_HOUR",
                OECD_PROD,
                "oecd",
                85.6,
                date(2025, 1, 1),
            )
        ]
    )
    che = (await client.get("/api/countries/CHE/force-coverage")).json()
    che_prod = next(f for f in che["forces"] if f["code"] == "productivity_output_growth")
    assert che_prod["status"] == "defined_not_sourced"
    assert all(not i["has_data"] for i in che_prod["live_inputs"])

    usa = (await client.get("/api/countries/USA/force-coverage")).json()
    usa_prod = next(f for f in usa["forces"] if f["code"] == "productivity_output_growth")
    assert usa_prod["status"] == "partial"  # productivity but no GDP growth rows
    by_code = {i["indicator_code"]: i for i in usa_prod["live_inputs"]}
    assert by_code["LABOUR_PRODUCTIVITY_PER_HOUR"]["has_data"]

    response = await client.get("/api/countries/ZZZ/force-coverage")
    assert response.status_code == 404


async def test_api_response_has_no_score_fields(client):
    await _persist(_che_full_dtos())
    data = (await client.get("/api/countries/CHE/force-coverage")).json()

    def _keys(obj) -> set[str]:
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
    assert "score" not in keys
    assert "force_score" not in keys
    assert "phase" not in keys
    assert "trend" not in keys