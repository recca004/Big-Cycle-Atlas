"""Sprint 5.6 tests: as-of alignment, freshness machinery, and the first
executable normalization path (DIRECT_0_100 for the three WGI governance
scores).

Synthetic observations persisted via the real persistence layer against
seeded SQLite — no external calls, no live APIs. No signal is persisted; no
force score, weight, momentum, relative score, or confidence exists here.
"""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.cycle.freshness import (
    DEFAULT_FRESHNESS_POLICIES,
    FreshnessDecayShape,
    FreshnessPolicy,
    evaluate_freshness,
    own_period_age,
)
from app.cycle.normalization_definitions import (
    CURRENT_MODEL_VERSION,
    FRESHNESS_THRESHOLDS,
    FreshnessClass,
    FreshnessThresholds,
    ModelVersionConfig,
    MomentumWindowResult,
    NormalizationFamily,
    ScoringPeriod,
    get_normalization_spec,
)
from app.cycle.normalizer import (
    NormalizationDataError,
    NormalizationNotImplementedError,
    normalize_indicator_as_of,
)
from app.data_sources.base import ObservationDTO
from app.db import session as session_module
from app.models import Observation
from app.services.alignment_service import (
    AlignmentError,
    align_observation_as_of,
    parse_scoring_period,
    quarter_end_date,
    shift_scoring_period_years,
)
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)

WGI_RL = "GOV_WGI_RL_SC"
WGI_CC = "GOV_WGI_CC_SC"
WGI_PV = "GOV_WGI_PV_SC"
BIS_GAP = "WS_CREDIT_GAP/Q.{cc}.P.A.C"

WGI_VALUES = {
    "RULE_OF_LAW_WGI_SCORE": (WGI_RL, 87.32),
    "CONTROL_OF_CORRUPTION_WGI_SCORE": (WGI_CC, 88.48),
    "POLITICAL_STABILITY_WGI_SCORE": (WGI_PV, 82.65),
}


def _wgi_dto(iso3: str, year: int, value: float, indicator: str = "RULE_OF_LAW_WGI_SCORE") -> ObservationDTO:
    external = WGI_VALUES[indicator][0]
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


def _bis_gap_dto(iso3: str, year: int, quarter: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code="CREDIT_TO_GDP_GAP",
        external_series_code=BIS_GAP,
        period=year,
        value=value,
        unit="percentage of GDP",
        source_key="bis",
        observation_date=date(year, 1 + (quarter - 1) * 3, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"TIME_PERIOD": f"{year}-Q{quarter}", "OBS_VALUE": value},
    )


async def _persist(dtos: list[ObservationDTO]) -> None:
    async with session_module._sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


async def _align(iso3: str, indicator: str, scoring_period: ScoringPeriod):
    async with session_module._sessionmaker() as session:
        return await align_observation_as_of(session, iso3, indicator, scoring_period)


async def _normalize(iso3: str, indicator: str, scoring_period: ScoringPeriod, **kwargs):
    async with session_module._sessionmaker() as session:
        return await normalize_indicator_as_of(
            session, iso3, indicator, scoring_period, **kwargs
        )


async def _observation_count() -> int:
    async with session_module._sessionmaker() as session:
        return (
            await session.execute(select(func.count()).select_from(Observation))
        ).scalar_one()


# --- 1. Quarter parsing / quarter-end dates -------------------------------------


def test_scoring_period_parsing_and_quarter_end_dates():
    assert parse_scoring_period("2025-Q2") == ScoringPeriod(2025, 2)
    assert parse_scoring_period(" 2025-Q4 ").label == "2025-Q4"
    ends = {
        1: date(2025, 3, 31),
        2: date(2025, 6, 30),
        3: date(2025, 9, 30),
        4: date(2025, 12, 31),
    }
    for quarter, end in ends.items():
        assert quarter_end_date(ScoringPeriod(2025, quarter)) == end
    for bad in ("2025-Q5", "2025-Q0", "2025Q2", "2025-2", "not-a-period"):
        with pytest.raises((AlignmentError, ValueError)):
            parse_scoring_period(bad)


# --- 2/3. Annual and quarterly observation alignment -----------------------------


