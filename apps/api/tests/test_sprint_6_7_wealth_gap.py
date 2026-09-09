"""Sprint 6.7 (DEC-034): WID wealth COMPLEMENT_0_100 + fifth executable force.

Regression matrix (Parts A-G):
- A: COMPLEMENT_0_100 level (raw 0 -> 100, raw 1 -> 0, midpoint 0.5 -> 50,
     exact float, out-of-range raises, no clamping, raw preserved)
- B: Missing/stale behavior (missing->None, stale->None, never zero,
     freshness never rescales)
- C: Dimension separation (WID relative/momentum/confidence None,
     relative_family/momentum_family are None not just gated)
- D: Execution-gate regression (WID momentum None, relative_score None)
- E: WGI/Education/DSR/credit-gap regression (unchanged)
- F: Force behavior (Wealth-gap IDENTITY_SINGLE, PROXY_CONDITION, exact level
     copy, PARTIAL, Gini SUPPORTING_CONTEXT, relative/momentum/confidence
     None, backtest_safe False, missing/stale->None, no equal weighting,
     no coverage scaling)
- G: 17-force orchestration (exactly 17, 5 executable at usable snapshot,
     12 intentionally unscored, Wealth-gap is the fifth, other forces
     unaffected)

No external HTTP. No force persistence. No public API.
"""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.cycle.force_aggregation_definitions import (
    FORCE_AGGREGATION_CONFIGS,
    FORCE_AGGREGATION_VERSION,
    ForceAggregationMode,
    ForceDimensionMode,
    ForceIndicatorRole,
    aggregation_mode,
)
from app.cycle.force_definitions import FORCE_DEFINITIONS, ForceCoverageStatus
from app.cycle.force_signal import aggregate_force_from_signals
from app.cycle.normalization_definitions import (
    CURRENT_MODEL_VERSION,
    NormalizationFamily,
    NormalizedSignal,
    ScoringPeriod,
    get_normalization_spec,
)
from app.cycle.normalizer import (
    NormalizationDataError,
    normalize_indicator_as_of,
)
from app.data_sources.base import ObservationDTO
from app.db import session as session_module
from app.models import Observation
from app.services.force_signal_service import build_force_signals_as_of
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)

WEALTH_CODE = "WID/shwealj992/p90p100"

WGI_RL = "GOV_WGI_RL_SC"
WGI_CC = "GOV_WGI_CC_SC"
WGI_PV = "GOV_WGI_PV_SC"

WGI_INDICATORS = {
    "RULE_OF_LAW_WGI_SCORE": WGI_RL,
    "CONTROL_OF_CORRUPTION_WGI_SCORE": WGI_CC,
    "POLITICAL_STABILITY_WGI_SCORE": WGI_PV,
}

_EDU_EXTERNAL_CODE = (
    "OECD.EDU.IMEP,DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA,1.0/"
    "{cc}._T.Y25T34.ISCED11A_5T8._T.POP._Z._T._Z."
    "ED_NED.POP._Z.PT_POP_SEX_AGE.OBS._Z.NEAC.A"
)


