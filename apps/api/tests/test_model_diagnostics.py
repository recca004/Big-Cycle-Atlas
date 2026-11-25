from app.research.composite import CompositeResult, ForceContribution, run_composite
from app.research.model_diagnostics import (
    actual_force_inclusion,
    compare_core_histories,
    semantic_force_matrix,
)
from app.cycle.force_signal import ForceSignal


def _core(score: float) -> dict:
    return {
        "countries": [
            {
                "iso3": "USA",
                "history": [
                    {
                        "period": "2024-Q4",
                        "score": score,
                        "stage": "Rise",
                    }
                ],
            }
        ]
    }


def test_material_equivalence_uses_numeric_tolerance_for_identical_models():
    comparison = compare_core_histories(_core(50.0), _core(50.0 + 1e-14))

    assert comparison.comparisons == 1
    assert comparison.exact_score_matches == 0
    assert comparison.near_score_matches == 1
    assert comparison.exact_stage_matches == 1
    assert not comparison.equivalent
    assert comparison.materially_equivalent


def test_indebtedness_is_configured_but_not_included_in_level_composites():
    matrix = semantic_force_matrix("model_a_equal")
    row = next(r for r in matrix if r["force_code"] == "indebtedness")

    assert row["configured_candidate"] is True
    assert row["semantics"] == "own_history_condition"
    assert row["semantically_eligible"] is False


def test_actual_force_inclusion_reports_semantic_exclusion():
    result = CompositeResult(
        model_id="test",
        model_version="v1",
        methodology_status="experimental",
        country_iso3="USA",
        scoring_period="2024-Q4",
        score=60.0,
        included_forces=("rule_of_law",),
        excluded_forces=("indebtedness: own-history condition",),
        missing_forces=(),
        weights={"rule_of_law": 1.0},
        coverage_ratio=1.0,
        contributions=(ForceContribution("rule_of_law", 60.0, 1.0, True),),
    )

    rows = actual_force_inclusion(result)
    indebtedness = next(r for r in rows if r["force_code"] == "indebtedness")

    assert indebtedness["status"] == "semantically_excluded"
    assert "own-history" in indebtedness["reason"]


def test_run_composite_excludes_indebtedness_without_dropping_scored_forces():
    signals = {
        force_code: ForceSignal(
            country_iso3="USA",
            force_code=force_code,
            scoring_period="2024-Q4",
            level_score=70.0,
        )
        for force_code in (
            "rule_of_law", "corruption", "internal_conflict",
            "leadership_capabilities",
        )
    }
    signals["indebtedness"] = ForceSignal(
        country_iso3="USA",
        force_code="indebtedness",
        scoring_period="2024-Q4",
        level_score=80.0,
    )

    result = run_composite("model_a_equal", signals, "USA", "2024-Q4")

    assert result.score == 70.0
    assert "rule_of_law" in result.included_forces
    assert "indebtedness" not in result.included_forces
    assert any("indebtedness" in item for item in result.excluded_forces)
