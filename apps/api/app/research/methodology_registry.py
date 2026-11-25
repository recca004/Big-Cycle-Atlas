"""Methodology registry — Mission 2 §7.

Every calculation method (production or experimental) is declared here with
an explicit state. The registry is the authoritative inventory used by:

- the force-progress metadata endpoint (§22),
- the research API (§17),
- the experimental-isolation tests (a method in a non-APPROVED state can
  never appear in the approved force-score pipeline).

States
------
APPROVED_PRODUCTION — may execute in the approved force-score pipeline.
VALIDATED_CANDIDATE — validated research artefact, not yet approved.
EXPERIMENTAL        — inspectable research method, never in production views.
CONTEXT_ONLY        — real data + documentation, no numerical score intended.
DEFERRED            — method exists in concept only; execution deferred.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MethodologyState(str, Enum):
    approved_production = "approved_production"
    validated_candidate = "validated_candidate"
    experimental = "experimental"
    context_only = "context_only"
    deferred = "deferred"


@dataclass(frozen=True)
class MethodDescriptor:
    """One declared calculation method. All fields are documentation-by-
    construction: a method cannot be registered without stating its
    semantics, inputs, and limitations."""

    method_id: str                 # stable identifier, e.g. "prod.rule_of_law.wgi_identity_v1"
    force_code: str                # force this method serves
    formula_id: str                # e.g. "identity_copy", "reference_percentile_midrank"
    version: str                   # method version, independent of model versions
    state: MethodologyState
    dimension: str                 # "level" | "relative" | "momentum" | "composite" | "classification"
    inputs: tuple[str, ...]        # indicator codes consumed
    interpretation: str            # what the number MEANS
    parameters: dict = field(default_factory=dict)
    reference_universe: str | None = None
    units: str = "score_0_100"
    missing_data_rule: str = "explicit_null"   # never zero-fill
    freshness_rule: str | None = None
    coverage_ceiling: str | None = None
    validation_artifacts: tuple[str, ...] = ()
    approval_decision: str | None = None       # e.g. "DEC-042 Option A"
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.state is MethodologyState.approved_production and not self.approval_decision:
            raise ValueError(
                f"{self.method_id}: APPROVED_PRODUCTION requires an "
                "approval_decision (owner ratification or recorded delegated "
                "working-model approval)"
            )


# --- The registry -------------------------------------------------------------

_ENTRIES: tuple[MethodDescriptor, ...] = (
    # -- Approved production methods (mirror of force_aggregation_definitions) --
    MethodDescriptor(
        method_id="prod.rule_of_law.wgi_identity_v1",
        force_code="rule_of_law", formula_id="identity_copy",
        version="v1", state=MethodologyState.approved_production,
        dimension="level", inputs=("RULE_OF_LAW_WGI_SCORE",),
        interpretation="Absolute WGI Rule-of-Law governance score (0-100)",
        freshness_rule="annual, max_age=2",
        approval_decision="DEC-019 lineage (Sprint 5.x)",
        limitations=("Perception composite with source uncertainty",),
    ),
    MethodDescriptor(
        method_id="prod.corruption.wgi_identity_v1",
        force_code="corruption", formula_id="identity_copy",
        version="v1", state=MethodologyState.approved_production,
        dimension="level", inputs=("CONTROL_OF_CORRUPTION_WGI_SCORE",),
        interpretation="Absolute WGI Control-of-Corruption score (0-100)",
        freshness_rule="annual, max_age=2",
        approval_decision="DEC-019 lineage (Sprint 5.x)",
        limitations=("Perception composite with source uncertainty",),
    ),
    MethodDescriptor(
        method_id="prod.internal_conflict.wgi_ps_v1",
        force_code="internal_conflict", formula_id="identity_copy",
        version="v1", state=MethodologyState.approved_production,
        dimension="level", inputs=("POLITICAL_STABILITY_WGI_SCORE",),
        interpretation="Absolute WGI Political-Stability score (0-100); perception proxy, not event counts",
        freshness_rule="annual, max_age=2", coverage_ceiling="partial",
        approval_decision="Sprint 6.x ratification",
        limitations=("Perception proxy for conflict risk", "PARTIAL ceiling"),
    ),
    MethodDescriptor(
        method_id="prod.leadership.wgi_ge_v1",
        force_code="leadership_capabilities", formula_id="identity_copy",
        version="v1", state=MethodologyState.approved_production,
        dimension="level", inputs=("GOVERNMENT_EFFECTIVENESS_WGI_SCORE",),
        interpretation="Absolute WGI Government-Effectiveness score (0-100)",
        freshness_rule="annual, max_age=2", coverage_ceiling="partial",
        approval_decision="DEC-041 (ratified)",
        limitations=(
            "Perception composite; conceptual overlap with RL/CC forces",
            "PARTIAL ceiling",
        ),
    ),
    MethodDescriptor(
        method_id="prod.education.oecd_attainment_v1",
        force_code="education", formula_id="identity_copy",
        version="v1", state=MethodologyState.approved_production,
        dimension="level", inputs=("TERTIARY_ATTAINMENT_25_34",),
        interpretation="Tertiary attainment % of 25-34 population (bounded 0-100)",
        freshness_rule="annual", coverage_ceiling="partial",
        approval_decision="Sprint 6.4 ratification",
        limitations=("OECD-only coverage (6/8)", "attainment, not quality"),
    ),
    MethodDescriptor(
        method_id="prod.indebtedness.dsr_minus_creditgap_v1",
        force_code="indebtedness", formula_id="condition_minus_penalty",
        version="v1", state=MethodologyState.approved_production,
        dimension="level",
        inputs=("DEBT_SERVICE_RATIO", "CREDIT_TO_GDP_GAP"),
        interpretation="Own-history debt-service condition minus credit-gap stress penalty",
        parameters={"penalty_weight": 0.5},
        freshness_rule="quarterly/annual mix",
        coverage_ceiling="partial",
        approval_decision="DEC-040 (ratified)",
        limitations=("Own-history semantics — not cross-country comparable",),
    ),
    MethodDescriptor(
        method_id="prod.wealth_gaps.wid_complement_v1",
        force_code="wealth_opportunity_values_gaps",
        formula_id="complement_0_100",
        version="v1", state=MethodologyState.approved_production,
        dimension="level", inputs=("WEALTH_SHARE_TOP_10",),
        interpretation="100 - top-10% wealth share (WID)",
        freshness_rule="annual, sparse", coverage_ceiling="partial",
        approval_decision="Sprint 6.7 ratification",
        limitations=("Sparse WID coverage", "wealth only — income/consumption Gini kept distinct"),
    ),
    MethodDescriptor(
        method_id="prod.productivity.oecd_percentile_v1",
        force_code="productivity_output_growth",
        formula_id="reference_percentile_midrank",
        version="v1", state=MethodologyState.approved_production,
        dimension="level", inputs=("LABOUR_PRODUCTIVITY_PER_HOUR",),
        interpretation="Mid-rank percentile within OECD LPPH universe — OECD-relative position, NOT global percentile",
        reference_universe="oecd_lpph_v1",
        parameters={"minimum_sample_n": 20},
        freshness_rule="annual", coverage_ceiling="partial",
        approval_decision="DEC-042 Option A (approved)",
        limitations=(
            "OECD-relative only — CHN/IND unavailable, not fabricated",
            "score moves when the reference population moves",
        ),
    ),
    MethodDescriptor(
        method_id="prod.productivity.own_history_pct_momentum_v1",
        force_code="productivity_output_growth",
        formula_id="pct_change_own_history",
        version="v1", state=MethodologyState.approved_production,
        dimension="momentum", inputs=("LABOUR_PRODUCTIVITY_PER_HOUR",),
        interpretation="Own-history % change in real productivity per hour (3y/5y/10y windows, primary 5y)",
        units="percent",
        parameters={"windows": (3, 5, 10), "primary": 5, "tolerance": 1},
        approval_decision="DEC-042 Option C (approved)",
        limitations=("Signed % change — not a 0-100 score",),
    ),
    MethodDescriptor(
        method_id="prod.character.lfp_wdi_percentile_v1",
        force_code="character_determination",
        formula_id="reference_percentile_midrank",
        version="v1", state=MethodologyState.approved_production,
        dimension="level", inputs=("LABOUR_FORCE_PARTICIPATION_RATE",),
        interpretation=(
            "LFP percentile within WDI universe — RELATIVE ECONOMIC "
            "PARTICIPATION only; never a measurement of national character "
            "or determination"
        ),
        reference_universe="wdi_lfp_v1",
        parameters={"minimum_sample_n": 100},
        freshness_rule="annual", coverage_ceiling="partial",
        approval_decision="Delegated working-model approval (V1 Mission 1)",
        limitations=(
            "Narrow participation proxy — entrepreneurship/innovation unmeasured",
            "higher participation not universally positive (income effects)",
            "PARTIAL ceiling",
        ),
    ),
    MethodDescriptor(
        method_id="prod.character.lfp_pct_momentum_v1",
        force_code="character_determination",
        formula_id="pct_change_own_history",
        version="v1", state=MethodologyState.approved_production,
        dimension="momentum", inputs=("LABOUR_FORCE_PARTICIPATION_RATE",),
        interpretation="Own-history % change in labour force participation",
        units="percent",
        parameters={"windows": (3, 5), "primary": 5, "tolerance": 1},
        approval_decision="Delegated working-model approval (V1 Mission 1)",
        limitations=("Signed % change — not a 0-100 score",),
    ),
    MethodDescriptor(
        method_id="prod.military.tracked8_relative_share_v1",
        force_code="military_strength",
        formula_id="relative_share_of_universe",
        version="v1", state=MethodologyState.approved_production,
        dimension="relative", inputs=("MILITARY_EXPENDITURE_USD",),
        interpretation="Country share of tracked-8 defence expenditure — INPUT measure, never capability",
        reference_universe="tracked_8",
        approval_decision="Delegated working-model approval (V1 Mission 1)",
        limitations=(
            "Share of spending, not effectiveness (SIPRI caveat)",
            "universe is 8 tracked countries, not global",
        ),
    ),
    # -- Context-only / deferred methods for the remaining forces ---------------
    MethodDescriptor(
        method_id="ctx.cost_competitiveness.ulc_context_v1",
        force_code="cost_competitiveness", formula_id="contextual_deferred",
        version="v1", state=MethodologyState.context_only,
        dimension="level", inputs=("UNIT_LABOUR_COST_GROWTH",),
        interpretation="ULC/CPI growth as cost-competitiveness context; level method undecided (DEC-018 open)",
        approval_decision=None,
        limitations=("Level method undecided — appreciation is not automatically improvement",),
    ),
    MethodDescriptor(
        method_id="prod.cost_competitiveness.reer_momentum_v1",
        force_code="cost_competitiveness", formula_id="own_history_signed_change",
        version="v1", state=MethodologyState.approved_production,
        dimension="momentum", inputs=("REER_INDEX",),
        interpretation=("Signed 5y change in the real effective exchange rate index — "
                        "appreciation/depreciation trajectory, NOT a strength score"),
        reference_universe=None, units="index_pct_change",
        parameters={"windows": (3, 5, 10), "primary": 5},
        approval_decision="Delegated working-model approval (V1 Mission 2, REER import)",
        limitations=(
            "Direction convention: rising REER = real appreciation — not automatically weakening",
            "Momentum dimension only; no level method approved",
        ),
    ),
    MethodDescriptor(
        method_id="ctx.trade.wdi_context_v1",
        force_code="trade_capital_flows", formula_id="contextual_deferred",
        version="v1", state=MethodologyState.context_only,
        dimension="level",
        inputs=("EXPORTS_GDP", "IMPORTS_GDP", "TRADE_BALANCE",
                "CURRENT_ACCOUNT_GDP", "FDI_NET_INFLOWS_GDP"),
        interpretation="Five WDI trade/capital series as context; no parameter-free composition (DEC-039)",
        limitations=("Trade surplus is NOT automatically positive",),
    ),
    MethodDescriptor(
        method_id="ctx.openness.structural_v1",
        force_code="global_openness", formula_id="contextual_deferred",
        version="v1", state=MethodologyState.context_only,
        dimension="level",
        inputs=("EXPORTS_GDP", "IMPORTS_GDP", "TRADE_BALANCE",
                "CURRENT_ACCOUNT_GDP", "FDI_NET_INFLOWS_GDP",
                "POPULATION", "GDP_CURRENT_USD"),
        interpretation=(
            "Trade intensity (derived TRADE_OPENNESS_GDP), external balance, "
            "FDI and size context — a functioning descriptive profile, not a "
            "level score"
        ),
        limitations=(
            "Trade intensity ≠ strength (DEC-035)",
            "Covers trade/capital only — people/ideas openness unmeasured",
            "Inputs overlap trade_capital_flows deliberately",
        ),
    ),
    MethodDescriptor(
        method_id="ctx.infrastructure.gcf_v1",
        force_code="infrastructure_investment", formula_id="contextual_deferred",
        version="v1", state=MethodologyState.context_only,
        dimension="level", inputs=("GROSS_CAPITAL_FORMATION_GDP",),
        interpretation="Investment effort only — not infrastructure quality (DEC-036)",
        limitations=("LPI discontinued; no quality series imported yet",),
    ),
    MethodDescriptor(
        method_id="ctx.resource_allocation.v1",
        force_code="resource_allocation_efficiency",
        formula_id="contextual_deferred",
        version="v1", state=MethodologyState.context_only,
        dimension="level",
        inputs=("GROSS_CAPITAL_FORMATION_GDP", "GDP_GROWTH",
                "LABOUR_PRODUCTIVITY_PER_HOUR"),
        interpretation=(
            "Investment & resource-allocation context: investment effort, "
            "output growth, labour productivity — the INPUT side only"
        ),
        limitations=(
            "Investment intensity does not measure allocation efficiency",
            "Overlaps productivity/infrastructure/indebtedness inputs",
        ),
    ),
    MethodDescriptor(
        method_id="ctx.geography.structural_v1",
        force_code="geography", formula_id="structural_static_profile",
        version="v1", state=MethodologyState.context_only,
        dimension="level", inputs=(),
        interpretation="Versioned structural facts (landlocked, maritime access, area) — never time-varying",
        limitations=("Static profile, no annual score",),
    ),
    MethodDescriptor(
        method_id="ctx.acts_of_nature.v1",
        force_code="acts_of_nature", formula_id="contextual_deferred",
        version="v1", state=MethodologyState.context_only,
        dimension="level", inputs=("NATURAL_DISASTER_AFFECTED_PCT",),
        interpretation=(
            "Structural disaster-exposure context: EM-DAT-derived % of "
            "population affected by droughts/floods/extreme temperatures, "
            "1990-2009 average published via WB at a single date"
        ),
        limitations=(
            "Single multi-decadal average — no annual event series",
            "Pandemic & climate-change exposure not covered",
            "Missing ≠ zero events",
        ),
    ),
)

METHODOLOGY_REGISTRY: dict[str, MethodDescriptor] = {
    m.method_id: m for m in _ENTRIES
}


def methods_for_force(
    force_code: str,
    states: frozenset[MethodologyState] | None = None,
) -> tuple[MethodDescriptor, ...]:
    return tuple(
        m for m in _ENTRIES
        if m.force_code == force_code
        and (states is None or m.state in states)
    )


def approved_methods() -> tuple[MethodDescriptor, ...]:
    return tuple(
        m for m in _ENTRIES if m.state is MethodologyState.approved_production
    )


def register_experimental(descriptor: MethodDescriptor) -> None:
    """Add an experimental/validated-candidate method at runtime (research
    engine use). Production states are registry-source only — a runtime
    registration claiming APPROVED_PRODUCTION is rejected here AND by the
    frozen-dataclass invariant above."""
    if descriptor.state is MethodologyState.approved_production:
        raise ValueError(
            "runtime registration cannot create APPROVED_PRODUCTION methods"
        )
    METHODOLOGY_REGISTRY[descriptor.method_id] = descriptor