async def test_annual_observation_alignment(client):
    await _persist([_wgi_dto("CHE", 2024, 87.32)])
    aligned = await _align("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert aligned is not None
    assert aligned.source_period == "2024"
    assert aligned.raw_value == 87.32
    assert aligned.vintage_number == 1
    # 2024-Q1 observation quarter -> 2025-Q2 scoring quarter = 5 scoring periods
    assert aligned.age_periods == 5


async def test_quarterly_observation_alignment(client):
    await _persist([_bis_gap_dto("CHE", 2025, 1, 4.2), _bis_gap_dto("CHE", 2025, 2, 5.1)])
    aligned = await _align("CHE", "CREDIT_TO_GDP_GAP", ScoringPeriod(2025, 2))
    assert aligned.source_period == "2025-Q2"
    assert aligned.raw_value == 5.1
    assert aligned.age_periods == 0
    # A 2025-Q3 observation is in the future of the 2025-Q2 snapshot — excluded.
    await _persist([_bis_gap_dto("CHE", 2025, 3, 6.0)])
    aligned = await _align("CHE", "CREDIT_TO_GDP_GAP", ScoringPeriod(2025, 2))
    assert aligned.source_period == "2025-Q2"


# --- 4. Latest-vintage selection --------------------------------------------------


async def test_latest_vintage_is_used(client):
    await _persist([_wgi_dto("CHE", 2024, 70.0)])
    await _persist([_wgi_dto("CHE", 2024, 75.0)])  # revision -> vintage 2
    aligned = await _align("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert aligned.raw_value == 75.0
    assert aligned.vintage_number == 2


# --- 5. Country isolation (ISSUE-004) ---------------------------------------------


async def test_country_isolation_usa_and_che(client):
    await _persist([_wgi_dto("USA", 2024, 60.0), _wgi_dto("CHE", 2024, 87.32)])
    che = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    usa = await _normalize("USA", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert che.level_score == 87.32
    assert usa.level_score == 60.0
    # USA's value must never appear in CHE's signal (and vice versa).
    assert che.raw_value != usa.raw_value
    assert che.country_iso3 == "CHE"
    assert usa.country_iso3 == "USA"


# --- 6/20. No future observation-period leakage -----------------------------------


async def test_no_future_observation_leakage(client):
    await _persist(
        [
            _wgi_dto("CHE", 2022, 80.0),
            _wgi_dto("CHE", 2023, 82.0),
            _wgi_dto("CHE", 2024, 87.0),
        ]
    )
    # Period-completeness (Part 0): annual 2023 is NOT complete at the 2023-Q2
    # snapshot, so alignment falls back to the latest COMPLETE year, 2022.
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2023, 2))
    assert signal.source_period == "2022"
    assert signal.raw_value == 80.0
    assert signal.level_score == 80.0
    # Period-level alignment only: actual release dates are unavailable, so
    # this is research scoring, never point-in-time scoring.
    assert signal.backtest_safe is False


# --- 6a. Part 0: period-complete eligibility (DEC-015) -----------------------------


async def test_annual_observation_not_eligible_before_year_end(client):
    await _persist([_wgi_dto("CHE", 2020, 70.0)])
    for quarter in (1, 2, 3):
        # Annual 2020 is period-incomplete at every 2020 Q1-Q3 snapshot.
        assert await _align("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2020, quarter)) is None
    # Normalize path: no signal, never a zero score.
    assert await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2020, 2)) is None


