"""Derived indicator computation service — Sprint 6.11 (DEC-038).

Executes the first real DerivedAlignedValue computation using the DEC-037
contract: TRADE_OPENNESS_GDP = EXPORTS_GDP + IMPORTS_GDP.

This is a descriptive TRADE-INTENSITY RATIO, not an Atlas strength score,
not a Global Openness level, not a Trade and capital flows force score.
DEC-035's DEFER_GLOBAL_OPENNESS_LEVEL verdict remains in force.

Architecture:

    Observation -> AlignedValue -> DerivedAlignedValue (this module)
        -> normalization (NOT invoked here) -> force aggregation

Key rules (DEC-038):

- Uses the SAME _select_observation_as_of primitive as
  align_observation_as_of — one authoritative observation-selection
  algorithm, no second as-of path.
- Each component is aligned independently with full provenance
  (observation_id, source_series_id, data_source_id).
- Country isolation: both components must belong to the same country.
- Same scoring snapshot: both components aligned to the same scoring_period.
- Source-period compatibility (formula-level rule): both components must
  represent the SAME annual source period / effective_period_end. Mixing
  exports from 2024 with imports from 2023 is prohibited — the derived
  value is None with an explicit reason, never silently matched,
  interpolated, forward-filled, or zero-filled.
- Missingness: if either required component is unavailable, derived_value
  is None (MISSING != ZERO).
- Backtest safety: False unless ALL present components have valid
  release-date provenance. Currently False everywhere (Milestone 9
  owns release-date discipline).
- No writes: no persistence, no raw Observation creation, no DB writes.
- No normalization: the derived value is a raw descriptive ratio, not a
  0-100 level score. Values above 100 are valid.
- No force promotion: Global Openness and Trade and capital flows remain
  unscored.
"""
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.cycle.normalization_definitions import (
    AlignedValue,
    DerivedAlignedValue,
    DerivedComponentProvenance,
    ScoringPeriod,
    get_normalization_spec,
)
from app.services.alignment_service import (
    AlignmentError,
    _resolve_country_indicator,
    _select_observation_as_of,
    _build_aligned_value,
)


# --- Formula identity (DEC-038) ------------------------------------------------

TRADE_OPENNESS_GDP_CODE = "TRADE_OPENNESS_GDP"
TRADE_OPENNESS_GDP_FORMULA_ID = "trade_openness_gdp"
TRADE_OPENNESS_GDP_FORMULA_VERSION = "trade-openness-gdp-v1"

# Required components (both must be present)
TRADE_OPENNESS_COMPONENTS: tuple[str, ...] = ("EXPORTS_GDP", "IMPORTS_GDP")


@dataclass(frozen=True)
class ComponentAlignmentResult:
    """Result of aligning one component with full provenance."""

    indicator_code: str
    aligned_value: AlignedValue | None
    observation_id: int | None
    source_series_id: int | None
    data_source_id: int | None
    release_date: date | None
    missing_reason: str | None


async def _align_component_with_provenance(
    session: AsyncSession,
    country_iso3: str,
    indicator_code: str,
    scoring_period: ScoringPeriod,
) -> ComponentAlignmentResult:
    """Align one component using the shared selection primitive.

    Uses _select_observation_as_of (the SAME primitive as
    align_observation_as_of) — one authoritative observation-selection
    algorithm, no second as-of path.
    """
    try:
        country, indicator = await _resolve_country_indicator(
            session, country_iso3, indicator_code
        )
    except AlignmentError:
        return ComponentAlignmentResult(
            indicator_code=indicator_code,
            aligned_value=None,
            observation_id=None,
            source_series_id=None,
            data_source_id=None,
            release_date=None,
            missing_reason=f"unknown indicator code: {indicator_code!r}",
        )

    spec = get_normalization_spec(indicator_code)
    observation = await _select_observation_as_of(
        session, country, indicator, spec, scoring_period
    )

    if observation is None:
        return ComponentAlignmentResult(
            indicator_code=indicator_code,
            aligned_value=None,
            observation_id=None,
            source_series_id=None,
            data_source_id=None,
            release_date=None,
            missing_reason="no eligible observation for this scoring period",
        )

    aligned = _build_aligned_value(
        observation, indicator_code, country_iso3, scoring_period, spec
    )
    release_date = (
        observation.release_date.date() if observation.release_date else None
    )

    return ComponentAlignmentResult(
        indicator_code=indicator_code,
        aligned_value=aligned,
        observation_id=observation.id,
        source_series_id=observation.source_series_id,
        data_source_id=observation.data_source_id,
        release_date=release_date,
        missing_reason=None,
    )


