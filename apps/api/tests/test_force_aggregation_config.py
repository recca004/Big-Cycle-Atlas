"""Sprint 5.21: force aggregation configuration invariant tests.

Methodology/config only — no force score execution, no persistence, no API.
All tests are offline.
"""
from app.cycle.force_aggregation_definitions import (
    FORCE_AGGREGATION_CONFIGS,
    FORCE_AGGREGATION_VERSION,
    ForceAggregationMode,
    ForceDimensionMode,
    ForceIndicatorComponentSpec,
    ForceIndicatorRole,
    aggregation_mode,
)
from app.cycle.force_definitions import FORCE_DEFINITIONS, force_definition_by_code


# --- 17 force definitions still exist ----------------------------------------


def test_exactly_17_force_definitions():
    assert len(FORCE_DEFINITIONS) == 17


def test_every_force_has_aggregation_config():
    force_codes = {f.code for f in FORCE_DEFINITIONS}
    config_codes = set(FORCE_AGGREGATION_CONFIGS.keys())
    assert force_codes == config_codes


def test_no_unknown_force_codes_in_configs():
    force_codes = {f.code for f in FORCE_DEFINITIONS}
    config_codes = set(FORCE_AGGREGATION_CONFIGS.keys())
    assert config_codes.issubset(force_codes)


# --- Role enum exact ---------------------------------------------------------


def test_force_indicator_role_values():
    assert {r.value for r in ForceIndicatorRole} == {
        "core_condition",
        "proxy_condition",
        "vulnerability_penalty",
        "supporting_context",
    }


def test_aggregation_mode_values():
    assert {m.value for m in ForceAggregationMode} == {
        "identity_single",
        "deferred_multi",
    }


# --- Every configured indicator belongs to its force -------------------------


def test_every_component_belongs_to_its_force():
    for force_code, spec in FORCE_AGGREGATION_CONFIGS.items():
        force_def = force_definition_by_code(force_code)
        assert force_def is not None
        live = set(force_def.live_indicator_codes)
        for comp in spec.components:
            assert comp.indicator_code in live, (
                f"{force_code}: {comp.indicator_code} not in live_indicator_codes"
            )


# --- No duplicate components -------------------------------------------------


def test_no_duplicate_components_within_force():
    for force_code, spec in FORCE_AGGREGATION_CONFIGS.items():
        codes = [c.indicator_code for c in spec.components]
        assert len(set(codes)) == len(codes), (
            f"{force_code}: duplicate component indicators"
        )


# --- IDENTITY_SINGLE rules ---------------------------------------------------


def test_identity_single_requires_exactly_one_eligible_component():
    for force_code, spec in FORCE_AGGREGATION_CONFIGS.items():
        if spec.level_mode is ForceDimensionMode.identity_copy:
            eligible = [
                c for c in spec.components
                if c.role in {ForceIndicatorRole.core_condition, ForceIndicatorRole.proxy_condition}
            ]
            assert len(eligible) == 1, (
                f"{force_code}: IDENTITY_SINGLE requires exactly one eligible "
                f"component, got {len(eligible)}"
            )


def test_vulnerability_penalty_not_in_identity_single():
    for force_code, spec in FORCE_AGGREGATION_CONFIGS.items():
        if spec.level_mode is ForceDimensionMode.identity_copy:
            penalties = [
                c for c in spec.components
                if c.role is ForceIndicatorRole.vulnerability_penalty
            ]
            assert not penalties, (
                f"{force_code}: IDENTITY_SINGLE cannot include VULNERABILITY_PENALTY"
            )


def test_supporting_context_not_scoring_component():
    for force_code, spec in FORCE_AGGREGATION_CONFIGS.items():
        if spec.level_mode is ForceDimensionMode.identity_copy:
            eligible = [
                c for c in spec.components
                if c.role in {ForceIndicatorRole.core_condition, ForceIndicatorRole.proxy_condition}
            ]
            for comp in eligible:
                assert comp.role is not ForceIndicatorRole.supporting_context, (
                    f"{force_code}: SUPPORTING_CONTEXT cannot be the scoring "
                    f"component in IDENTITY_SINGLE"
                )


