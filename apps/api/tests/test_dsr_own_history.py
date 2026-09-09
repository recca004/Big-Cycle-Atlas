"""Sprint 5.10 tests: DSR OWN_HISTORY level normalization (DEC-019).

The first non-WGI level signal: the country's current DEBT_SERVICE_RATIO
positioned within ITS OWN expanding historical distribution as of the
scoring snapshot — an empirical mid-rank stress percentile, inverted to a
strength level. Cross-country raw-DSR ranking is prohibited; DSR relative /
momentum / confidence stay None.

Synthetic observations persisted via the real persistence layer against
seeded SQLite — no external calls, no live APIs. No signal is persisted; no
force score, weight, or phase exists here.
"""
from datetime import date, datetime, timezone
from dataclasses import replace

import pytest
from sqlalchemy import func, select

from app.cycle.normalization_definitions import (
    CURRENT_MODEL_VERSION,
    ModelVersionConfig,
    NormalizationFamily,
    OwnHistoryLevelConfig,
    OwnHistoryLevelResult,
    ScoringPeriod,
    get_normalization_spec,
)
from app.cycle.normalizer import (
    NormalizationNotImplementedError,
    normalize_indicator_as_of,
    own_history_stress_position,
)
from app.data_sources.base import ObservationDTO
from app.db import session as session_module
from app.models import Observation
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)

DSR = "DEBT_SERVICE_RATIO"
DSR_EXTERNAL = "WS_DSR/Q.{cc}.P"


def _dsr_dto(iso3: str, year: int, quarter: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code=DSR,
        external_series_code=DSR_EXTERNAL,
        period=year,
        value=value,
        unit="per cent",
        source_key="bis",
        observation_date=date(year, 1 + (quarter - 1) * 3, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"TIME_PERIOD": f"{year}-Q{quarter}", "OBS_VALUE": value},
    )


def _quarter_dtos(iso3: str, start_year: int, start_q: int, values: list[float]) -> list[ObservationDTO]:
    """DTOS on consecutive quarters starting at (start_year, start_q)."""
    dtos = []
    year, quarter = start_year, start_q
    for value in values:
        dtos.append(_dsr_dto(iso3, year, quarter, value))
        quarter += 1
        if quarter > 4:
            quarter = 1
            year += 1
    return dtos


def _period_label(year: int, quarter: int) -> str:
    return f"{year}-Q{quarter}"


async def _persist(dtos: list[ObservationDTO]) -> None:
    async with session_module._sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


async def _normalize(iso3: str, scoring_period: ScoringPeriod, **kwargs):
    async with session_module._sessionmaker() as session:
        return await normalize_indicator_as_of(
            session, iso3, DSR, scoring_period, **kwargs
        )


async def _observation_count() -> int:
    async with session_module._sessionmaker() as session:
        return (
            await session.execute(select(func.count()).select_from(Observation))
        ).scalar_one()


# A 20-quarter run: 2000-Q1 .. 2004-Q4.
TWENTY_QUARTERS = [10.0 + i for i in range(20)]  # 10.0 .. 29.0 ascending
SNAPSHOT_2004_Q4 = ScoringPeriod(2004, 4)


# --- 1/3. Execution gate + expanding calibration ---------------------------------


async def test_dsr_own_history_level_enabled_and_computed(client):
    await _persist(_quarter_dtos("CHE", 2000, 1, TWENTY_QUARTERS))
    signal = await _normalize("CHE", SNAPSHOT_2004_Q4)
    assert signal is not None
    assert signal.method is NormalizationFamily.own_history
    oh = signal.own_history_level
    assert oh is not None
    assert oh.sample_n == 20
    assert oh.minimum_sample_n == 20
    assert oh.earliest_source_period == "2000-Q1"
    assert oh.latest_source_period == "2004-Q4"
    # Ascending history: current 29.0 is the historical MAXIMUM stress ->
    # lowest level score the method can produce for n=20.
    assert oh.rank == 20.0
    assert oh.stress_percentile == pytest.approx(97.5)
    assert signal.level_score == pytest.approx(2.5)


