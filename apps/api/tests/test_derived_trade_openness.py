"""Sprint 6.11 tests: first executable DerivedAlignedValue — TRADE_OPENNESS_GDP.

Tests the derived computation TRADE_OPENNESS_GDP = EXPORTS_GDP + IMPORTS_GDP
using the DEC-037 contract and the DEC-038 formula approval.

Covers the 20 required test cases:
1. exact arithmetic: 40 + 30 = 70
2. values above 100 remain valid and unclamped
3. country isolation
4. same scoring snapshot
5. source-period mismatch produces None
6. missing exports produces None
7. missing imports produces None
8. real zero input remains a real zero, not missing
9. component observation identities are retained
10. component source-series identities are retained
11. component data-source identities are retained
12. distinct vintages remain distinct
13. latest-vintage selection inherited from alignment
14. period-complete rules inherited
15. no future-period selection
16. unsafe component keeps derived backtest_safe False
17. no raw Observation is created
18. no DB writes
19. existing align_observation_as_of behavior unchanged
20. existing normalization/force tests unchanged (verified by full pytest)

Uses SQLite and seeded data only — no external API calls.
"""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.cycle.normalization_definitions import ScoringPeriod
from app.data_sources.base import ObservationDTO
from app.db import session as session_module
from app.models import Observation
from app.services.alignment_service import align_observation_as_of
from app.services.derived_indicator_service import (
    TRADE_OPENNESS_GDP_CODE,
    TRADE_OPENNESS_GDP_FORMULA_ID,
    TRADE_OPENNESS_GDP_FORMULA_VERSION,
    derive_trade_openness_as_of,
)
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)

# World Bank external series codes for the two components
EXPORTS_EXT = "NE.EXP.GNFS.ZS"
IMPORTS_EXT = "NE.IMP.GNFS.ZS"


def _wb_dto(
    iso3: str,
    indicator: str,
    external: str,
    year: int,
    value: float,
) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code=indicator,
        external_series_code=external,
        period=year,
        value=value,
        unit="% of GDP",
        source_key="world_bank",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


def _exports_dto(iso3: str, year: int, value: float) -> ObservationDTO:
    return _wb_dto(iso3, "EXPORTS_GDP", EXPORTS_EXT, year, value)


def _imports_dto(iso3: str, year: int, value: float) -> ObservationDTO:
    return _wb_dto(iso3, "IMPORTS_GDP", IMPORTS_EXT, year, value)


async def _persist(dtos: list[ObservationDTO]) -> None:
    async with session_module._sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


async def _derive(iso3: str, scoring_period: ScoringPeriod):
    async with session_module._sessionmaker() as session:
        return await derive_trade_openness_as_of(session, iso3, scoring_period)


async def _align(iso3: str, indicator: str, scoring_period: ScoringPeriod):
    async with session_module._sessionmaker() as session:
        return await align_observation_as_of(session, iso3, indicator, scoring_period)


async def _observation_count() -> int:
    async with session_module._sessionmaker() as session:
        return (
            await session.execute(select(func.count()).select_from(Observation))
        ).scalar_one()


# --- 1. Exact arithmetic: 40 + 30 = 70 ------------------------------------------


async def test_exact_arithmetic(client):
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    assert result.derived_value is not None
    assert result.derived_value == 70.0
    assert result.derived_indicator_code == TRADE_OPENNESS_GDP_CODE
    assert result.formula_id == TRADE_OPENNESS_GDP_FORMULA_ID
    assert result.formula_version == TRADE_OPENNESS_GDP_FORMULA_VERSION


# --- 2. Values above 100 remain valid and unclamped ---------------------------