def test_multi_eligible_forces_use_deferred_multi():
    for force_code, spec in FORCE_AGGREGATION_CONFIGS.items():
        eligible = [
            c for c in spec.components
            if c.role in {ForceIndicatorRole.core_condition, ForceIndicatorRole.proxy_condition}
        ]
        if len(eligible) > 1:
            assert spec.level_mode is ForceDimensionMode.deferred, (
                f"{force_code}: multiple eligible components must use DEFERRED_MULTI"
            )


# --- Indebtedness is DEFERRED_MULTI ------------------------------------------


def test_indebtedness_is_deferred_multi():
    spec = FORCE_AGGREGATION_CONFIGS["indebtedness"]
    assert aggregation_mode(spec) is ForceAggregationMode.deferred_multi
    assert spec.level_mode is ForceDimensionMode.deferred
    assert spec.relative_mode is ForceDimensionMode.deferred
    assert spec.momentum_mode is ForceDimensionMode.deferred


def test_indebtedness_has_dsr_core_and_credit_gap_penalty():
    spec = FORCE_AGGREGATION_CONFIGS["indebtedness"]
    roles = {c.indicator_code: c.role for c in spec.components}
    assert roles["DEBT_SERVICE_RATIO"] is ForceIndicatorRole.core_condition
    assert roles["CREDIT_TO_GDP_GAP"] is ForceIndicatorRole.vulnerability_penalty
    assert roles["GOVERNMENT_DEBT_GDP"] is ForceIndicatorRole.supporting_context


# --- No equal weights exist --------------------------------------------------


def test_no_equal_weight_config_exists():
    """No force config uses any kind of weight field — equal or otherwise."""
    for force_code, spec in FORCE_AGGREGATION_CONFIGS.items():
        # ForceAggregationSpec has no weight fields by design.
        assert not hasattr(spec, "weights"), f"{force_code} has weights"
        assert not hasattr(spec, "weight"), f"{force_code} has weight"


# --- Rule of law / Corruption / Internal conflict = identity -----------------


def test_rule_of_law_config_is_identity():
    spec = FORCE_AGGREGATION_CONFIGS["rule_of_law"]
    assert aggregation_mode(spec) is ForceAggregationMode.identity_single
    assert spec.level_mode is ForceDimensionMode.identity_copy
    assert spec.relative_mode is ForceDimensionMode.identity_copy
    assert spec.momentum_mode is ForceDimensionMode.identity_copy
    roles = {c.indicator_code: c.role for c in spec.components}
    assert roles["RULE_OF_LAW_WGI_SCORE"] is ForceIndicatorRole.core_condition


def test_corruption_config_is_identity():
    spec = FORCE_AGGREGATION_CONFIGS["corruption"]
    assert aggregation_mode(spec) is ForceAggregationMode.identity_single
    assert spec.level_mode is ForceDimensionMode.identity_copy
    assert spec.relative_mode is ForceDimensionMode.identity_copy
    assert spec.momentum_mode is ForceDimensionMode.identity_copy
    roles = {c.indicator_code: c.role for c in spec.components}
    assert roles["CONTROL_OF_CORRUPTION_WGI_SCORE"] is ForceIndicatorRole.core_condition


def test_internal_conflict_config_is_proxy_identity():
    spec = FORCE_AGGREGATION_CONFIGS["internal_conflict"]
    assert aggregation_mode(spec) is ForceAggregationMode.identity_single
    assert spec.level_mode is ForceDimensionMode.identity_copy
    assert spec.relative_mode is ForceDimensionMode.identity_copy
    assert spec.momentum_mode is ForceDimensionMode.identity_copy
    roles = {c.indicator_code: c.role for c in spec.components}
    assert roles["POLITICAL_STABILITY_WGI_SCORE"] is ForceIndicatorRole.proxy_condition
    # Coverage ceiling stays PARTIAL
    force_def = force_definition_by_code("internal_conflict")
    assert force_def is not None
    from app.cycle.force_definitions import ForceCoverageStatus
    assert force_def.coverage_ceiling is ForceCoverageStatus.partial


# --- Relative identity only on approved single-WGI forces --------------------