async def test_annual_observation_eligible_at_year_end_quarter(client):
    await _persist([_wgi_dto("CHE", 2020, 70.0)])
    aligned = await _align("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2020, 4))
    assert aligned is not None
    assert aligned.source_period == "2020"
    assert aligned.effective_period_end == date(2020, 12, 31)


async def test_incomplete_year_falls_back_to_latest_complete_year(client):
    await _persist([_wgi_dto("CHE", 2023, 82.0), _wgi_dto("CHE", 2024, 87.0)])
    aligned = await _align("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2024, 2))
    assert aligned.source_period == "2023"
    assert aligned.raw_value == 82.0
    assert aligned.effective_period_end == date(2023, 12, 31)


async def test_quarterly_observation_period_completeness(client):
    await _persist([_bis_gap_dto("CHE", 2025, 1, 4.2), _bis_gap_dto("CHE", 2025, 2, 5.1)])
    # 2025-Q2 is NOT eligible at the 2025-Q1 snapshot: align to Q1.
    aligned = await _align("CHE", "CREDIT_TO_GDP_GAP", ScoringPeriod(2025, 1))
    assert aligned.source_period == "2025-Q1"
    assert aligned.raw_value == 4.2
    assert aligned.effective_period_end == date(2025, 3, 31)
    # Q2 becomes eligible at the 2025-Q2 snapshot.
    aligned = await _align("CHE", "CREDIT_TO_GDP_GAP", ScoringPeriod(2025, 2))
    assert aligned.source_period == "2025-Q2"
    assert aligned.effective_period_end == date(2025, 6, 30)


async def test_period_complete_alignment_never_mutates_raw_observations(client):
    await _persist([_wgi_dto("CHE", 2020, 70.0)])
    await _align("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2021, 1))
    async with session_module._sessionmaker() as session:
        observations = (await session.execute(select(Observation))).scalars().all()
    # The derived effective_period_end (2020-12-31) is provenance only — the
    # raw row keeps its original period_start, and no rows were added.
    assert len(observations) == 1
    assert observations[0].period_start.date() == date(2020, 1, 1)


# --- 7/21. Pre-first-observation -> unavailable, never 0 --------------------------


async def test_scoring_before_first_observation_returns_none(client):
    await _persist([_wgi_dto("CHE", 1996, 70.0)])
    scoring_period = ScoringPeriod(1990, 1)
    assert await _align("CHE", "RULE_OF_LAW_WGI_SCORE", scoring_period) is None
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", scoring_period)
    assert signal is None  # no observation, no signal — never a zero score


# --- 8. Freshness machinery (explicit test policies) ------------------------------


def test_freshness_factor_stays_within_0_1_for_all_ages():
    for thresholds in (
        FreshnessThresholds(FreshnessClass.annual, 1, 3, 5),
        FreshnessThresholds(FreshnessClass.quarterly, 2, 8, 12),
        FreshnessThresholds(FreshnessClass.irregular, 2, 4, 8),
    ):
        for shape in FreshnessDecayShape:
            policy = FreshnessPolicy(thresholds=thresholds, decay_shape=shape)
            for age in (0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 4.9, 5.0, 7.0, 12.0):
                result = evaluate_freshness(age, policy)
                assert 0.0 <= result.factor <= 1.0


def test_exponential_decay_honors_half_life_definition():
    policy = FreshnessPolicy(thresholds=FreshnessThresholds(FreshnessClass.annual, 1, 3, 5))
    assert evaluate_freshness(1.0, policy).factor == 1.0  # full-confidence window
    assert evaluate_freshness(3.0, policy).factor == pytest.approx(0.5)
    between = evaluate_freshness(2.0, policy).factor
    assert 0.5 < between < 1.0


def test_linear_decay_shape_is_parameterized():
    policy = FreshnessPolicy(
        thresholds=FreshnessThresholds(FreshnessClass.annual, 1, 3, 5),
        decay_shape=FreshnessDecayShape.linear,
    )
    # Linear from 1.0 at full confidence to 0.0 at the unusable threshold.
    assert evaluate_freshness(3.0, policy).factor == pytest.approx(0.5)
    assert evaluate_freshness(5.0, policy).is_usable is False


def test_freshness_policy_validates_threshold_ordering():
    with pytest.raises(ValueError):  # half-life must exceed full confidence
        FreshnessPolicy(thresholds=FreshnessThresholds(FreshnessClass.annual, 3, 1, 5))
    with pytest.raises(ValueError):  # unusable must exceed half-life
        FreshnessPolicy(thresholds=FreshnessThresholds(FreshnessClass.annual, 1, 5, 3))
    with pytest.raises(ValueError):  # full confidence cannot be negative
        FreshnessPolicy(thresholds=FreshnessThresholds(FreshnessClass.annual, -1, 3, 5))


def test_default_freshness_policies_use_the_sprint_5_5_model_parameters():
    for freshness_class, thresholds in FRESHNESS_THRESHOLDS.items():
        policy = DEFAULT_FRESHNESS_POLICIES[freshness_class]
        assert policy.thresholds is thresholds
    # The decay shape is an explicit Sprint 5.6 initial model choice (§17 stays open).
    assert all(
        policy.decay_shape is FreshnessDecayShape.exponential
        for policy in DEFAULT_FRESHNESS_POLICIES.values()
    )


def test_own_period_age_conversion():
    assert own_period_age(5, FreshnessClass.annual) == pytest.approx(1.25)
    assert own_period_age(5, FreshnessClass.irregular) == pytest.approx(1.25)
    assert own_period_age(5, FreshnessClass.quarterly) == 5.0


# --- 9/22. Stale data becomes unusable — never zero ---------------------------------


def test_stale_data_is_unusable_not_zero():
    policy = FreshnessPolicy(thresholds=FreshnessThresholds(FreshnessClass.annual, 1, 3, 5))
    result = evaluate_freshness(7.5, policy)
    assert result.is_usable is False
    assert result.factor == 0.0
    assert result.is_stale is True


async def test_stale_observation_produces_no_signal(client):
    await _persist([_wgi_dto("CHE", 2018, 80.0)])
    # 2018-Q1 -> 2025-Q2 = 30 scoring periods = 7.5 years; annual unusable after 5.
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal is None  # not produced-with-zero: no economic score survives


# --- 10. DIRECT_0_100 identity transform --------------------------------------------


async def test_direct_0_100_level_score_is_the_validated_raw_score(client):
    await _persist([_wgi_dto("CHE", 2024, 87.32)])
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal.method is NormalizationFamily.direct_0_100
    assert signal.level_score == 87.32
    assert signal.raw_value == signal.level_score  # no z-score/rank/rescale/invert


async def test_recent_observation_has_full_freshness(client):
    await _persist([_wgi_dto("CHE", 2024, 87.32)])
    # Annual 2024 first becomes period-eligible at the 2024-Q4 snapshot (Part 0).
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2024, 4))
    # 2024-Q1 -> 2024-Q4 = 3 scoring periods = 0.75 years, within the 1-year window.
    assert signal.freshness_factor == 1.0
    assert signal.is_stale is False


# --- 11/12. Out-of-range provider values raise; no silent clamp ----------------------


async def test_out_of_range_provider_values_raise_no_clamp(client):
    await _persist([_wgi_dto("CHE", 2024, -1.0)])
    with pytest.raises(NormalizationDataError):
        await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    await _persist([_wgi_dto("USA", 2024, 101.0)])
    with pytest.raises(NormalizationDataError):
        await _normalize("USA", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))


