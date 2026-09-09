"""Sprint 5.22: force signal service / DB integration tests.

Uses seeded SQLite + synthetic WGI observations persisted via the real
persistence layer. No external HTTP. No force persistence. No API.
"""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.cycle.force_definitions import ForceCoverageStatus
from app.cycle.normalization_definitions import ScoringPeriod
from app.cycle.normalizer import normalize_indicator_as_of
from app.data_sources.base import ObservationDTO
from app.db import session as session_module
from app.models import Observation
from app.services.force_signal_service import build_force_signals_as_of
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)

WGI_RL = "GOV_WGI_RL_SC"
WGI_CC = "GOV_WGI_CC_SC"
WGI_PV = "GOV_WGI_PV_SC"

WGI_INDICATORS = {
    "RULE_OF_LAW_WGI_SCORE": WGI_RL,
    "CONTROL_OF_CORRUPTION_WGI_SCORE": WGI_CC,
    "POLITICAL_STABILITY_WGI_SCORE": WGI_PV,
}


def _wgi_dto(iso3: str, year: int, value: float, indicator: str = "RULE_OF_LAW_WGI_SCORE") -> ObservationDTO:
    external = WGI_INDICATORS[indicator]
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code=indicator,
        external_series_code=external,
        period=year,
        value=value,
        unit="score 0-100",
        source_key="world_bank",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


async def _persist(dtos: list[ObservationDTO]) -> None:
    async with session_module._sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


async def _observation_count() -> int:
    async with session_module._sessionmaker() as session:
        return (
            await session.execute(select(func.count()).select_from(Observation))
        ).scalar_one()


async def _build_signals(iso3: str, period: ScoringPeriod, client=None):
    async with session_module._sessionmaker() as session:
        return await build_force_signals_as_of(session, iso3, period)


# --- 17 forces returned --------------------------------------------------------


@pytest.mark.asyncio
async def test_exactly_17_force_signals_returned(client):
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    assert len(signals) == 17


@pytest.mark.asyncio
async def test_all_17_force_codes_present(client):
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    codes = [s.force_code for s in signals]
    from app.cycle.force_definitions import FORCE_DEFINITIONS
    expected = [f.code for f in FORCE_DEFINITIONS]
    assert codes == expected  # same order too


# --- Rule of law / Corruption / Internal conflict executable -------------------


@pytest.mark.asyncio
async def test_rule_of_law_signal_equals_direct_normalized_indicator(client):
    """ForceSignal level must equal the direct normalized indicator signal."""
    # Persist WGI data for CHE
    dtos = [
        _wgi_dto("CHE", 2024, 87.32, "RULE_OF_LAW_WGI_SCORE"),
        _wgi_dto("CHE", 2019, 85.0, "RULE_OF_LAW_WGI_SCORE"),  # 5y anchor
    ]
    await _persist(dtos)
    period = ScoringPeriod(2025, 2)

    # Direct normalized signal
    async with session_module._sessionmaker() as session:
        direct = await normalize_indicator_as_of(
            session, "CHE", "RULE_OF_LAW_WGI_SCORE", period
        )
    assert direct is not None

    # Force signal
    signals = await _build_signals("CHE", period)
    rl = next(s for s in signals if s.force_code == "rule_of_law")
    assert rl.level_score == direct.level_score
    assert rl.scoring_component_indicator == "RULE_OF_LAW_WGI_SCORE"


@pytest.mark.asyncio
async def test_corruption_signal_equals_direct_normalized_indicator(client):
    dtos = [
        _wgi_dto("CHE", 2024, 88.48, "CONTROL_OF_CORRUPTION_WGI_SCORE"),
        _wgi_dto("CHE", 2019, 86.0, "CONTROL_OF_CORRUPTION_WGI_SCORE"),
    ]
    await _persist(dtos)
    period = ScoringPeriod(2025, 2)
    async with session_module._sessionmaker() as session:
        direct = await normalize_indicator_as_of(
            session, "CHE", "CONTROL_OF_CORRUPTION_WGI_SCORE", period
        )
    assert direct is not None
    signals = await _build_signals("CHE", period)
    corr = next(s for s in signals if s.force_code == "corruption")
    assert corr.level_score == direct.level_score


@pytest.mark.asyncio
async def test_internal_conflict_signal_equals_direct_normalized_indicator(client):
    dtos = [
        _wgi_dto("CHE", 2024, 82.65, "POLITICAL_STABILITY_WGI_SCORE"),
        _wgi_dto("CHE", 2019, 80.0, "POLITICAL_STABILITY_WGI_SCORE"),
    ]
    await _persist(dtos)
    period = ScoringPeriod(2025, 2)
    async with session_module._sessionmaker() as session:
        direct = await normalize_indicator_as_of(
            session, "CHE", "POLITICAL_STABILITY_WGI_SCORE", period
        )
    assert direct is not None
    signals = await _build_signals("CHE", period)
    ic = next(s for s in signals if s.force_code == "internal_conflict")
    assert ic.level_score == direct.level_score


# --- Internal conflict stays PARTIAL ------------------------------------------


