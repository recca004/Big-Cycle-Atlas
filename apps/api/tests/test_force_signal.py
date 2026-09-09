"""Sprint 5.22: pure ForceSignal / aggregator tests.

Methodology/config only — no DB, no HTTP. Tests the pure
aggregate_force_from_signals function with synthetic NormalizedSignal objects.
"""
import pytest

from app.cycle.force_aggregation_definitions import (
    FORCE_AGGREGATION_CONFIGS,
    ForceAggregationMode,
    ForceDimensionMode,
    ForceIndicatorComponentSpec,
    ForceIndicatorRole,
)
from app.cycle.force_definitions import ForceCoverageStatus
from app.cycle.force_signal import ForceSignal, aggregate_force_from_signals
from app.cycle.normalization_definitions import (
    NormalizationFamily,
    NormalizedSignal,
    ScoringPeriod,
)


def _make_wgi_signal(
    indicator_code: str,
    country: str = "CHE",
    period: str = "2025-Q2",
    level: float | None = 80.0,
    relative: float | None = 68.75,
    momentum: float | None = 2.5,
    universe_id: str | None = "tracked_8",
    expected_n: int | None = 8,
    usable_n: int | None = 8,
    rank: float | None = 6.0,
    keep_provenance_when_relative_none: bool = False,
) -> NormalizedSignal:
    """Build a synthetic WGI-like NormalizedSignal for testing.

    By default, when relative is None, all relative provenance is nulled
    (matching the old helper behavior). Set keep_provenance_when_relative_none
    = True to preserve universe_id/expected_n/usable_n even when relative is
    None — this is the DEC-017 incomplete-universe case where the universe
    metadata is real provenance even when the score is missing. relative_rank
    is always nulled when relative is None (NormalizedSignal invariant).
    """
    if relative is None and not keep_provenance_when_relative_none:
        rank = None
        universe_id = None
        expected_n = None
        usable_n = None
    if relative is None:
        # relative_rank requires relative_score (NormalizedSignal invariant).
        rank = None
    return NormalizedSignal(
        indicator_code=indicator_code,
        country_iso3=country,
        as_of_period=ScoringPeriod(2025, 2),
        raw_value=level if level is not None else 0.0,
        source_period="2024",
        method=NormalizationFamily.direct_0_100,
        model_version="normalization-v0.8",
        level_score=level,
        relative_score=relative,
        momentum=momentum,
        confidence=None,
        reference_universe_id=universe_id,
        reference_universe_expected_n=expected_n,
        reference_universe_usable_n=usable_n,
        relative_rank=rank,
        backtest_safe=False,
    )


def _make_dsr_signal(
    country: str = "CHE",
    period: str = "2025-Q2",
    level: float | None = 75.0,
) -> NormalizedSignal:
    return NormalizedSignal(
        indicator_code="DEBT_SERVICE_RATIO",
        country_iso3=country,
        as_of_period=ScoringPeriod(2025, 2),
        raw_value=15.0,
        source_period="2025-Q1",
        method=NormalizationFamily.own_history,
        model_version="normalization-v0.8",
        level_score=level,
        relative_score=None,
        momentum=None,
        confidence=None,
        backtest_safe=False,
    )


def _make_credit_gap_signal(
    country: str = "CHE",
    period: str = "2025-Q2",
    level: float | None = 50.0,
) -> NormalizedSignal:
    return NormalizedSignal(
        indicator_code="CREDIT_TO_GDP_GAP",
        country_iso3=country,
        as_of_period=ScoringPeriod(2025, 2),
        raw_value=1.0,
        source_period="2025-Q1",
        method=NormalizationFamily.one_sided_vulnerability,
        model_version="normalization-v0.8",
        level_score=level,
        relative_score=None,
        momentum=None,
        confidence=None,
        backtest_safe=False,
    )


# --- 1-3: identity copies exact level ----------------------------------------


def test_rule_of_law_identity_copies_exact_level():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE", level=82.5)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.level_score == 82.5
    assert fs.aggregation_method is ForceAggregationMode.identity_single


def test_corruption_identity_copies_exact_level():
    spec = FORCE_AGGREGATION_CONFIGS["corruption"]
    signal = _make_wgi_signal("CONTROL_OF_CORRUPTION_WGI_SCORE", level=77.0)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"CONTROL_OF_CORRUPTION_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.level_score == 77.0


def test_internal_conflict_proxy_identity_copies_exact_level():
    spec = FORCE_AGGREGATION_CONFIGS["internal_conflict"]
    signal = _make_wgi_signal("POLITICAL_STABILITY_WGI_SCORE", level=70.0)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"POLITICAL_STABILITY_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.partial,
    )
    assert fs.level_score == 70.0


# --- 4: PARTIAL coverage does not change internal-conflict level ----------------