async def test_values_above_100_valid(client):
    await _persist([
        _exports_dto("USA", 2024, 60.0),
        _imports_dto("USA", 2024, 55.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    assert result.derived_value == 115.0
    assert result.derived_value > 100  # unclamped


# --- 3. Country isolation ------------------------------------------------------


async def test_country_isolation(client):
    """USA's exports must not appear in CHE's derived value."""
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
        _exports_dto("CHE", 2024, 70.0),
        _imports_dto("CHE", 2024, 60.0),
    ])
    usa = await _derive("USA", ScoringPeriod(2025, 4))
    che = await _derive("CHE", ScoringPeriod(2025, 4))
    assert usa.derived_value == 70.0
    assert che.derived_value == 130.0
    assert usa.country_iso3 == "USA"
    assert che.country_iso3 == "CHE"
    # USA components must be USA, CHE components must be CHE
    for comp in usa.components:
        if comp.aligned_value is not None:
            assert comp.aligned_value.country_iso3 == "USA"
    for comp in che.components:
        if comp.aligned_value is not None:
            assert comp.aligned_value.country_iso3 == "CHE"


# --- 4. Same scoring snapshot --------------------------------------------------


async def test_same_scoring_snapshot(client):
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    sp = ScoringPeriod(2025, 4)
    result = await _derive("USA", sp)
    assert result.scoring_period == sp
    for comp in result.components:
        if comp.aligned_value is not None:
            assert comp.aligned_value.scoring_period == sp


# --- 5. Source-period mismatch produces None -----------------------------------


async def test_source_period_mismatch_produces_none(client):
    """Exports from 2024 + imports from 2023 must NOT produce a value."""
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2023, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    # Both components are present (aligned) but source periods differ
    # — derived value must be None
    assert result.derived_value is None
    # Both components should still carry their provenance
    exports_comp = [c for c in result.components if c.indicator_code == "EXPORTS_GDP"][0]
    imports_comp = [c for c in result.components if c.indicator_code == "IMPORTS_GDP"][0]
    assert exports_comp.aligned_value is not None
    assert exports_comp.aligned_value.source_period == "2024"
    assert imports_comp.aligned_value is not None
    assert imports_comp.aligned_value.source_period == "2023"


# --- 6. Missing exports produces None ------------------------------------------


async def test_missing_exports_produces_none(client):
    await _persist([
        _imports_dto("USA", 2024, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    assert result.derived_value is None
    exports_comp = [c for c in result.components if c.indicator_code == "EXPORTS_GDP"][0]
    imports_comp = [c for c in result.components if c.indicator_code == "IMPORTS_GDP"][0]
    assert exports_comp.aligned_value is None
    assert exports_comp.missing_reason is not None
    assert imports_comp.aligned_value is not None
    assert imports_comp.missing_reason is None


# --- 7. Missing imports produces None ------------------------------------------


async def test_missing_imports_produces_none(client):
    await _persist([
        _exports_dto("USA", 2024, 40.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    assert result.derived_value is None
    exports_comp = [c for c in result.components if c.indicator_code == "EXPORTS_GDP"][0]
    imports_comp = [c for c in result.components if c.indicator_code == "IMPORTS_GDP"][0]
    assert exports_comp.aligned_value is not None
    assert imports_comp.aligned_value is None
    assert imports_comp.missing_reason is not None


# --- 8. Real zero input remains a real zero, not missing -----------------------


async def test_real_zero_input_not_missing(client):
    """A real 0.0 value is a valid observation, not a missing one."""
    await _persist([
        _exports_dto("USA", 2024, 0.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    assert result.derived_value is not None
    assert result.derived_value == 30.0  # 0.0 + 30.0
    exports_comp = [c for c in result.components if c.indicator_code == "EXPORTS_GDP"][0]
    assert exports_comp.aligned_value is not None
    assert exports_comp.aligned_value.raw_value == 0.0
    assert exports_comp.missing_reason is None


# --- 9. Component observation identities are retained -------------------------


async def test_observation_identities_retained(client):
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    for comp in result.components:
        assert comp.aligned_value is not None
        assert comp.observation_id is not None
        assert comp.observation_id > 0
    # The two components must have distinct observation IDs
    obs_ids = [c.observation_id for c in result.components]
    assert len(set(obs_ids)) == 2


# --- 10. Component source-series identities are retained -----------------------


async def test_source_series_identities_retained(client):
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    for comp in result.components:
        assert comp.aligned_value is not None
        assert comp.source_series_id is not None
        assert comp.source_series_id > 0


# --- 11. Component data-source identities are retained -------------------------


async def test_data_source_identities_retained(client):
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    for comp in result.components:
        assert comp.aligned_value is not None
        assert comp.data_source_id is not None
        assert comp.data_source_id > 0


# --- 12. Distinct vintages remain distinct -------------------------------------


async def test_distinct_vintages_remain_distinct(client):
    """Exports vintage 2 + imports vintage 1 — both vintages preserved."""
    await _persist([_exports_dto("USA", 2024, 40.0)])
    await _persist([_exports_dto("USA", 2024, 45.0)])  # revision -> vintage 2
    await _persist([_imports_dto("USA", 2024, 30.0)])  # vintage 1
    result = await _derive("USA", ScoringPeriod(2025, 4))
    assert result.derived_value == 75.0  # 45.0 (vintage 2) + 30.0 (vintage 1)
    exports_comp = [c for c in result.components if c.indicator_code == "EXPORTS_GDP"][0]
    imports_comp = [c for c in result.components if c.indicator_code == "IMPORTS_GDP"][0]
    assert exports_comp.aligned_value.vintage_number == 2
    assert imports_comp.aligned_value.vintage_number == 1


# --- 13. Latest-vintage selection inherited from alignment ---------------------


async def test_latest_vintage_inherited(client):
    """The derived layer must use the latest vintage, same as alignment."""
    await _persist([_exports_dto("USA", 2024, 40.0)])
    await _persist([_exports_dto("USA", 2024, 50.0)])  # vintage 2
    await _persist([_imports_dto("USA", 2024, 30.0)])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    # Must use vintage 2 (50.0), not vintage 1 (40.0)
    assert result.derived_value == 80.0  # 50.0 + 30.0
    exports_comp = [c for c in result.components if c.indicator_code == "EXPORTS_GDP"][0]
    assert exports_comp.aligned_value.vintage_number == 2
    assert exports_comp.aligned_value.raw_value == 50.0


# --- 14. Period-complete rules inherited ---------------------------------------


async def test_period_complete_inherited(client):
    """An annual 2024 observation is NOT eligible at 2024-Q3 (period not complete)."""
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    # 2024 annual obs is not complete until 2024-12-31, so at 2024-Q3
    # (snapshot 2024-09-30) it is NOT eligible
    result = await _derive("USA", ScoringPeriod(2024, 3))
    assert result.derived_value is None
    for comp in result.components:
        assert comp.aligned_value is None
        assert comp.missing_reason is not None
    # At 2024-Q4 (snapshot 2024-12-31) it IS eligible
    result_q4 = await _derive("USA", ScoringPeriod(2024, 4))
    assert result_q4.derived_value == 70.0


# --- 15. No future-period selection -------------------------------------------


async def test_no_future_period_selection(client):
    """A 2025 observation must not be selected at a 2024-Q4 snapshot."""
    await _persist([
        _exports_dto("USA", 2025, 40.0),
        _imports_dto("USA", 2025, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2024, 4))
    assert result.derived_value is None
    for comp in result.components:
        assert comp.aligned_value is None


# --- 16. Unsafe component keeps derived backtest_safe False --------------------


async def test_backtest_safe_false(client):
    """Derived backtest_safe must be False (release-date discipline is M9)."""
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    assert result.backtest_safe is False
    for comp in result.components:
        assert comp.component_backtest_safe is False


# --- 17. No raw Observation is created -----------------------------------------


async def test_no_raw_observation_created(client):
    """The derived service must not create any new Observation rows."""
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    count_before = await _observation_count()
    await _derive("USA", ScoringPeriod(2025, 4))
    count_after = await _observation_count()
    assert count_after == count_before


# --- 18. No DB writes ----------------------------------------------------------


async def test_no_db_writes(client):
    """The derived service must not write to the database."""
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    count_before = await _observation_count()
    # Call derive multiple times
    for _ in range(3):
        await _derive("USA", ScoringPeriod(2025, 4))
    count_after = await _observation_count()
    assert count_after == count_before


# --- 19. Existing align_observation_as_of behavior unchanged --------------------


async def test_align_observation_as_of_unchanged(client):
    """The refactored alignment must produce the same results as before."""
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    # Test that align_observation_as_of still works correctly
    exports_aligned = await _align("USA", "EXPORTS_GDP", ScoringPeriod(2025, 4))
    assert exports_aligned is not None
    assert exports_aligned.indicator_code == "EXPORTS_GDP"
    assert exports_aligned.country_iso3 == "USA"
    assert exports_aligned.raw_value == 40.0
    assert exports_aligned.source_period == "2024"
    assert exports_aligned.vintage_number == 1

    imports_aligned = await _align("USA", "IMPORTS_GDP", ScoringPeriod(2025, 4))
    assert imports_aligned is not None
    assert imports_aligned.indicator_code == "IMPORTS_GDP"
    assert imports_aligned.raw_value == 30.0

    # Test None when no eligible observation
    empty_aligned = await _align("USA", "EXPORTS_GDP", ScoringPeriod(2023, 4))
    assert empty_aligned is None


# --- 20. Formula identity and version -----------------------------------------


async def test_formula_identity_and_version(client):
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    assert result.formula_id == "trade_openness_gdp"
    assert result.formula_version == "trade-openness-gdp-v1"
    assert result.derived_indicator_code == "TRADE_OPENNESS_GDP"


# --- Additional: component indicator codes preserved ---------------------------


async def test_component_indicator_codes_preserved(client):
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    codes = [c.indicator_code for c in result.components]
    assert "EXPORTS_GDP" in codes
    assert "IMPORTS_GDP" in codes
    assert len(codes) == 2


# --- Additional: effective_period_end preserved --------------------------------


async def test_effective_period_end_preserved(client):
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    for comp in result.components:
        assert comp.aligned_value is not None
        assert comp.aligned_value.effective_period_end == date(2024, 12, 31)


# --- Additional: both components same source period produces value -------------


async def test_same_source_period_produces_value(client):
    """Both components from 2024 — derived value should be computed."""
    await _persist([
        _exports_dto("USA", 2024, 40.0),
        _imports_dto("USA", 2024, 30.0),
    ])
    result = await _derive("USA", ScoringPeriod(2025, 4))
    assert result.derived_value == 70.0
    exports_comp = [c for c in result.components if c.indicator_code == "EXPORTS_GDP"][0]
    imports_comp = [c for c in result.components if c.indicator_code == "IMPORTS_GDP"][0]
    assert exports_comp.aligned_value.source_period == "2024"
    assert imports_comp.aligned_value.source_period == "2024"
