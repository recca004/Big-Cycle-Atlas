"""Indicator-level normalizer — Sprint 5.6 + Sprint 5.7 momentum + Sprint 5.8
relative + Sprint 5.10 DSR own-history level + Sprint 5.12 credit-gap
one-sided vulnerability level.

Layering (NORMALIZATION.md, preserved):

    Observation -> as-of alignment -> AlignedValue -> indicator normalizer -> NormalizedSignal

This module works entirely at the INDICATOR level. No force aggregation, no
force weights, no Big Cycle phase — the force layer does not exist yet.

Implemented (Sprint 5.6): DIRECT_0_100 level only (the three WGI governance
scores). Implemented (Sprint 5.7, DEC-016): OWN_HISTORY momentum for the WGI
x3 — the SIGNED change in the provider's own 0-100 points between the current
aligned raw value and the anchor aligned raw value, for the model-versioned
windows (3y, 5y). Implemented (Sprint 5.8, DEC-017):
CROSS_SECTIONAL_RELATIVE relative scores for the WGI x3 within the frozen
tracked_8 universe.

Implemented (Sprint 5.10, DEC-019): OWN_HISTORY LEVEL for EXACTLY
DEBT_SERVICE_RATIO — the first non-WGI level signal. The level answers
"where is the country's current DSR relative to ITS OWN historical DSR
distribution available as of this snapshot?" Calibration is the country's
EXPANDING own history of REAL observations (one latest-vintage value per
actual source period, via the alignment layer's own_history_as_of —
country isolation, DEC-015 period-complete eligibility, no future data, no
forward-fill); the current observation is INCLUDED. Method: empirical
mid-rank plotting position — stress_percentile = 100 * (average_rank - 0.5)
/ n with rank 1 = lowest DSR (least stress), ties = average rank;
level_score = 100 - stress_percentile (higher DSR = greater burden = weaker;
finite-sample endpoints are NOT forced to 100/0). Minimum sample = 20
observations (Atlas MODEL PARAMETER): insufficient history -> level_score
None, never zero, with the counts carried as provenance. Freshness gates the
CURRENT value only and NEVER scales the score; historical calibration points
are not decayed. Cross-country DSR ranking is prohibited (relative None);
DSR momentum is NOT implemented in this sprint (registry 4q/8q windows stay
unapproved); confidence stays None.

Implemented (Sprint 5.12, DEC-021): ONE_SIDED_VULNERABILITY LEVEL for EXACTLY
CREDIT_TO_GDP_GAP — the second non-WGI level signal, with the OWNER-APPROVED
curve: level_score = 50 for a gap at or below +2pp (the no-excess region is
deliberately NEUTRAL 50, not 100 — absence of excess credit is not evidence
of strength), then LINEAR from (+2, 50) to (+10, 0), and 0 at or above +10pp
(endpoint clamps: no floor below +2, no cap above +10 — a negative gap
carries NO penalty per DEC-020). The +2/+10 breakpoints coincide with the
Basel CCyB guide's L/H reference points; the 50/0 score mapping is an Atlas
MODEL PARAMETER, not Basel methodology truth — the gap remains a common
reference point, NOT a mechanical standalone rule. Same execution-gate
pattern as DSR: a registry ONE_SIDED_VULNERABILITY family alone never
auto-enables — an explicit one_sided_vulnerability_configs entry in the model
version is required, and v0.6 carries exactly one: CREDIT_TO_GDP_GAP. No
minimum-history gate (the curve is parametric). Freshness gates the CURRENT
observation only and NEVER scales the score. Credit-gap relative stays
CONTEXTUAL_DEFERRED (None) and registry momentum windows (4q/8q) stay
UNAPPROVED (momentum None). Confidence stays None.

Execution gates: OWN_HISTORY level requires BOTH the registry level family
AND an explicit own_history_level_configs entry in the model version — a
registry OWN_HISTORY entry alone never auto-enables an indicator; the same
gate applies to ONE_SIDED_VULNERABILITY (explicit
one_sided_vulnerability_configs entry required). No generic fallback exists
anywhere.

Still None on every signal: confidence (composition unresolved, §17 — the
freshness FACTOR is carried, but it is not the confidence score).

Every signal carries backtest_safe = False: alignment is by observation
period, not by historical release date (Milestone 9 owns that). Computed on
demand; nothing is persisted.
"""
from collections.abc import Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from app.cycle.freshness import (
    FreshnessPolicy,
    DEFAULT_FRESHNESS_POLICIES,
    evaluate_freshness,
    own_period_age,
)
from app.cycle.normalization_definitions import (
    CURRENT_MODEL_VERSION,
    ModelVersionConfig,
    MomentumWindowResult,
    NormalizationDataError,
    NormalizationFamily,
    NormalizationNotImplementedError,
    NormalizationSpec,
    NormalizedSignal,
    OneSidedVulnerabilityConfig,
    OneSidedVulnerabilityResult,
    OwnHistoryLevelResult,
    REFERENCE_UNIVERSES,
    ScoringPeriod,
    get_normalization_spec,
)
from app.cycle.relative import build_relative_cross_section
from app.services.alignment_service import (
    align_observation_as_of,
    own_history_as_of,
    shift_scoring_period_years,
)