def test_partial_coverage_does_not_change_internal_conflict_level():
    spec = FORCE_AGGREGATION_CONFIGS["internal_conflict"]
    signal = _make_wgi_signal("POLITICAL_STABILITY_WGI_SCORE", level=70.0)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"POLITICAL_STABILITY_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.partial,
        coverage_ceiling=ForceCoverageStatus.partial,
    )
    assert fs.level_score == 70.0  # NOT multiplied by coverage
    assert fs.coverage_status is ForceCoverageStatus.partial
    assert fs.coverage_ceiling is ForceCoverageStatus.partial


# --- 5-6: relative identity + provenance --------------------------------------


def test_identity_relative_copied_exactly():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE", relative=55.5)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.relative_score == 55.5


def test_relative_provenance_copied_exactly():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal(
        "RULE_OF_LAW_WGI_SCORE",
        universe_id="tracked_8",
        expected_n=8,
        usable_n=8,
        rank=6.0,
    )
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.reference_universe_id == "tracked_8"
    assert fs.reference_universe_expected_n == 8
    assert fs.reference_universe_usable_n == 8
    assert fs.relative_rank == 6.0


# --- 7-9: momentum / None propagation ----------------------------------------


def test_identity_momentum_copied_exactly():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE", momentum=3.5)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.momentum == 3.5


def test_momentum_none_remains_none():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE", momentum=None)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.momentum is None


def test_level_none_remains_none():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE", level=None, relative=None, momentum=None)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.level_score is None
    assert fs.relative_score is None  # component relative is also None
    assert fs.momentum is None


# --- 10: zero is preserved ONLY when it is an actual valid component score ----


def test_zero_level_preserved_when_actual_score():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE", level=0.0, relative=None, momentum=None)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.level_score == 0.0  # actual zero, not missing


def test_missing_component_level_is_none_not_zero():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": None},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.level_score is None  # missing -> None, NOT zero


# --- 11: no clamping ----------------------------------------------------------


def test_no_clamping_high_level():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE", level=100.0)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.level_score == 100.0


def test_invalid_level_raises():
    """ForceSignal must reject out-of-range level_score (never clamp)."""
    import pytest
    with pytest.raises(ValueError, match="level_score must be in"):
        ForceSignal(
            country_iso3="CHE",
            force_code="rule_of_law",
            scoring_period="2025-Q2",
            level_score=150.0,
        )


# --- 12-14: confidence / backtest / versions ---------------------------------


def test_confidence_always_none():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE")
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.confidence is None


def test_backtest_safe_false():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE")
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.backtest_safe is False


def test_versions_correct():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE")
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.force_model_version == "force-aggregation-v0.3"
    assert fs.normalization_model_version == "normalization-v0.8"


# --- 15: supporting context cannot alter numeric result ----------------------


def test_supporting_context_cannot_alter_numeric_result():
    """A deferred force with supporting context must have None scores.

    Uses military_strength (2 SUPPORTING_CONTEXT, DEFERRED_MULTI) —
    wealth_opportunity_values_gaps was promoted to PROXY_CONDITION +
    IDENTITY_SINGLE in Sprint 6.7 so it no longer fits this test.
    """
    spec = FORCE_AGGREGATION_CONFIGS["military_strength"]
    fake_signal = NormalizedSignal(
        indicator_code="MILITARY_EXPENDITURE_GDP",
        country_iso3="CHE",
        as_of_period=ScoringPeriod(2025, 2),
        raw_value=2.5,
        source_period="2024",
        method=NormalizationFamily.monotonic_negative,
        model_version="normalization-v0.8",
        level_score=90.0,  # fake — should NOT propagate
    )
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"MILITARY_EXPENDITURE_GDP": fake_signal},
        coverage_status=ForceCoverageStatus.partial,
    )
    assert fs.level_score is None
    assert fs.aggregation_method is ForceAggregationMode.deferred_multi
    assert "MILITARY_EXPENDITURE_GDP" in fs.deferred_components


def test_education_proxy_identity_copies_exact_level():
    """Sprint 6.4 (DEC-032): Education is PROXY_CONDITION + IDENTITY_SINGLE.

    The force level_score must equal the indicator level_score (aligned raw
    OECD percentage). relative/momentum/confidence stay None.
    """
    spec = FORCE_AGGREGATION_CONFIGS["education"]
    assert spec.level_mode is ForceDimensionMode.identity_copy
    assert spec.relative_mode is ForceDimensionMode.deferred
    assert spec.momentum_mode is ForceDimensionMode.deferred
    roles = {c.indicator_code: c.role for c in spec.components}
    assert roles["TERTIARY_ATTAINMENT_25_34"] is ForceIndicatorRole.proxy_condition
    fake_signal = NormalizedSignal(
        indicator_code="TERTIARY_ATTAINMENT_25_34",
        country_iso3="CHE",
        as_of_period=ScoringPeriod(2025, 2),
        raw_value=52.0,
        source_period="2024",
        method=NormalizationFamily.direct_0_100,
        model_version="normalization-v0.8",
        level_score=52.0,
    )
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"TERTIARY_ATTAINMENT_25_34": fake_signal},
        coverage_status=ForceCoverageStatus.partial,
    )
    assert fs.level_score == 52.0  # exact copy of indicator level
    assert fs.relative_score is None  # DEC-032: not approved
    assert fs.momentum is None  # DEC-032: not approved
    assert fs.confidence is None
    assert fs.aggregation_method is ForceAggregationMode.identity_single
    assert fs.scoring_component_indicator == "TERTIARY_ATTAINMENT_25_34"
    assert fs.backtest_safe is False


