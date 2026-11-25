"""Research orchestration — Mission 2 §15, Mission 4 §23.

Async services composing existing force-signal machinery with the
experimental composite + cycle engines. Everything returned is labelled
experimental; the execution_mode records exactly how historical inputs
were selected (retrospective latest-vintage by default, strict as-of only
when an explicit ExecutionSpec is supplied).
"""
from __future__ import annotations

from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from app.cycle.execution_modes import (
    RETROSPECTIVE_SPEC,
    ExecutionSpec,
)
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
    execution: ExecutionSpec | None = None,
) -> CompositeResult:
    spec = execution or RETROSPECTIVE_SPEC
    signals = await force_signal_service.build_force_signals_as_of(
        session, country_iso3, scoring_period, execution=spec
    )
    result = run_composite(
        model_id,
        {s.force_code: s for s in signals},
        country_iso3,
        f"{scoring_period.year}-Q{scoring_period.quarter}",
    )
    # §25: composite safety propagates from ALL included inputs — a single
    # non-strict input disqualifies the whole result.
    safe = (
        spec.is_strict
        and result.score is not None
        and all(
            s.backtest_safe
            for s in signals
            if s.force_code in result.included_forces
        )
    )
    return replace(
        result, backtest_safe=safe, execution_mode=spec.mode.value
    )


async def cycle_history(
    session: AsyncSession,
    country_iso3: str,
    model_id: str,
    start_year: int,
    end_year: int,
    latest: ScoringPeriod,
    cfg: CycleModelConfig | None = None,
    execution: ExecutionSpec | None = None,
) -> CycleResult:
    """Retrospective experimental cycle history at annual (Q4) snapshots.

    Earliest usable period is determined by actual composite coverage —
    never inferred from the earliest raw GDP observation."""
    if model_id not in COMPOSITE_MODELS:
        raise KeyError(model_id)
    spec = execution or RETROSPECTIVE_SPEC
    cfg = cfg or CycleModelConfig()
    series: list[tuple[str, float | None]] = []
    all_safe = spec.is_strict
    for year in range(start_year, end_year + 1):
        sp = ScoringPeriod(year, 4)
        if (sp.year, sp.quarter) > (latest.year, latest.quarter):
            break
        result = await composite_at(
            session, country_iso3, sp, model_id, execution=spec
        )
        all_safe = all_safe and result.backtest_safe
        series.append((f"{year}-Q4", result.score))
    classified = classify_series(country_iso3, series, cfg)
    # §25: cycle safety propagates from the COMPLETE historical path.
    return replace(
        classified,
        backtest_safe=classified.backtest_safe and all_safe,
        execution_mode=spec.mode.value,
    )