async def test_expanding_window_grows_with_the_snapshot(client):
    await _persist(_quarter_dtos("CHE", 2000, 1, TWENTY_QUARTERS))
    early = await _normalize("CHE", ScoringPeriod(2002, 4))  # 12 obs
    late = await _normalize("CHE", ScoringPeriod(2004, 4))  # 20 obs
    assert early.own_history_level.sample_n == 12
    assert early.own_history_level.latest_source_period == "2002-Q4"
    assert late.own_history_level.sample_n == 20
    assert late.own_history_level.latest_source_period == "2004-Q4"
    assert late.own_history_level.earliest_source_period == "2000-Q1"


async def test_registry_own_history_alone_does_not_auto_enable(client):
    await _persist(_quarter_dtos("CHE", 2000, 1, TWENTY_QUARTERS))
    no_dsr_config = replace(
        ModelVersionConfig(
            version_id="test-no-own-history",
            normalization_method="test",
            reference_universe_id="tracked_8",
            momentum_windows=CURRENT_MODEL_VERSION.momentum_windows,
            momentum_primary_window_years=CURRENT_MODEL_VERSION.momentum_primary_window_years,
            momentum_anchor_tolerance_periods=CURRENT_MODEL_VERSION.momentum_anchor_tolerance_periods,
        ),
        own_history_level_configs={},
    )
    assert DSR not in no_dsr_config.own_history_level_configs
    with pytest.raises(NormalizationNotImplementedError):
        await _normalize("CHE", SNAPSHOT_2004_Q4, model_config=no_dsr_config)


async def test_own_history_level_config_requires_positive_minimum(client):
    with pytest.raises(ValueError):
        OwnHistoryLevelConfig(minimum_sample_n=0)


async def test_current_model_version_enables_exactly_dsr(client):
    assert CURRENT_MODEL_VERSION.version_id == "normalization-v0.7"
    assert (
        CURRENT_MODEL_VERSION.normalization_method
        == "sprint-6.4-education-direct-0-100-explicit-dimension-gates"
    )
    # Sprint 5.12 left the DSR configuration untouched.
    assert set(CURRENT_MODEL_VERSION.own_history_level_configs) == {DSR}
    # The registry's ONLY own-history level indicator is DSR — the config and
    # the registry agree.
    own_history_registry = {
        code
        for code in ("DEBT_SERVICE_RATIO", "CREDIT_TO_GDP_GAP", "GDP_GROWTH")
        if get_normalization_spec(code).level_family is NormalizationFamily.own_history
    }
    assert own_history_registry == {DSR}


# --- 4. No future leakage (Part 16) ----------------------------------------------


async def test_future_observation_has_zero_effect_on_the_score(client):
    # 44 quarters 2000-Q1 .. 2010-Q4; the 2008-Q1 value is extreme.
    values = [15.0] * 44
    await _persist(_quarter_dtos("CHE", 2000, 1, values))
    before = await _normalize("CHE", ScoringPeriod(2005, 2))
    assert before.own_history_level.sample_n == 22  # 2000-Q1 .. 2005-Q2
    assert before.own_history_level.latest_source_period == "2005-Q2"
    # A very high future observation (2008-Q1) must not move the 2005-Q2 score.
    await _persist([_dsr_dto("CHE", 2008, 1, 999.0)])
    after = await _normalize("CHE", ScoringPeriod(2005, 2))
    assert after.level_score == before.level_score
    assert after.own_history_level.sample_n == 22
    assert after.own_history_level.rank == before.own_history_level.rank


# --- 5. Latest vintage inside the calibration sample ----------------------------