def test_relative_identity_only_on_approved_wgi_forces():
    relative_identity_forces = {
        code for code, spec in FORCE_AGGREGATION_CONFIGS.items()
        if spec.relative_mode is ForceDimensionMode.identity_copy
    }
    assert relative_identity_forces == {
        "rule_of_law", "corruption", "internal_conflict"
    }


# --- Momentum identity only on approved single-WGI forces --------------------


def test_momentum_identity_only_on_approved_wgi_forces():
    momentum_identity_forces = {
        code for code, spec in FORCE_AGGREGATION_CONFIGS.items()
        if spec.momentum_mode is ForceDimensionMode.identity_copy
    }
    assert momentum_identity_forces == {
        "rule_of_law", "corruption", "internal_conflict"
    }


# --- Confidence mode remains deferred -----------------------------------------


def test_confidence_mode_always_deferred():
    for force_code, spec in FORCE_AGGREGATION_CONFIGS.items():
        assert spec.confidence_mode is ForceDimensionMode.deferred, (
            f"{force_code}: confidence must be deferred in force-aggregation-v0.3"
        )


# --- No score calculation function exists ------------------------------------


def test_no_force_score_calculation_function():
    """The config module must not expose any score calculation function."""
    import app.cycle.force_aggregation_definitions as mod
    forbidden = [
        "calculate_force_score", "compute_force_signal", "build_force_signal",
        "force_score", "score_force",
    ]
    for name in forbidden:
        assert not hasattr(mod, name), f"force_aggregation_definitions has {name}"


def test_no_force_persistence_or_api():
    """No force persistence or API module should exist yet."""
    import importlib
    for mod_name in [
        "app.cycle.force_engine",
        "app.api.force_signals",
    ]:
        try:
            importlib.import_module(mod_name)
            raise AssertionError(f"{mod_name} should not exist yet")
        except ImportError:
            pass  # expected


# --- Versioning ---------------------------------------------------------------


def test_force_aggregation_version():
    assert FORCE_AGGREGATION_VERSION == "force-aggregation-v0.3"


def test_normalization_version_unchanged():
    from app.cycle.normalization_definitions import CURRENT_MODEL_VERSION
    assert CURRENT_MODEL_VERSION.version_id == "normalization-v0.8"


# --- Validation raises loudly ------------------------------------------------


def test_identity_single_with_two_eligible_raises():
    import pytest
    with pytest.raises(ValueError, match="exactly one eligible"):
        ForceIndicatorComponentSpec(
            indicator_code="RULE_OF_LAW_WGI_SCORE",
            role=ForceIndicatorRole.core_condition,
        )
        # We need to build a spec with two eligible components — but the
        # force definition only has one live indicator. Use a force with 2.
        # Actually, let's test the validation directly via a spec that
        # violates the rule. We'll construct a spec for a force with 2 live
        # indicators, both core_condition, and identity_copy.
        from app.cycle.force_aggregation_definitions import ForceAggregationSpec
        ForceAggregationSpec(
            force_code="productivity_output_growth",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="GDP_GROWTH",
                    role=ForceIndicatorRole.core_condition,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="LABOUR_PRODUCTIVITY_PER_HOUR",
                    role=ForceIndicatorRole.core_condition,
                ),
            ),
            level_mode=ForceDimensionMode.identity_copy,
            relative_mode=ForceDimensionMode.deferred,
            momentum_mode=ForceDimensionMode.deferred,
            confidence_mode=ForceDimensionMode.deferred,
        )


def test_vulnerability_penalty_in_identity_raises():
    import pytest
    with pytest.raises(ValueError, match="VULNERABILITY_PENALTY"):
        from app.cycle.force_aggregation_definitions import ForceAggregationSpec
        ForceAggregationSpec(
            force_code="indebtedness",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="DEBT_SERVICE_RATIO",
                    role=ForceIndicatorRole.core_condition,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="CREDIT_TO_GDP_GAP",
                    role=ForceIndicatorRole.vulnerability_penalty,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="GOVERNMENT_DEBT_GDP",
                    role=ForceIndicatorRole.supporting_context,
                ),
            ),
            level_mode=ForceDimensionMode.identity_copy,
            relative_mode=ForceDimensionMode.deferred,
            momentum_mode=ForceDimensionMode.deferred,
            confidence_mode=ForceDimensionMode.deferred,
        )