# --- 13. WGI three indicators dispatch ----------------------------------------------


async def test_wgi_three_indicators_dispatch_to_direct_0_100(client):
    dtos = [
        _wgi_dto("CHE", 2024, value, indicator=indicator)
        for indicator, (_, value) in WGI_VALUES.items()
    ]
    await _persist(dtos)
    for indicator, (_, value) in WGI_VALUES.items():
        signal = await _normalize("CHE", indicator, ScoringPeriod(2025, 2))
        assert signal is not None, indicator
        assert signal.method is NormalizationFamily.direct_0_100
        assert signal.level_score == value


# --- 14. Unsupported families fail loudly -------------------------------------------


async def test_unsupported_normalization_families_raise(client):
    for indicator in (
        "GDP_GROWTH",  # contextual_deferred since Sprint 5.9 (was target_band)
        "EXPORTS_GDP",  # contextual_deferred
        "GINI_INDEX",  # monotonic_negative (direction approved, curve deferred)
    ):
        with pytest.raises(NormalizationNotImplementedError):
            await _normalize("CHE", indicator, ScoringPeriod(2025, 2))
    with pytest.raises(ValueError):  # not a canonical indicator at all
        await _normalize("CHE", "NOT_AN_INDICATOR", ScoringPeriod(2025, 2))


# --- Sprint 5.9 audit (DEC-018): exact post-audit level families -------------------


def test_sprint_5_9_audit_level_families_exact():
    expected = {
        # Reclassified to CONTEXTUAL_DEFERRED — universal band/saturating
        # proposals disproved (DEC-018).
        "GDP_GROWTH": NormalizationFamily.contextual_deferred,
        "GROSS_CAPITAL_FORMATION_GDP": NormalizationFamily.contextual_deferred,
        "INFLATION_CPI": NormalizationFamily.contextual_deferred,
        "UNIT_LABOUR_COST_GROWTH": NormalizationFamily.contextual_deferred,
        # Confirmed families (no numeric thresholds/curves approved).
        "GINI_INDEX": NormalizationFamily.monotonic_negative,
        # Reclassified from asymmetric target_band by the Sprint 5.11
        # evidence audit (DEC-020): positive-side vulnerability supported,
        # negative-side penalty NOT supported.
        "CREDIT_TO_GDP_GAP": NormalizationFamily.one_sided_vulnerability,
        "DEBT_SERVICE_RATIO": NormalizationFamily.own_history,
        "LABOUR_PRODUCTIVITY_PER_HOUR": NormalizationFamily.monotonic_positive,
    }
    for indicator, family in expected.items():
        spec = get_normalization_spec(indicator)
        assert spec.level_family is family, indicator