def test_education_missing_indicator_level_none():
    """Sprint 6.4: missing/stale Education indicator -> force level None."""
    spec = FORCE_AGGREGATION_CONFIGS["education"]
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHN",
        scoring_period="2025-Q4",
        component_signals={"TERTIARY_ATTAINMENT_25_34": None},
        coverage_status=ForceCoverageStatus.partial,
    )
    assert fs.level_score is None
    assert fs.relative_score is None
    assert fs.momentum is None
    assert fs.confidence is None
    assert fs.aggregation_method is ForceAggregationMode.identity_single
    assert "TERTIARY_ATTAINMENT_25_34" in fs.missing_components


# --- 16: Indebtedness DSR + credit gap both present -> force level None -------


def test_indebtedness_dsr_credit_gap_present_force_level_none():
    spec = FORCE_AGGREGATION_CONFIGS["indebtedness"]
    dsr = _make_dsr_signal(level=75.0)
    credit_gap = _make_credit_gap_signal(level=50.0)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={
            "DEBT_SERVICE_RATIO": dsr,
            "CREDIT_TO_GDP_GAP": credit_gap,
            "GOVERNMENT_DEBT_GDP": None,  # supporting context
        },
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.level_score is None
    assert fs.relative_score is None
    assert fs.momentum is None
    assert fs.aggregation_method is ForceAggregationMode.deferred_multi
    # Component signals preserved as provenance
    assert len(fs.component_signals) == 2  # DSR + credit gap
    assert "GOVERNMENT_DEBT_GDP" in fs.deferred_components


# --- 17: no equal-weight result exists ---------------------------------------


def test_no_equal_weight_result_indebtedness():
    """Indebtedness must NOT produce an average of DSR and credit gap."""
    spec = FORCE_AGGREGATION_CONFIGS["indebtedness"]
    dsr = _make_dsr_signal(level=80.0)
    credit_gap = _make_credit_gap_signal(level=40.0)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={
            "DEBT_SERVICE_RATIO": dsr,
            "CREDIT_TO_GDP_GAP": credit_gap,
            "GOVERNMENT_DEBT_GDP": None,
        },
        coverage_status=ForceCoverageStatus.available,
    )
    # The average would be 60.0 — this must NOT be the result.
    assert fs.level_score != 60.0
    assert fs.level_score is None


# --- 18: component order cannot change deferred output -------------------------


def test_component_order_does_not_change_deferred_output():
    spec = FORCE_AGGREGATION_CONFIGS["indebtedness"]
    dsr = _make_dsr_signal(level=75.0)
    credit_gap = _make_credit_gap_signal(level=50.0)
    signals_a = {
        "DEBT_SERVICE_RATIO": dsr,
        "CREDIT_TO_GDP_GAP": credit_gap,
        "GOVERNMENT_DEBT_GDP": None,
    }
    signals_b = {
        "GOVERNMENT_DEBT_GDP": None,
        "CREDIT_TO_GDP_GAP": credit_gap,
        "DEBT_SERVICE_RATIO": dsr,
    }
    fs_a = aggregate_force_from_signals(
        force_spec=spec, country_iso3="CHE", scoring_period="2025-Q2",
        component_signals=signals_a, coverage_status=ForceCoverageStatus.available,
    )
    fs_b = aggregate_force_from_signals(
        force_spec=spec, country_iso3="CHE", scoring_period="2025-Q2",
        component_signals=signals_b, coverage_status=ForceCoverageStatus.available,
    )
    assert fs_a.level_score == fs_b.level_score  # both None
    assert fs_a.aggregation_method == fs_b.aggregation_method


# --- Independent dimension propagation ---------------------------------------


def test_independent_dimension_propagation():
    """level=80, relative=68.75, momentum=None -> force copies each independently."""
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE", level=80.0, relative=68.75, momentum=None)
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.level_score == 80.0
    assert fs.relative_score == 68.75
    assert fs.momentum is None  # None propagates, does NOT block other dims


def test_scoring_component_indicator_recorded():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE")
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.scoring_component_indicator == "RULE_OF_LAW_WGI_SCORE"