async def test_latest_vintage_per_historical_period_used_once(client):
    values = list(TWENTY_QUARTERS)
    await _persist(_quarter_dtos("CHE", 2000, 1, values))
    # Revise 2003-Q1 (the 13th quarter, value 22.0) -> vintage 2.
    await _persist([_dsr_dto("CHE", 2003, 1, 40.0)])
    signal = await _normalize("CHE", SNAPSHOT_2004_Q4)
    oh = signal.own_history_level
    assert oh.sample_n == 20  # the revised period counts ONCE, not twice
    # New value 40.0 is the historical max; current 29.0 has 18 values below
    # it (10..21, 23..28 — the superseded 22.0 must NOT participate) -> rank 19.
    assert oh.rank == 19.0
    assert signal.level_score == pytest.approx(7.5)
    assert signal.raw_value == 29.0


# --- 6. Country isolation --------------------------------------------------------


async def test_country_isolation_che_and_deu(client):
    await _persist(_quarter_dtos("CHE", 2000, 1, TWENTY_QUARTERS))
    # DEU's own history must not enter CHE's calibration sample.
    await _persist(_quarter_dtos("DEU", 2000, 1, [90.0 + i for i in range(20)]))
    che = await _normalize("CHE", SNAPSHOT_2004_Q4)
    assert che.own_history_level.sample_n == 20
    assert che.own_history_level.rank == 20.0  # CHE's own max, unaffected by DEU
    assert che.level_score == pytest.approx(2.5)
    deu = await _normalize("DEU", SNAPSHOT_2004_Q4)
    assert deu.own_history_level.sample_n == 20
    assert deu.level_score == pytest.approx(2.5)  # DEU's own max within its own sample


# --- 7/8. Real observations only; no zero-fill ------------------------------------


async def test_missing_quarter_is_a_gap_not_a_zero(client):
    # 21 quarters 2000-Q1 .. 2005-Q1 with 2003-Q1 missing: 20 ACTUAL
    # observations, one gap. The gap must not become a zero-filled sample
    # point (a phantom 0.0 minimum would shift every rank).
    values = [10.0 + i for i in range(21)]
    dtos = _quarter_dtos("CHE", 2000, 1, values)
    without_gap = [dto for dto in dtos if dto.observation_date != date(2003, 1, 1)]
    assert len(without_gap) == 20  # sanity: exactly one quarter removed
    await _persist(without_gap)
    signal = await _normalize("CHE", ScoringPeriod(2005, 1))
    oh = signal.own_history_level
    assert oh.sample_n == 20  # the gap is NOT a 21st (zero) observation
    assert oh.earliest_source_period == "2000-Q1"
    assert oh.latest_source_period == "2005-Q1"
    # Current 30.0 is the historical max among the 20 real values -> rank 20,
    # level 2.5 exactly. With a zero-filled gap the sample would be n=21 and
    # the level 2.381 — this exact value proves no zero-fill happened.
    assert oh.rank == 20.0
    assert signal.level_score == pytest.approx(2.5)


async def test_one_actual_observation_counted_once(client):
    await _persist(_quarter_dtos("CHE", 2000, 1, TWENTY_QUARTERS))
    signal = await _normalize("CHE", SNAPSHOT_2004_Q4)
    assert signal.own_history_level.sample_n == 20
    assert signal.own_history_level.earliest_source_period == "2000-Q1"
    assert signal.own_history_level.latest_source_period == "2004-Q4"


# --- 9/10/11. Minimum history boundary -------------------------------------------


async def test_n19_current_exists_but_level_none(client):
    # 2000-Q1 .. 2004-Q3 = 19 quarters: the raw current value exists, the
    # signal exists, but the level score is None — never zero.
    await _persist(_quarter_dtos("CHE", 2000, 1, [10.0 + i for i in range(19)]))
    signal = await _normalize("CHE", ScoringPeriod(2004, 3))
    assert signal is not None
    assert signal.raw_value == 28.0
    assert signal.source_period == "2004-Q3"
    assert signal.level_score is None
    oh = signal.own_history_level
    assert oh.sample_n == 19
    assert oh.minimum_sample_n == 20
    assert oh.rank is None and oh.stress_percentile is None and oh.level_score is None
    assert signal.freshness_factor is not None  # freshness provenance travels


