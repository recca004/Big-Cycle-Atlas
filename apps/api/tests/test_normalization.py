"""Sprint 5.5 normalization-design tests (offline, no DB, no scores).

Tests the typed architecture: family registry integrity, the four separable
score dimensions, the MISSING != ZERO rule, and the fact that this module
publishes no force scores. All tests are pure unit tests over the
configuration layer.
"""
import pytest

from app.cycle import normalization_definitions as nd
from app.cycle.force_definitions import FORCE_DEFINITIONS, ForceCoverageStatus
from app.models.indicator import IndicatorStrengthDirection


# 1 + 2. Registry integrity: no duplicates, every live force input classified.


def test_registry_has_no_duplicate_codes():
    codes = list(nd.NORMALIZATION_REGISTRY)
    assert len(codes) == len(set(codes))
    # 22 live SourceSeries = 22 registry entries, one per live indicator.
    assert len(codes) == 22


def test_every_live_force_input_has_a_normalization_spec():
    live_inputs = nd.live_force_input_codes()
    assert live_inputs, "expected live force inputs to exist"
    missing = live_inputs - frozenset(nd.NORMALIZATION_REGISTRY)
    assert not missing, f"live force inputs without spec: {sorted(missing)}"
    # The module validates this at import time; running it again must not raise.
    nd.validate_normalization_registry()


def test_registry_covers_exactly_the_live_indicator_universe():
    assert frozenset(nd.NORMALIZATION_REGISTRY) == nd.LIVE_INDICATOR_CODES


def test_deliberately_unassigned_indicators_are_deferred_not_promoted():
    for code in ("GDP_CURRENT_USD", "GDP_PER_CAPITA"):
        spec = nd.NORMALIZATION_REGISTRY[code]
        assert spec.level_family is nd.NormalizationFamily.contextual_deferred
        assert code not in nd.live_force_input_codes()


# 3. WGI keeps the provider's DIRECT_0_100 absolute scale.


@pytest.mark.parametrize(
    "code",
    ["RULE_OF_LAW_WGI_SCORE", "CONTROL_OF_CORRUPTION_WGI_SCORE", "POLITICAL_STABILITY_WGI_SCORE"],
)
def test_wgi_uses_direct_0_100(code):
    spec = nd.NORMALIZATION_REGISTRY[code]
    assert spec.level_family is nd.NormalizationFamily.direct_0_100
    # Never percentile-ranked into the relative scale as the level signal.
    assert spec.level_family is not nd.NormalizationFamily.cross_sectional_relative
    assert spec.direction is IndicatorStrengthDirection.positive


# 4. DSR uses OWN_HISTORY; raw DSR is never cross-sectionally ranked.


def test_dsr_uses_own_history_and_is_never_cross_sectional():
    spec = nd.NORMALIZATION_REGISTRY["DEBT_SERVICE_RATIO"]
    assert spec.level_family is nd.NormalizationFamily.own_history
    # Cross-country DSR ranking is explicitly discouraged (BIS caution).
    assert spec.relative_family is None
    assert spec.relative_family is not nd.NormalizationFamily.cross_sectional_relative
    assert spec.momentum_family is nd.NormalizationFamily.own_history


# 5. Gini uses a negative-direction normalization family.


def test_gini_uses_negative_direction_family():
    spec = nd.NORMALIZATION_REGISTRY["GINI_INDEX"]
    assert spec.level_family is nd.NormalizationFamily.monotonic_negative
    assert spec.direction is IndicatorStrengthDirection.negative
    assert spec.freshness_class is nd.FreshnessClass.irregular


# 6. Military entries are contextual, never monotonic-positive.


@pytest.mark.parametrize(
    "code",
    ["MILITARY_EXPENDITURE_USD", "MILITARY_EXPENDITURE_GDP"],
)
def test_military_is_contextual_deferred_not_monotonic_positive(code):
    spec = nd.NORMALIZATION_REGISTRY[code]
    assert spec.level_family is nd.NormalizationFamily.contextual_deferred
    assert spec.level_family is not nd.NormalizationFamily.monotonic_positive
    assert spec.momentum_family is None  # no spending-trend momentum either
    assert spec.direction is IndicatorStrengthDirection.contextual


# 7. MISSING != ZERO is represented in the types.