@pytest.mark.asyncio
async def test_internal_conflict_stays_partial(client):
    dtos = [
        _wgi_dto("CHE", 2024, 82.65, "POLITICAL_STABILITY_WGI_SCORE"),
        _wgi_dto("CHE", 2019, 80.0, "POLITICAL_STABILITY_WGI_SCORE"),
    ]
    await _persist(dtos)
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    ic = next(s for s in signals if s.force_code == "internal_conflict")
    assert ic.coverage_status is ForceCoverageStatus.partial
    assert ic.coverage_ceiling is ForceCoverageStatus.partial
    # Level can still be non-None despite PARTIAL — coverage != strength
    if ic.level_score is not None:
        assert ic.level_score > 0  # not zeroed by PARTIAL


# --- Indebtedness: coverage may be AVAILABLE while score None ------------------


@pytest.mark.asyncio
async def test_indebtedness_force_level_none(client):
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    debt = next(s for s in signals if s.force_code == "indebtedness")
    assert debt.level_score is None
    assert debt.relative_score is None
    assert debt.momentum is None


# --- Deferred indicators don't crash the 17-force build ------------------------


@pytest.mark.asyncio
async def test_deferred_indicators_dont_crash_build(client):
    """Gini, WID, etc. are SUPPORTING_CONTEXT — must not crash.

    Education is now PROXY_CONDITION (Sprint 6.4): with no observation it
    returns level_score None and the indicator lands in missing_components
    (not deferred_components).
    """
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    edu = next(s for s in signals if s.force_code == "education")
    assert edu.level_score is None
    assert "TERTIARY_ATTAINMENT_25_34" in edu.missing_components


# --- No raw writes / no derived persistence ------------------------------------


@pytest.mark.asyncio
async def test_no_raw_observation_writes(client):
    count_before = await _observation_count()
    await _build_signals("CHE", ScoringPeriod(2025, 2))
    count_after = await _observation_count()
    assert count_after == count_before  # no writes


@pytest.mark.asyncio
async def test_no_api_publication(client):
    """No force_signals API module should exist."""
    import importlib
    try:
        importlib.import_module("app.api.force_signals")
        raise AssertionError("app.api.force_signals should not exist")
    except ImportError:
        pass  # expected


# --- Confidence / backtest / versions ------------------------------------------


@pytest.mark.asyncio
async def test_confidence_none_on_all_signals(client):
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    for s in signals:
        assert s.confidence is None


@pytest.mark.asyncio
async def test_backtest_safe_false_on_all_signals(client):
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    for s in signals:
        assert s.backtest_safe is False


@pytest.mark.asyncio
async def test_versions_on_all_signals(client):
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    for s in signals:
        assert s.force_model_version == "force-aggregation-v0.2"
        assert s.normalization_model_version == "normalization-v0.7"


# --- Country isolation ---------------------------------------------------------


@pytest.mark.asyncio
async def test_country_isolation(client):
    """CHE signals must not depend on USA data."""
    dtos_che = [
        _wgi_dto("CHE", 2024, 87.32, "RULE_OF_LAW_WGI_SCORE"),
        _wgi_dto("CHE", 2019, 85.0, "RULE_OF_LAW_WGI_SCORE"),
    ]
    dtos_usa = [
        _wgi_dto("USA", 2024, 70.0, "RULE_OF_LAW_WGI_SCORE"),
        _wgi_dto("USA", 2019, 68.0, "RULE_OF_LAW_WGI_SCORE"),
    ]
    await _persist(dtos_che + dtos_usa)
    period = ScoringPeriod(2025, 2)
    che_signals = await _build_signals("CHE", period)
    usa_signals = await _build_signals("USA", period)
    che_rl = next(s for s in che_signals if s.force_code == "rule_of_law")
    usa_rl = next(s for s in usa_signals if s.force_code == "rule_of_law")
    assert che_rl.level_score != usa_rl.level_score  # different countries


# --- Pre-first WGI history -> None --------------------------------------------


@pytest.mark.asyncio
async def test_pre_first_wgi_history_returns_none(client):
    """A country with NO WGI data must get None, not zero."""
    # CHN has no WGI data in this test DB (we only persisted CHE + USA above)
    # Use a country we know has no data in the test context
    signals = await _build_signals("CHN", ScoringPeriod(1995, 1))
    rl = next(s for s in signals if s.force_code == "rule_of_law")
    assert rl.level_score is None  # missing -> None, not zero


# --- Multi-country regression --------------------------------------------------


@pytest.mark.asyncio
async def test_multi_country_regression(client):
    """Build signals for multiple countries — all return 17 forces."""
    dtos = []
    for iso3 in ("CHE", "USA", "GBR", "JPN"):
        for ind in WGI_INDICATORS:
            dtos.append(_wgi_dto(iso3, 2024, 75.0, ind))
            dtos.append(_wgi_dto(iso3, 2019, 73.0, ind))
    await _persist(dtos)
    period = ScoringPeriod(2025, 2)
    for iso3 in ("CHE", "USA", "GBR", "JPN"):
        signals = await _build_signals(iso3, period)
        assert len(signals) == 17
        rl = next(s for s in signals if s.force_code == "rule_of_law")
        assert rl.level_score == 75.0  # all same value