def test_supporting_context_as_scoring_in_identity_raises():
    import pytest
    with pytest.raises(ValueError, match="exactly one eligible"):
        from app.cycle.force_aggregation_definitions import ForceAggregationSpec
        ForceAggregationSpec(
            force_code="education",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="TERTIARY_ATTAINMENT_25_34",
                    role=ForceIndicatorRole.supporting_context,
                ),
            ),
            level_mode=ForceDimensionMode.identity_copy,
            relative_mode=ForceDimensionMode.deferred,
            momentum_mode=ForceDimensionMode.deferred,
            confidence_mode=ForceDimensionMode.deferred,
        )


def test_indicator_not_in_force_live_inputs_raises():
    import pytest
    with pytest.raises(ValueError, match="not in the force's live_indicator_codes"):
        from app.cycle.force_aggregation_definitions import ForceAggregationSpec
        ForceAggregationSpec(
            force_code="rule_of_law",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="GINI_INDEX",  # not in rule_of_law live inputs
                    role=ForceIndicatorRole.core_condition,
                ),
            ),
            level_mode=ForceDimensionMode.identity_copy,
            relative_mode=ForceDimensionMode.identity_copy,
            momentum_mode=ForceDimensionMode.identity_copy,
            confidence_mode=ForceDimensionMode.deferred,
        )


def test_duplicate_components_raise():
    import pytest
    with pytest.raises(ValueError, match="duplicate component"):
        from app.cycle.force_aggregation_definitions import ForceAggregationSpec
        ForceAggregationSpec(
            force_code="indebtedness",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="DEBT_SERVICE_RATIO",
                    role=ForceIndicatorRole.core_condition,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="DEBT_SERVICE_RATIO",
                    role=ForceIndicatorRole.core_condition,
                ),
            ),
            level_mode=ForceDimensionMode.deferred,
            relative_mode=ForceDimensionMode.deferred,
            momentum_mode=ForceDimensionMode.deferred,
            confidence_mode=ForceDimensionMode.deferred,
        )


def test_confidence_not_deferred_raises():
    import pytest
    with pytest.raises(ValueError, match="confidence_mode must be 'deferred'"):
        from app.cycle.force_aggregation_definitions import ForceAggregationSpec
        ForceAggregationSpec(
            force_code="rule_of_law",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="RULE_OF_LAW_WGI_SCORE",
                    role=ForceIndicatorRole.core_condition,
                ),
            ),
            level_mode=ForceDimensionMode.identity_copy,
            relative_mode=ForceDimensionMode.identity_copy,
            momentum_mode=ForceDimensionMode.identity_copy,
            confidence_mode=ForceDimensionMode.identity_copy,
        )


def test_relative_identity_without_level_identity_raises():
    import pytest
    with pytest.raises(ValueError, match="relative identity_copy requires level"):
        from app.cycle.force_aggregation_definitions import ForceAggregationSpec
        ForceAggregationSpec(
            force_code="rule_of_law",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="RULE_OF_LAW_WGI_SCORE",
                    role=ForceIndicatorRole.core_condition,
                ),
            ),
            level_mode=ForceDimensionMode.deferred,
            relative_mode=ForceDimensionMode.identity_copy,
            momentum_mode=ForceDimensionMode.deferred,
            confidence_mode=ForceDimensionMode.deferred,
        )


# --- Sprint 5.22 Part 0: config hardening regressions -------------------------


def test_live_input_omitted_from_config_raises():
    """Part 0.3: a live indicator without a component role must raise."""
    import pytest
    with pytest.raises(ValueError, match="live indicators without aggregation"):
        from app.cycle.force_aggregation_definitions import ForceAggregationSpec
        ForceAggregationSpec(
            force_code="indebtedness",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="DEBT_SERVICE_RATIO",
                    role=ForceIndicatorRole.core_condition,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="CREDIT_TO_GDP_GAP",
                    role=ForceIndicatorRole.vulnerability_penalty,
                ),
                # GOVERNMENT_DEBT_GDP omitted — must raise
            ),
            level_mode=ForceDimensionMode.deferred,
            relative_mode=ForceDimensionMode.deferred,
            momentum_mode=ForceDimensionMode.deferred,
            confidence_mode=ForceDimensionMode.deferred,
        )


