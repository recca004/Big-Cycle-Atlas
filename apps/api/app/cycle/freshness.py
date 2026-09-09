"""Freshness evaluation machinery — Sprint 5.6 (executable part of NORMALIZATION.md §5).

Threshold values come from the Sprint 5.5 typed design
(`FRESHNESS_THRESHOLDS` in normalization_definitions.py) — MODEL PARAMETERS,
versioned, initial model choices, NOT provider truth.

Decay SHAPE — SETTLED (DEC-013, 2026-09-09): exponential is the current
accepted methodology. It is parameterized here (`FreshnessDecayShape`);
exponential is the default and the only shape that honors the half-life
definition ("age at which freshness has decayed to ~0.5") for arbitrary
threshold values. The linear implementation remains available as an
alternative for tests and possible future model versions — it is NOT current
methodology. Changing the shape is a model-version change, never a silent
edit.

Pure module: no DB access, no raw-observation writes. Stale data makes a
signal UNUSABLE (not produced, never produced-with-zero) — MISSING != ZERO.
"""
from dataclasses import dataclass
from enum import Enum

from app.cycle.normalization_definitions import (
    FRESHNESS_THRESHOLDS,
    FreshnessClass,
    FreshnessThresholds,
    _assert_in_range,
)


class FreshnessDecayShape(str, Enum):
    """How the freshness factor decays between full confidence and unusable.

    exponential: factor = 0.5 ** ((age - full) / (half_life - full)) — passes
        through exactly 0.5 at half_life for any thresholds (initial default).
    linear: factor falls linearly from 1.0 at full confidence to 0.0 at the
        unusable threshold (half_life is then only approximate).
    """

    exponential = "exponential"
    linear = "linear"


@dataclass(frozen=True)
class FreshnessPolicy:
    """One policy per freshness class: thresholds + decay shape.

    Tests supply explicit policies; production uses DEFAULT_FRESHNESS_POLICIES
    (FRESHNESS_THRESHOLDS + the documented initial decay shape).
    """

    thresholds: FreshnessThresholds
    decay_shape: FreshnessDecayShape = FreshnessDecayShape.exponential

    def __post_init__(self) -> None:
        t = self.thresholds
        if t.full_confidence_periods < 0:
            raise ValueError("full_confidence_periods must be >= 0")
        if t.half_life_periods <= t.full_confidence_periods:
            raise ValueError(
                f"{t.freshness_class.value}: half_life_periods "
                f"({t.half_life_periods}) must exceed full_confidence_periods "
                f"({t.full_confidence_periods})"
            )
        if t.unusable_after_periods <= t.half_life_periods:
            raise ValueError(
                f"{t.freshness_class.value}: unusable_after_periods "
                f"({t.unusable_after_periods}) must exceed half_life_periods "
                f"({t.half_life_periods})"
            )


@dataclass(frozen=True)
class FreshnessResult:
    """Outcome of freshness evaluation for one aligned observation.

    age_periods: age in the series' OWN periods (years for annual/irregular,
        quarters for quarterly) — not the scoring-clock quarter count.
    factor: 0..1 freshness factor (an input to a future confidence score —
        NOT itself the confidence score).
    is_stale: age is beyond the full-confidence window (freshness decaying).
    is_usable: False means the signal is NOT produced for this snapshot —
        never produced-with-zero.
    """

    age_periods: float
    factor: float
    is_stale: bool
    is_usable: bool

    def __post_init__(self) -> None:
        _assert_in_range(self.factor, (0.0, 1.0), "freshness factor")


def own_period_age(age_in_quarters: int, freshness_class: FreshnessClass) -> float:
    """Convert a scoring-clock age (integer quarters between the observation's
    quarter and the scoring quarter) into the series' own period unit:

    quarterly -> quarters; annual and irregular -> years.
    """
    if freshness_class is FreshnessClass.quarterly:
        return float(age_in_quarters)
    return age_in_quarters / 4.0


def evaluate_freshness(age_in_own_periods: float, policy: FreshnessPolicy) -> FreshnessResult:
    """Evaluate freshness for one aligned observation.

    - age <= full_confidence_periods -> factor 1.0
    - age >= unusable_after_periods   -> is_usable False, factor 0.0
    - in between: decay per the policy's shape (see FreshnessDecayShape)
    """
    t = policy.thresholds
    if age_in_own_periods < 0:
        raise ValueError(f"age cannot be negative, got {age_in_own_periods}")

    is_stale = age_in_own_periods > t.full_confidence_periods
    if age_in_own_periods <= t.full_confidence_periods:
        return FreshnessResult(age_periods=age_in_own_periods, factor=1.0, is_stale=False, is_usable=True)
    if age_in_own_periods >= t.unusable_after_periods:
        return FreshnessResult(age_periods=age_in_own_periods, factor=0.0, is_stale=True, is_usable=False)

    if policy.decay_shape is FreshnessDecayShape.exponential:
        factor = 0.5 ** (
            (age_in_own_periods - t.full_confidence_periods)
            / (t.half_life_periods - t.full_confidence_periods)
        )
    else:
        factor = 1.0 - (
            (age_in_own_periods - t.full_confidence_periods)
            / (t.unusable_after_periods - t.full_confidence_periods)
        )
    return FreshnessResult(age_periods=age_in_own_periods, factor=factor, is_stale=True, is_usable=True)


DEFAULT_FRESHNESS_POLICIES: dict[FreshnessClass, FreshnessPolicy] = {
    freshness_class: FreshnessPolicy(thresholds=thresholds)
    for freshness_class, thresholds in FRESHNESS_THRESHOLDS.items()
}