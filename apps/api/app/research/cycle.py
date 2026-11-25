"""Experimental cycle engine — Mission 2 §13-§14.

Consumes a national-conditions series (composite scores per scoring period)
and produces EXPERIMENTAL phase/stage classifications with hysteresis,
minimum duration, and explicit missing-data handling. All thresholds are
model assumptions, never validated constants.

Three public phases: RISE / PEAK / DECLINE.
Eight internal stages: EARLY_RISE, RISE, LATE_RISE, PEAK, LATE_PEAK,
EARLY_DECLINE, DECLINE, RESET.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

CYCLE_ENGINE_VERSION = "cycle-engine-v0.1"


class PublicPhase(str, Enum):
    rise = "RISE"
    peak = "PEAK"
    decline = "DECLINE"


class Stage(str, Enum):
    early_rise = "EARLY_RISE"
    rise = "RISE"
    late_rise = "LATE_RISE"
    peak = "PEAK"
    late_peak = "LATE_PEAK"
    early_decline = "EARLY_DECLINE"
    decline = "DECLINE"
    reset = "RESET"


STAGE_PHASE: dict[Stage, PublicPhase] = {
    Stage.early_rise: PublicPhase.rise,
    Stage.rise: PublicPhase.rise,
    Stage.late_rise: PublicPhase.rise,
    Stage.peak: PublicPhase.peak,
    Stage.late_peak: PublicPhase.peak,
    Stage.early_decline: PublicPhase.decline,
    Stage.decline: PublicPhase.decline,
    Stage.reset: PublicPhase.decline,
}


@dataclass(frozen=True)
class CycleModelConfig:
    """Explicit assumptions — every threshold is declared."""
    model_id: str = "cycle_classifier_v1"
    version: str = "v1"
    # Momentum thresholds (score-point change over `momentum_window` periods)
    rise_threshold: float = 1.0        # momentum above -> rising
    decline_threshold: float = -1.0    # momentum below -> declining
    momentum_window_periods: int = 4   # quarters for the trend check
    # Level bands for peak detection (on the composite score)
    peak_low: float = 60.0             # score >= peak_low while flat = peak
    reset_high: float = 35.0           # score < reset_high while falling = reset
    # Transition rules
    min_stage_periods: int = 2         # hysteresis: min periods in a stage
    persist_periods: int = 2           # candidate stage must persist N periods
    min_observations: int = 12         # min scored periods to classify at all
    min_coverage_ratio: float = 0.5    # fraction of periods with scores


@dataclass(frozen=True)
class ClassifiedPoint:
    period: str
    score: float | None
    momentum: float | None
    stage: Stage | None
    phase: PublicPhase | None
    reason: str


@dataclass(frozen=True)
class CycleResult:
    model_id: str
    model_version: str
    methodology_status: str            # always "experimental"
    country_iso3: str
    points: tuple[ClassifiedPoint, ...]
    transitions: tuple[dict, ...]
    coverage_ratio: float
    warnings: tuple[str, ...] = ()
    backtest_safe: bool = False
    # Which information-selection mode produced the inputs (§23).
    execution_mode: str = "retrospective_latest_vintage"


def _raw_stage(score: float, momentum: float, cfg: CycleModelConfig) -> Stage:
    """Map (level, momentum) -> candidate stage (pre-hysteresis)."""
    rising = momentum >= cfg.rise_threshold
    falling = momentum <= cfg.decline_threshold
    if falling and score < cfg.reset_high:
        return Stage.reset
    if falling:
        return Stage.early_decline if score >= cfg.peak_low else Stage.decline
    if rising:
        if score >= cfg.peak_low:
            return Stage.late_rise
        return Stage.rise if score >= 45.0 else Stage.early_rise
    # flat-ish momentum
    if score >= cfg.peak_low:
        return Stage.peak
    if score < cfg.reset_high:
        return Stage.decline
    # mid-range flat: continue prior direction — resolved by caller via
    # carry-forward; marker: pick late_peak if momentum negative, rise else.
    return Stage.late_peak if momentum < 0 else Stage.rise


def classify_series(
    country_iso3: str,
    series: list[tuple[str, float | None]],
    cfg: CycleModelConfig = CycleModelConfig(),
) -> CycleResult:
    """Classify one country's (period, score) series.

    Missing scores never produce a stage; a missing run interrupts
    persistence counting. A country below min coverage/min observations is
    returned unclassified with the reason, never guessed.
    """
    total = len(series)
    scored = [(p, s) for p, s in series if s is not None]
    coverage = len(scored) / total if total else 0.0
    if len(scored) < cfg.min_observations or coverage < cfg.min_coverage_ratio:
        return CycleResult(
            model_id=cfg.model_id, model_version=cfg.version,
            methodology_status="experimental",
            country_iso3=country_iso3,
            points=tuple(
                ClassifiedPoint(p, s, None, None, None,
                                "insufficient coverage/observations")
                for p, s in series
            ),
            transitions=(),
            coverage_ratio=coverage,
            warnings=(
                f"unclassified: {len(scored)} scored of {total} periods "
                f"(min {cfg.min_observations}, coverage "
                f"{cfg.min_coverage_ratio:.0%})",
            ),
        )

    # Compute momentum over window (score-point change across N quarters).
    values = [s for _, s in series]
    points: list[ClassifiedPoint] = []
    current_stage: Stage | None = None
    stage_run = 0
    candidate: Stage | None = None
    candidate_run = 0
    transitions: list[dict] = []

    last_scored_idx = -1
    for i, (period, score) in enumerate(series):
        if score is None:
            points.append(ClassifiedPoint(period, None, None, None, None,
                                          "missing score"))
            candidate_run = 0
            candidate = None
            continue
        j = len([k for k in range(i + 1) if series[k][1] is not None]) - 1
        # momentum vs N-scored-observations ago
        scored_so_far = [s for _, s in series[: i + 1] if s is not None]
        base_idx = max(0, len(scored_so_far) - 1 - cfg.momentum_window_periods)
        momentum = (
            score - scored_so_far[base_idx]
            if len(scored_so_far) - 1 >= cfg.momentum_window_periods
            else 0.0
        )
        raw = _raw_stage(score, momentum, cfg)

        if current_stage is None:
            current_stage = raw
            stage_run = 1
            transitions.append({"period": period, "to": raw.value,
                                "reason": "initial"})
        elif raw == current_stage:
            stage_run += 1
            candidate = None
            candidate_run = 0
        else:
            # hysteresis: a different raw stage must persist persist_periods
            # before transitioning; min_stage_periods gates early flips.
            if raw == candidate:
                candidate_run += 1
            else:
                candidate = raw
                candidate_run = 1
            if (
                candidate_run >= cfg.persist_periods
                and stage_run >= cfg.min_stage_periods
            ):
                transitions.append({
                    "period": period,
                    "from": current_stage.value,
                    "to": candidate.value,
                    "reason": f"persisted {candidate_run} periods",
                })
                current_stage = candidate
                stage_run = 1
                candidate = None
                candidate_run = 0
            else:
                stage_run += 1  # remain; candidate accumulating

        points.append(ClassifiedPoint(
            period, score, round(momentum, 4),
            current_stage, STAGE_PHASE[current_stage],
            f"stage={current_stage.value} run={stage_run}"
            + (f" candidate={candidate.value}x{candidate_run}"
               if candidate else ""),
        ))
        last_scored_idx = i

    return CycleResult(
        model_id=cfg.model_id, model_version=cfg.version,
        methodology_status="experimental",
        country_iso3=country_iso3,
        points=tuple(points),
        transitions=tuple(transitions),
        coverage_ratio=coverage,
        warnings=(
            "EXPERIMENTAL classifier — thresholds are model assumptions, "
            "not validated constants; hysteresis suppresses single-period "
            "flips by design",
        ),
    )
