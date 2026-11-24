"""Measurement semantics + force-dimension compatibility — Mission 2 §9.

A shared 0-100 range is NOT evidence of compatibility. Each scored force
dimension is classified by what the number actually MEANS; composite models
declare which semantics classes they may mix.
"""
from __future__ import annotations

from enum import Enum


class MeasurementSemantics(str, Enum):
    # Directly bounded source measure (WGI 0-100, attainment %).
    absolute_bounded = "absolute_bounded"
    # Position within a named reference universe (percentile).
    reference_relative = "reference_relative"
    # Condition vs own history (own_history level, stress transforms).
    own_history_condition = "own_history_condition"
    # Signed historical change (percent or points) — never a level.
    signed_momentum = "signed_momentum"
    # Descriptive share of a universe (military relative_share).
    descriptive_share = "descriptive_share"
    # Structural/static profile — not time-varying.
    structural_context = "structural_context"
    # Vulnerability adjustment input (credit-gap penalty).
    vulnerability_adjustment = "vulnerability_adjustment"


# Which level dimensions exist per force and what they mean.
FORCE_LEVEL_SEMANTICS: dict[str, MeasurementSemantics] = {
    "rule_of_law": MeasurementSemantics.absolute_bounded,
    "corruption": MeasurementSemantics.absolute_bounded,
    "internal_conflict": MeasurementSemantics.absolute_bounded,
    "leadership_capabilities": MeasurementSemantics.absolute_bounded,
    "education": MeasurementSemantics.absolute_bounded,
    "wealth_opportunity_values_gaps": MeasurementSemantics.absolute_bounded,
    "indebtedness": MeasurementSemantics.own_history_condition,
    "productivity_output_growth": MeasurementSemantics.reference_relative,
    "character_determination": MeasurementSemantics.reference_relative,
}

FORCE_RELATIVE_SEMANTICS: dict[str, MeasurementSemantics] = {
    "military_strength": MeasurementSemantics.descriptive_share,
}


# Compatibility: semantics classes that MAY be combined in a composite
# national-conditions score. Signed momentum and descriptive share are
# NEVER composable into a 0-100 level.
COMPOSABLE_LEVEL_SEMANTICS: frozenset[MeasurementSemantics] = frozenset(
    {
        MeasurementSemantics.absolute_bounded,
        MeasurementSemantics.reference_relative,
    }
)


def level_compatibility(force_code: str) -> tuple[bool, str]:
    """(allowed, reason) for including a force level in a 0-100 composite."""
    sem = FORCE_LEVEL_SEMANTICS.get(force_code)
    if sem is None:
        return False, "no scored level dimension"
    if sem not in COMPOSABLE_LEVEL_SEMANTICS:
        return (
            False,
            f"semantics={sem.value} not composable into a 0-100 level "
            "(own-history condition / share / structural — different "
            "measurement meaning, not just a different scale)",
        )
    return True, "compatible"


# Domain groupings for Model B (candidate grouping — §11 Model B).
FORCE_DOMAINS: dict[str, str] = {
    "rule_of_law": "institutional",
    "corruption": "institutional",
    "internal_conflict": "institutional",
    "leadership_capabilities": "institutional",
    "education": "human_capital",
    "character_determination": "human_capital",
    "productivity_output_growth": "productive_capacity",
    "infrastructure_investment": "productive_capacity",
    "resource_allocation_efficiency": "productive_capacity",
    "indebtedness": "financial_conditions",
    "wealth_opportunity_values_gaps": "financial_conditions",
    "trade_capital_flows": "international_position",
    "global_openness": "international_position",
    "cost_competitiveness": "international_position",
    "military_strength": "structural_resilience",
    "geography": "structural_resilience",
    "acts_of_nature": "structural_resilience",
}

# Conceptual overlap groups — composite models down-weight correlated
# clusters so four WGI governance forces don't dominate (§10).
OVERLAP_GROUPS: tuple[tuple[str, ...], ...] = (
    ("rule_of_law", "corruption", "internal_conflict", "leadership_capabilities"),
    ("productivity_output_growth", "resource_allocation_efficiency"),
    ("infrastructure_investment", "resource_allocation_efficiency"),
    ("trade_capital_flows", "global_openness"),
    ("indebtedness", "trade_capital_flows"),
    ("education", "character_determination"),
)
