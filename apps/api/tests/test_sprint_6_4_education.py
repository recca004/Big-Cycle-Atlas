"""Sprint 6.4 (DEC-032): Education DIRECT_0_100 + fourth executable force.

Regression matrix (Parts A-G):
- A: DIRECT_0_100 level (Education level = raw percentage, 0/100 accepted,
     out-of-range raises, no clamping, WGI unchanged)
- B: Missing/stale behavior (missing->None, stale->None, never zero,
     freshness never rescales)
- C: Dimension separation (Education relative/momentum/confidence None,
     direct relative helper rejects, level family change alone cannot
     auto-enable)
- D: Execution-gate regression (Education momentum None, relative_score None,
     direct relative helper rejects)
- E: WGI regression (WGI x3 level/momentum/relative unchanged)
- F: Force behavior (Education IDENTITY_SINGLE, PROXY_CONDITION, exact level
     copy, PARTIAL, relative/momentum/confidence None, backtest_safe False,
     missing/stale->None, no equal weighting, no coverage scaling)
- G: 17-force orchestration (exactly 17, 4 executable at usable snapshot,
     Education None at stale/missing, other forces unaffected)

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
    NormalizationNotImplementedError,
    normalize_indicator_as_of,
)
from app.cycle.relative import build_relative_cross_section
from app.data_sources.base import ObservationDTO
from app.db import session as session_module
from app.models import Observation
from app.services.force_signal_service import build_force_signals_as_of
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)

# OECD external_series_code for TERTIARY_ATTAINMENT_25_34 — the seed stores
# the {cc} template (not country-specific); the persistence layer matches
# the exact string, so tests must use the template.
_EDU_EXTERNAL_CODE = (
    "OECD.EDU.IMEP,DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA,1.0/"
    "{cc}._T.Y25T34.ISCED11A_5T8._T.POP._Z._T._Z."
    "ED_NED.POP._Z.PT_POP_SEX_AGE.OBS._Z.NEAC.A"
)

WGI_RL = "GOV_WGI_RL_SC"
WGI_CC = "GOV_WGI_CC_SC"
WGI_PV = "GOV_WGI_PV_SC"

WGI_INDICATORS = {
    "RULE_OF_LAW_WGI_SCORE": WGI_RL,
    "CONTROL_OF_CORRUPTION_WGI_SCORE": WGI_CC,
    "POLITICAL_STABILITY_WGI_SCORE": WGI_PV,
}


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


# --- Part A: DIRECT_0_100 level ----------------------------------------------


@pytest.mark.asyncio
async def test_education_level_equals_aligned_raw_percentage(client):
    """Education level_score IS the aligned raw OECD percentage exactly."""
    await _persist([_edu_dto("CHE", 2024, 52.5)])
    signal = await _normalize("CHE", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.method is NormalizationFamily.direct_0_100
    assert signal.level_score == 52.5
    assert signal.raw_value == signal.level_score  # no rescale/invert/zscore


@pytest.mark.asyncio
async def test_education_level_zero_and_hundred_accepted(client):
    """Values at 0 and 100 are valid bounds — accepted, not clamped."""
    await _persist([_edu_dto("USA", 2024, 0.0)])
    s0 = await _normalize("USA", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert s0 is not None
    assert s0.level_score == 0.0
    await _persist([_edu_dto("DEU", 2024, 100.0)])
    s100 = await _normalize("DEU", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert s100 is not None
    assert s100.level_score == 100.0


@pytest.mark.asyncio
async def test_education_out_of_range_raises_no_clamp(client):
    """Out-of-range provider values raise NormalizationDataError — no clamp."""
    await _persist([_edu_dto("FRA", 2024, -0.5)])
    with pytest.raises(NormalizationDataError):
        await _normalize("FRA", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    await _persist([_edu_dto("GBR", 2024, 100.5)])
    with pytest.raises(NormalizationDataError):
        await _normalize("GBR", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))


# --- Part B: Missing/stale behavior ------------------------------------------


@pytest.mark.asyncio
async def test_education_missing_observation_returns_none(client):
    """No observation -> no signal (None, never zero)."""
    signal = await _normalize("CHE", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert signal is None


@pytest.mark.asyncio
async def test_education_stale_observation_returns_none(client):
    """CHN's only observation is 2010 — stale at 2025-Q4 -> None."""
    await _persist([_edu_dto("CHN", 2010, 30.0)])
    signal = await _normalize("CHN", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 4))
    assert signal is None  # stale, never zero


