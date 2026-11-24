"""Mission 2 research-layer tests: methodology registry isolation, composite
engine gates, cycle classifier hysteresis/missing-data, API contracts."""
import pytest

from app.cycle.force_signal import ForceSignal
from app.research.composite import (
    COMPOSITE_MODELS,
    run_composite,
)
from app.research.cycle import CycleModelConfig, Stage, classify_series
from app.research.methodology_registry import (
    METHODOLOGY_REGISTRY,
    MethodologyState,
    MethodDescriptor,
    approved_methods,
    register_experimental,
)
from app.research.semantics import level_compatibility


def _sig(force: str, level: float | None) -> ForceSignal:
    from app.cycle.force_definitions import ForceCoverageStatus
    return ForceSignal(
        country_iso3="USA", force_code=force, scoring_period="2025-Q4",
        level_score=level,
        coverage_status=(ForceCoverageStatus.available
                         if level is not None else ForceCoverageStatus.missing),
    )


# --- Methodology registry ----------------------------------------------------


def test_approved_methods_have_approval_decisions():
    for m in approved_methods():
        assert m.approval_decision, m.method_id


def test_no_experimental_method_in_production_registry_state():
    # APPROVED_PRODUCTION construction without a decision must fail.
    with pytest.raises(ValueError):
        MethodDescriptor(
            method_id="bad", force_code="x", formula_id="f", version="v1",
            state=MethodologyState.approved_production, dimension="level",
            inputs=(), interpretation="n/a",
        )


def test_runtime_registration_cannot_create_production():
    d = MethodDescriptor(
        method_id="exp.test", force_code="x", formula_id="f", version="v1",
        state=MethodologyState.approved_production, dimension="level",
        inputs=(), interpretation="n/a",
        approval_decision="fake",
    )
    with pytest.raises(ValueError):
        register_experimental(d)
    assert "exp.test" not in METHODOLOGY_REGISTRY


def test_every_scored_force_has_approved_method():
    for code in ("rule_of_law", "corruption", "internal_conflict",
                 "leadership_capabilities", "education", "indebtedness",
                 "wealth_opportunity_values_gaps", "productivity_output_growth",
                 "character_determination"):
        assert any(m.force_code == code for m in approved_methods()), code


# --- Semantics / compatibility ------------------------------------------------


def test_indebtedness_level_not_composable():
    ok, reason = level_compatibility("indebtedness")
    assert not ok and "own_history" in reason


def test_military_has_no_level_dimension():
    ok, _ = level_compatibility("military_strength")
    assert not ok


# --- Composite engine ----------------------------------------------------------


def _all_signals(levels: dict[str, float | None]) -> dict[str, ForceSignal]:
    return {f: _sig(f, v) for f, v in levels.items()}


FULL = {
    "rule_of_law": 80.0, "corruption": 70.0, "internal_conflict": 60.0,
    "leadership_capabilities": 75.0, "education": 50.0,
    "wealth_opportunity_values_gaps": 40.0, "indebtedness": 65.0,
    "productivity_output_growth": 90.0, "character_determination": 55.0,
}


def test_model_a_equal_uses_all_compatible():
    res = run_composite("model_a_equal", _all_signals(FULL), "USA", "2025-Q4")
    assert res.methodology_status == "experimental"
    # indebtedness excluded by semantics, others weighted equally
    assert "indebtedness" not in res.included_forces
    assert len(res.included_forces) == 8
    expected = sum(v for k, v in FULL.items() if k != "indebtedness") / 8
    assert res.score == pytest.approx(expected)
    assert res.backtest_safe is False


def test_model_b_domain_balances_governance_cluster():
    res = run_composite("model_b_domain", _all_signals(FULL), "USA", "2025-Q4")
    # institutional domain = 4 forces but only 1/N_domains of total weight
    inst = {f: w for f, w in res.weights.items()
            if f in ("rule_of_law", "corruption", "internal_conflict",
                     "leadership_capabilities")}
    assert len(inst) == 4
    total_inst = sum(inst.values())
    assert total_inst == pytest.approx(1 / 4)  # 1 of 4 populated domains


