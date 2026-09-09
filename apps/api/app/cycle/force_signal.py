"""ForceSignal — derived, NON-PERSISTED force-level signal (Sprint 5.22).

Companion to .dev/FORCE_AGGREGATION.md. This module implements the ForceSignal
dataclass and the PURE aggregation function that consumes already-produced
NormalizedSignal objects.

Layering (preserved from NORMALIZATION.md + FORCE_AGGREGATION.md):

    Observation -> AlignedValue -> NormalizedSignal -> ForceSignal

This module works at the FORCE level. It does NOT:
- query the database (the pure function accepts NormalizedSignal objects)
- accept raw Observations
- persist anything
- expose an API
- calculate confidence
- compose multi-indicator forces (DEFERRED_MULTI -> None)

Sprint 5.22 implements exactly DEC-029 / force-aggregation-v0.1:
- IDENTITY_SINGLE for Rule of law, Corruption, Internal conflict proxy
- DEFERRED_MULTI for all other forces (level/relative/momentum = None)
- confidence = None everywhere
- backtest_safe = False everywhere

Sprint 6.4 (DEC-032) / force-aggregation-v0.2 promotes Education to the
fourth executable force:
- IDENTITY_SINGLE for Rule of law, Corruption, Internal conflict proxy,
  Education (PROXY_CONDITION, PARTIAL ceiling)
- DEFERRED_MULTI for all other 13 forces (level/relative/momentum = None)
- Education level copies TERTIARY_ATTAINMENT_25_34's level_score (aligned
  raw OECD percentage); Education relative/momentum/confidence stay None
- confidence = None everywhere; backtest_safe = False everywhere

Sprint 6.7 (DEC-034) / force-aggregation-v0.3 promotes Wealth-gap to the
fifth executable force:
- IDENTITY_SINGLE for Rule of law, Corruption, Internal conflict proxy,
  Education (PROXY_CONDITION, PARTIAL ceiling), Wealth-gap (PROXY_CONDITION,
  PARTIAL ceiling)
- DEFERRED_MULTI for all other 12 forces (level/relative/momentum = None)
- Wealth-gap level copies WEALTH_SHARE_TOP_10's level_score
  (100 * (1 - raw_share)); GINI_INDEX stays SUPPORTING_CONTEXT (not
  averaged, not combined); Wealth-gap relative/momentum/confidence stay None
- confidence = None everywhere; backtest_safe = False everywhere
"""
from dataclasses import dataclass, field
from typing import Optional

from app.cycle.force_aggregation_definitions import (
    FORCE_AGGREGATION_CONFIGS,
    FORCE_AGGREGATION_VERSION,
    ForceAggregationMode,
    ForceAggregationSpec,
    ForceDimensionMode,
    ForceIndicatorComponentSpec,
    ForceIndicatorRole,
    aggregation_mode,
)
from app.cycle.force_definitions import ForceCoverageStatus
from app.cycle.normalization_definitions import (
    CURRENT_MODEL_VERSION,
    NormalizedSignal,
)


def _resolve_normalization_version(
    present_signals: list[NormalizedSignal],
) -> str:
    """Derive the ForceSignal normalization_model_version from contributing
    NormalizedSignals.

    Each NormalizedSignal carries its own `model_version: str` provenance. A
    ForceSignal must never claim a normalization version different from the
    actual contributing signals. If contributing signals disagree on version,
    fail loudly (no silent "majority" or "first" wins). If no signals are
    present, fall back to CURRENT_MODEL_VERSION.version_id — this is a
    documentation limitation: a force with no contributing signals has no
    real normalization provenance to propagate, so the current model version
    is the only honest placeholder.

    TODO(future): when normalization versioning becomes per-indicator
    (different indicators on different approved versions), this resolver
    must be replaced with an explicit per-component version map rather than
    a single shared string. For force-aggregation-v0.2 all implemented
    indicators share normalization-v0.7, so a single string is correct.
    """
    if not present_signals:
        return CURRENT_MODEL_VERSION.version_id
    versions = {s.model_version for s in present_signals}
    if len(versions) > 1:
        raise ValueError(
            f"contributing NormalizedSignals disagree on model_version: "
            f"{sorted(versions)}"
        )
    return present_signals[0].model_version


# --- ForceSignal type --------------------------------------------------------


