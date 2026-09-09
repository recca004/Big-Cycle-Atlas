"""Normalization architecture skeleton — Sprint 5.5 (design, not scores).

Companion to .dev/NORMALIZATION.md (the methodology source of truth). This
module is a typed CONFIGURATION layer: it defines score semantics, the
normalization family registry for every live indicator, and the structures a
future scoring sprint will fill. It deliberately contains:

- NO normalizer computation beyond trivial range validation helpers
- NO force scores, weights, momentum values, or confidence numbers
- NO API connection

Score fields (level_score / relative_score / momentum / confidence) are
Optional and None by default until the scoring sprint publishes a validated
methodology. Raw observations are never touched by this layer.

Historical caution: without reliable release-date discipline (Milestone 9),
any normalization of historical data is CURRENT/RESEARCH scoring, never
point-in-time/backtest scoring — hence backtest_safe defaults to False.
"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from app.cycle.force_definitions import (
    FORCE_DEFINITIONS,
    ForceCoverageStatus,
)
from app.models.indicator import IndicatorStrengthDirection

# --- Score semantics (Section 1 of NORMALIZATION.md) ------------------------

class NormalizationNotImplementedError(Exception):
    """The indicator's family has no implemented normalizer yet.

    Raised instead of silently falling back to a generic transform —
    unimplemented families must stay visibly unimplemented. (Canonical home
    since Sprint 5.8 so the relative engine and the normalizer share ONE
    exception type; app.cycle.normalizer re-exports it.)
    """


class NormalizationDataError(Exception):
    """A provider value violates the range its normalization family assumes.

    Raised instead of clamping: provider/schema anomalies stay visible
    (e.g. a DIRECT_0_100 observation of -1 or 101). (Canonical home since
    Sprint 5.8; app.cycle.normalizer re-exports it.)
    """


LEVEL_SCORE_RANGE = (0.0, 100.0)
RELATIVE_SCORE_RANGE = (0.0, 100.0)
MOMENTUM_RANGE = (-100.0, 100.0)
CONFIDENCE_RANGE = (0.0, 1.0)


def _assert_in_range(value: float, allowed: tuple[float, float], name: str) -> None:
    low, high = allowed
    if not low <= value <= high:
        raise ValueError(f"{name} must be in [{low}, {high}], got {value}")


def validate_level_score(value: float) -> None:
    _assert_in_range(value, LEVEL_SCORE_RANGE, "level_score")


def validate_relative_score(value: float) -> None:
    _assert_in_range(value, RELATIVE_SCORE_RANGE, "relative_score")


def validate_momentum(value: float) -> None:
    _assert_in_range(value, MOMENTUM_RANGE, "momentum")


def validate_confidence(value: float) -> None:
    _assert_in_range(value, CONFIDENCE_RANGE, "confidence")


# --- Quarterly scoring clock (Section 2) -------------------------------------


@dataclass(frozen=True)
class ScoringPeriod:
    """A quarterly scoring snapshot, e.g. ScoringPeriod(2025, 4) = 2025-Q4.

    Lives only in the derived layer — raw observation dates are never altered.
    """

    year: int
    quarter: int

    def __post_init__(self) -> None:
        if not 1 <= self.quarter <= 4:
            raise ValueError(f"quarter must be 1-4, got {self.quarter}")
        if self.year < 1900 or self.year > 2200:
            raise ValueError(f"implausible year: {self.year}")

    @property
    def label(self) -> str:
        return f"{self.year}-Q{self.quarter}"


# --- Freshness policy (Section 5) --------------------------------------------


class FreshnessClass(str, Enum):
    quarterly = "quarterly"
    annual = "annual"
    irregular = "irregular"


@dataclass(frozen=True)
class FreshnessThresholds:
    """MODEL PARAMETERS — initial model choices, versioned; NOT provider truth.

    full_confidence_periods: age (in the series' own periods) within which
        freshness_confidence is ~1.
    half_life_periods: age at which freshness_confidence has decayed to ~0.5.
    unusable_after_periods: age beyond which the indicator is unavailable for
        that snapshot (the signal is not produced — never produced-with-zero).
    """

    freshness_class: FreshnessClass
    full_confidence_periods: int
    half_life_periods: int
    unusable_after_periods: int


FRESHNESS_THRESHOLDS: dict[FreshnessClass, FreshnessThresholds] = {
    FreshnessClass.quarterly: FreshnessThresholds(
        freshness_class=FreshnessClass.quarterly,
        full_confidence_periods=2,
        half_life_periods=8,
        unusable_after_periods=12,
    ),
    FreshnessClass.annual: FreshnessThresholds(
        freshness_class=FreshnessClass.annual,
        full_confidence_periods=1,
        half_life_periods=3,
        unusable_after_periods=5,
    ),
    FreshnessClass.irregular: FreshnessThresholds(
        freshness_class=FreshnessClass.irregular,
        full_confidence_periods=2,
        half_life_periods=4,
        unusable_after_periods=8,
    ),
}


# --- Normalization families (Section 6) ---------------------------------------


class NormalizationFamily(str, Enum):
    direct_0_100 = "direct_0_100"
    monotonic_positive = "monotonic_positive"
    monotonic_negative = "monotonic_negative"
    monotonic_saturating = "monotonic_saturating"
    target_band = "target_band"
    # Added by Sprint 5.11 (DEC-020): a ONE-SIDED vulnerability mapping — no
    # stress is signaled at or below a neutral ceiling, and stress rises
    # monotonically ABOVE it. Unlike target_band, the below-ceiling region
    # carries NO penalty: for the one indicator currently in this family
    # (CREDIT_TO_GDP_GAP), authoritative evidence supports positive-side
    # excess-credit thresholds but NO negative-side penalty threshold.
    one_sided_vulnerability = "one_sided_vulnerability"
    own_history = "own_history"
    cross_sectional_relative = "cross_sectional_relative"
    relative_share = "relative_share"
    contextual_deferred = "contextual_deferred"


@dataclass(frozen=True)
class NormalizationSpec:
    """Typed normalization classification for one live indicator.

    One family per dimension (level / relative / momentum) — the four score
    dimensions stay separable. None = that dimension is not (yet) defensible
    for this indicator. contextual_deferred is an explicit, valid entry: the
    curve is deliberately unresolved (never invented to fill the registry).

    Ceilings (DEC-009) act at the FORCE layer only — specs never clamp or
    modify indicator values.
    """

    indicator_code: str
    direction: IndicatorStrengthDirection
    level_family: NormalizationFamily
    relative_family: Optional[NormalizationFamily]
    momentum_family: Optional[NormalizationFamily]
    freshness_class: FreshnessClass
    absolute_comparable: bool = False
    relative_comparable: bool = False
    backtest_safe: bool = False
    momentum_windows: tuple[int, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        # A momentum family without windows, or windows without a family, is a
        # configuration mistake — fail loudly.
        if (self.momentum_family is None) != (len(self.momentum_windows) == 0):
            raise ValueError(
                f"{self.indicator_code}: momentum_family and momentum_windows "
                "must be set together"
            )


# --- As-of alignment (Section 3) ----------------------------------------------


@dataclass(frozen=True)
class AlignedValue:
    """Latest known usable observation aligned to a scoring period.

    Typed structure only in Sprint 5.5 — NOT persisted. Provenance (source
    period, age, vintage) always travels with the value; no forward-fill, no
    interpolation.

    effective_period_end (Part 0, DEC-015): the derived last day of the raw
    observation's OWN economic period (annual/irregular -> YYYY-12-31,
    quarterly -> quarter end). Eligibility at a snapshot requires this date
    to be at or before the snapshot's quarter end — computed in the derived
    layer only, never persisted, raw observations never modified.
    """

    indicator_code: str
    country_iso3: str
    scoring_period: ScoringPeriod
    source_period: str
    raw_value: float
    age_periods: int
    effective_period_end: date
    freshness_factor: Optional[float] = None  # 0..1, computed by the scoring sprint
    is_stale: bool = False
    vintage_number: int = 1

    def __post_init__(self) -> None:
        if self.freshness_factor is not None:
            _assert_in_range(self.freshness_factor, (0.0, 1.0), "freshness_factor")


# --- Momentum (Section 9; Sprint 5.7: WGI OWN_HISTORY only) ---------------------


@dataclass(frozen=True)
class MomentumWindowResult:
    """Per-window momentum provenance and change (DEC-016).

    Sprint 5.7: WGI x3 only — the change is the SIGNED difference in the
    provider's own 0-100 points (current aligned raw - anchor aligned raw).
    It is WGI-scale-specific and NOT approved for direct cross-indicator
    aggregation (separate calibration methodology required first).

    change is None when the anchor cannot be aligned, the aligned anchor is
    older than the versioned tolerance, or the window is otherwise unusable —
    missing history is NEVER zero and never silently substituted.
    """

    window_years: int
    requested_anchor_period: str  # scoring-clock label, e.g. "2020-Q2"
    anchor_source_period: Optional[str] = None  # actual aligned source, e.g. "2019"
    change: Optional[float] = None

    def __post_init__(self) -> None:
        if self.window_years <= 0:
            raise ValueError(f"window_years must be positive, got {self.window_years}")
        if self.change is not None:
            validate_momentum(self.change)


# --- Own-history level (Sprint 5.10: DSR only, DEC-019) -------------------------


@dataclass(frozen=True)
class OwnHistoryLevelResult:
    """Own-history level provenance and score (DEC-019, Sprint 5.10).

    The level signal answers: where does the country's current value sit
    relative to ITS OWN expanding historical distribution available as of the
    snapshot? For DEBT_SERVICE_RATIO (the only enabled indicator): higher DSR
    = greater debt-service burden, so level_score = 100 - stress_percentile
    where stress_percentile is the empirical mid-rank plotting position of the
    current value within the country's own calibration sample (current
    observation INCLUDED).

    level_score/rank/stress_percentile are None when the expanding sample is
    smaller than the versioned minimum (sample_n < minimum_sample_n) —
    insufficient history is NEVER a zero and never a stretched sample.
    earliest/latest_source_period describe the actual calibration span (one
    real observation per source period — never forward-filled, interpolated,
    or duplicated across derived quarters).
    """

    sample_n: int
    minimum_sample_n: int
    earliest_source_period: Optional[str] = None
    latest_source_period: Optional[str] = None
    rank: Optional[float] = None  # average (mid) rank, 1 = lowest value / least stress
    stress_percentile: Optional[float] = None  # 100 * (average_rank - 0.5) / n
    level_score: Optional[float] = None  # 100 - stress_percentile

    def __post_init__(self) -> None:
        if self.sample_n < 0:
            raise ValueError(f"sample_n must be >= 0, got {self.sample_n}")
        if self.minimum_sample_n <= 0:
            raise ValueError(
                f"minimum_sample_n must be positive, got {self.minimum_sample_n}"
            )
        if self.stress_percentile is not None:
            _assert_in_range(self.stress_percentile, (0.0, 100.0), "stress_percentile")
        if self.level_score is not None:
            validate_level_score(self.level_score)
        # The three scored fields travel together: insufficient history leaves
        # ALL of them None (provenance counts still travel).
        if self.level_score is not None and (
            self.rank is None or self.stress_percentile is None
        ):
            raise ValueError("level_score requires rank + stress_percentile provenance")
        if self.level_score is None and (
            self.rank is not None or self.stress_percentile is not None
        ):
            raise ValueError("rank/stress_percentile require a level_score")


@dataclass(frozen=True)
class OwnHistoryLevelConfig:
    """Versioned MODEL PARAMETERS for one indicator's OWN_HISTORY level.

    Sprint 5.10 enables exactly one: DEBT_SERVICE_RATIO. A registry
    OWN_HISTORY level_family alone does NOT make an indicator executable — an
    explicit config entry in the model version is required (no generic
    auto-enable, no fallback).
    """

    minimum_sample_n: int  # Atlas MODEL PARAMETER, NOT provider truth

    def __post_init__(self) -> None:
        if self.minimum_sample_n <= 0:
            raise ValueError(
                f"minimum_sample_n must be positive, got {self.minimum_sample_n}"
            )


# --- One-sided vulnerability level (Sprint 5.12: credit gap only, DEC-021) -------


@dataclass(frozen=True)
class OneSidedVulnerabilityConfig:
    """Versioned MODEL PARAMETERS for one indicator's ONE_SIDED_VULNERABILITY
    level (DEC-021, Sprint 5.12).

    The curve signals EXCESS-credit vulnerability on the positive side only:
    no stress is scored at or below `neutral_ceiling` (the flat no-excess
    region carries the `no_excess_score` — deliberately neutral, NOT a health
    claim), and stress rises LINEARLY from the ceiling to
    `saturation_value`, where the score reaches `saturated_score` and stays
    there (endpoint clamps, DEC-020 owner approval).

    Sprint 5.12 enables exactly one indicator: CREDIT_TO_GDP_GAP, with the
    owner-approved curve (neutral ceiling +2pp, saturation +10pp, no-excess
    region = 50, saturation = 0). These are ATLAS MODEL PARAMETERS — the
    breakpoints COINCIDE with the Basel CCyB guide's L/H reference points
    (bcbs187), but the score mapping (especially the 50 no-excess score) is
    an Atlas choice, not provider or Basel methodology truth.
    """

    neutral_ceiling: float
    saturation_value: float
    no_excess_score: float
    saturated_score: float

    def __post_init__(self) -> None:
        if self.saturation_value <= self.neutral_ceiling:
            raise ValueError(
                f"saturation_value ({self.saturation_value}) must exceed "
                f"neutral_ceiling ({self.neutral_ceiling})"
            )
        validate_level_score(self.no_excess_score)
        validate_level_score(self.saturated_score)
        # Stress must rise (score fall) monotonically above the ceiling.
        if self.saturated_score > self.no_excess_score:
            raise ValueError(
                f"saturated_score ({self.saturated_score}) must be <= "
                f"no_excess_score ({self.no_excess_score})"
            )


@dataclass(frozen=True)
class OneSidedVulnerabilityResult:
    """Provenance for a ONE_SIDED_VULNERABILITY level (DEC-021, Sprint 5.12).

    Carries the exact curve parameters applied, so a signal is reproducible
    from its model version alone. level_score is None only when the signal
    was not produced at all (no eligible observation / too stale) — the
    curve itself always yields a score for any real value.
    """

    neutral_ceiling: float
    saturation_value: float
    no_excess_score: float
    saturated_score: float
    level_score: float

    def __post_init__(self) -> None:
        validate_level_score(self.level_score)
        # The applied curve must be a valid configuration.
        OneSidedVulnerabilityConfig(
            neutral_ceiling=self.neutral_ceiling,
            saturation_value=self.saturation_value,
            no_excess_score=self.no_excess_score,
            saturated_score=self.saturated_score,
        )


# --- Normalized signal (Sections 1 + 4) ----------------------------------------


@dataclass(frozen=True)
class NormalizedSignal:
    """Per-indicator derived signal. Published (Sprint 5.7): level_score for
    DIRECT_0_100 (WGI x3) and momentum for the WGI x3 OWN_HISTORY primary
    window. Published (Sprint 5.8, DEC-017): relative_score for the WGI x3 —
    the country's relative position within the tracked_8 comparison universe
    (mid-rank plotting position; NEVER a global/world percentile).
    Published (Sprint 5.10, DEC-019): level_score for DEBT_SERVICE_RATIO
    (OWN_HISTORY). Published (Sprint 5.12, DEC-021): level_score for
    CREDIT_TO_GDP_GAP (ONE_SIDED_VULNERABILITY — owner-approved curve). Still
    None everywhere: confidence — and momentum for every non-WGI indicator,
    relative_score for every non-WGI indicator. No force aggregation exists
    at this layer.
    """

    indicator_code: str
    country_iso3: str
    as_of_period: ScoringPeriod
    raw_value: float
    source_period: str
    method: NormalizationFamily
    model_version: str
    level_score: Optional[float] = None
    relative_score: Optional[float] = None
    momentum: Optional[float] = None
    confidence: Optional[float] = None
    reference_universe_id: Optional[str] = None
    backtest_safe: bool = False
    # Relative provenance (Sprint 5.8, DEC-017 — WGI x3 only): the universe id
    # and its expected/usable member counts travel even when the universe is
    # INCOMPLETE (usable_n < expected_n -> relative_score/relative_rank are
    # None — a 7/8 cross-section is never silently scored as tracked_8).
    # Missing members never become zero.
    reference_universe_expected_n: Optional[int] = None
    reference_universe_usable_n: Optional[int] = None
    relative_rank: Optional[float] = None
    # Freshness provenance from as-of alignment (Sprint 5.6) — an input to a
    # future confidence score, never the confidence score itself.
    freshness_factor: Optional[float] = None
    is_stale: bool = False
    # Momentum provenance (Sprint 5.7, DEC-016 — WGI x3 only): the headline
    # momentum is the PRIMARY window's change and nothing else (no averaging,
    # no silent fallback to another window). momentum_window_years names the
    # window behind the headline value (None when the primary is
    # unavailable); momentum_windows keeps BOTH windows' provenance.
    momentum_window_years: Optional[int] = None
    momentum_windows: tuple[MomentumWindowResult, ...] = ()
    # Own-history level provenance (Sprint 5.10, DEC-019 — DSR only): the
    # expanding own-history calibration counts/span + rank/stress/score. None
    # for every indicator without an own-history level config (WGI carries
    # momentum_windows instead; the dimensions stay separable).
    own_history_level: Optional[OwnHistoryLevelResult] = None
    # One-sided vulnerability provenance (Sprint 5.12, DEC-021 — credit gap
    # only): the exact curve parameters + the resulting level_score. None for
    # every indicator without a one-sided vulnerability level config.
    one_sided_vulnerability_level: Optional[OneSidedVulnerabilityResult] = None

    @classmethod
    def unscored(
        cls,
        *,
        indicator_code: str,
        country_iso3: str,
        as_of_period: ScoringPeriod,
        raw_value: float,
        source_period: str,
        method: NormalizationFamily,
        model_version: str,
    ) -> "NormalizedSignal":
        """A signal with data present but no derived scores.

        Represents the MISSING != ZERO rule in the type system: absent scores
        are None, never 0 — an unscored signal is never a zero score.
        """
        return cls(
            indicator_code=indicator_code,
            country_iso3=country_iso3,
            as_of_period=as_of_period,
            raw_value=raw_value,
            source_period=source_period,
            method=method,
            model_version=model_version,
        )

    def __post_init__(self) -> None:
        if self.level_score is not None:
            validate_level_score(self.level_score)
        if self.relative_score is not None:
            validate_relative_score(self.relative_score)
        if self.momentum is not None:
            validate_momentum(self.momentum)
        if self.confidence is not None:
            validate_confidence(self.confidence)
        if self.freshness_factor is not None:
            _assert_in_range(self.freshness_factor, (0.0, 1.0), "freshness_factor")
        if self.reference_universe_expected_n is not None and self.reference_universe_expected_n <= 0:
            raise ValueError(
                f"reference_universe_expected_n must be positive, got "
                f"{self.reference_universe_expected_n}"
            )
        if (
            self.reference_universe_usable_n is not None
            and self.reference_universe_expected_n is not None
            and not 0 <= self.reference_universe_usable_n <= self.reference_universe_expected_n
        ):
            raise ValueError(
                f"reference_universe_usable_n must be within "
                f"[0, {self.reference_universe_expected_n}], got "
                f"{self.reference_universe_usable_n}"
            )
        if self.relative_rank is not None and self.relative_score is None:
            raise ValueError("relative_rank requires relative_score")
        if (
            self.relative_score is not None
            and self.reference_universe_id is None
        ):
            raise ValueError("relative_score requires reference_universe_id provenance")


# --- Reference universe + model versioning (Sections 13-15) -------------------


@dataclass(frozen=True)
class ReferenceUniverseSpec:
    """A VERSIONED MODEL comparison universe (DEC-017, Sprint 5.8).

    Membership is FROZEN per universe id — it is never derived from the DB
    (not from the Country table, not from who currently has data). Adding a
    country to the platform does NOT silently change a universe: a changed
    universe gets a NEW id and a new model version, never an in-place edit.
    tracked_8's membership is cross-checked against the canonical
    packages/shared country list in tests, but the model keeps its own frozen
    definition so historical results stay reproducible.
    """

    id: str
    members: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("universe id must be non-empty")
        if not self.members:
            raise ValueError(f"universe {self.id!r} has no members")
        if len(set(self.members)) != len(self.members):
            raise ValueError(f"universe {self.id!r} has duplicate members")


TRACKED_8_MEMBERS: tuple[str, ...] = (
    "USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND",
)

TRACKED_8_UNIVERSE = ReferenceUniverseSpec(
    id="tracked_8",
    members=TRACKED_8_MEMBERS,
)

REFERENCE_UNIVERSES: dict[str, ReferenceUniverseSpec] = {
    # n=8 is enough for UI comparisons but a weak statistical reference
    # distribution — CROSS_SECTIONAL_RELATIVE results are positions within
    # tracked_8, NEVER a global/world percentile. expanded_global arrives
    # with a future universe change (a new model version, not an in-place
    # recalibration).
    TRACKED_8_UNIVERSE.id: TRACKED_8_UNIVERSE,
}


@dataclass(frozen=True)
class ModelVersionConfig:
    """Bundles everything a derived result needs to be reproducible.

    Configuration-first: no model_versions DB table exists yet (planned in
    docs/data-model.md). Calibration windows never see future data
    (NORMALIZATION.md Section 15).
    """

    version_id: str
    normalization_method: str
    force_mapping_version: str
    reference_universe_id: str
    calibration_window_end: Optional[date] = None
    calibration_window_start: Optional[date] = None
    momentum_windows: dict[str, tuple[int, ...]] = field(default_factory=dict)
    # Sprint 5.7 (DEC-016) — both are MODEL PARAMETERS, versioned:
    # the headline momentum comes from ONE primary window (no averaging, no
    # fallback), and an aligned anchor may be at most N own periods older
    # than the requested anchor period's year (WGI annual: 1 = the known
    # 1997/1999/2001 biennial gaps resolve to the prior year).
    momentum_primary_window_years: dict[str, int] = field(default_factory=dict)
    momentum_anchor_tolerance_periods: dict[str, int] = field(default_factory=dict)
    # Sprint 5.10 (DEC-019) — MODEL PARAMETERS: OWN_HISTORY level is enabled
    # per indicator by an explicit entry here; a registry OWN_HISTORY
    # level_family alone never auto-enables it. Currently exactly one entry:
    # DEBT_SERVICE_RATIO (empirical mid-rank own-history stress position,
    # expanding as-of calibration, current observation included, higher DSR =
    # more stress, level = 100 - stress percentile).
    own_history_level_configs: dict[str, OwnHistoryLevelConfig] = field(
        default_factory=dict
    )
    # Sprint 5.12 (DEC-021) — MODEL PARAMETERS: ONE_SIDED_VULNERABILITY level
    # is enabled per indicator by an explicit entry here; a registry
    # ONE_SIDED_VULNERABILITY level_family alone never auto-enables it.
    # Currently exactly one entry: CREDIT_TO_GDP_GAP (owner-approved curve —
    # flat 50 at/below +2pp, linear to 0 at +10pp, clamped 0 above).
    one_sided_vulnerability_configs: dict[str, OneSidedVulnerabilityConfig] = field(
        default_factory=dict
    )
    backtest_safe: bool = False  # False until Milestone 9 (release-date discipline)

    def __post_init__(self) -> None:
        if self.reference_universe_id not in REFERENCE_UNIVERSES:
            raise ValueError(
                f"unknown reference universe: {self.reference_universe_id}"
            )
        if (
            self.calibration_window_start is not None
            and self.calibration_window_end is not None
            and self.calibration_window_start > self.calibration_window_end
        ):
            raise ValueError("calibration window start is after its end")
        # Momentum config must be internally consistent: primary window must
        # be one of the declared windows, and every primary/tolerance entry
        # needs windows.
        for indicator, primary in self.momentum_primary_window_years.items():
            if indicator not in self.momentum_windows:
                raise ValueError(
                    f"{indicator}: primary window declared without windows"
                )
            if primary not in self.momentum_windows[indicator]:
                raise ValueError(
                    f"{indicator}: primary window {primary} is not one of "
                    f"{self.momentum_windows[indicator]}"
                )
        for indicator in self.momentum_anchor_tolerance_periods:
            if indicator not in self.momentum_windows:
                raise ValueError(
                    f"{indicator}: anchor tolerance declared without windows"
                )


CURRENT_MODEL_VERSION = ModelVersionConfig(
    # v0.1: Sprint 5.6 first executable path (alignment + freshness +
    # DIRECT_0_100 for the WGI x3). v0.2: Part 0 (DEC-015) period-complete
    # alignment eligibility. v0.3: Sprint 5.7 (DEC-016) WGI OWN_HISTORY
    # momentum — signed raw provider-point change, 3y/5y windows, primary =
    # 5y, anchor tolerance = 1 annual period, higher WGI = positive.
    # v0.4: Sprint 5.8 (DEC-017) WGI x3 CROSS_SECTIONAL_RELATIVE on the
    # frozen tracked_8 universe — mid-rank plotting position
    # 100 * (average_rank - 0.5) / n, ties = average rank, higher WGI =
    # stronger, ALL 8 members usable or no relative score (usable/expected
    # counts carried as provenance), same as-of snapshot + DEC-015 alignment
    # per member, freshness gates usability but NEVER scales the score.
    # NOT a global/world percentile. The v0.3 exponential freshness policy
    # (DEC-013) applies to the CURRENT observation only; historical anchors
    # are intentionally NOT freshness-decayed.
    # v0.5: Sprint 5.10 (DEC-019) DSR OWN_HISTORY LEVEL — the first non-WGI
    # level signal, enabled for EXACTLY DEBT_SERVICE_RATIO via the explicit
    # own_history_level_configs entry (registry OWN_HISTORY alone never
    # auto-enables). Method: empirical mid-rank own-history — expanding
    # as-of calibration over REAL observations only (one latest-vintage value
    # per actual source period, DEC-015 period-complete, no future data, no
    # forward-fill), current observation INCLUDED, ties = average rank,
    # stress_percentile = 100 * (average_rank - 0.5) / n with higher DSR =
    # greater burden, level_score = 100 - stress_percentile (finite-sample
    # endpoints NOT forced to 100/0), minimum sample = 20 observations (an
    # Atlas MODEL PARAMETER, not BIS methodology truth — insufficient history
    # = None, never zero), freshness gates the CURRENT value only and NEVER
    # scales the score; historical calibration points are not decayed. DSR
    # relative = None (cross-country DSR ranking prohibited), DSR momentum
    # NOT implemented (registry 4q/8q windows stay unapproved), confidence
    # None. All v0.4 WGI configuration unchanged. Research/current scoring
    # only — NOT production validated, NOT backtest safe.
    # v0.6: Sprint 5.12 (DEC-021) CREDIT_TO_GDP_GAP ONE_SIDED_VULNERABILITY
    # LEVEL — the second non-WGI level signal, enabled for EXACTLY
    # CREDIT_TO_GDP_GAP via an explicit one_sided_vulnerability_configs entry
    # (registry family alone never auto-enables). OWNER-APPROVED curve
    # (DEC-021): level_score = 50 for a gap at or below +2pp (the no-excess
    # region is deliberately NEUTRAL 50, not 100 — absence of excess credit is
    # not evidence of strength), then LINEAR from (+2, 50) to (+10, 0), and 0
    # at or above +10pp (endpoint clamps: no floor below +2, no cap above
    # +10). The +2/+10 breakpoints COINCIDE with the Basel CCyB guide's L/H
    # reference points (bcbs187); the 50/0 score mapping is an Atlas MODEL
    # PARAMETER, not Basel methodology truth — the gap remains a common
    # reference point, NOT a mechanical standalone rule (DEC-020 caveats
    # carried). No minimum-history gate: the curve is parametric, unlike the
    # DSR own-history calibration. Freshness gates the CURRENT observation
    # only and NEVER scales the score. Credit-gap relative stays
    # CONTEXTUAL_DEFERRED (None) and registry momentum windows (4q/8q) stay
    # UNAPPROVED (momentum None). All v0.5 WGI + DSR configuration unchanged.
    version_id="normalization-v0.6",
    normalization_method="sprint-5.12-credit-gap-one-sided-level-r1",
    force_mapping_version="m5.4",
    reference_universe_id="tracked_8",
    momentum_windows={
        "RULE_OF_LAW_WGI_SCORE": (3, 5),
        "CONTROL_OF_CORRUPTION_WGI_SCORE": (3, 5),
        "POLITICAL_STABILITY_WGI_SCORE": (3, 5),
    },
    momentum_primary_window_years={
        "RULE_OF_LAW_WGI_SCORE": 5,
        "CONTROL_OF_CORRUPTION_WGI_SCORE": 5,
        "POLITICAL_STABILITY_WGI_SCORE": 5,
    },
    momentum_anchor_tolerance_periods={
        "RULE_OF_LAW_WGI_SCORE": 1,
        "CONTROL_OF_CORRUPTION_WGI_SCORE": 1,
        "POLITICAL_STABILITY_WGI_SCORE": 1,
    },
    own_history_level_configs={
        # Sprint 5.10 (DEC-019): exactly one enabled indicator. 20 quarterly
        # observations ~ 5 years of the country's own history — an Atlas
        # versioned MODEL PARAMETER, not a BIS threshold or provider fact.
        "DEBT_SERVICE_RATIO": OwnHistoryLevelConfig(minimum_sample_n=20),
    },
    one_sided_vulnerability_configs={
        # Sprint 5.12 (DEC-021): the owner-approved credit-gap curve. The
        # breakpoints coincide with the Basel CCyB guide L/H reference points;
        # the 50/0 score mapping is an Atlas choice (no-excess region is
        # deliberately neutral, NOT a health claim).
        "CREDIT_TO_GDP_GAP": OneSidedVulnerabilityConfig(
            neutral_ceiling=2.0,
            saturation_value=10.0,
            no_excess_score=50.0,
            saturated_score=0.0,
        ),
    },
    backtest_safe=False,
)


# --- Registry: every live indicator classified (Section 7) ---------------------

LIVE_INDICATOR_CODES: frozenset[str] = frozenset(
    {
        # World Bank (15 live SourceSeries)
        "GDP_GROWTH",
        "GDP_CURRENT_USD",
        "GDP_PER_CAPITA",
        "EXPORTS_GDP",
        "IMPORTS_GDP",
        "TRADE_BALANCE",
        "CURRENT_ACCOUNT_GDP",
        "GROSS_CAPITAL_FORMATION_GDP",
        "GINI_INDEX",
        "INFLATION_CPI",
        "MILITARY_EXPENDITURE_USD",
        "MILITARY_EXPENDITURE_GDP",
        "RULE_OF_LAW_WGI_SCORE",
        "CONTROL_OF_CORRUPTION_WGI_SCORE",
        "POLITICAL_STABILITY_WGI_SCORE",
        # BIS (2)
        "CREDIT_TO_GDP_GAP",
        "DEBT_SERVICE_RATIO",
        # OECD (2)
        "LABOUR_PRODUCTIVITY_PER_HOUR",
        "UNIT_LABOUR_COST_GROWTH",
    }
)

_WGI_NOTE = (
    "Provider's fixed 0-100 absolute scale (2025 revision) preserved as the "
    "level signal — never percentile-ranked. Perception-based composite with "
    "measurement uncertainty (CI/SE series documented, not imported). "
    "SOURCE indicator, not a force score."
)

NORMALIZATION_REGISTRY: dict[str, NormalizationSpec] = {
    spec.indicator_code: spec
    for spec in (
        # -- World Bank -------------------------------------------------------
        NormalizationSpec(
            indicator_code="GDP_GROWTH",
            direction=IndicatorStrengthDirection.positive,
            level_family=NormalizationFamily.contextual_deferred,
            relative_family=NormalizationFamily.cross_sectional_relative,
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(3, 5),
            freshness_class=FreshnessClass.annual,
            absolute_comparable=True,
            relative_comparable=True,
            notes=(
                "Output growth (cyclical + structural), not productivity. "
                "Sprint 5.9 audit (DEC-018): a UNIVERSAL TARGET_BAND is not "
                "defensible — potential growth differs by development stage "
                "(tracked_8 medians 2015-2025: IND 7.2 / CHN 6.1 vs JPN 0.8 / "
                "DEU 1.1), so one band would punish catch-up growth and/or "
                "reward stagnation. Level RECLASSIFIED to CONTEXTUAL_DEFERRED; "
                "future design candidate: own-history deviation + relative "
                "growth + potential-growth gap (no potential-output series "
                "imported). Relative/momentum proposals remain unapproved."
            ),
        ),
        NormalizationSpec(
            indicator_code="GDP_CURRENT_USD",
            direction=IndicatorStrengthDirection.positive,
            level_family=NormalizationFamily.contextual_deferred,
            relative_family=NormalizationFamily.contextual_deferred,
            momentum_family=None,
            freshness_class=FreshnessClass.annual,
            notes=(
                "Deliberately unassigned (economic scale/context). Nominal USD; "
                "any future relative-power role needs PPP/deflation — a "
                "separate explicitly justified decision."
            ),
        ),
        NormalizationSpec(
            indicator_code="GDP_PER_CAPITA",
            direction=IndicatorStrengthDirection.positive,
            level_family=NormalizationFamily.contextual_deferred,
            relative_family=NormalizationFamily.contextual_deferred,
            momentum_family=None,
            freshness_class=FreshnessClass.annual,
            notes=(
                "Deliberately unassigned. Nominal; would need PPP and likely "
                "log transform before any use."
            ),
        ),
        NormalizationSpec(
            indicator_code="EXPORTS_GDP",
            direction=IndicatorStrengthDirection.positive,
            level_family=NormalizationFamily.contextual_deferred,
            relative_family=NormalizationFamily.contextual_deferred,
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(3, 5),
            freshness_class=FreshnessClass.annual,
            absolute_comparable=True,
            notes=(
                "High exports = integration/demand, NOT automatically good. "
                "Trade force is a multi-indicator contextual case; no "
                "monotonic curve invented this sprint."
            ),
        ),
        NormalizationSpec(
            indicator_code="IMPORTS_GDP",
            direction=IndicatorStrengthDirection.negative,
            level_family=NormalizationFamily.contextual_deferred,
            relative_family=NormalizationFamily.contextual_deferred,
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(3, 5),
            freshness_class=FreshnessClass.annual,
            absolute_comparable=True,
            notes=(
                "Catalog direction is negative, but imports are NOT simply "
                "bad (capital goods, supply-chain integration, demand). Level "
                "curve deferred; the catalog direction is NOT encoded as a "
                "monotonic-negative normalization."
            ),
        ),
        NormalizationSpec(
            indicator_code="TRADE_BALANCE",
            direction=IndicatorStrengthDirection.positive,
            level_family=NormalizationFamily.contextual_deferred,
            relative_family=NormalizationFamily.contextual_deferred,
            momentum_family=None,
            freshness_class=FreshnessClass.annual,
            absolute_comparable=True,
            notes=(
                "Sign and magnitude both ambiguous (surplus = competitiveness "
                "or weak demand; deficit = investment or imbalance). Deferred "
                "rather than invented."
            ),
        ),
        NormalizationSpec(
            indicator_code="CURRENT_ACCOUNT_GDP",
            direction=IndicatorStrengthDirection.positive,
            level_family=NormalizationFamily.contextual_deferred,
            relative_family=NormalizationFamily.contextual_deferred,
            momentum_family=None,
            freshness_class=FreshnessClass.annual,
            absolute_comparable=True,
            notes=(
                "Large surpluses and large deficits both carry meanings; "
                "banding deferred."
            ),
        ),
        NormalizationSpec(
            indicator_code="GROSS_CAPITAL_FORMATION_GDP",
            direction=IndicatorStrengthDirection.positive,
            level_family=NormalizationFamily.contextual_deferred,
            relative_family=NormalizationFamily.cross_sectional_relative,
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(3, 5),
            freshness_class=FreshnessClass.annual,
            absolute_comparable=True,
            relative_comparable=True,
            notes=(
                "Investment effort, not infrastructure quality. Sprint 5.9 "
                "audit (DEC-018): MONOTONIC_SATURATING disproved — very high "
                "GCF can reflect credit-driven overinvestment / inefficient "
                "allocation (both tails carry meaning), and a 'healthy' level "
                "is economy-model-dependent (tracked_8 medians: CHN 42.4 vs "
                "GBR 18.5), so a universal band would also encode arbitrary "
                "norms. Level RECLASSIFIED to CONTEXTUAL_DEFERRED; future "
                "design candidate: deviation from the country's own "
                "investment norm."
            ),
        ),
        NormalizationSpec(
            indicator_code="GINI_INDEX",
            direction=IndicatorStrengthDirection.negative,
            level_family=NormalizationFamily.monotonic_negative,
            relative_family=NormalizationFamily.cross_sectional_relative,
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(5,),  # irregular years — window in observations, only when enough exist
            freshness_class=FreshnessClass.irregular,
            absolute_comparable=True,
            relative_comparable=True,
            notes=(
                "Higher = more income inequality. Sprint 5.9 audit (DEC-018): "
                "direction CONFIRMED (MONOTONIC_NEGATIVE) but NO numeric "
                "curve approved — '100 - Gini' is NOT an approved mapping "
                "(an Atlas 50 would have no defensible meaning); global "
                "empirical calibration and survey-base (income vs "
                "consumption) comparability remain open. Irregular survey "
                "years: never forward-filled; freshness decay applies to "
                "stale values. Feeds the PARTIAL-capped wealth gaps force — "
                "the ceiling acts at the force layer only."
            ),
        ),
        NormalizationSpec(
            indicator_code="INFLATION_CPI",
            direction=IndicatorStrengthDirection.contextual,
            level_family=NormalizationFamily.contextual_deferred,
            relative_family=NormalizationFamily.contextual_deferred,
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(3, 5),
            freshness_class=FreshnessClass.annual,
            absolute_comparable=True,
            notes=(
                "Domestic price pressure only: never raw level. Sprint 5.9 "
                "audit (DEC-018): a universal raw-CPI band would encode '2% "
                "ideal for every country' — inflation objectives differ "
                "across countries/regimes (tracked_8 medians: IND 6.35 vs JPN "
                "0.29), and cost competitiveness needs exchange rates + "
                "partner-country prices (not imported). Level RECLASSIFIED to "
                "CONTEXTUAL_DEFERRED until a defensible per-country target/"
                "reference exists; the series stays live for coverage."
            ),
        ),
        NormalizationSpec(
            indicator_code="MILITARY_EXPENDITURE_USD",
            direction=IndicatorStrengthDirection.contextual,
            level_family=NormalizationFamily.contextual_deferred,
            relative_family=NormalizationFamily.relative_share,
            momentum_family=None,
            freshness_class=FreshnessClass.annual,
            notes=(
                "Nominal, scale-dependent; spending != capability (DEC-011). "
                "CONTEXTUAL_DEFERRED level — no more-spending-is-stronger "
                "curve. Future relative concept: share of tracked/global "
                "military expenditure, or PPP-adjusted resources."
            ),
        ),
        NormalizationSpec(
            indicator_code="MILITARY_EXPENDITURE_GDP",
            direction=IndicatorStrengthDirection.contextual,
            level_family=NormalizationFamily.contextual_deferred,
            relative_family=NormalizationFamily.contextual_deferred,
            momentum_family=None,
            freshness_class=FreshnessClass.annual,
            absolute_comparable=True,
            notes=(
                "Effort/burden, not capability (DEC-011). CONTEXTUAL_DEFERRED "
                "until the force-scoring sprint defines the interaction with "
                "absolute spending."
            ),
        ),
        NormalizationSpec(
            indicator_code="RULE_OF_LAW_WGI_SCORE",
            direction=IndicatorStrengthDirection.positive,
            level_family=NormalizationFamily.direct_0_100,
            relative_family=NormalizationFamily.cross_sectional_relative,
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(3, 5),
            freshness_class=FreshnessClass.annual,
            absolute_comparable=True,
            relative_comparable=True,
            notes=_WGI_NOTE + " Biennial gaps 1997/1999/2001.",
        ),
        NormalizationSpec(
            indicator_code="CONTROL_OF_CORRUPTION_WGI_SCORE",
            direction=IndicatorStrengthDirection.positive,
            level_family=NormalizationFamily.direct_0_100,
            relative_family=NormalizationFamily.cross_sectional_relative,
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(3, 5),
            freshness_class=FreshnessClass.annual,
            absolute_comparable=True,
            relative_comparable=True,
            notes=(
                "Higher = stronger control of corruption; raw value never "
                "reversed. " + _WGI_NOTE
            ),
        ),
        NormalizationSpec(
            indicator_code="POLITICAL_STABILITY_WGI_SCORE",
            direction=IndicatorStrengthDirection.positive,
            level_family=NormalizationFamily.direct_0_100,
            relative_family=NormalizationFamily.cross_sectional_relative,
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(3, 5),
            freshness_class=FreshnessClass.annual,
            absolute_comparable=True,
            relative_comparable=True,
            notes=(
                "Feeds the PARTIAL-capped internal-conflict force (DEC-009); "
                "the ceiling acts at the force layer only — this indicator "
                "spec is a normal DIRECT_0_100 entry. " + _WGI_NOTE
            ),
        ),
        # -- BIS ---------------------------------------------------------------
        NormalizationSpec(
            indicator_code="CREDIT_TO_GDP_GAP",
            direction=IndicatorStrengthDirection.contextual,
            level_family=NormalizationFamily.one_sided_vulnerability,
            relative_family=NormalizationFamily.contextual_deferred,
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(4, 8),
            freshness_class=FreshnessClass.quarterly,
            absolute_comparable=True,
            notes=(
                "ONE_SIDED_VULNERABILITY (reclassified from asymmetric "
                "TARGET_BAND by the Sprint 5.11 evidence audit, DEC-020): the "
                "indicator measures EXCESS-CREDIT vulnerability on the "
                "positive side. Authoritative evidence (Basel CCyB guide L=2/"
                "H=10 as a policy-guide reference point; BIS 2018 EWI red "
                "threshold ~9pp, amber 4-9) supports positive-side "
                "vulnerability breakpoints, but NO authoritative evidence "
                "supports a negative-side penalty threshold — the Basel "
                "guide is flat zero below +2, and a persistent negative gap "
                "is a post-crisis bust/measurement artifact, NOT an "
                "unhealthy-debt signal in itself. The DEC-018 'very negative "
                "= deleveraging/weak credit' penalty expectation is RETRACTED "
                "by DEC-020; deleveraging/weak-credit conditions belong to "
                "other signals (DSR level, credit growth, output). "
                "IMPLEMENTED in Sprint 5.12 (DEC-021) with the owner-approved "
                "curve: level_score = 50 at or below +2pp (no-excess region "
                "deliberately NEUTRAL, not 100), linear from (+2, 50) to "
                "(+10, 0), 0 at or above +10pp. The +2/+10 breakpoints "
                "coincide with the Basel guide L/H reference points; the "
                "50/0 mapping is an Atlas MODEL PARAMETER. The gap remains a "
                "common reference point, NOT a mechanical standalone rule "
                "(DEC-020 caveats). Relative CONTEXTUAL_DEFERRED (None); "
                "registry momentum windows (4q/8q) stay UNAPPROVED."
            ),
        ),
        NormalizationSpec(
            indicator_code="DEBT_SERVICE_RATIO",
            direction=IndicatorStrengthDirection.contextual,
            level_family=NormalizationFamily.own_history,
            relative_family=None,  # cross-country DSR levels explicitly discouraged (BIS caution)
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(4, 8),
            freshness_class=FreshnessClass.quarterly,
            notes=(
                "OWN_HISTORY level (BIS: cross-country DSR levels less "
                "meaningful than changes relative to each country's own "
                "history — income definitions differ). Never cross-sectionally "
                "rank raw DSR. Sprint 5.9 audit (DEC-018): CONFIRMED as the "
                "next implementation target — READY_FOR_IMPLEMENTATION_DESIGN "
                "(own-history stress-position percentile; open design "
                "questions listed in NORMALIZATION.md Sprint 5.9 audit)."
            ),
        ),
        # -- OECD ---------------------------------------------------------------
        NormalizationSpec(
            indicator_code="LABOUR_PRODUCTIVITY_PER_HOUR",
            direction=IndicatorStrengthDirection.positive,
            level_family=NormalizationFamily.monotonic_positive,
            relative_family=NormalizationFamily.cross_sectional_relative,
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(3, 5),
            freshness_class=FreshnessClass.annual,
            absolute_comparable=True,
            relative_comparable=True,
            notes=(
                "Structural productive capability (USD PPP/hour, built for "
                "comparison). Level AND own-history growth stay separable: "
                "high level + weak growth != low level + fast improvement. "
                "Sprint 5.9 audit (DEC-018): direction (higher PPP/hour = "
                "stronger structural productivity) approved, but NO "
                "absolute 0-100 mapping without an external calibration "
                "distribution — tracked_8 min-max is explicitly rejected "
                "(CHN/IND not covered by OECD; pooled tracked_8 range 33.5-"
                "90.5 is not a global distribution). Level curve deferred "
                "pending an expanded calibration universe decision."
            ),
        ),
        NormalizationSpec(
            indicator_code="UNIT_LABOUR_COST_GROWTH",
            direction=IndicatorStrengthDirection.contextual,
            level_family=NormalizationFamily.contextual_deferred,
            relative_family=NormalizationFamily.contextual_deferred,
            momentum_family=NormalizationFamily.own_history,
            momentum_windows=(4, 8),
            freshness_class=FreshnessClass.quarterly,
            absolute_comparable=True,
            notes=(
                "Sprint 5.9 audit (DEC-018): raw domestic ULC growth is not "
                "by itself a relative-competitiveness measure — an absolute "
                "health score needs exchange rates + partner-country ULC + "
                "inflation-regime context (none imported), and an arbitrary "
                "zero-centered band is not defensible. Level RECLASSIFIED to "
                "CONTEXTUAL_DEFERRED; the series stays live for coverage. "
                "CHN/IND: no ULC — their force score must compute from "
                "available inputs only (lower confidence), never zero-fill "
                "the missing ULC."
            ),
        ),
    )
}


def live_force_input_codes() -> frozenset[str]:
    """All canonical indicators currently mapped as live inputs of any force."""
    codes: set[str] = set()
    for force in FORCE_DEFINITIONS:
        codes.update(force.live_indicator_codes)
    return frozenset(codes)


def validate_normalization_registry() -> None:
    """Fail loudly on registry configuration mistakes.

    Raises ValueError on: duplicate codes, registry/universe-of-live-indicators
    mismatch, or a live force input with no normalization entry.
    """
    live = live_force_input_codes()
    missing = live - frozenset(NORMALIZATION_REGISTRY)
    if missing:
        raise ValueError(
            f"live force inputs with no normalization spec: {sorted(missing)}"
        )
    unknown = frozenset(NORMALIZATION_REGISTRY) - LIVE_INDICATOR_CODES
    if unknown:
        raise ValueError(
            f"normalization specs for non-live indicators: {sorted(unknown)}"
        )
    # Deliberately unassigned indicators must be explicitly DEFERRED, never
    # promoted into force scoring by accident.
    unassigned = {"GDP_CURRENT_USD", "GDP_PER_CAPITA"} & live
    if unassigned:
        raise ValueError(
            f"deliberately unassigned indicators became force inputs: "
            f"{sorted(unassigned)}"
        )
    # Own-history level configs (Sprint 5.10 gate): an entry for an indicator
    # whose registry level family is not OWN_HISTORY is a configuration
    # mistake — fail loudly. (Checked here, not in ModelVersionConfig, because
    # the registry is defined after the model-version constants.)
    for indicator, config in CURRENT_MODEL_VERSION.own_history_level_configs.items():
        spec = NORMALIZATION_REGISTRY.get(indicator)
        if spec is None:
            raise ValueError(
                f"own-history level config for an unknown indicator: {indicator}"
            )
        if spec.level_family is not NormalizationFamily.own_history:
            raise ValueError(
                f"{indicator}: own-history level config but registry level family "
                f"is {spec.level_family.value}"
            )
    # One-sided vulnerability configs (Sprint 5.12 gate): an entry for an
    # indicator whose registry level family is not ONE_SIDED_VULNERABILITY is
    # a configuration mistake — fail loudly.
    for indicator in CURRENT_MODEL_VERSION.one_sided_vulnerability_configs:
        spec = NORMALIZATION_REGISTRY.get(indicator)
        if spec is None:
            raise ValueError(
                f"one-sided vulnerability level config for an unknown "
                f"indicator: {indicator}"
            )
        if spec.level_family is not NormalizationFamily.one_sided_vulnerability:
            raise ValueError(
                f"{indicator}: one-sided vulnerability level config but "
                f"registry level family is {spec.level_family.value}"
            )


# Module-level validation: the registry fails loudly at import time, not at
# first use in production scoring.
validate_normalization_registry()


def get_normalization_spec(indicator_code: str) -> NormalizationSpec:
    try:
        return NORMALIZATION_REGISTRY[indicator_code]
    except KeyError:
        raise ValueError(
            f"no normalization spec for indicator: {indicator_code}"
        ) from None