# Re-exported since Sprint 5.8 (canonical home: normalization_definitions) so
# existing `from app.cycle.normalizer import ...` imports keep working.
__all__ = [
    "NormalizationDataError",
    "NormalizationNotImplementedError",
    "normalize_indicator_as_of",
]


async def _momentum_window_result(
    session: AsyncSession,
    country_iso3: str,
    indicator_code: str,
    scoring_period: ScoringPeriod,
    window_years: int,
    anchor_tolerance_periods: int,
    current_raw: float,
) -> MomentumWindowResult:
    """One window's signed change + provenance (DEC-016).

    The anchor is align_observation_as_of at the shifted scoring period —
    the SAME machinery as the current value, so country isolation
    (ISSUE-004), latest-vintage selection, DEC-015 period-complete
    eligibility, and no-future-leakage all apply. The aligned anchor may be
    older than the requested anchor year (period-completeness + historical
    gaps); the versioned tolerance bounds how much older. Outside tolerance:
    change = None — never zero, never a stretched window. The anchor is NOT
    freshness-decayed: it is intentionally historical.
    """
    anchor_period = shift_scoring_period_years(scoring_period, window_years)
    anchor = await align_observation_as_of(
        session, country_iso3, indicator_code, anchor_period
    )
    if anchor is None:
        return MomentumWindowResult(
            window_years=window_years,
            requested_anchor_period=anchor_period.label,
            anchor_source_period=None,
            change=None,
        )
    # Tolerance in own periods: for the WGI (annual) gate the effective
    # period end's year IS the source year, so this is "at most N source
    # years older than the requested anchor year" (1 covers the known
    # 1997/1999/2001 biennial gaps).
    years_older = anchor_period.year - anchor.effective_period_end.year
    if years_older > anchor_tolerance_periods:
        return MomentumWindowResult(
            window_years=window_years,
            requested_anchor_period=anchor_period.label,
            anchor_source_period=anchor.source_period,
            change=None,
        )
    if not 0.0 <= anchor.raw_value <= 100.0:
        raise NormalizationDataError(
            f"{indicator_code} for {country_iso3} anchor at source period "
            f"{anchor.source_period}: DIRECT_0_100 expects a provider value "
            f"in [0, 100], got {anchor.raw_value} — refusing to clamp"
        )
    # Higher WGI = stronger governance (DEC-016): no sign inversion.
    change = current_raw - anchor.raw_value
    return MomentumWindowResult(
        window_years=window_years,
        requested_anchor_period=anchor_period.label,
        anchor_source_period=anchor.source_period,
        change=change,
    )


