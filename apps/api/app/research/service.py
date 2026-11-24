"""Research orchestration — Mission 2 §15.

Async services composing existing force-signal machinery with the
experimental composite + cycle engines. Everything returned is labelled
experimental and retrospective (latest vintages; backtest_safe=False).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.cycle.normalization_definitions import ScoringPeriod
from app.research.composite import (
    COMPOSITE_MODELS,
    CompositeResult,
    run_composite,
)
from app.research.cycle import (
    CycleModelConfig,
    CycleResult,
    classify_series,
)
from app.services import force_signal_service


async def composite_at(
    session: AsyncSession,
    country_iso3: str,
    scoring_period: ScoringPeriod,
    model_id: str,
) -> CompositeResult:
    signals = await force_signal_service.build_force_signals_as_of(
        session, country_iso3, scoring_period
    )
    return run_composite(
        model_id,
        {s.force_code: s for s in signals},
        country_iso3,
        f"{scoring_period.year}-Q{scoring_period.quarter}",
    )


async def cycle_history(
    session: AsyncSession,
    country_iso3: str,
    model_id: str,
    start_year: int,
    end_year: int,
    latest: ScoringPeriod,
    cfg: CycleModelConfig | None = None,
) -> CycleResult:
    """Retrospective experimental cycle history at annual (Q4) snapshots.

    Earliest usable period is determined by actual composite coverage —
    never inferred from the earliest raw GDP observation."""
    if model_id not in COMPOSITE_MODELS:
        raise KeyError(model_id)
    cfg = cfg or CycleModelConfig()
    series: list[tuple[str, float | None]] = []
    for year in range(start_year, end_year + 1):
        sp = ScoringPeriod(year, 4)
        if (sp.year, sp.quarter) > (latest.year, latest.quarter):
            break
        result = await composite_at(session, country_iso3, sp, model_id)
        series.append((f"{year}-Q4", result.score))
    return classify_series(country_iso3, series, cfg)