async def test_credit_to_gdp_gap_still_unscored_after_sprint_5_11(client):
    # The Sprint 5.11 reclassification (DEC-020) is METHODOLOGY ONLY: the
    # one_sided_vulnerability family carries no executable score yet, and
    # no numeric Atlas breakpoint was approved.
    with pytest.raises(NormalizationNotImplementedError) as excinfo:
        await _normalize("CHE", "CREDIT_TO_GDP_GAP", ScoringPeriod(2025, 2))
    assert "not implemented" in str(excinfo.value)


async def test_sprint_5_9_reclassified_indicators_still_raise(client):
    # A family change to CONTEXTUAL_DEFERRED must NOT make any level score
    # executable — every non-WGI indicator still raises.
    for indicator in (
        "GDP_GROWTH",
        "GROSS_CAPITAL_FORMATION_GDP",
        "INFLATION_CPI",
        "UNIT_LABOUR_COST_GROWTH",
    ):
        with pytest.raises(NormalizationNotImplementedError):
            await _normalize("CHE", indicator, ScoringPeriod(2025, 2))


# --- 15-18. Not-implemented dimensions stay None; backtest safety -------------------


async def _che_signal() -> object:
    await _persist([_wgi_dto("CHE", 2024, 87.32)])
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal is not None
    return signal


async def test_relative_score_stays_none_when_universe_is_incomplete(client):
    # Only CHE has data: 1/8 usable members -> NO relative score, but the
    # universe provenance still travels (DEC-017).
    signal = await _che_signal()
    assert signal.relative_score is None
    assert signal.relative_rank is None
    assert signal.reference_universe_id == "tracked_8"
    assert signal.reference_universe_expected_n == 8
    assert signal.reference_universe_usable_n == 1


async def test_momentum_stays_none_when_history_is_missing(client):
    # Only a 2024 obs exists: no alignable anchor -> momentum is None
    # (missing history is NEVER zero, and there is no shorter-window fallback).
    signal = await _che_signal()
    assert signal.momentum is None
    assert signal.momentum_window_years is None
    assert all(result.change is None for result in signal.momentum_windows)


async def test_confidence_is_not_calculated(client):
    signal = await _che_signal()
    # Freshness factor is carried, but it is NOT the confidence score.
    assert signal.confidence is None
    assert signal.freshness_factor is not None


async def test_every_signal_is_marked_backtest_unsafe(client):
    signal = await _che_signal()
    assert signal.backtest_safe is False
    assert signal.model_version == CURRENT_MODEL_VERSION.version_id


async def test_model_config_claiming_backtest_safety_is_rejected(client):
    await _persist([_wgi_dto("CHE", 2024, 87.32)])
    config = ModelVersionConfig(
        version_id="pretend-safe",
        normalization_method="test",
        force_mapping_version="m5.4",
        reference_universe_id="tracked_8",
        backtest_safe=True,
    )
    with pytest.raises(ValueError):
        await _normalize(
            "CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2), model_config=config
        )


# --- 19. No DB writes / no raw mutation ---------------------------------------------


async def test_normalization_never_writes_or_mutates_the_db(client):
    await _persist(
        [
            _wgi_dto("CHE", 2022, 80.0),
            _wgi_dto("CHE", 2023, 82.0),
            _wgi_dto("CHE", 2024, 87.0),
        ]
    )
    before = await _observation_count()
    for scoring_period in (
        ScoringPeriod(2023, 2),
        ScoringPeriod(2024, 2),
        ScoringPeriod(2025, 2),
    ):
        signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", scoring_period)
        assert signal is not None
    assert await _observation_count() == before  # no synthetic rows, ever


# --- 23. WGI biennial gaps are never filled -----------------------------------------


async def test_wgi_biennial_gap_is_not_filled(client):
    await _persist([_wgi_dto("CHE", 1996, 70.0), _wgi_dto("CHE", 1998, 72.0)])
    # 1997 is a historical WGI gap year — 1997-Q2 must align to 1996.
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(1997, 2))
    assert signal.source_period == "1996"
    assert signal.raw_value == 70.0
    # 1996-Q1 -> 1997-Q2 = 5 scoring periods = 1.25 years: aging but usable.
    assert signal.freshness_factor < 1.0
    assert signal.is_stale is True
    async with session_module._sessionmaker() as session:
        fabricated = (
            await session.execute(
                select(func.count())
                .select_from(Observation)
                .where(Observation.period_start >= date(1997, 1, 1))
                .where(Observation.period_start < date(1998, 1, 1))
            )
        ).scalar_one()
    assert fabricated == 0  # no synthetic 1997 row was created