@dataclass(frozen=True)
class ForceSignal:
    """Per-force derived signal. NON-PERSISTED (Sprint 5.22).

    Published dimensions (Sprint 5.22, force-aggregation-v0.1; Sprint 6.4,
    force-aggregation-v0.2):
    - level_score: identity copy from the single eligible component for the
      4 approved forces (Rule of law, Corruption, Internal conflict proxy,
      Education); None for all other forces.
    - relative_score: identity copy (with full provenance) for the 3
      approved WGI forces; None for Education and all other forces.
    - momentum: identity copy for the 3 approved WGI forces; None for
      Education and all other forces.
    - confidence: None everywhere (DEC-023 deferred numeric confidence).

    Still None everywhere: confidence. backtest_safe = False everywhere.

    MISSING != ZERO: absent dimensions are None, never 0. An unscored force
    is never a zero-score force.

    Coverage is INDEPENDENT from strength: a force may have coverage =
    AVAILABLE with level_score = None (e.g. Indebtedness), or coverage =
    PARTIAL with level_score = 70 (e.g. Internal conflict proxy). Coverage
    never multiplies the score.
    """

    country_iso3: str
    force_code: str
    scoring_period: str

    # Score dimensions — None when not approved or component unavailable.
    level_score: Optional[float] = None
    relative_score: Optional[float] = None
    momentum: Optional[float] = None
    confidence: Optional[float] = None

    # Coverage (independent from strength).
    coverage_status: ForceCoverageStatus = ForceCoverageStatus.missing
    coverage_ceiling: Optional[ForceCoverageStatus] = None

    # Component provenance — the NormalizedSignals that fed this force.
    # Preserved even when the force aggregate is None (DEFERRED_MULTI).
    component_signals: tuple[NormalizedSignal, ...] = ()
    # Indicators that have no signal (no eligible observation / too stale).
    missing_components: tuple[str, ...] = ()
    # Indicators whose role is SUPPORTING_CONTEXT or whose normalization is
    # not implemented — recorded as deferred, not scored.
    deferred_components: tuple[str, ...] = ()

    # Methodology provenance.
    aggregation_method: ForceAggregationMode = ForceAggregationMode.deferred_multi
    force_model_version: str = FORCE_AGGREGATION_VERSION
    normalization_model_version: str = CURRENT_MODEL_VERSION.version_id
    backtest_safe: bool = False

    # Relative provenance (identity-copy forces only): copied, not recomputed.
    reference_universe_id: Optional[str] = None
    reference_universe_expected_n: Optional[int] = None
    reference_universe_usable_n: Optional[int] = None
    relative_rank: Optional[float] = None

    # The configured component that produced the score (identity forces only).
    scoring_component_indicator: Optional[str] = None

    def __post_init__(self) -> None:
        # Score range validation — never clamp, invalid -> error.
        if self.level_score is not None:
            if not 0.0 <= self.level_score <= 100.0:
                raise ValueError(
                    f"{self.force_code}: level_score must be in [0, 100], "
                    f"got {self.level_score}"
                )
        if self.relative_score is not None:
            if not 0.0 <= self.relative_score <= 100.0:
                raise ValueError(
                    f"{self.force_code}: relative_score must be in [0, 100], "
                    f"got {self.relative_score}"
                )
        if self.momentum is not None:
            if not -100.0 <= self.momentum <= 100.0:
                raise ValueError(
                    f"{self.force_code}: momentum must be in [-100, 100], "
                    f"got {self.momentum}"
                )
        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError(
                    f"{self.force_code}: confidence must be in [0, 1], "
                    f"got {self.confidence}"
                )


# --- Pure aggregation function ----------------------------------------------


def aggregate_force_from_signals(
    force_spec: ForceAggregationSpec,
    country_iso3: str,
    scoring_period: str,
    component_signals: dict[str, Optional[NormalizedSignal]],
    coverage_status: ForceCoverageStatus,
    coverage_ceiling: Optional[ForceCoverageStatus] = None,
) -> ForceSignal:
    """PURE aggregation: consume NormalizedSignal objects, produce ForceSignal.

    No DB query. No raw Observation accepted. No persistence.

    IDENTITY_SINGLE (Rule of law, Corruption, Internal conflict proxy):
        force.level_score = component.level_score (exact copy, no rescale)
        force.relative_score = component.relative_score (exact copy + provenance)
        force.momentum = component.momentum (exact copy)
        Each dimension propagates independently — None stays None, never zero.

    DEFERRED_MULTI (all other forces):
        level/relative/momentum/confidence = None.
        Component signals preserved as provenance. No averaging.

    SUPPORTING_CONTEXT components never contribute numerically — they are
    recorded as deferred_components.
    """
    mode = aggregation_mode(force_spec)

    # Partition components into scored / missing / deferred.
    present_signals: list[NormalizedSignal] = []
    missing: list[str] = []
    deferred: list[str] = []

    for comp in force_spec.components:
        signal = component_signals.get(comp.indicator_code)
        if comp.role is ForceIndicatorRole.supporting_context:
            # Supporting context never contributes numerically. It is always
            # deferred — even if a signal happens to exist, it is NOT used.
            deferred.append(comp.indicator_code)
            continue
        if signal is None:
            # No eligible observation / too stale / normalization not
            # implemented. Missing != zero.
            missing.append(comp.indicator_code)
            continue
        present_signals.append(signal)

    if mode is ForceAggregationMode.identity_single:
        return _build_identity_single(
            force_spec=force_spec,
            country_iso3=country_iso3,
            scoring_period=scoring_period,
            component_signals=component_signals,
            present_signals=present_signals,
            missing=missing,
            deferred=deferred,
            coverage_status=coverage_status,
            coverage_ceiling=coverage_ceiling,
        )

    # DEFERRED_MULTI — all numeric dimensions None, provenance preserved.
    return ForceSignal(
        country_iso3=country_iso3,
        force_code=force_spec.force_code,
        scoring_period=scoring_period,
        level_score=None,
        relative_score=None,
        momentum=None,
        confidence=None,
        coverage_status=coverage_status,
        coverage_ceiling=coverage_ceiling,
        component_signals=tuple(present_signals),
        missing_components=tuple(missing),
        deferred_components=tuple(deferred),
        aggregation_method=ForceAggregationMode.deferred_multi,
        normalization_model_version=_resolve_normalization_version(
            present_signals
        ),
    )