# --- Sprint 5.22.1: relative provenance with score=None (DEC-017) --------------


def test_relative_provenance_copied_when_score_none():
    """DEC-017 incomplete-universe: provenance is copied even when
    relative_score is None. The universe metadata is real provenance even
    when the score is missing. Never turn missing relative into zero.
    """
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal(
        "RULE_OF_LAW_WGI_SCORE",
        level=80.0,
        relative=None,
        momentum=None,
        universe_id="tracked_8",
        expected_n=8,
        usable_n=7,
        rank=None,
        keep_provenance_when_relative_none=True,
    )
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.relative_score is None  # missing -> None, NOT zero
    assert fs.reference_universe_id == "tracked_8"
    assert fs.reference_universe_expected_n == 8
    assert fs.reference_universe_usable_n == 7
    assert fs.relative_rank is None  # rank requires score (invariant)


def test_relative_provenance_not_fabricated_when_no_signal():
    """When there is no component signal at all, provenance must NOT be
    fabricated. All provenance fields stay None.
    """
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": None},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.relative_score is None
    assert fs.reference_universe_id is None
    assert fs.reference_universe_expected_n is None
    assert fs.reference_universe_usable_n is None
    assert fs.relative_rank is None


def test_relative_provenance_copied_for_all_three_wgi_forces():
    """All 3 WGI identity forces copy relative provenance even when
    relative_score is None (incomplete-universe case).
    """
    for force_code, indicator in (
        ("rule_of_law", "RULE_OF_LAW_WGI_SCORE"),
        ("corruption", "CONTROL_OF_CORRUPTION_WGI_SCORE"),
        ("internal_conflict", "POLITICAL_STABILITY_WGI_SCORE"),
    ):
        spec = FORCE_AGGREGATION_CONFIGS[force_code]
        signal = _make_wgi_signal(
            indicator,
            level=70.0,
            relative=None,
            momentum=None,
            universe_id="tracked_8",
            expected_n=8,
            usable_n=6,
            rank=None,
            keep_provenance_when_relative_none=True,
        )
        fs = aggregate_force_from_signals(
            force_spec=spec,
            country_iso3="CHE",
            scoring_period="2025-Q2",
            component_signals={indicator: signal},
            coverage_status=ForceCoverageStatus.available,
        )
        assert fs.relative_score is None
        assert fs.reference_universe_id == "tracked_8"
        assert fs.reference_universe_expected_n == 8
        assert fs.reference_universe_usable_n == 6
        assert fs.relative_rank is None


# --- Sprint 5.22.1: version provenance propagation ----------------------------


def test_normalization_version_copied_from_component_signal():
    """ForceSignal.normalization_model_version must equal the contributing
    NormalizedSignal's model_version, not a fabricated default.
    """
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    signal = _make_wgi_signal("RULE_OF_LAW_WGI_SCORE")
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": signal},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.normalization_model_version == signal.model_version
    assert fs.normalization_model_version == "normalization-v0.8"


def test_normalization_version_fallback_when_no_signal():
    """When no component signal exists, fall back to CURRENT_MODEL_VERSION."""
    from app.cycle.normalization_definitions import CURRENT_MODEL_VERSION
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    fs = aggregate_force_from_signals(
        force_spec=spec,
        country_iso3="CHE",
        scoring_period="2025-Q2",
        component_signals={"RULE_OF_LAW_WGI_SCORE": None},
        coverage_status=ForceCoverageStatus.available,
    )
    assert fs.normalization_model_version == CURRENT_MODEL_VERSION.version_id


def test_normalization_version_mismatch_raises():
    """If contributing signals disagree on model_version, fail loudly."""
    import pytest
    spec = FORCE_AGGREGATION_CONFIGS["indebtedness"]
    dsr = _make_dsr_signal(level=75.0)
    # Build a credit-gap signal with a DIFFERENT model_version.
    credit_gap = NormalizedSignal(
        indicator_code="CREDIT_TO_GDP_GAP",
        country_iso3="CHE",
        as_of_period=ScoringPeriod(2025, 2),
        raw_value=1.0,
        source_period="2025-Q1",
        method=NormalizationFamily.one_sided_vulnerability,
        model_version="normalization-v0.999",  # mismatch
        level_score=50.0,
        relative_score=None,
        momentum=None,
        confidence=None,
        backtest_safe=False,
    )
    with pytest.raises(ValueError, match="disagree on model_version"):
        aggregate_force_from_signals(
            force_spec=spec,
            country_iso3="CHE",
            scoring_period="2025-Q2",
            component_signals={
                "DEBT_SERVICE_RATIO": dsr,
                "CREDIT_TO_GDP_GAP": credit_gap,
                "GOVERNMENT_DEBT_GDP": None,
            },
            coverage_status=ForceCoverageStatus.available,
        )