# --- Sprint 5.7: WGI OWN_HISTORY momentum (DEC-016) -------------------------------


def _windows_by_year(signal) -> dict[int, MomentumWindowResult]:
    return {result.window_years: result for result in signal.momentum_windows}


def test_shift_scoring_period_years_moves_year_keeps_quarter():
    assert shift_scoring_period_years(ScoringPeriod(2025, 2), 5) == ScoringPeriod(2020, 2)
    assert shift_scoring_period_years(ScoringPeriod(2025, 4), 3) == ScoringPeriod(2022, 4)
    assert shift_scoring_period_years(ScoringPeriod(2025, 2), 0) == ScoringPeriod(2025, 2)
    with pytest.raises(ValueError):  # negative years rejected
        shift_scoring_period_years(ScoringPeriod(2025, 2), -1)
    with pytest.raises(ValueError):  # before the plausible-year floor
        shift_scoring_period_years(ScoringPeriod(1902, 2), 5)


def test_current_model_version_is_v0_5_dsr_own_history_level():
    assert CURRENT_MODEL_VERSION.version_id == "normalization-v0.5"
    assert (
        CURRENT_MODEL_VERSION.normalization_method
        == "sprint-5.10-dsr-own-history-level-r1"
    )
    # Sprint 5.10 enables OWN_HISTORY level for EXACTLY DEBT_SERVICE_RATIO.
    own_history = CURRENT_MODEL_VERSION.own_history_level_configs
    assert set(own_history) == {"DEBT_SERVICE_RATIO"}
    assert own_history["DEBT_SERVICE_RATIO"].minimum_sample_n == 20
    assert CURRENT_MODEL_VERSION.backtest_safe is False
    assert CURRENT_MODEL_VERSION.reference_universe_id == "tracked_8"
    for indicator in WGI_VALUES:
        spec = get_normalization_spec(indicator)
        assert CURRENT_MODEL_VERSION.momentum_windows[indicator] == spec.momentum_windows
        assert spec.momentum_windows == (3, 5)
        assert CURRENT_MODEL_VERSION.momentum_primary_window_years[indicator] == 5
        assert CURRENT_MODEL_VERSION.momentum_anchor_tolerance_periods[indicator] == 1
        assert spec.relative_family is NormalizationFamily.cross_sectional_relative
        assert spec.level_family is NormalizationFamily.direct_0_100


def test_model_config_rejects_primary_window_outside_windows():
    with pytest.raises(ValueError):
        ModelVersionConfig(
            version_id="bad",
            normalization_method="t",
            force_mapping_version="m",
            reference_universe_id="tracked_8",
            momentum_windows={"RULE_OF_LAW_WGI_SCORE": (3, 5)},
            momentum_primary_window_years={"RULE_OF_LAW_WGI_SCORE": 4},
        )
    with pytest.raises(ValueError):  # tolerance declared without windows
        ModelVersionConfig(
            version_id="bad",
            normalization_method="t",
            force_mapping_version="m",
            reference_universe_id="tracked_8",
            momentum_anchor_tolerance_periods={"RULE_OF_LAW_WGI_SCORE": 1},
        )


def test_momentum_window_result_validates_range():
    with pytest.raises(ValueError):  # above +100
        MomentumWindowResult(window_years=5, requested_anchor_period="2020-Q2", change=150.0)
    with pytest.raises(ValueError):  # below -100
        MomentumWindowResult(window_years=5, requested_anchor_period="2020-Q2", change=-100.5)
    boundary = MomentumWindowResult(
        window_years=5, requested_anchor_period="2020-Q2", change=-100.0
    )
    assert boundary.change == -100.0  # boundary itself is valid
    with pytest.raises(ValueError):  # window must be positive
        MomentumWindowResult(window_years=0, requested_anchor_period="2020-Q2")