async def test_n20_first_eligible_level_score(client):
    # 2000-Q1 .. 2004-Q4 = 20 quarters: the first own-history level score.
    await _persist(_quarter_dtos("CHE", 2000, 1, TWENTY_QUARTERS))
    signal = await _normalize("CHE", ScoringPeriod(2004, 4))
    assert signal.level_score is not None
    assert signal.own_history_level.sample_n == 20


# --- 12-20. Empirical mid-rank method ---------------------------------------------


def test_pure_stress_position_formula_and_ties():
    # Part 6/9 example: 10, 12, 12, 15 — the tied 12s share rank (2+3)/2 = 2.5.
    rank, stress = own_history_stress_position([10.0, 12.0, 12.0, 15.0], 12.0)
    assert rank == 2.5
    assert stress == pytest.approx(100.0 * (2.5 - 0.5) / 4)  # 50.0
    # Ties are never broken by order: any permutation gives the same result.
    for sample in ([12.0, 10.0, 15.0, 12.0], [15.0, 12.0, 12.0, 10.0], [10.0, 15.0, 12.0, 12.0]):
        assert own_history_stress_position(sample, 12.0) == (rank, stress)
    # Constant history: every observation ties -> rank (n+1)/2 -> stress 50.
    rank_c, stress_c = own_history_stress_position([7.0] * 20, 7.0)
    assert rank_c == 10.5
    assert stress_c == 50.0
    # Empty sample / current-not-in-sample are configuration errors.
    with pytest.raises(ValueError):
        own_history_stress_position([], 5.0)
    with pytest.raises(ValueError):
        own_history_stress_position([1.0, 2.0], 3.0)


async def test_lowest_historical_dsr_is_high_score(client):
    # Current is the historical MINIMUM stress -> highest level for n=20
    # (97.5, NOT 100 — finite-sample endpoints are never forced).
    values = [30.0 - i for i in range(20)]  # 30.0 down to 11.0
    await _persist(_quarter_dtos("CHE", 2000, 1, values))
    signal = await _normalize("CHE", SNAPSHOT_2004_Q4)
    assert signal.own_history_level.rank == 1.0
    assert signal.own_history_level.stress_percentile == pytest.approx(2.5)
    assert signal.level_score == pytest.approx(97.5)


async def test_highest_historical_dsr_is_low_score(client):
    await _persist(_quarter_dtos("CHE", 2000, 1, TWENTY_QUARTERS))
    signal = await _normalize("CHE", SNAPSHOT_2004_Q4)
    assert signal.level_score == pytest.approx(2.5)  # NOT 0 — no endpoint clamp


async def test_median_history_scores_approximately_50(client):
    # 9 below, 9 above, and the current observation tied with one historical
    # value at the middle: average rank (10 + 11)/2 = 10.5 -> stress 50.
    values = [10.0 + i for i in range(9)] + [21.0 + i for i in range(9)]
    values += [19.5, 19.5]  # the last (current, 2004-Q4) ties at the middle
    assert len(values) == 20
    await _persist(_quarter_dtos("CHE", 2000, 1, values))
    signal = await _normalize("CHE", SNAPSHOT_2004_Q4)
    assert signal.own_history_level.rank == 10.5
    assert signal.level_score == pytest.approx(50.0)


async def test_level_formula_exact_rank3_of_20(client):
    # Distinct values; current (29.0 minus two outliers...) — construct so the
    # current value sits exactly at rank 3: two values below, 17 above.
    values = [5.0, 6.0] + [50.0 + i for i in range(18)]
    values[-1] = 7.5  # current, at 2004-Q4, third-lowest
    await _persist(_quarter_dtos("CHE", 2000, 1, values))
    signal = await _normalize("CHE", SNAPSHOT_2004_Q4)
    oh = signal.own_history_level
    assert oh.rank == 3.0
    assert oh.stress_percentile == pytest.approx(100.0 * (3.0 - 0.5) / 20.0)  # 12.5
    assert signal.level_score == pytest.approx(87.5)