def _wealth_dto(iso3: str, year: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code="WEALTH_SHARE_TOP_10",
        external_series_code=WEALTH_CODE,
        period=year,
        value=value,
        unit="share (0-1)",
        source_key="wid",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


def _wgi_dto(iso3: str, year: int, value: float, indicator: str = "RULE_OF_LAW_WGI_SCORE") -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code=indicator,
        external_series_code=WGI_INDICATORS[indicator],
        period=year,
        value=value,
        unit="score 0-100",
        source_key="world_bank",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


def _edu_dto(iso3: str, year: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code="TERTIARY_ATTAINMENT_25_34",
        external_series_code=_EDU_EXTERNAL_CODE,
        period=year,
        value=value,
        unit="percent",
        source_key="oecd",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


async def _persist(dtos: list[ObservationDTO]) -> None:
    async with session_module._sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


async def _normalize(iso3: str, indicator: str, scoring_period: ScoringPeriod, **kwargs):
    async with session_module._sessionmaker() as session:
        return await normalize_indicator_as_of(
            session, iso3, indicator, scoring_period, **kwargs
        )


async def _build_signals(iso3: str, period: ScoringPeriod):
    async with session_module._sessionmaker() as session:
        return await build_force_signals_as_of(session, iso3, period)


async def _observation_count() -> int:
    async with session_module._sessionmaker() as session:
        return (
            await session.execute(select(func.count()).select_from(Observation))
        ).scalar_one()


# --- Part A: COMPLEMENT_0_100 level ------------------------------------------


@pytest.mark.asyncio
async def test_wealth_level_raw_zero_equals_hundred(client):
    """raw 0 -> level 100 (bottom 90% holds all wealth)."""
    await _persist([_wealth_dto("CHE", 2024, 0.0)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.level_score == 100.0


@pytest.mark.asyncio
async def test_wealth_level_raw_one_equals_zero(client):
    """raw 1 -> level 0 (top 10% holds all wealth)."""
    await _persist([_wealth_dto("CHE", 2024, 1.0)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.level_score == 0.0


@pytest.mark.asyncio
async def test_wealth_level_ordinary_value(client):
    """raw 0.65 -> level 35."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.level_score == pytest.approx(35.0)


@pytest.mark.asyncio
async def test_wealth_level_midpoint_semantics(client):
    """raw 0.50 -> level 50 (bottom 90% holds half of wealth)."""
    await _persist([_wealth_dto("CHE", 2024, 0.50)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.level_score == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_wealth_level_exact_float(client):
    """raw 0.4074 -> level 100*(1-0.4074) = 59.26 exactly."""
    raw = 0.4074
    expected = 100.0 * (1.0 - raw)
    await _persist([_wealth_dto("CHE", 2024, raw)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.level_score == expected


@pytest.mark.asyncio
async def test_wealth_out_of_range_negative_raises(client):
    """raw < 0 raises NormalizationDataError — no clamp."""
    await _persist([_wealth_dto("FRA", 2024, -0.01)])
    with pytest.raises(NormalizationDataError):
        await _normalize("FRA", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))


@pytest.mark.asyncio
async def test_wealth_out_of_range_above_one_raises(client):
    """raw > 1 raises NormalizationDataError — no clamp."""
    await _persist([_wealth_dto("GBR", 2024, 1.01)])
    with pytest.raises(NormalizationDataError):
        await _normalize("GBR", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))


@pytest.mark.asyncio
async def test_wealth_raw_value_preserved(client):
    """The raw Observation value is preserved unchanged in the signal."""
    await _persist([_wealth_dto("CHE", 2024, 0.7234)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.raw_value == 0.7234  # raw preserved, not altered


@pytest.mark.asyncio
async def test_wealth_method_is_complement_0_100(client):
    """The method field is COMPLEMENT_0_100."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.method is NormalizationFamily.complement_0_100


@pytest.mark.asyncio
async def test_wealth_model_version_v0_8(client):
    """The model_version is normalization-v0.8."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.model_version == "normalization-v0.8"


# --- Part B: Missing/stale behavior ------------------------------------------


@pytest.mark.asyncio
async def test_wealth_missing_observation_returns_none(client):
    """No observation -> no signal (None, never zero)."""
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is None


@pytest.mark.asyncio
async def test_wealth_stale_observation_returns_none(client):
    """A 2010 observation is stale at 2025-Q4 -> None."""
    await _persist([_wealth_dto("CHN", 2010, 0.70)])
    signal = await _normalize("CHN", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 4))
    assert signal is None  # stale, never zero


@pytest.mark.asyncio
async def test_wealth_missing_never_becomes_zero(client):
    """Missing observation must never produce a zero score."""
    signal = await _normalize("JPN", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is None
    assert signal is not 0


@pytest.mark.asyncio
async def test_wealth_freshness_never_scales_score(client):
    """Freshness gates usability but NEVER scales the complement score."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.level_score == pytest.approx(35.0)  # exact, not scaled
    assert signal.freshness_factor is not None
    assert 0.0 <= signal.freshness_factor <= 1.0


# --- Part C: Dimension separation ---------------------------------------------


@pytest.mark.asyncio
async def test_wealth_relative_is_none(client):
    """WID relative_score stays None (DEC-034: not approved)."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.relative_score is None
    assert signal.relative_rank is None
    assert signal.reference_universe_id is None


@pytest.mark.asyncio
async def test_wealth_momentum_is_none(client):
    """WID momentum stays None (DEC-034: not approved)."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.momentum is None
    assert signal.momentum_window_years is None
    assert signal.momentum_windows == ()


@pytest.mark.asyncio
async def test_wealth_confidence_is_none(client):
    """WID confidence stays None (composition unresolved)."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.confidence is None


@pytest.mark.asyncio
async def test_wealth_backtest_safe_false(client):
    """WID backtest_safe must be False."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.backtest_safe is False


def test_wealth_spec_relative_family_is_none():
    """The registry spec has relative_family = None (not just gated)."""
    spec = get_normalization_spec("WEALTH_SHARE_TOP_10")
    assert spec.level_family is NormalizationFamily.complement_0_100
    assert spec.relative_family is None
    assert spec.momentum_family is None


# --- Part D: Execution-gate regression ----------------------------------------


@pytest.mark.asyncio
async def test_wealth_momentum_remains_none(client):
    """After COMPLEMENT_0_100, momentum MUST remain None."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.momentum is None


@pytest.mark.asyncio
async def test_wealth_relative_remains_none(client):
    """After COMPLEMENT_0_100, relative_score MUST remain None."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signal = await _normalize("CHE", "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.relative_score is None


# --- Part E: WGI/Education/DSR/credit-gap regression (unchanged) ---------------


@pytest.mark.asyncio
async def test_wgi_level_unchanged(client):
    """WGI x3 level_score must equal the raw value (unchanged by Sprint 6.7)."""
    await _persist([_wgi_dto("CHE", 2024, 87.32, "RULE_OF_LAW_WGI_SCORE")])
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.level_score == 87.32


@pytest.mark.asyncio
async def test_wgi_momentum_unchanged(client):
    """WGI x3 momentum must still be computed (approved set includes WGI)."""
    dtos = [
        _wgi_dto("CHE", 2024, 87.32, "RULE_OF_LAW_WGI_SCORE"),
        _wgi_dto("CHE", 2019, 85.0, "RULE_OF_LAW_WGI_SCORE"),
    ]
    await _persist(dtos)
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.momentum is not None
    assert signal.momentum == pytest.approx(2.32)


@pytest.mark.asyncio
async def test_education_level_unchanged(client):
    """Education level_score must equal the raw percentage (unchanged)."""
    await _persist([_edu_dto("CHE", 2024, 52.5)])
    signal = await _normalize("CHE", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.level_score == 52.5


# --- Part F: Force behavior ---------------------------------------------------


def test_wealth_gap_force_config_is_proxy_identity():
    """Wealth-gap force config: PROXY_CONDITION + IDENTITY_SINGLE, PARTIAL."""
    spec = FORCE_AGGREGATION_CONFIGS["wealth_opportunity_values_gaps"]
    assert aggregation_mode(spec) is ForceAggregationMode.identity_single
    assert spec.level_mode is ForceDimensionMode.identity_copy
    assert spec.relative_mode is ForceDimensionMode.deferred
    assert spec.momentum_mode is ForceDimensionMode.deferred
    assert spec.confidence_mode is ForceDimensionMode.deferred
    roles = {c.indicator_code: c.role for c in spec.components}
    assert roles["WEALTH_SHARE_TOP_10"] is ForceIndicatorRole.proxy_condition
    assert roles["GINI_INDEX"] is ForceIndicatorRole.supporting_context


def test_wealth_gap_force_coverage_ceiling_partial():
    """Wealth-gap coverage_ceiling must be PARTIAL (proxy-condition guard)."""
    from app.cycle.force_definitions import force_definition_by_code
    fd = force_definition_by_code("wealth_opportunity_values_gaps")
    assert fd is not None
    assert fd.coverage_ceiling is ForceCoverageStatus.partial


def test_wealth_gap_force_no_equal_weights():
    """No weight fields exist on the Wealth-gap force config."""
    spec = FORCE_AGGREGATION_CONFIGS["wealth_opportunity_values_gaps"]
    assert not hasattr(spec, "weights")
    assert not hasattr(spec, "weight")


@pytest.mark.asyncio
async def test_wealth_gap_force_level_copies_indicator_level(client):
    """Wealth-gap force level_score == indicator level_score (exact copy)."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    period = ScoringPeriod(2025, 2)
    direct = await _normalize("CHE", "WEALTH_SHARE_TOP_10", period)
    assert direct is not None
    signals = await _build_signals("CHE", period)
    wg = next(s for s in signals if s.force_code == "wealth_opportunity_values_gaps")
    assert wg.level_score == direct.level_score
    assert wg.level_score == pytest.approx(35.0)
    assert wg.scoring_component_indicator == "WEALTH_SHARE_TOP_10"


@pytest.mark.asyncio
async def test_wealth_gap_force_relative_momentum_confidence_none(client):
    """Wealth-gap force relative/momentum/confidence stay None."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    wg = next(s for s in signals if s.force_code == "wealth_opportunity_values_gaps")
    assert wg.relative_score is None
    assert wg.momentum is None
    assert wg.confidence is None


@pytest.mark.asyncio
async def test_wealth_gap_force_backtest_safe_false(client):
    """Wealth-gap force backtest_safe must be False."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    wg = next(s for s in signals if s.force_code == "wealth_opportunity_values_gaps")
    assert wg.backtest_safe is False


@pytest.mark.asyncio
async def test_wealth_gap_force_missing_indicator_level_none(client):
    """Missing WID indicator -> force level None (never zero)."""
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    wg = next(s for s in signals if s.force_code == "wealth_opportunity_values_gaps")
    assert wg.level_score is None
    assert "WEALTH_SHARE_TOP_10" in wg.missing_components


@pytest.mark.asyncio
async def test_wealth_gap_force_no_coverage_scaling(client):
    """PARTIAL coverage must NOT scale or zero the Wealth-gap level."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    wg = next(s for s in signals if s.force_code == "wealth_opportunity_values_gaps")
    assert wg.coverage_status is ForceCoverageStatus.partial
    assert wg.coverage_ceiling is ForceCoverageStatus.partial
    assert wg.level_score == pytest.approx(35.0)  # not scaled by PARTIAL


@pytest.mark.asyncio
async def test_wealth_gap_force_gini_is_supporting_context(client):
    """Gini must appear as deferred_components, never as a scoring component."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    wg = next(s for s in signals if s.force_code == "wealth_opportunity_values_gaps")
    assert "GINI_INDEX" in wg.deferred_components
    assert wg.scoring_component_indicator == "WEALTH_SHARE_TOP_10"


def test_wealth_gap_force_no_raw_observation_in_arithmetic():
    """No raw Observation enters force arithmetic — only NormalizedSignal."""
    spec = FORCE_AGGREGATION_CONFIGS["wealth_opportunity_values_gaps"]
    fake_signal = NormalizedSignal(
        indicator_code="WEALTH_SHARE_TOP_10",
        country_iso3="CHE",
        as_of_period=ScoringPeriod(2025, 2),
        raw_value=0.65,
        source_period="2024",
        method=NormalizationFamily.complement_0_100,
        model_version="normalization-v0.8",
        level_score=35.0,
    )
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={
            "WEALTH_SHARE_TOP_10": fake_signal,
            "GINI_INDEX": None,  # supporting context -> deferred
        },
        coverage_status=ForceCoverageStatus.partial,
    )
    assert fs.level_score == 35.0
    assert fs.aggregation_method is ForceAggregationMode.identity_single
    assert fs.scoring_component_indicator == "WEALTH_SHARE_TOP_10"
    assert "GINI_INDEX" in fs.deferred_components


# --- Part G: 17-force orchestration ------------------------------------------


@pytest.mark.asyncio
async def test_exactly_17_force_signals(client):
    """Build must return exactly 17 ForceSignal objects."""
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    assert len(signals) == 17
    assert len(signals) == len(FORCE_DEFINITIONS)


@pytest.mark.asyncio
async def test_five_executable_force_levels_at_usable_snapshot(client):
    """At a usable snapshot, exactly 5 forces have non-None level scores."""
    dtos = []
    # WGI x3 for CHE (with 5y anchors for momentum)
    for ind in WGI_INDICATORS:
        dtos.append(_wgi_dto("CHE", 2024, 80.0, ind))
        dtos.append(_wgi_dto("CHE", 2019, 78.0, ind))
    # Education for CHE
    dtos.append(_edu_dto("CHE", 2024, 52.5))
    # WID wealth for CHE
    dtos.append(_wealth_dto("CHE", 2024, 0.65))
    await _persist(dtos)
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    executable = [s for s in signals if s.level_score is not None]
    assert len(executable) == 5
    codes = {s.force_code for s in executable}
    assert codes == {
        "rule_of_law",
        "corruption",
        "internal_conflict",
        "education",
        "wealth_opportunity_values_gaps",
    }


@pytest.mark.asyncio
async def test_twelve_intentionally_unscored_forces(client):
    """Exactly 12 forces are intentionally unscored (DEFERRED_MULTI)."""
    dtos = []
    for ind in WGI_INDICATORS:
        dtos.append(_wgi_dto("CHE", 2024, 80.0, ind))
        dtos.append(_wgi_dto("CHE", 2019, 78.0, ind))
    dtos.append(_edu_dto("CHE", 2024, 52.5))
    dtos.append(_wealth_dto("CHE", 2024, 0.65))
    await _persist(dtos)
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    unscored = [s for s in signals if s.level_score is None]
    assert len(unscored) == 12


@pytest.mark.asyncio
async def test_wealth_gap_none_at_missing_snapshot_other_forces_unaffected(client):
    """Missing WID -> Wealth-gap None; other 4 forces unaffected."""
    dtos = []
    for ind in WGI_INDICATORS:
        dtos.append(_wgi_dto("CHE", 2024, 80.0, ind))
        dtos.append(_wgi_dto("CHE", 2019, 78.0, ind))
    dtos.append(_edu_dto("CHE", 2024, 52.5))
    # No WID data persisted
    await _persist(dtos)
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    wg = next(s for s in signals if s.force_code == "wealth_opportunity_values_gaps")
    assert wg.level_score is None  # missing -> None
    rl = next(s for s in signals if s.force_code == "rule_of_law")
    corr = next(s for s in signals if s.force_code == "corruption")
    ic = next(s for s in signals if s.force_code == "internal_conflict")
    edu = next(s for s in signals if s.force_code == "education")
    assert rl.level_score == 80.0
    assert corr.level_score == 80.0
    assert ic.level_score == 80.0
    assert edu.level_score == 52.5


@pytest.mark.asyncio
async def test_no_writes_during_force_build(client):
    """Force signal build must not write any observations."""
    count_before = await _observation_count()
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    count_after_persist = await _observation_count()
    await _build_signals("CHE", ScoringPeriod(2025, 2))
    count_after_build = await _observation_count()
    assert count_after_build == count_after_persist  # build adds no writes


@pytest.mark.asyncio
async def test_versions_on_signals(client):
    """All signals carry the new model versions."""
    await _persist([_wealth_dto("CHE", 2024, 0.65)])
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    for s in signals:
        assert s.force_model_version == FORCE_AGGREGATION_VERSION
        assert s.normalization_model_version == CURRENT_MODEL_VERSION.version_id
    assert FORCE_AGGREGATION_VERSION == "force-aggregation-v0.3"
    assert CURRENT_MODEL_VERSION.version_id == "normalization-v0.8"


@pytest.mark.asyncio
async def test_multi_country_wealth_normalization(client):
    """Multiple countries produce independent wealth levels."""
    dtos = [
        _wealth_dto("USA", 2024, 0.70),   # level 30
        _wealth_dto("CHE", 2024, 0.45),   # level 55
        _wealth_dto("DEU", 2024, 0.60),   # level 40
    ]
    await _persist(dtos)
    for iso3, expected in [("USA", 30.0), ("CHE", 55.0), ("DEU", 40.0)]:
        signal = await _normalize(iso3, "WEALTH_SHARE_TOP_10", ScoringPeriod(2025, 2))
        assert signal is not None
        assert signal.level_score == pytest.approx(expected)