async def test_momentum_exact_signed_raw_point_change(client):
    await _persist(
        [
            _wgi_dto("CHE", 2019, 80.0),
            _wgi_dto("CHE", 2020, 82.0),
            _wgi_dto("CHE", 2021, 83.0),
            _wgi_dto("CHE", 2022, 84.0),
            _wgi_dto("CHE", 2023, 85.0),
            _wgi_dto("CHE", 2024, 87.32),
        ]
    )
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal is not None
    by_window = _windows_by_year(signal)
    # Both windows calculated, with requested + actual anchor provenance.
    assert set(by_window) == {3, 5}
    # 5y: requested 2020-Q2; annual 2020 is period-incomplete at Q2 (DEC-015)
    # so the anchor aligns to 2019: 87.32 - 80.0.
    assert by_window[5].requested_anchor_period == "2020-Q2"
    assert by_window[5].anchor_source_period == "2019"
    assert by_window[5].change == pytest.approx(87.32 - 80.0)
    # 3y diagnostic: requested 2022-Q2 -> actual 2021: 87.32 - 83.0.
    assert by_window[3].requested_anchor_period == "2022-Q2"
    assert by_window[3].anchor_source_period == "2021"
    assert by_window[3].change == pytest.approx(87.32 - 83.0)
    # Headline momentum = the 5y change ONLY (no averaging with 3y).
    assert signal.momentum == pytest.approx(7.32)
    assert signal.momentum == by_window[5].change
    assert signal.momentum_window_years == 5


async def test_momentum_rising_wgi_is_positive(client):
    await _persist(
        [_wgi_dto("CHE", year, value) for year, value in [
            (2019, 80.0), (2020, 82.0), (2021, 83.0), (2022, 84.0), (2023, 85.0), (2024, 90.0),
        ]]
    )
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal.momentum == pytest.approx(10.0)  # higher WGI = positive, no inversion


async def test_momentum_falling_wgi_is_negative(client):
    await _persist(
        [_wgi_dto("CHE", year, value) for year, value in [
            (2019, 90.0), (2020, 89.0), (2021, 88.0), (2022, 86.0), (2023, 84.0), (2024, 80.0),
        ]]
    )
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal.momentum == pytest.approx(-10.0)


async def test_momentum_zero_change_is_a_real_zero_not_missing(client):
    await _persist(
        [_wgi_dto("CHE", year, value) for year, value in [
            (2019, 85.0), (2020, 85.0), (2021, 85.0), (2022, 85.0), (2023, 85.0), (2024, 85.0),
        ]]
    )
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal.momentum is not None
    assert signal.momentum == 0.0
    assert signal.momentum_window_years == 5


async def test_primary_5y_unavailable_momentum_none_3y_visible(client):
    # History starts 2021: nothing is period-complete before the 2020-Q2
    # anchor period, but the 3y window (2022-Q2 -> 2021) works.
    await _persist(
        [_wgi_dto("CHE", year, value) for year, value in [
            (2021, 83.0), (2022, 84.0), (2023, 85.0), (2024, 87.32),
        ]]
    )
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal is not None  # the level signal still exists
    assert signal.level_score == 87.32
    assert signal.momentum is None  # NO silent fallback to 3y
    assert signal.momentum_window_years is None
    by_window = _windows_by_year(signal)
    assert by_window[5].change is None
    assert by_window[5].anchor_source_period is None
    assert by_window[3].anchor_source_period == "2021"
    assert by_window[3].change == pytest.approx(4.32)  # diagnostic remains visible


async def test_one_year_wgi_gap_accepted_by_anchor_tolerance(client):
    # 1997 and 1999 are WGI biennial gaps: anchors one source year older
    # than requested are accepted (tolerance = 1 annual period).
    await _persist(
        [_wgi_dto("CHE", year, value) for year, value in [
            (1996, 70.0), (1998, 72.0), (2001, 75.0),
        ]]
    )
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2002, 2))
    by_window = _windows_by_year(signal)
    # 5y requested 1997-Q2 -> actual 1996 (one year older: allowed).
    assert by_window[5].anchor_source_period == "1996"
    assert by_window[5].change == pytest.approx(75.0 - 70.0)
    # 3y requested 1999-Q2 -> actual 1998 (also one year older: allowed).
    assert by_window[3].anchor_source_period == "1998"
    assert by_window[3].change == pytest.approx(3.0)
    assert signal.momentum == pytest.approx(5.0)
    assert signal.momentum_window_years == 5