async def test_constant_history_scores_exactly_50(client):
    await _persist(_quarter_dtos("CHE", 2000, 1, [13.7] * 20))
    signal = await _normalize("CHE", SNAPSHOT_2004_Q4)
    assert signal.own_history_level.rank == 10.5
    assert signal.level_score == pytest.approx(50.0)


def test_own_history_level_result_validation():
    # Scored fields travel together; insufficient history leaves all None.
    ok = OwnHistoryLevelResult(
        sample_n=20, minimum_sample_n=20,
        earliest_source_period="2000-Q1", latest_source_period="2004-Q4",
        rank=3.0, stress_percentile=12.5, level_score=87.5,
    )
    assert ok.level_score == 87.5
    with pytest.raises(ValueError):
        OwnHistoryLevelResult(
            sample_n=19, minimum_sample_n=20,
            earliest_source_period="2000-Q1", latest_source_period="2004-Q3",
            rank=None, stress_percentile=None, level_score=0.0,  # zero masquerading
        )
    with pytest.raises(ValueError):
        OwnHistoryLevelResult(
            sample_n=19, minimum_sample_n=20,
            earliest_source_period="2000-Q1", latest_source_period="2004-Q3",
            rank=3.0, stress_percentile=None, level_score=None,  # rank without score
        )
    with pytest.raises(ValueError):
        OwnHistoryLevelResult(sample_n=19, minimum_sample_n=20, rank=3.0)


# --- 21. Stale/unusable current -> no signal ---------------------------------------


async def test_unusably_stale_current_gives_no_signal(client):
    # History ends 2002-Q4; scoring 2006-Q1 -> current age 13 quarters >
    # the quarterly unusable threshold (12) -> NO signal, never zero.
    await _persist(_quarter_dtos("CHE", 2000, 1, [10.0 + i for i in range(12)]))
    signal = await _normalize("CHE", ScoringPeriod(2006, 1))
    assert signal is None


# --- 22/23. Freshness never scales; calibration points never decayed ------------


async def test_freshness_factor_never_scales_level_score(client):
    # 20 quarters ending 2004-Q4, scored at 2005-Q2: current age = 1 quarter
    # (within the 2-quarter full-confidence window -> factor 1.0)... use a
    # snapshot 3 quarters after 2004-Q4 -> age 3 -> decaying factor < 1.0.
    values = [10.0 + i for i in range(19)] + [30.0]
    await _persist(_quarter_dtos("CHE", 2000, 1, values))
    signal = await _normalize("CHE", ScoringPeriod(2005, 3))
    assert signal.freshness_factor < 1.0  # stale-but-usable, factor carried
    assert signal.is_stale is True
    # The score equals the UNSCALED mid-rank computation: current 30.0 is the
    # historical max -> rank 20 -> level 2.5, regardless of the <1 factor.
    rank, stress = own_history_stress_position(
        [signal.raw_value] + values[:-1], signal.raw_value
    )
    assert signal.level_score == pytest.approx(100.0 - stress)
    assert signal.level_score == pytest.approx(2.5)


async def test_historical_calibration_points_not_freshness_decayed(client):
    # The 2000-Q1 observation is 19 quarters old at the snapshot — far beyond
    # the unusable threshold — yet it participates in the calibration sample.
    values = [10.0 + i for i in range(19)] + [30.0]
    await _persist(_quarter_dtos("CHE", 2000, 1, values))
    signal = await _normalize("CHE", ScoringPeriod(2005, 3))
    assert signal.own_history_level.sample_n == 20  # all 20, incl. the oldest
    assert signal.own_history_level.earliest_source_period == "2000-Q1"


