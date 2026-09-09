"""Force signal service — orchestrates normalization + aggregation (Sprint 5.22).

Architecture (preserved):

    Observation -> align_observation_as_of -> NormalizedSignal -> ForceSignal

This service calls the EXISTING normalizer (normalize_indicator_as_of) for
configured indicators. It does NOT duplicate normalization logic. It does NOT
implement a parallel WGI scoring query.

Country scoping, latest-vintage selection, DEC-015 period-complete
eligibility, and no-future-leakage are all INHERITED from the alignment +
normalization layers.

Sprint 5.22 / force-aggregation-v0.1:
- 3 of 17 forces approved for IDENTITY_SINGLE (Rule of law, Corruption,
  Internal conflict proxy).
- 14 of 17 forces DEFERRED_MULTI (level/relative/momentum = None).
- confidence = None everywhere; backtest_safe = False everywhere.
- No persistence. No public API.

Sprint 6.4 / force-aggregation-v0.2 (DEC-032):
- 4 of 17 forces approved for IDENTITY_SINGLE (Rule of law, Corruption,
  Internal conflict proxy, Education).
- 13 of 17 forces DEFERRED_MULTI (level/relative/momentum = None).
- Education is a PROXY_CONDITION (PARTIAL ceiling) — its level copies the
  TERTIARY_ATTAINMENT_25_34 aligned raw percentage; relative/momentum/
  confidence stay None.
- confidence = None everywhere; backtest_safe = False everywhere.
- No persistence. No public API.

Sprint 6.7 / force-aggregation-v0.3 (DEC-034):
- 5 of 17 forces approved for IDENTITY_SINGLE (Rule of law, Corruption,
  Internal conflict proxy, Education, Wealth-gap).
- 12 of 17 forces DEFERRED_MULTI (level/relative/momentum = None).
- Wealth-gap is a PROXY_CONDITION (PARTIAL ceiling) — its level copies the
  WEALTH_SHARE_TOP_10 level_score (100 * (1 - raw_share)); GINI_INDEX stays
  SUPPORTING_CONTEXT (not averaged, not combined); relative/momentum/
  confidence stay None.
- confidence = None everywhere; backtest_safe = False everywhere.
- No persistence. No public API.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cycle.force_aggregation_definitions import (
    FORCE_AGGREGATION_CONFIGS,
    ForceAggregationSpec,
    ForceIndicatorRole,
)
from app.cycle.force_definitions import FORCE_DEFINITIONS, ForceCoverageStatus
from app.cycle.force_signal import ForceSignal, aggregate_force_from_signals
from app.cycle.normalization_definitions import NormalizedSignal, ScoringPeriod
from app.cycle.normalizer import normalize_indicator_as_of
from app.models import Country
from app.services.force_coverage_service import get_force_coverage


async def build_force_signals_as_of(
    session: AsyncSession,
    country_iso3: str,
    scoring_period: ScoringPeriod,
) -> tuple[ForceSignal, ...]:
    """Build exactly 17 ForceSignals for one country as of a scoring period.

    Returns exactly 17 entries — one per force definition, in definition
    order. No force is silently omitted.

    For each force:
    - coverage_status and coverage_ceiling come from the EXISTING deterministic
      force coverage service (not recomputed from signal presence).
    - component NormalizedSignals are produced by calling
      normalize_indicator_as_of for each configured component.
    - SUPPORTING_CONTEXT components are NOT normalized numerically (their
      normalization is deliberately not implemented) — they are recorded as
      deferred_components.
    - The pure aggregate_force_from_signals function produces the ForceSignal.

    No DB writes. No raw Observation accepted into force arithmetic.
    """
    # Resolve country_id for the coverage service.
    country_id = (
        await session.execute(
            select(Country.id).where(Country.iso3 == country_iso3)
        )
    ).scalar_one_or_none()
    if country_id is None:
        raise ValueError(f"unknown country iso3: {country_iso3}")

    # Coverage from the EXISTING deterministic service.
    coverages = await get_force_coverage(session, country_id)
    coverage_by_code = {cov.definition.code: cov for cov in coverages}

    signals: list[ForceSignal] = []
    for force_def in FORCE_DEFINITIONS:
        spec: ForceAggregationSpec = FORCE_AGGREGATION_CONFIGS[force_def.code]
        cov = coverage_by_code[force_def.code]

        # Build component NormalizedSignals.
        component_signals: dict[str, NormalizedSignal | None] = {}
        for comp in spec.components:
            if comp.role is ForceIndicatorRole.supporting_context:
                # Do NOT invoke unsupported numeric normalization for
                # supporting context. Record as deferred — no fake signal.
                component_signals[comp.indicator_code] = None
                continue
            # For eligible components (CORE_CONDITION / PROXY_CONDITION /
            # VULNERABILITY_PENALTY), call the normalizer. If the indicator's
            # normalization is not implemented, the normalizer raises
            # NormalizationNotImplementedError — but for v0.1 the only
            # eligible/vulnerability components with implemented normalization
            # are the WGI x3 (DIRECT_0_100), DSR (OWN_HISTORY), and credit gap
            # (ONE_SIDED_VULNERABILITY). All three are implemented.
            signal = await normalize_indicator_as_of(
                session,
                country_iso3=country_iso3,
                indicator_code=comp.indicator_code,
                scoring_period=scoring_period,
            )
            component_signals[comp.indicator_code] = signal

        force_signal = aggregate_force_from_signals(
            force_spec=spec,
            country_iso3=country_iso3,
            scoring_period=scoring_period.label,
            component_signals=component_signals,
            coverage_status=cov.status,
            coverage_ceiling=force_def.coverage_ceiling,
        )
        signals.append(force_signal)

    return tuple(signals)