async def test_anchor_beyond_one_year_tolerance_rejected_never_stretched(client):
    # Only 1996 exists before 2001: the 3y anchor period 1999-Q2 aligns to
    # 1996 (three years older than requested) - rejected, change = None.
    await _persist([_wgi_dto("CHE", 1996, 70.0), _wgi_dto("CHE", 2001, 75.0)])
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2002, 2))
    by_window = _windows_by_year(signal)
    assert by_window[3].anchor_source_period == "1996"  # provenance still visible
    assert by_window[3].change is None  # but the window is never silently stretched
    # 5y requested 1997-Q2 -> 1996 is within tolerance: primary still works.
    assert by_window[5].change == pytest.approx(5.0)
    assert signal.momentum == pytest.approx(5.0)


async def test_period_complete_anchor_semantics_inherited_from_alignment(client):
    # 2020 exists but is NOT period-complete at the 2020-Q2 anchor period
    # (DEC-015): the 5y window has no anchor at all — never the incomplete
    # 2020 value itself. The 3y anchor period 2022-Q2 DOES align to 2020,
    # but that is two years older than requested: outside tolerance, change
    # stays None with the actual anchor visible in provenance.
    await _persist([_wgi_dto("CHE", 2020, 82.0), _wgi_dto("CHE", 2024, 87.32)])
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal.level_score == 87.32
    assert signal.momentum is None
    by_window = _windows_by_year(signal)
    assert by_window[5].anchor_source_period is None
    assert by_window[5].change is None
    assert by_window[3].anchor_source_period == "2020"
    assert by_window[3].change is None


async def test_anchor_uses_latest_vintage(client):
    await _persist([_wgi_dto("CHE", 2019, 80.0)])
    await _persist([_wgi_dto("CHE", 2019, 81.0)])  # revision -> vintage 2
    await _persist([_wgi_dto("CHE", 2024, 87.32)])
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    by_window = _windows_by_year(signal)
    assert by_window[5].anchor_source_period == "2019"
    assert by_window[5].change == pytest.approx(87.32 - 81.0)  # vintage 2, not 80.0


async def test_anchor_country_isolation_usa_and_che(client):
    await _persist(
        [
            _wgi_dto("CHE", 2019, 80.0), _wgi_dto("CHE", 2024, 87.32),
            _wgi_dto("USA", 2019, 60.0), _wgi_dto("USA", 2024, 62.0),
        ]
    )
    che = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    usa = await _normalize("USA", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert che.momentum == pytest.approx(7.32)  # never USA's anchor
    assert usa.momentum == pytest.approx(2.0)  # never CHE's anchor


async def test_no_future_anchor_observation(client):
    # The 5y anchor period is 1997-Q2: the 1998 observation's period ends
    # after that snapshot, so it must NOT be the anchor.
    await _persist([_wgi_dto("CHE", 1998, 72.0), _wgi_dto("CHE", 2001, 75.0)])
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2002, 2))
    by_window = _windows_by_year(signal)
    assert by_window[5].anchor_source_period is None
    assert by_window[5].change is None
    # 3y (1999-Q2 -> 1998) is legitimate: visible, but momentum stays None.
    assert by_window[3].anchor_source_period == "1998"
    assert by_window[3].change == pytest.approx(3.0)
    assert signal.momentum is None


async def test_anchor_not_freshness_decayed_momentum_not_scaled(client):
    await _persist([_wgi_dto("CHE", 2019, 80.0), _wgi_dto("CHE", 2024, 87.32)])
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    # The CURRENT observation is stale (factor < 1), but momentum is the raw
    # signed point change: never multiplied by the freshness factor, and the
    # 5-year-old anchor gets no decay of its own.
    assert signal.freshness_factor < 1.0
    assert signal.momentum == pytest.approx(7.32)
    assert signal.momentum != pytest.approx(7.32 * signal.freshness_factor)


async def test_out_of_range_anchor_raises_no_clamp(client):
    await _persist([_wgi_dto("CHE", 2019, 200.0), _wgi_dto("CHE", 2024, 87.32)])
    with pytest.raises(NormalizationDataError):
        await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))


async def test_momentum_computed_from_aligned_raw_not_level_score(client):
    # Momentum comes from aligned RAW values; it only coincides with the
    # level-score difference because DIRECT_0_100 is currently the identity.
    await _persist(
        [_wgi_dto("CHE", year, value) for year, value in [
            (2019, 80.0), (2020, 82.0), (2021, 83.0), (2022, 84.0), (2023, 85.0), (2024, 87.32),
        ]]
    )
    signal = await _normalize("CHE", "RULE_OF_LAW_WGI_SCORE", ScoringPeriod(2025, 2))
    assert signal.momentum == pytest.approx(signal.raw_value - 80.0)