def own_history_stress_position(
    sample: Sequence[float], current: float
) -> tuple[float, float]:
    """Empirical mid-rank stress position of `current` within its own-history
    sample (DEC-019).

    sample must CONTAIN the current value (the expanding calibration includes
    it by construction). Sorted ascending, rank 1 = lowest value = least
    stress. Ties share the AVERAGE of the tied positions — deterministic and
    input-order independent (never broken by period, row id, or insertion
    order). stress_percentile = 100 * (average_rank - 0.5) / n — a plotting
    position, so a finite observed history never forces 100/0 endpoints.
    Pure function: no DB access, no persistence.
    """
    n = len(sample)
    if n == 0:
        raise ValueError("own_history_stress_position requires a non-empty sample")
    strictly_below = sum(1 for value in sample if value < current)
    tied = sum(1 for value in sample if value == current)
    if tied == 0:
        raise ValueError("current value is not part of the calibration sample")
    average_rank = strictly_below + (tied + 1) / 2.0
    stress_percentile = 100.0 * (average_rank - 0.5) / n
    return average_rank, stress_percentile


def one_sided_vulnerability_level(
    value: float, config: OneSidedVulnerabilityConfig
) -> float:
    """Owner-approved ONE_SIDED_VULNERABILITY level curve (DEC-021, Sprint 5.12).

    value <= neutral_ceiling  -> no_excess_score (deliberately neutral —
        absence of excess credit is NOT evidence of strength).
    neutral_ceiling < value < saturation_value -> LINEAR from
        (ceiling, no_excess_score) to (saturation, saturated_score).
    value >= saturation_value -> saturated_score (endpoint clamp).

    Higher score = less excess-credit vulnerability. Pure function: no DB
    access, no persistence.
    """
    if value <= config.neutral_ceiling:
        return config.no_excess_score
    if value >= config.saturation_value:
        return config.saturated_score
    span = config.saturation_value - config.neutral_ceiling
    fraction = (value - config.neutral_ceiling) / span
    return config.no_excess_score + fraction * (
        config.saturated_score - config.no_excess_score
    )


async def normalize_indicator_as_of(
    session: AsyncSession,
    country_iso3: str,
    indicator_code: str,
    scoring_period: ScoringPeriod,
    model_config: ModelVersionConfig = CURRENT_MODEL_VERSION,
    freshness_policy: FreshnessPolicy | None = None,
) -> NormalizedSignal | None:
    """Normalize one indicator for one country as of a quarterly snapshot.

    Returns None when no eligible observation exists or the aligned
    observation is too stale per the freshness policy — the signal is NOT
    produced, never produced-with-zero (MISSING != ZERO).
    """
    if model_config.backtest_safe:
        # No release-date discipline exists yet (Milestone 9). No model
        # version may claim backtest safety before then.
        raise ValueError(
            f"model version {model_config.version_id!r} claims backtest_safe=True; "
            "release-date discipline does not exist until Milestone 9"
        )

    spec = get_normalization_spec(indicator_code)
    if spec.level_family is NormalizationFamily.direct_0_100:
        return await _normalize_direct_0_100_as_of(
            session, spec, country_iso3, scoring_period, model_config, freshness_policy
        )
    if spec.level_family is NormalizationFamily.own_history:
        return await _normalize_own_history_as_of(
            session, spec, country_iso3, scoring_period, model_config, freshness_policy
        )
    if spec.level_family is NormalizationFamily.one_sided_vulnerability:
        return await _normalize_one_sided_vulnerability_as_of(
            session, spec, country_iso3, scoring_period, model_config, freshness_policy
        )
    raise NormalizationNotImplementedError(
        f"{indicator_code}: level family {spec.level_family.value} is not "
        "implemented (executable: DIRECT_0_100 for the WGI x3, OWN_HISTORY for "
        "DEBT_SERVICE_RATIO only, ONE_SIDED_VULNERABILITY for "
        "CREDIT_TO_GDP_GAP only)"
    )


