"""Composite-model correctness diagnostics.

These helpers distinguish configured model eligibility, semantic eligibility
and actual inclusion in a calculated result. They are pure functions so the
research exporter, API and tests share the same interpretation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.research.composite import COMPOSITE_MODELS, CompositeResult
from app.research.semantics import (
    FORCE_DOMAINS,
    FORCE_LEVEL_SEMANTICS,
    OVERLAP_GROUPS,
    level_compatibility,
)


@dataclass(frozen=True)
class ResultComparison:
    comparisons: int
    exact_score_matches: int
    near_score_matches: int
    exact_stage_matches: int
    identical_value_presence: int
    max_abs_score_difference: float | None
    exact_score_share: float
    near_score_share: float
    exact_stage_share: float

    @property
    def equivalent(self) -> bool:
        return (
            self.comparisons > 0
            and self.exact_score_matches == self.comparisons
            and self.exact_stage_matches == self.comparisons
            and self.identical_value_presence == self.comparisons
        )

    @property
    def materially_equivalent(self) -> bool:
        """Same values/stages within numeric tolerance across the full history."""
        return (
            self.comparisons > 0
            and self.near_score_matches == self.comparisons
            and self.exact_stage_matches == self.comparisons
            and self.identical_value_presence == self.comparisons
        )


def semantic_force_matrix(model_id: str) -> list[dict[str, Any]]:
    """Configured/semantic eligibility for one composite model."""
    spec = COMPOSITE_MODELS[model_id]
    rows = []
    for force_code in sorted(spec.eligible_forces):
        semantic_ok, reason = level_compatibility(force_code)
        sem = FORCE_LEVEL_SEMANTICS.get(force_code)
        rows.append(
            {
                "model_id": model_id,
                "force_code": force_code,
                "configured_candidate": True,
                "semantics": sem.value if sem else None,
                "semantically_eligible": semantic_ok,
                "semantic_reason": reason,
                "domain": FORCE_DOMAINS.get(force_code),
                "overlap_groups": [
                    "+".join(group) for group in OVERLAP_GROUPS if force_code in group
                ],
            }
        )
    return rows


def all_semantic_force_matrices() -> list[dict[str, Any]]:
    return [
        row
        for model_id in COMPOSITE_MODELS
        for row in semantic_force_matrix(model_id)
    ]


def actual_force_inclusion(result: CompositeResult) -> list[dict[str, Any]]:
    """Actual contribution status for one calculated result."""
    rows = []
    for contribution in result.contributions:
        rows.append(
            {
                "model_id": result.model_id,
                "country": result.country_iso3,
                "period": result.scoring_period,
                "force_code": contribution.force_code,
                "status": "included",
                "value": contribution.value,
                "weight": contribution.weight,
                "reason": None,
            }
        )
    for force_code in result.missing_forces:
        rows.append(
            {
                "model_id": result.model_id,
                "country": result.country_iso3,
                "period": result.scoring_period,
                "force_code": force_code,
                "status": "missing",
                "value": None,
                "weight": None,
                "reason": "no scored force level at period",
            }
        )
    for item in result.excluded_forces:
        force_code, _, reason = str(item).partition(": ")
        rows.append(
            {
                "model_id": result.model_id,
                "country": result.country_iso3,
                "period": result.scoring_period,
                "force_code": force_code,
                "status": "semantically_excluded",
                "value": None,
                "weight": None,
                "reason": reason or "excluded",
            }
        )
    return rows


def compare_result_histories(
    left: Iterable[dict[str, Any]],
    right: Iterable[dict[str, Any]],
    *,
    tolerance: float = 1e-9,
) -> ResultComparison:
    """Compare same-key score/stage histories from two core payloads.

    Expected row shape is `country`, `period`, `score`, `stage`. Missing rows
    are paired by key; null-vs-null counts as identical value presence, while
    null-vs-value does not.
    """
    left_map = {(r["country"], r["period"]): r for r in left}
    right_map = {(r["country"], r["period"]): r for r in right}
    keys = sorted(left_map.keys() & right_map.keys())
    exact = near = stage = presence = 0
    max_diff: float | None = None
    for key in keys:
        a = left_map[key]
        b = right_map[key]
        if a.get("stage") == b.get("stage"):
            stage += 1
        av = a.get("score")
        bv = b.get("score")
        if av is None and bv is None:
            presence += 1
            exact += 1
            near += 1
            continue
        if av is None or bv is None:
            continue
        presence += 1
        diff = abs(float(av) - float(bv))
        max_diff = diff if max_diff is None else max(max_diff, diff)
        if diff == 0:
            exact += 1
        if diff <= tolerance:
            near += 1
    n = len(keys)
    return ResultComparison(
        comparisons=n,
        exact_score_matches=exact,
        near_score_matches=near,
        exact_stage_matches=stage,
        identical_value_presence=presence,
        max_abs_score_difference=max_diff,
        exact_score_share=exact / n if n else 0.0,
        near_score_share=near / n if n else 0.0,
        exact_stage_share=stage / n if n else 0.0,
    )


def compare_core_histories(
    left_core: dict[str, Any],
    right_core: dict[str, Any],
    *,
    tolerance: float = 1e-9,
) -> ResultComparison:
    """Compare all country/period histories between two core payloads."""
    def rows(core: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "country": c["iso3"],
                "period": p["period"],
                "score": p["score"],
                "stage": p["stage"],
            }
            for c in core.get("countries", [])
            for p in c.get("history", [])
        ]

    return compare_result_histories(
        rows(left_core), rows(right_core), tolerance=tolerance
    )