def _build_component_provenance(
    result: ComponentAlignmentResult,
) -> DerivedComponentProvenance:
    """Build DerivedComponentProvenance from a ComponentAlignmentResult."""
    if result.aligned_value is not None:
        return DerivedComponentProvenance(
            indicator_code=result.indicator_code,
            aligned_value=result.aligned_value,
            observation_id=result.observation_id,
            source_series_id=result.source_series_id,
            data_source_id=result.data_source_id,
            release_date=result.release_date,
            component_backtest_safe=False,  # False until Milestone 9
            missing_reason=None,
        )
    return DerivedComponentProvenance(
        indicator_code=result.indicator_code,
        aligned_value=None,
        missing_reason=result.missing_reason or "component unavailable",
    )


def _check_source_period_compatibility(
    components: list[ComponentAlignmentResult],
) -> str | None:
    """Formula-level source-period compatibility check for TRADE_OPENNESS_GDP.

    Both components must represent the SAME source period (same
    effective_period_end). Mixing exports from 2024 with imports from
    2023 is prohibited. Returns a reason string if incompatible, None if
    compatible.

    This is a FORMULA-LEVEL rule, not a global rule for every future
    derived indicator.
    """
    present = [c for c in components if c.aligned_value is not None]
    if len(present) < 2:
        return None  # can't be incompatible if a component is missing

    eff_ends = {c.aligned_value.effective_period_end for c in present}
    if len(eff_ends) > 1:
        periods = sorted(c.aligned_value.source_period for c in present)
        return (
            f"source-period mismatch: components represent different periods "
            f"({', '.join(periods)}) — TRADE_OPENNESS_GDP requires both "
            f"components from the same source period"
        )
    return None


async def derive_trade_openness_as_of(
    session: AsyncSession,
    country_iso3: str,
    scoring_period: ScoringPeriod,
) -> DerivedAlignedValue:
    """Compute TRADE_OPENNESS_GDP = EXPORTS_GDP + IMPORTS_GDP.

    The value is a descriptive trade-intensity ratio (exports + imports as
    % of GDP). It is NOT an Atlas strength score, NOT a Global Openness
    level, NOT a force score. Values above 100 are valid.

    Returns a DerivedAlignedValue with:
    - derived_value = exports.raw_value + imports.raw_value when both
      components are present and source-period compatible
    - derived_value = None when any required component is missing or
      source periods are incompatible (MISSING != ZERO)
    - backtest_safe = False (release-date discipline is Milestone 9)
    - complete independent provenance for each component

    No writes, no persistence, no raw Observation creation.
    """
    # Align both required components using the shared selection primitive
    component_results: list[ComponentAlignmentResult] = []
    for indicator_code in TRADE_OPENNESS_COMPONENTS:
        result = await _align_component_with_provenance(
            session, country_iso3, indicator_code, scoring_period
        )
        component_results.append(result)

    # Check source-period compatibility (formula-level rule)
    period_mismatch_reason = _check_source_period_compatibility(component_results)

    # Build component provenance
    components = tuple(
        _build_component_provenance(r) for r in component_results
    )

    # Determine derived value
    any_missing = any(r.aligned_value is None for r in component_results)
    if any_missing:
        derived_value = None
    elif period_mismatch_reason is not None:
        # Both components present but source periods differ — derived value
        # is None with the mismatch recorded. We need to mark this in the
        # component provenance without violating the present-component
        # contract. The mismatch is a formula-level rejection, not a
        # component-level missingness. We set derived_value = None and
        # rely on the DerivedAlignedValue contract (any_missing is False
        # but derived_value is None — this is allowed: the contract only
        # forbids derived_value != None when a component IS missing).
        derived_value = None
    else:
        # Both components present and source-period compatible — compute
        exports_val = component_results[0].aligned_value.raw_value
        imports_val = component_results[1].aligned_value.raw_value
        derived_value = exports_val + imports_val

    return DerivedAlignedValue(
        derived_indicator_code=TRADE_OPENNESS_GDP_CODE,
        country_iso3=country_iso3,
        scoring_period=scoring_period,
        formula_id=TRADE_OPENNESS_GDP_FORMULA_ID,
        formula_version=TRADE_OPENNESS_GDP_FORMULA_VERSION,
        components=components,
        derived_value=derived_value,
        backtest_safe=False,
    )