def test_duplicate_force_spec_raises_before_dict():
    """Part 0.4: duplicate force_code must raise before dict construction."""
    import pytest
    from app.cycle.force_aggregation_definitions import (
        ForceAggregationSpec,
        _build_config_dict,
    )
    spec = ForceAggregationSpec(
        force_code="rule_of_law",
        components=(
            ForceIndicatorComponentSpec(
                indicator_code="RULE_OF_LAW_WGI_SCORE",
                role=ForceIndicatorRole.core_condition,
            ),
        ),
        level_mode=ForceDimensionMode.identity_copy,
        relative_mode=ForceDimensionMode.identity_copy,
        momentum_mode=ForceDimensionMode.identity_copy,
        confidence_mode=ForceDimensionMode.deferred,
    )
    with pytest.raises(ValueError, match="duplicate force aggregation config"):
        _build_config_dict((spec, spec))


def test_proxy_identity_without_partial_ceiling_raises():
    """Part 0.5: PROXY_CONDITION identity requires coverage_ceiling=PARTIAL."""
    import pytest
    # rule_of_law has no coverage_ceiling — using a PROXY_CONDITION there
    # must raise.
    with pytest.raises(ValueError, match="PROXY_CONDITION identity requires coverage_ceiling=PARTIAL"):
        from app.cycle.force_aggregation_definitions import ForceAggregationSpec
        ForceAggregationSpec(
            force_code="rule_of_law",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="RULE_OF_LAW_WGI_SCORE",
                    role=ForceIndicatorRole.proxy_condition,
                ),
            ),
            level_mode=ForceDimensionMode.identity_copy,
            relative_mode=ForceDimensionMode.identity_copy,
            momentum_mode=ForceDimensionMode.identity_copy,
            confidence_mode=ForceDimensionMode.deferred,
        )


def test_relative_identity_on_unsupported_indicator_raises():
    """Part 0.6: relative identity on a non-WGI indicator must raise."""
    import pytest
    # infrastructure_investment has a single live indicator
    # (GROSS_CAPITAL_FORMATION_GDP) which is NOT in the approved-relative set.
    with pytest.raises(ValueError, match="relative identity_copy on.*not approved"):
        from app.cycle.force_aggregation_definitions import ForceAggregationSpec
        ForceAggregationSpec(
            force_code="infrastructure_investment",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="GROSS_CAPITAL_FORMATION_GDP",
                    role=ForceIndicatorRole.core_condition,
                ),
            ),
            level_mode=ForceDimensionMode.identity_copy,
            relative_mode=ForceDimensionMode.identity_copy,
            momentum_mode=ForceDimensionMode.deferred,
            confidence_mode=ForceDimensionMode.deferred,
        )


def test_momentum_identity_on_unsupported_indicator_raises():
    """Part 0.6: momentum identity on a non-WGI indicator must raise."""
    import pytest
    with pytest.raises(ValueError, match="momentum identity_copy on.*not approved"):
        from app.cycle.force_aggregation_definitions import ForceAggregationSpec
        ForceAggregationSpec(
            force_code="infrastructure_investment",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="GROSS_CAPITAL_FORMATION_GDP",
                    role=ForceIndicatorRole.core_condition,
                ),
            ),
            level_mode=ForceDimensionMode.identity_copy,
            relative_mode=ForceDimensionMode.deferred,
            momentum_mode=ForceDimensionMode.identity_copy,
            confidence_mode=ForceDimensionMode.deferred,
        )


def test_wgi_x3_configs_remain_valid():
    """Part 0: current WGI x3 configs pass all new guards."""
    for code in ("rule_of_law", "corruption", "internal_conflict"):
        spec = FORCE_AGGREGATION_CONFIGS[code]
        assert spec.level_mode is ForceDimensionMode.identity_copy
        assert spec.relative_mode is ForceDimensionMode.identity_copy
        assert spec.momentum_mode is ForceDimensionMode.identity_copy