# --- 24-27. Other dimensions stay None; backtest unsafe ---------------------------


async def test_dsr_dimensions_stay_none_and_backtest_unsafe(client):
    await _persist(_quarter_dtos("CHE", 2000, 1, TWENTY_QUARTERS))
    signal = await _normalize("CHE", SNAPSHOT_2004_Q4)
    assert signal.relative_score is None  # cross-country DSR ranking prohibited
    assert signal.reference_universe_id is None
    assert signal.momentum is None  # DSR momentum NOT approved in this sprint
    assert signal.momentum_windows == ()
    assert signal.confidence is None
    assert signal.backtest_safe is False
    assert signal.model_version == "normalization-v0.7"


# --- 28-30. WGI outputs unchanged -------------------------------------------------


async def test_wgi_level_momentum_relative_unchanged_with_dsr_present(client):
    # The dispatch refactor must not move WGI outputs: level == raw,
    # momentum = signed 5y change, relative = tracked_8 mid-rank position.
    from app.data_sources.base import ObservationDTO as DTO

    def wgi_dto(iso3: str, year: int, value: float) -> DTO:
        return DTO(
            country_iso3=iso3,
            indicator_code="RULE_OF_LAW_WGI_SCORE",
            external_series_code="GOV_WGI_RL_SC",
            period=year,
            value=value,
            unit="score 0-100",
            source_key="world_bank",
            observation_date=date(year, 1, 1),
            release_date=None,
            retrieved_at=RETRIEVED_AT,
            raw_payload={"test": True},
        )

    snapshot = ScoringPeriod(2025, 2)
    dtos = []
    for iso3 in ("USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND"):
        dtos.append(wgi_dto(iso3, 2024, 80.0))
        dtos.append(wgi_dto(iso3, 2019, 75.0))
    dtos.append(wgi_dto("CHE", 2024, 87.32))  # revision -> vintage 2 for CHE
    await _persist(dtos)

    async with session_module._sessionmaker() as session:
        signal = await normalize_indicator_as_of(
            session, "CHE", "RULE_OF_LAW_WGI_SCORE", snapshot
        )
    assert signal is not None
    assert signal.method is NormalizationFamily.direct_0_100
    assert signal.level_score == 87.32  # DIRECT_0_100 identity unchanged
    assert signal.momentum is not None
    assert signal.momentum == pytest.approx(87.32 - 75.0)
    assert signal.momentum_window_years == 5
    assert signal.own_history_level is None  # DSR provenance absent on WGI
    assert signal.reference_universe_id == "tracked_8"
    assert signal.relative_score is not None  # complete 8/8 universe
    assert signal.model_version == "normalization-v0.7"


# --- 32/33. No writes; no force scores --------------------------------------------


async def test_dsr_normalization_never_writes_or_mutates_raw_rows(client):
    await _persist(_quarter_dtos("CHE", 2000, 1, TWENTY_QUARTERS))
    before_count = await _observation_count()
    signal = await _normalize("CHE", SNAPSHOT_2004_Q4)
    assert signal is not None
    after_count = await _observation_count()
    assert after_count == before_count
    # Raw period_start values are untouched (quarter-start dates preserved).
    async with session_module._sessionmaker() as session:
        starts = (
            await session.execute(
                select(Observation.period_start).order_by(Observation.period_start)
            )
        ).scalars().all()
    assert starts[0].date() == date(2000, 1, 1)
    assert starts[-1].date() == date(2004, 10, 1)


def test_normalized_signal_has_no_force_fields():
    # Structural: the signal stays INDICATOR-level — no force score, weight,
    # or phase field exists on the type.
    from typing import get_type_hints

    from app.cycle.normalization_definitions import NormalizedSignal

    fields = set(get_type_hints(NormalizedSignal))
    for forbidden in ("force_score", "weight", "phase", "stage", "force"):
        assert forbidden not in fields