def test_model_d_strict_missing_returns_none():
    levels = dict(FULL)
    levels["corruption"] = None
    res = run_composite("model_d_comparable", _all_signals(levels),
                        "USA", "2025-Q4")
    assert res.score is None
    assert "corruption" in res.missing_forces
    assert any("not comparable" in w for w in res.warnings)


def test_model_a_min_coverage_gate():
    levels = {k: None for k in FULL}
    levels["rule_of_law"] = 80.0
    res = run_composite("model_a_equal", _all_signals(levels), "USA", "2025-Q4")
    assert res.score is None  # 1/9 < min_coverage 0.5


def test_composite_deterministic():
    a = run_composite("model_a_equal", _all_signals(FULL), "USA", "2025-Q4")
    b = run_composite("model_a_equal", _all_signals(FULL), "USA", "2025-Q4")
    assert a == b


# --- Cycle classifier ----------------------------------------------------------


def _series(scores):
    return [(f"{2000 + i}-Q4", s) for i, s in enumerate(scores)]


def test_classifier_requires_min_observations():
    res = classify_series("USA", _series([50.0] * 5))
    assert all(p.stage is None for p in res.points)
    assert res.warnings


def test_classifier_rise_then_decline_with_hysteresis():
    scores = [40.0 + i for i in range(15)]          # rising 40→54
    scores += [54.0 - i for i in range(15)]         # falling 54→40
    res = classify_series("USA", _series(scores))
    stages = [p.stage for p in res.points]
    assert stages[3] in (Stage.rise, Stage.early_rise)
    assert stages[-1] in (Stage.decline, Stage.early_decline,
                          Stage.reset)
    # transitions exist and are sparse (hysteresis prevents flapping)
    assert 1 < len(res.transitions) < 10


def test_classifier_missing_gaps_unclassified():
    scores = [50.0] * 20
    scores[10] = None
    res = classify_series("USA", _series(scores))
    assert res.points[10].stage is None
    assert res.points[10].reason == "missing score"
    assert res.points[9].stage is not None


def test_classifier_single_period_flip_suppressed():
    scores = [50.0] * 16
    scores[8] = 80.0  # one-period spike
    res = classify_series("USA", _series(scores))
    # a 1-period excursion must NOT flip the stage (persist=2)
    stages_at = [p.stage for p in res.points]
    assert stages_at[7] == stages_at[9]


def test_classifier_experimental_label():
    res = classify_series("USA", _series([50.0] * 20))
    assert res.methodology_status == "experimental"
    assert res.backtest_safe is False


# --- Research API contracts -----------------------------------------------------


async def test_research_models_endpoint(client):
    r = await client.get("/api/research/models")
    assert r.status_code == 200
    body = r.json()
    assert {m["model_id"] for m in body} == set(COMPOSITE_MODELS)
    assert all(m["methodology_status"] == "experimental" for m in body)


async def test_research_progress_matches_registry(client):
    r = await client.get("/api/research/progress")
    assert r.status_code == 200
    body = r.json()
    assert len(body["forces"]) == 17
    # counts must equal force list length
    assert sum(body["counts"].values()) == 17
    # no scored-level force may lack an approved method
    for f in body["forces"]:
        if f["implementation_status"] in ("approved_level", "partial"):
            assert f["methods"], f["force_code"]


async def test_research_cycle_unknown_model_rejected(client):
    r = await client.get("/api/research/countries/USA/cycle?model=evil")
    assert r.status_code == 422


async def test_research_methods_state_filter(client):
    r = await client.get("/api/research/methods?state=experimental")
    assert r.status_code == 200
    r = await client.get("/api/research/methods?state=bogus")
    assert r.status_code == 422


async def test_experimental_never_in_force_scores_contract(client):
    """Regression: the approved force-score endpoint must not surface any
    experimental/composite numbers."""
    r = await client.get("/api/countries/USA/force-scores")
    assert r.status_code == 200
    body = r.json()
    assert "composite" not in body
    assert all(f.get("model_version", "").startswith("force-aggregation")
               for f in body["forces"])