async def _normalize_one_sided_vulnerability_as_of(
    session: AsyncSession,
    spec: NormalizationSpec,
    country_iso3: str,
    scoring_period: ScoringPeriod,
    model_config: ModelVersionConfig,
    freshness_policy: FreshnessPolicy | None,
) -> NormalizedSignal | None:
    """ONE_SIDED_VULNERABILITY level (DEC-021, Sprint 5.12): credit gap only.

    The registry's one_sided_vulnerability level family does NOT auto-enable
    an indicator — an explicit one_sided_vulnerability_configs entry in the
    model version is required, and v0.6 carries exactly one:
    CREDIT_TO_GDP_GAP, with the owner-approved curve (flat 50 at/below +2pp,
    linear to 0 at +10pp, clamped above). No minimum-history gate: the curve
    is parametric, unlike the DSR own-history calibration.
    """
    config = model_config.one_sided_vulnerability_configs.get(spec.indicator_code)
    if config is None:
        raise NormalizationNotImplementedError(
            f"{spec.indicator_code}: registry ONE_SIDED_VULNERABILITY level "
            f"family, but no one-sided vulnerability level config exists in "
            f"model version {model_config.version_id!r} — not auto-enabled"
        )

    policy = freshness_policy or DEFAULT_FRESHNESS_POLICIES[spec.freshness_class]
    aligned = await align_observation_as_of(
        session, country_iso3, spec.indicator_code, scoring_period
    )
    if aligned is None:
        return None  # no eligible observation — no signal, never a zero

    freshness = evaluate_freshness(
        own_period_age(aligned.age_periods, spec.freshness_class), policy
    )
    if not freshness.is_usable:
        # Too stale: no signal for this snapshot — never a zero score.
        return None

    level_score = one_sided_vulnerability_level(aligned.raw_value, config)

    return NormalizedSignal(
        indicator_code=spec.indicator_code,
        country_iso3=country_iso3,
        as_of_period=scoring_period,
        raw_value=aligned.raw_value,
        source_period=aligned.source_period,
        method=NormalizationFamily.one_sided_vulnerability,
        model_version=model_config.version_id,
        level_score=level_score,
        relative_score=None,  # CONTEXTUAL_DEFERRED — deliberately unresolved
        momentum=None,  # registry 4q/8q windows stay UNAPPROVED (DEC-021)
        confidence=None,  # deliberately not calculated (composition unresolved, §17)
        reference_universe_id=None,
        one_sided_vulnerability_level=OneSidedVulnerabilityResult(
            neutral_ceiling=config.neutral_ceiling,
            saturation_value=config.saturation_value,
            no_excess_score=config.no_excess_score,
            saturated_score=config.saturated_score,
            level_score=level_score,
        ),
        backtest_safe=model_config.backtest_safe,
        freshness_factor=freshness.factor,
        is_stale=freshness.is_stale,
    )


async def _normalize_own_history_as_of(
    session: AsyncSession,
    spec: NormalizationSpec,
    country_iso3: str,
    scoring_period: ScoringPeriod,
    model_config: ModelVersionConfig,
    freshness_policy: FreshnessPolicy | None,
) -> NormalizedSignal | None:
    """OWN_HISTORY level (DEC-019, Sprint 5.10): DEBT_SERVICE_RATIO only.

    The registry's own_history level family does NOT auto-enable an
    indicator — an explicit own_history_level_configs entry in the model
    version is required, and the current model version carries exactly one:
    DEBT_SERVICE_RATIO.
    """
    config = model_config.own_history_level_configs.get(spec.indicator_code)
    if config is None:
        raise NormalizationNotImplementedError(
            f"{spec.indicator_code}: registry OWN_HISTORY level family, but no "
            f"own-history level config exists in model version "
            f"{model_config.version_id!r} — not auto-enabled"
        )

    policy = freshness_policy or DEFAULT_FRESHNESS_POLICIES[spec.freshness_class]
    history = await own_history_as_of(
        session, country_iso3, spec.indicator_code, scoring_period
    )
    if not history:
        return None  # no eligible observation — no signal, never a zero

    # The current observation is the newest element of the expanding sample
    # (included by construction — the sample IS the history through T).
    current = history[-1]
    freshness = evaluate_freshness(
        own_period_age(current.age_periods, spec.freshness_class), policy
    )
    if not freshness.is_usable:
        # Too stale: no signal for this snapshot — never a zero score.
        return None

    sample = [obs.raw_value for obs in history]
    rank: float | None = None
    stress_percentile: float | None = None
    level_score: float | None = None
    if len(sample) >= config.minimum_sample_n:
        rank, stress_percentile = own_history_stress_position(
            sample, current.raw_value
        )
        # Higher DSR = greater debt-service burden = weaker (DEC-019): the
        # level score inverts the stress percentile. NOT clamped to 0/100 —
        # a finite observed history does not prove absolute strength/weakness.
        level_score = 100.0 - stress_percentile
    # Insufficient history: level_score stays None — never zero, never a
    # stretched sample; the counts still travel as provenance.

    return NormalizedSignal(
        indicator_code=spec.indicator_code,
        country_iso3=country_iso3,
        as_of_period=scoring_period,
        raw_value=current.raw_value,
        source_period=current.source_period,
        method=NormalizationFamily.own_history,
        model_version=model_config.version_id,
        level_score=level_score,
        relative_score=None,  # cross-country DSR ranking is prohibited (BIS caution)
        momentum=None,  # DSR momentum NOT approved in this sprint
        confidence=None,  # deliberately not calculated (composition unresolved, §17)
        reference_universe_id=None,
        own_history_level=OwnHistoryLevelResult(
            sample_n=len(sample),
            minimum_sample_n=config.minimum_sample_n,
            earliest_source_period=history[0].source_period,
            latest_source_period=current.source_period,
            rank=rank,
            stress_percentile=stress_percentile,
            level_score=level_score,
        ),
        backtest_safe=model_config.backtest_safe,
        freshness_factor=freshness.factor,
        is_stale=freshness.is_stale,
    )