def _build_identity_single(
    *,
    force_spec: ForceAggregationSpec,
    country_iso3: str,
    scoring_period: str,
    component_signals: dict[str, Optional[NormalizedSignal]],
    present_signals: list[NormalizedSignal],
    missing: list[str],
    deferred: list[str],
    coverage_status: ForceCoverageStatus,
    coverage_ceiling: Optional[ForceCoverageStatus],
) -> ForceSignal:
    """Build an IDENTITY_SINGLE ForceSignal.

    The eligible component is exactly one (validated at config time). Copy
    its dimensions exactly — no rescaling, no weighting, no averaging, no
    rounding. None propagates independently per dimension.
    """
    # Find the single eligible component (CORE_CONDITION or PROXY_CONDITION).
    eligible_comp: Optional[ForceIndicatorComponentSpec] = None
    for comp in force_spec.components:
        if comp.role in {
            ForceIndicatorRole.core_condition,
            ForceIndicatorRole.proxy_condition,
        }:
            eligible_comp = comp
            break
    # Config validation guarantees exactly one eligible component.
    assert eligible_comp is not None

    signal = component_signals.get(eligible_comp.indicator_code)

    # If the eligible component has no signal, all dimensions are None.
    if signal is None:
        return ForceSignal(
            country_iso3=country_iso3,
            force_code=force_spec.force_code,
            scoring_period=scoring_period,
            level_score=None,
            relative_score=None,
            momentum=None,
            confidence=None,
            coverage_status=coverage_status,
            coverage_ceiling=coverage_ceiling,
            component_signals=tuple(present_signals),
            missing_components=tuple(
                missing + [eligible_comp.indicator_code]
                if eligible_comp.indicator_code not in missing
                else missing
            ),
            deferred_components=tuple(deferred),
            aggregation_method=ForceAggregationMode.identity_single,
            scoring_component_indicator=eligible_comp.indicator_code,
            normalization_model_version=_resolve_normalization_version(
                present_signals
            ),
        )

    # Copy dimensions exactly — each propagates independently.
    level_score = signal.level_score if force_spec.level_mode is ForceDimensionMode.identity_copy else None
    relative_score = signal.relative_score if force_spec.relative_mode is ForceDimensionMode.identity_copy else None
    momentum = signal.momentum if force_spec.momentum_mode is ForceDimensionMode.identity_copy else None

    # Relative provenance: copy, do not recompute. Copy whenever the component
    # signal exists AND relative identity_copy is approved — even if
    # relative_score is None (DEC-017 incomplete-universe semantics: the
    # universe metadata is real provenance even when the score is missing).
    # Never fabricate provenance when there is no component signal (handled
    # in the signal-is-None branch above).
    reference_universe_id = None
    reference_universe_expected_n = None
    reference_universe_usable_n = None
    relative_rank = None
    if force_spec.relative_mode is ForceDimensionMode.identity_copy:
        reference_universe_id = signal.reference_universe_id
        reference_universe_expected_n = signal.reference_universe_expected_n
        reference_universe_usable_n = signal.reference_universe_usable_n
        relative_rank = signal.relative_rank

    return ForceSignal(
        country_iso3=country_iso3,
        force_code=force_spec.force_code,
        scoring_period=scoring_period,
        level_score=level_score,
        relative_score=relative_score,
        momentum=momentum,
        confidence=None,  # always None (DEC-023)
        coverage_status=coverage_status,
        coverage_ceiling=coverage_ceiling,
        component_signals=tuple(present_signals),
        missing_components=tuple(missing),
        deferred_components=tuple(deferred),
        aggregation_method=ForceAggregationMode.identity_single,
        scoring_component_indicator=eligible_comp.indicator_code,
        reference_universe_id=reference_universe_id,
        reference_universe_expected_n=reference_universe_expected_n,
        reference_universe_usable_n=reference_universe_usable_n,
        relative_rank=relative_rank,
        normalization_model_version=_resolve_normalization_version(
            present_signals
        ),
    )
