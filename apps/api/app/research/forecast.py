"""Forecast research architecture (Mission 5 §10-§12).

Typed contracts for stage-transition forecasts over 1y/2y/5y/10y horizons
plus the explicit readiness evaluator that gates them. No numerical
production forecast is emitted unless every required gate passes — a
failed gate returns an unavailable forecast, never a fictional
probability or a default 50%.

All thresholds in ReadinessRequirements are declared MODEL ASSUMPTIONS,
not universal scientific rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

FORECAST_ARCHITECTURE_VERSION = "forecast-arch-v1"


class ForecastHorizon(str, Enum):
    one_year = "1y"
    two_years = "2y"
    five_years = "5y"
    ten_years = "10y"


HORIZON_QUARTERS: dict[ForecastHorizon, int] = {
    ForecastHorizon.one_year: 4,
    ForecastHorizon.two_years: 8,
    ForecastHorizon.five_years: 20,
    ForecastHorizon.ten_years: 40,
}


@dataclass(frozen=True)
class ReadinessRequirements:
    """Sample requirements — MODEL ASSUMPTIONS (versioned here), not
    universal scientific rules. Chosen so a binary transition target has
    a minimally meaningful positive class and out-of-sample split."""
    version: str = "readiness-req-v1"
    min_total_scored_periods: int = 100     # enough history to split at all
    min_independent_transitions: int = 30   # positive-label count
    min_strict_eligible_periods: int = 1    # strict path must be non-empty
    min_oos_periods: int = 40               # chronological holdout size
    max_autocorrelation_run: int = 8        # same-label runs tolerated


@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    value: float | int | str | None
    requirement: str
    note: str = ""


@dataclass(frozen=True)
class HorizonReadiness:
    horizon: ForecastHorizon
    horizon_quarters: int
    gates: tuple[GateResult, ...]
    available: bool
    unavailable_reason: str | None
    eligible_samples: int
    positive_transitions: int


@dataclass(frozen=True)
class TransitionRecord:
    """One genuine stage transition (never an initial assignment)."""
    country_iso3: str
    period: str
    from_stage: str
    to_stage: str
    model_id: str


@dataclass(frozen=True)
class ForecastReadinessReport:
    model_id: str
    model_version: str
    requirements_version: str
    horizon_results: tuple[HorizonReadiness, ...]
    overall_available: bool
    blockers: tuple[str, ...]
    total_scored_periods: int
    total_genuine_transitions: int
    strict_eligible_periods: int


def _period_index(period: str) -> int:
    """'2020-Q4' -> absolute quarter index."""
    year, q = period.split("-Q")
    return int(year) * 4 + int(q)


def transitions_within(
    transitions: list[TransitionRecord],
    origin_period: str,
    horizon: ForecastHorizon,
) -> int:
    """Count transitions inside (origin, origin+horizon] quarters."""
    lo = _period_index(origin_period)
    hi = lo + HORIZON_QUARTERS[horizon]
    return sum(
        1 for t in transitions
        if lo < _period_index(t.period) <= hi
    )


def evaluate_readiness(
    model_id: str,
    model_version: str,
    scored_periods: list[str],
    transitions: list[TransitionRecord],
    strict_eligible_periods: int,
    requirements: ReadinessRequirements = ReadinessRequirements(),
) -> ForecastReadinessReport:
    """Evaluate forecast readiness for one model over one dataset.

    Pure function — the caller supplies the transition dataset (e.g. from
    the retrospective diagnostics manifest). Each gate is reported
    individually; a failed gate produces a clear blocker string.
    """
    total_periods = len(scored_periods)
    total_transitions = len(transitions)
    post_2015 = sum(1 for t in transitions if t.period >= "2015")

    horizon_results: list[HorizonReadiness] = []
    for horizon in ForecastHorizon:
        hq = HORIZON_QUARTERS[horizon]
        # Eligible origins: scored periods with a full horizon of
        # forward history inside the sample (labels must be observable).
        eligible_origins = [
            p for p in scored_periods
            if _period_index(p) + hq <= _period_index(scored_periods[-1])
        ] if scored_periods else []
        positives = sum(
            1 for p in eligible_origins
            if transitions_within(transitions, p, horizon) > 0
        )
        gates = (
            GateResult(
                gate="sample_size",
                passed=total_periods >= requirements.min_total_scored_periods,
                value=total_periods,
                requirement=f">= {requirements.min_total_scored_periods}",
            ),
            GateResult(
                gate="eligible_origins",
                passed=len(eligible_origins) >= requirements.min_oos_periods,
                value=len(eligible_origins),
                requirement=(
                    f">= {requirements.min_oos_periods} origins with a "
                    f"fully observable {horizon.value} horizon"
                ),
            ),
            GateResult(
                gate="independent_transitions",
                passed=(
                    total_transitions
                    >= requirements.min_independent_transitions
                ),
                value=total_transitions,
                requirement=(
                    f">= {requirements.min_independent_transitions} "
                    "genuine transitions dataset-wide"
                ),
                note=f"{post_2015} of them post-2015",
            ),
            GateResult(
                gate="positive_labels",
                passed=positives >= requirements.min_independent_transitions,
                value=positives,
                requirement=(
                    f">= {requirements.min_independent_transitions} "
                    "positive labels at this horizon"
                ),
            ),
            GateResult(
                gate="strict_availability",
                passed=(
                    strict_eligible_periods
                    >= requirements.min_strict_eligible_periods
                ),
                value=strict_eligible_periods,
                requirement=(
                    f">= {requirements.min_strict_eligible_periods} "
                    "strict-eligible scored periods"
                ),
                note=(
                    "retrospective-only data cannot support a strict "
                    "backtest claim"
                ),
            ),
        )
        failed = [g for g in gates if not g.passed]
        horizon_results.append(HorizonReadiness(
            horizon=horizon,
            horizon_quarters=hq,
            gates=gates,
            available=not failed,
            unavailable_reason=(
                "; ".join(
                    f"{g.gate}: {g.value} (needs {g.requirement})"
                    for g in failed
                )
                if failed else None
            ),
            eligible_samples=len(eligible_origins),
            positive_transitions=positives,
        ))

    blockers = tuple(sorted({
        g.gate for hr in horizon_results for g in hr.gates if not g.passed
    }))
    return ForecastReadinessReport(
        model_id=model_id,
        model_version=model_version,
        requirements_version=requirements.version,
        horizon_results=tuple(horizon_results),
        overall_available=all(hr.available for hr in horizon_results),
        blockers=blockers,
        total_scored_periods=total_periods,
        total_genuine_transitions=total_transitions,
        strict_eligible_periods=strict_eligible_periods,
    )


# --- §12 benchmark candidates (research scaffolding, chronology-safe) ---------


def persistence_benchmark(
    stage_path: list[str | None],
) -> dict:
    """Persistence baseline: predict next stage == current stage.

    Chronology-safe by construction (each prediction uses only the
    immediately preceding observed stage). Reports raw accuracy — the
    number any learned model must beat.
    """
    pairs = [
        (a, b) for a, b in zip(stage_path, stage_path[1:])
        if a is not None and b is not None
    ]
    if not pairs:
        return {"samples": 0, "correct": 0, "accuracy": None}
    correct = sum(1 for a, b in pairs if a == b)
    return {
        "samples": len(pairs),
        "correct": correct,
        "accuracy": correct / len(pairs),
    }


def unconditional_frequency(
    transitions: list[TransitionRecord],
    total_periods: int,
    horizon: ForecastHorizon,
) -> dict:
    """Unconditional base rate: share of origins with >=1 transition
    inside the horizon — the trivial probability any calibrated model
    must beat to be useful."""
    origins = sorted({_period_index(t.period) for t in transitions})
    if total_periods <= 0 or not origins:
        return {"horizon": horizon.value, "base_rate": None}
    # origins are transition periods; approximate base rate from the
    # transition density over the whole sample.
    rate = len(transitions) / total_periods
    return {
        "horizon": horizon.value,
        "base_rate": rate,
        "note": "unconditional frequency — the floor a calibrated model must beat",
    }