@pytest.mark.asyncio
async def test_education_missing_never_becomes_zero(client):
    """Missing observation must never produce a zero score."""
    signal = await _normalize("JPN", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert signal is None
    assert signal is not 0


@pytest.mark.asyncio
async def test_education_freshness_never_scales_score(client):
    """Freshness gates usability but NEVER scales the direct raw score."""
    await _persist([_edu_dto("CHE", 2024, 47.3)])
    signal = await _normalize("CHE", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.level_score == 47.3  # exact raw, not scaled by freshness
    assert signal.freshness_factor is not None
    assert 0.0 <= signal.freshness_factor <= 1.0


# --- Part C: Dimension separation --------------------------------------------


@pytest.mark.asyncio
async def test_education_relative_is_none(client):
    """Education relative_score stays None (DEC-032: not approved)."""
    await _persist([_edu_dto("CHE", 2024, 52.0)])
    signal = await _normalize("CHE", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.relative_score is None
    assert signal.relative_rank is None
    assert signal.reference_universe_id is None


@pytest.mark.asyncio
async def test_education_momentum_is_none(client):
    """Education momentum stays None (DEC-032: not approved)."""
    await _persist([_edu_dto("CHE", 2024, 52.0)])
    signal = await _normalize("CHE", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.momentum is None
    assert signal.momentum_window_years is None
    assert signal.momentum_windows == ()


@pytest.mark.asyncio
async def test_education_confidence_is_none(client):
    """Education confidence stays None (composition unresolved)."""
    await _persist([_edu_dto("CHE", 2024, 52.0)])
    signal = await _normalize("CHE", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.confidence is None


@pytest.mark.asyncio
async def test_direct_relative_helper_rejects_education(client):
    """A direct call to build_relative_cross_section for Education must raise.

    Education is DIRECT_0_100 + CROSS_SECTIONAL_RELATIVE but NOT in the
    approved set — the helper must reject it loudly.
    """
    from app.cycle.normalization_definitions import REFERENCE_UNIVERSES
    async with session_module._sessionmaker() as session:
        with pytest.raises(NormalizationNotImplementedError):
            await build_relative_cross_section(
                session,
                "TERTIARY_ATTAINMENT_25_34",
                ScoringPeriod(2025, 2),
                REFERENCE_UNIVERSES["tracked_8"],
            )


@pytest.mark.asyncio
async def test_level_family_change_alone_cannot_auto_enable_relative(client):
    """Education is DIRECT_0_100 + CROSS_SECTIONAL_RELATIVE but relative is None.

    This proves the hazard is fixed: changing only the level family does NOT
    silently enable relative scoring — the explicit approved set gates it.
    """
    await _persist([_edu_dto("CHE", 2024, 52.0)])
    signal = await _normalize("CHE", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert signal is not None
    spec = get_normalization_spec("TERTIARY_ATTAINMENT_25_34")
    assert spec.level_family is NormalizationFamily.direct_0_100
    assert spec.relative_family is NormalizationFamily.cross_sectional_relative
    assert signal.relative_score is None  # approved set gates it, not family


@pytest.mark.asyncio
async def test_level_family_change_alone_cannot_auto_enable_momentum(client):
    """Education is DIRECT_0_100 + OWN_HISTORY but momentum is None."""
    await _persist([_edu_dto("CHE", 2024, 52.0)])
    signal = await _normalize("CHE", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert signal is not None
    spec = get_normalization_spec("TERTIARY_ATTAINMENT_25_34")
    assert spec.level_family is NormalizationFamily.direct_0_100
    assert spec.momentum_family is NormalizationFamily.own_history
    assert signal.momentum is None  # approved set gates it, not family


# --- Part D: Execution-gate regression ---------------------------------------


@pytest.mark.asyncio
async def test_education_momentum_remains_none_after_reclassification(client):
    """After Education became DIRECT_0_100, momentum MUST remain None."""
    await _persist([_edu_dto("CHE", 2024, 52.0)])
    signal = await _normalize("CHE", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.momentum is None


@pytest.mark.asyncio
async def test_education_relative_remains_none_after_reclassification(client):
    """After Education became DIRECT_0_100, relative_score MUST remain None."""
    await _persist([_edu_dto("CHE", 2024, 52.0)])
    signal = await _normalize("CHE", "TERTIARY_ATTAINMENT_25_34", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.relative_score is None


# --- Part E: WGI regression (unchanged) --------------------------------------


@pytest.mark.asyncio
async def test_wgi_level_unchanged(client):
    """WGI x3 level_score must equal the raw value (unchanged by Sprint 6.4)."""
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
async def test_wgi_relative_unchanged(client):
    """WGI x3 relative must still be computed (approved set includes WGI)."""
    dtos = []
    for iso3, value in (
        ("USA", 70.0), ("CHN", 40.0), ("CHE", 87.0), ("DEU", 80.0),
        ("FRA", 75.0), ("GBR", 78.0), ("JPN", 72.0), ("IND", 50.0),
    ):
        dtos.append(_wgi_dto(iso3, 2024, value, "RULE_OF_LAW_WGI_SCORE"))
    await _persist(dtos)
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.relative_score is not None
    assert signal.reference_universe_id == "tracked_8"


# --- Part F: Force behavior --------------------------------------------------


def test_education_force_config_is_proxy_identity():
    """Education force config: PROXY_CONDITION + IDENTITY_SINGLE, PARTIAL."""
    spec = FORCE_AGGREGATION_CONFIGS["education"]
    assert aggregation_mode(spec) is ForceAggregationMode.identity_single
    assert spec.level_mode is ForceDimensionMode.identity_copy
    assert spec.relative_mode is ForceDimensionMode.deferred
    assert spec.momentum_mode is ForceDimensionMode.deferred
    assert spec.confidence_mode is ForceDimensionMode.deferred
    roles = {c.indicator_code: c.role for c in spec.components}
    assert roles["TERTIARY_ATTAINMENT_25_34"] is ForceIndicatorRole.proxy_condition


def test_education_force_coverage_ceiling_partial():
    """Education coverage_ceiling must be PARTIAL (proxy-condition guard)."""
    from app.cycle.force_definitions import force_definition_by_code
    fd = force_definition_by_code("education")
    assert fd is not None
    assert fd.coverage_ceiling is ForceCoverageStatus.partial


def test_education_force_no_equal_weights():
    """No weight fields exist on the Education force config."""
    spec = FORCE_AGGREGATION_CONFIGS["education"]
    assert not hasattr(spec, "weights")
    assert not hasattr(spec, "weight")


@pytest.mark.asyncio
async def test_education_force_level_copies_indicator_level(client):
    """Education force level_score == indicator level_score (exact copy)."""
    await _persist([_edu_dto("CHE", 2024, 52.5)])
    period = ScoringPeriod(2025, 2)
    direct = await _normalize("CHE", "TERTIARY_ATTAINMENT_25_34", period)
    assert direct is not None
    signals = await _build_signals("CHE", period)
    edu = next(s for s in signals if s.force_code == "education")
    assert edu.level_score == direct.level_score
    assert edu.level_score == 52.5
    assert edu.scoring_component_indicator == "TERTIARY_ATTAINMENT_25_34"


@pytest.mark.asyncio
async def test_education_force_relative_momentum_confidence_none(client):
    """Education force relative/momentum/confidence stay None."""
    await _persist([_edu_dto("CHE", 2024, 52.5)])
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    edu = next(s for s in signals if s.force_code == "education")
    assert edu.relative_score is None
    assert edu.momentum is None
    assert edu.confidence is None


@pytest.mark.asyncio
async def test_education_force_backtest_safe_false(client):
    """Education force backtest_safe must be False."""
    await _persist([_edu_dto("CHE", 2024, 52.5)])
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    edu = next(s for s in signals if s.force_code == "education")
    assert edu.backtest_safe is False


@pytest.mark.asyncio
async def test_education_force_missing_indicator_level_none(client):
    """Missing Education indicator -> force level None (never zero)."""
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    edu = next(s for s in signals if s.force_code == "education")
    assert edu.level_score is None
    assert "TERTIARY_ATTAINMENT_25_34" in edu.missing_components


@pytest.mark.asyncio
async def test_education_force_stale_indicator_level_none(client):
    """Stale Education indicator -> force level None (never zero)."""
    await _persist([_edu_dto("CHN", 2010, 30.0)])
    signals = await _build_signals("CHN", ScoringPeriod(2025, 4))
    edu = next(s for s in signals if s.force_code == "education")
    assert edu.level_score is None


@pytest.mark.asyncio
async def test_education_force_no_coverage_scaling(client):
    """PARTIAL coverage must NOT scale or zero the Education level."""
    await _persist([_edu_dto("CHE", 2024, 52.5)])
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    edu = next(s for s in signals if s.force_code == "education")
    assert edu.coverage_status is ForceCoverageStatus.partial
    assert edu.coverage_ceiling is ForceCoverageStatus.partial
    assert edu.level_score == 52.5  # not scaled by PARTIAL


# --- Part G: 17-force orchestration ------------------------------------------


@pytest.mark.asyncio
async def test_exactly_17_force_signals(client):
    """Build must return exactly 17 ForceSignal objects."""
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    assert len(signals) == 17
    assert len(signals) == len(FORCE_DEFINITIONS)


@pytest.mark.asyncio
async def test_four_executable_force_levels_at_usable_snapshot(client):
    """At a usable snapshot, exactly 4 forces have non-None level scores."""
    dtos = []
    # WGI x3 for CHE (with 5y anchors for momentum)
    for ind in WGI_INDICATORS:
        dtos.append(_wgi_dto("CHE", 2024, 80.0, ind))
        dtos.append(_wgi_dto("CHE", 2019, 78.0, ind))
    # Education for CHE
    dtos.append(_edu_dto("CHE", 2024, 52.5))
    await _persist(dtos)
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    executable = [s for s in signals if s.level_score is not None]
    assert len(executable) == 4
    codes = {s.force_code for s in executable}
    assert codes == {"rule_of_law", "corruption", "internal_conflict", "education"}


@pytest.mark.asyncio
async def test_education_none_at_stale_snapshot_other_forces_unaffected(client):
    """CHN stale Education -> Education None; other 3 forces unaffected."""
    dtos = []
    for ind in WGI_INDICATORS:
        dtos.append(_wgi_dto("CHN", 2024, 60.0, ind))
        dtos.append(_wgi_dto("CHN", 2019, 58.0, ind))
    dtos.append(_edu_dto("CHN", 2010, 30.0))  # stale
    await _persist(dtos)
    signals = await _build_signals("CHN", ScoringPeriod(2025, 4))
    edu = next(s for s in signals if s.force_code == "education")
    assert edu.level_score is None  # stale -> None
    rl = next(s for s in signals if s.force_code == "rule_of_law")
    corr = next(s for s in signals if s.force_code == "corruption")
    ic = next(s for s in signals if s.force_code == "internal_conflict")
    assert rl.level_score == 60.0
    assert corr.level_score == 60.0
    assert ic.level_score == 60.0


@pytest.mark.asyncio
async def test_no_writes_during_force_build(client):
    """Force signal build must not write any observations."""
    count_before = await _observation_count()
    await _persist([_edu_dto("CHE", 2024, 52.5)])
    count_after_persist = await _observation_count()
    await _build_signals("CHE", ScoringPeriod(2025, 2))
    count_after_build = await _observation_count()
    assert count_after_build == count_after_persist  # build adds no writes


@pytest.mark.asyncio
async def test_versions_on_signals(client):
    """All signals carry the new model versions."""
    await _persist([_edu_dto("CHE", 2024, 52.5)])
    signals = await _build_signals("CHE", ScoringPeriod(2025, 2))
    for s in signals:
        assert s.force_model_version == FORCE_AGGREGATION_VERSION
        assert s.normalization_model_version == CURRENT_MODEL_VERSION.version_id
    assert FORCE_AGGREGATION_VERSION == "force-aggregation-v0.2"
    assert CURRENT_MODEL_VERSION.version_id == "normalization-v0.7"