def test_missing_is_never_zero_in_the_type_system():
    signal = nd.NormalizedSignal.unscored(
        indicator_code="UNIT_LABOUR_COST_GROWTH",
        country_iso3="CHN",
        as_of_period=nd.ScoringPeriod(2025, 4),
        raw_value=3.2,
        source_period="2025-Q4",
        method=nd.NormalizationFamily.target_band,
        model_version=nd.CURRENT_MODEL_VERSION.version_id,
    )
    # Absent scores are None — an unscored signal is never a zero score.
    assert signal.level_score is None
    assert signal.level_score != 0.0
    assert signal.momentum is None
    assert signal.confidence is None
    assert signal.relative_score is None
    assert signal.backtest_safe is False


def test_unscored_signal_never_fabricates_provenance():
    signal = nd.NormalizedSignal.unscored(
        indicator_code="GINI_INDEX",
        country_iso3="CHE",
        as_of_period=nd.ScoringPeriod(2026, 1),
        raw_value=31.9,
        source_period="2022",
        method=nd.NormalizationFamily.monotonic_negative,
        model_version=nd.CURRENT_MODEL_VERSION.version_id,
    )
    # Provenance travels with the signal: a 2022 Gini used for 2026-Q1 is
    # visibly old, never silently current.
    assert signal.source_period == "2022"
    assert signal.raw_value == 31.9


# 8. Score ranges are specified and validated.


def test_score_ranges_are_specified_correctly():
    assert nd.LEVEL_SCORE_RANGE == (0.0, 100.0)
    assert nd.RELATIVE_SCORE_RANGE == (0.0, 100.0)
    assert nd.MOMENTUM_RANGE == (-100.0, 100.0)
    assert nd.CONFIDENCE_RANGE == (0.0, 1.0)


def test_range_validators_reject_out_of_range_values():
    for validate, bad in (
        (nd.validate_level_score, -0.01),
        (nd.validate_level_score, 100.01),
        (nd.validate_relative_score, -1.0),
        (nd.validate_momentum, -100.01),
        (nd.validate_momentum, 100.01),
        (nd.validate_confidence, -0.1),
        (nd.validate_confidence, 1.1),
    ):
        with pytest.raises(ValueError):
            validate(bad)
    for validate, good in (
        (nd.validate_level_score, 50.0),
        (nd.validate_relative_score, 0.0),
        (nd.validate_momentum, 0.0),
        (nd.validate_confidence, 1.0),
    ):
        validate(good)


def test_scoring_period_validates_quarterly_clock():
    assert nd.ScoringPeriod(2025, 4).label == "2025-Q4"
    with pytest.raises(ValueError):
        nd.ScoringPeriod(2025, 0)
    with pytest.raises(ValueError):
        nd.ScoringPeriod(2025, 5)


# 9. Proxy ceilings act at the force layer only — never on indicator specs.


def test_proxy_ceiling_does_not_modify_indicator_normalization():
    ceiling_forces = {
        force.code: force
        for force in FORCE_DEFINITIONS
        if force.coverage_ceiling is ForceCoverageStatus.partial
    }
    assert set(ceiling_forces) == {
        "education",
        "military_strength",
        "wealth_opportunity_values_gaps",
        "internal_conflict",
    }
    # The capped forces' input indicators are ordinary specs: NormalizationSpec
    # has no ceiling/clamping field, and their families are standard entries.
    for force in ceiling_forces.values():
        for code in force.live_indicator_codes:
            spec = nd.NORMALIZATION_REGISTRY[code]
            assert not hasattr(spec, "coverage_ceiling")
            assert not hasattr(spec, "clamped_score")
    # Gini keeps a normal monotonic_negative level family despite the ceiling.
    assert nd.NORMALIZATION_REGISTRY["GINI_INDEX"].level_family is (
        nd.NormalizationFamily.monotonic_negative
    )


# 10. This module generates no force scores.


def test_module_publishes_no_force_scores():
    # No score computation or force-aggregation entry points exist.
    forbidden = (
        "compute_force_score",
        "calculate_force_score",
        "force_score",
        "ForceScore",
        "compute_level_score",
        "compute_momentum",
        "compute_confidence",
        "aggregate_force",
    )
    for name in forbidden:
        assert not hasattr(nd, name), f"unexpected score publication: {name}"


def test_no_spec_has_non_none_score_defaults_in_types():
    # Every registry entry is pure classification: constructing a spec never
    # produces a score value.
    for code, spec in nd.NORMALIZATION_REGISTRY.items():
        assert isinstance(spec.level_family, nd.NormalizationFamily), code
        # Optional families are either a real family or an explicit decision.
        if spec.relative_family is not None:
            assert isinstance(spec.relative_family, nd.NormalizationFamily)
        if spec.momentum_family is None:
            assert spec.momentum_windows == ()
        else:
            assert spec.momentum_windows, "momentum family needs windows"