async def _normalize_direct_0_100_as_of(
    session: AsyncSession,
    spec: NormalizationSpec,
    country_iso3: str,
    scoring_period: ScoringPeriod,
    model_config: ModelVersionConfig,
    freshness_policy: FreshnessPolicy | None,
) -> NormalizedSignal | None:
    """DIRECT_0_100 path (Sprints 5.6-5.8): WGI x3 level + momentum + relative.

    Behavior is UNCHANGED by Sprint 5.10's dispatch refactor — WGI outputs
    must not depend on the new DSR own-history path.
    """
    indicator_code = spec.indicator_code
    policy = freshness_policy or DEFAULT_FRESHNESS_POLICIES[spec.freshness_class]

    aligned = await align_observation_as_of(session, country_iso3, indicator_code, scoring_period)
    if aligned is None:
        return None

    freshness = evaluate_freshness(
        own_period_age(aligned.age_periods, spec.freshness_class), policy
    )
    if not freshness.is_usable:
        # Too stale: no signal for this snapshot — never a zero score.
        return None

    raw = aligned.raw_value
    if not 0.0 <= raw <= 100.0:
        raise NormalizationDataError(
            f"{indicator_code} for {country_iso3} at source period "
            f"{aligned.source_period}: DIRECT_0_100 expects a provider value in "
            f"[0, 100], got {raw} — refusing to clamp"
        )

    # --- Momentum (Sprint 5.7, DEC-016): WGI x3 OWN_HISTORY only -------------
    # Execution gate: BOTH the level family (DIRECT_0_100) and the momentum
    # family (OWN_HISTORY) must hold. For Sprint 5.7 this resolves exactly to
    # the WGI x3 — other indicators' registry OWN_HISTORY momentum_family
    # entries do NOT make their momentum approved, and no generic fallback
    # exists.
    if not (
        spec.level_family is NormalizationFamily.direct_0_100
        and spec.momentum_family is NormalizationFamily.own_history
    ):
        raise NormalizationNotImplementedError(
            f"{indicator_code}: momentum gate requires level DIRECT_0_100 + "
            f"momentum OWN_HISTORY (got {spec.level_family.value} + "
            f"{spec.momentum_family.value if spec.momentum_family else None})"
        )
    windows = model_config.momentum_windows.get(indicator_code, spec.momentum_windows)
    primary_window = model_config.momentum_primary_window_years.get(indicator_code)
    tolerance = model_config.momentum_anchor_tolerance_periods.get(indicator_code)
    if not windows or primary_window is None or tolerance is None:
        raise NormalizationNotImplementedError(
            f"{indicator_code}: momentum windows/primary/tolerance are not "
            f"configured in model version {model_config.version_id!r}"
        )

    # Computed from ALIGNED RAW values — never from level_score (which only
    # happens to equal raw for DIRECT_0_100 today).
    window_results = tuple(
        [
            await _momentum_window_result(
                session,
                country_iso3,
                indicator_code,
                scoring_period,
                window_years,
                tolerance,
                raw,
            )
            for window_years in windows
        ]
    )
    primary_result = next(
        (r for r in window_results if r.window_years == primary_window), None
    )
    momentum: float | None = None
    momentum_window_years: int | None = None
    if primary_result is not None and primary_result.change is not None:
        momentum = primary_result.change
        momentum_window_years = primary_window
    # If the primary window is unavailable: momentum stays None — NO
    # averaging with other windows and NO silent fallback to a shorter one;
    # the other windows remain visible in momentum_windows provenance.

    # --- Relative (Sprint 5.8, DEC-017): WGI x3 CROSS_SECTIONAL_RELATIVE ------
    # Execution gate: BOTH the relative family (CROSS_SECTIONAL_RELATIVE) and
    # the level family (DIRECT_0_100 — checked above) must hold. For Sprint
    # 5.8 this resolves exactly to the WGI x3: GDP_GROWTH, GCF, Gini, and
    # labour productivity also say CROSS_SECTIONAL_RELATIVE in the registry,
    # but their level families are NOT executable/approved, so they raise at
    # the level gate — their relative scoring must NOT silently enable.
    relative_score: float | None = None
    relative_rank: float | None = None
    reference_universe_id: str | None = None
    universe_expected_n: int | None = None
    universe_usable_n: int | None = None
    if spec.relative_family is NormalizationFamily.cross_sectional_relative:
        universe = REFERENCE_UNIVERSES[model_config.reference_universe_id]
        cross_section = await build_relative_cross_section(
            session, indicator_code, scoring_period, universe, freshness_policy=policy
        )
        # Provenance travels even when the universe is INCOMPLETE — a 7/8
        # cross-section is never silently scored as tracked_8.
        reference_universe_id = cross_section.universe_id
        universe_expected_n = cross_section.expected_n
        universe_usable_n = cross_section.usable_n
        member = cross_section.member_for(country_iso3)
        if cross_section.is_complete and member is not None:
            relative_rank = member.rank
            relative_score = member.relative_score
        # Freshness gates member usability inside the cross-section — it
        # NEVER scales relative_score (economic position, not trust).
    elif spec.relative_family is not None:
        raise NormalizationNotImplementedError(
            f"{indicator_code}: relative family {spec.relative_family.value} is "
            "not implemented (Sprint 5.8 implements CROSS_SECTIONAL_RELATIVE "
            "for the WGI x3 only)"
        )
    # spec.relative_family None: the dimension is not defensible for this
    # indicator — relative_score stays None.

    return NormalizedSignal(
        indicator_code=indicator_code,
        country_iso3=country_iso3,
        as_of_period=scoring_period,
        raw_value=raw,
        source_period=aligned.source_period,
        method=NormalizationFamily.direct_0_100,
        model_version=model_config.version_id,
        # DIRECT_0_100: the provider's absolute 0-100 scale IS the level
        # signal — no z-score, rank, percentile, rescale, invert, or
        # winsorize. Indicator-level signal, NOT a force score.
        level_score=raw,
        # Relative position within tracked_8 (DEC-017) — a SEPARATE dimension
        # from level_score; never a rescale of it, never a global percentile.
        relative_score=relative_score,
        relative_rank=relative_rank,
        reference_universe_id=reference_universe_id,
        reference_universe_expected_n=universe_expected_n,
        reference_universe_usable_n=universe_usable_n,
        confidence=None,  # deliberately not calculated (composition unresolved, §17)
        momentum=momentum,
        momentum_window_years=momentum_window_years,
        momentum_windows=window_results,
        backtest_safe=model_config.backtest_safe,
        freshness_factor=freshness.factor,
        is_stale=freshness.is_stale,
    )