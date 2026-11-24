"""Force aggregation configuration — Sprint 5.21 (methodology) + Sprint 5.22
(hardening) + Sprint 6.4 (Education promotion, DEC-032) + Sprint 6.7
(Wealth-gap promotion, DEC-034). Companion to .dev/FORCE_AGGREGATION.md.

This module is a typed CONFIGURATION layer. It defines:

- ForceIndicatorRole: how a mapped indicator may participate in aggregation
- ForceAggregationMode: when a force may publish a numeric signal
- ForceIndicatorComponentSpec: one indicator's role within a force
- ForceAggregationSpec: a force's aggregation configuration
- FORCE_AGGREGATION_CONFIGS: the explicit per-force approval matrix

It deliberately contains:
- NO force score computation (the executable ForceSignal lives in
  app/cycle/force_signal.py, added in Sprint 5.22)
- NO force persistence
- NO force API

Sprint 5.22 added structural hardening to this config layer:
- live-input config completeness guard (every force live input MUST have a
  component role)
- real duplicate force-config detection (tuple-first + _build_config_dict)
- proxy-condition ceiling guard (PROXY_CONDITION identity requires PARTIAL)
- dimension approval guard (relative/momentum identity_copy only on WGI x3)

Sprint 6.4 (DEC-032) promoted Education to the fourth executable force:
- Education: SUPPORTING_CONTEXT → PROXY_CONDITION; DEFERRED_MULTI →
  IDENTITY_SINGLE. Coverage stays PARTIAL. relative/momentum/confidence
  stay deferred. 4/17 forces executable; 13/17 intentionally unscored.

Sprint 6.7 (DEC-034) promoted Wealth-gap to the fifth executable force:
- WEALTH_SHARE_TOP_10: SUPPORTING_CONTEXT → PROXY_CONDITION;
  DEFERRED_MULTI → IDENTITY_SINGLE. GINI_INDEX stays
  SUPPORTING_CONTEXT (income inequality != wealth concentration; not
  averaged, not combined). Coverage stays PARTIAL.
  relative/momentum/confidence stay deferred. 5/17 forces executable;
  12/17 intentionally unscored.

Validation rules fail loudly at import time. Every one of the 17 forces is
represented explicitly — either with an approved aggregation config or with
DEFERRED_MULTI / no config (the design distinguishes approved aggregation
configs from intentionally unconfigured forces).

Versioning (FORCE_AGGREGATION.md §10):
- Indicator normalization version: normalization-v0.8 (Sprint 6.7, owned by
  app/cycle/normalization_definitions.py)
- Force aggregation version: force-aggregation-v0.4 (this module, Sprint 6.7)
"""
from dataclasses import dataclass
from enum import Enum

from app.cycle.force_definitions import (
    FORCE_DEFINITIONS,
    ForceCoverageStatus,
    force_definition_by_code,
)


# --- Enums -------------------------------------------------------------------


class ForceIndicatorRole(str, Enum):
    """How a mapped indicator may participate in force aggregation.

    CORE_CONDITION
        A normalized 0-100 condition whose direction is higher = stronger.
        Eligible for force level aggregation under an explicitly approved
        aggregation rule.

    PROXY_CONDITION
        Same numeric orientation as CORE_CONDITION, but measures only a
        narrower proxy for the conceptual force. Requires the force's
        coverage/proxy semantics to expose that incompleteness (PARTIAL
        ceiling).

    VULNERABILITY_PENALTY
        A signal representing an asymmetric vulnerability/risk component.
        Must NOT be naively averaged with CORE_CONDITION. Requires a
        force-specific composition formula before it may affect force
        level.

    SUPPORTING_CONTEXT
        Relevant raw/normalized context without approved numeric contribution
        to the force aggregate.
    """

    core_condition = "core_condition"
    proxy_condition = "proxy_condition"
    vulnerability_penalty = "vulnerability_penalty"
    supporting_context = "supporting_context"


# Roles eligible to be the single scoring component in IDENTITY_SINGLE.
IDENTITY_ELIGIBLE_ROLES: frozenset[ForceIndicatorRole] = frozenset(
    {ForceIndicatorRole.core_condition, ForceIndicatorRole.proxy_condition}
)


class ForceAggregationMode(str, Enum):
    """When a force may publish a numeric signal.

    IDENTITY_SINGLE
        The ONLY approved numeric aggregation. force.level_score =
        indicator.level_score for exactly one eligible component. No
        rescaling, no weighting, no averaging.

    DEFERRED_MULTI
        Used whenever 2+ numeric components require composition, a
        vulnerability penalty must interact with a condition score, or
        weights are unresolved. Result: force dimension = None.
    """

    identity_single = "identity_single"
    # V1 Mission 1: level deferred but relative/momentum identity_copy — a
    # type-C module publishing a dimension without an approved level.
    dimension_only = "dimension_only"
    condition_minus_penalty = "condition_minus_penalty"
    deferred_multi = "deferred_multi"


class ForceDimensionMode(str, Enum):
    """Per-dimension approval. 'deferred' means the dimension is None."""

    identity_copy = "identity_copy"
    condition_minus_penalty = "condition_minus_penalty"
    deferred = "deferred"


# --- Approved dimension capability (Sprint 5.22 Part 0.6) --------------------
#
# A config claiming relative_mode or momentum_mode = identity_copy must refer
# to an indicator whose CURRENT approved NormalizedSignal methodology
# actually supports that dimension. For force-aggregation-v0.1 this resolves
# to the WGI x3 only (DIRECT_0_100 level + CROSS_SECTIONAL_RELATIVE relative +
# OWN_HISTORY momentum). DSR has no relative/momentum; credit gap has no
# relative/momentum. This is an EXPLICIT typed mapping for v0.1 — not a
# generic cross-layer capability query (which would require redesign). If
# future sprints approve more dimensions, extend this mapping explicitly.
INDICATORS_WITH_APPROVED_RELATIVE: frozenset[str] = frozenset(
    {
        "RULE_OF_LAW_WGI_SCORE",
        "CONTROL_OF_CORRUPTION_WGI_SCORE",
        "POLITICAL_STABILITY_WGI_SCORE",
        # V1 Mission 1 (delegated): MILITARY_EXPENDITURE_USD relative_share —
        # share of tracked-8 defence expenditure (INPUT measure, SIPRI
        # caveat — never a capability score).
        "MILITARY_EXPENDITURE_USD",
    }
)

INDICATORS_WITH_APPROVED_MOMENTUM: frozenset[str] = frozenset(
    {
        "RULE_OF_LAW_WGI_SCORE",
        "CONTROL_OF_CORRUPTION_WGI_SCORE",
        "POLITICAL_STABILITY_WGI_SCORE",
        # DEC-042 Option C (V1 Mission 1, owner-approved): LPPH percent-change
        # own-history momentum — the force's momentum is the indicator's
        # signed % change, NOT a 0-100 score and NOT comparable to WGI-point
        # momentum.
        "LABOUR_PRODUCTIVITY_PER_HOUR",
        # V1 Mission 1 (delegated): LFP percent-change own-history momentum.
        "LABOUR_FORCE_PARTICIPATION_RATE",
    }
)


# --- Specs -------------------------------------------------------------------


@dataclass(frozen=True)
class ForceIndicatorComponentSpec:
    """One indicator's role within a force aggregation config.

    The indicator_code must belong to the force's live_indicator_codes
    (validated at config build time).
    """

    indicator_code: str
    role: ForceIndicatorRole


@dataclass(frozen=True)
class ForceAggregationSpec:
    """A force's aggregation configuration.

    Validation (run at module import via _validate_configs):
    - force_code must match a real ForceDefinition
    - every component's indicator_code must be in the force's
      live_indicator_codes
    - no duplicate component indicators within a force
    - IDENTITY_SINGLE requires exactly one eligible scoring component
      (CORE_CONDITION or PROXY_CONDITION) and no VULNERABILITY_PENALTY
    - VULNERABILITY_PENALTY must never be silently included in IDENTITY_SINGLE
    - SUPPORTING_CONTEXT must never contribute numerically (it may appear as
      provenance but never as the scoring component)
    - a force with multiple eligible numeric components cannot use
      IDENTITY_SINGLE
    """

    force_code: str
    components: tuple[ForceIndicatorComponentSpec, ...]
    level_mode: ForceDimensionMode
    relative_mode: ForceDimensionMode
    momentum_mode: ForceDimensionMode
    confidence_mode: ForceDimensionMode  # always 'deferred' in v0.1
    notes: str = ""

    def __post_init__(self) -> None:
        # confidence_mode is always deferred in force-aggregation-v0.4.
        if self.confidence_mode is not ForceDimensionMode.deferred:
            raise ValueError(
                f"{self.force_code}: confidence_mode must be 'deferred' in "
                f"force-aggregation-v0.4 (got {self.confidence_mode})"
            )

        # No duplicate component indicators.
        codes = [c.indicator_code for c in self.components]
        if len(set(codes)) != len(codes):
            raise ValueError(
                f"{self.force_code}: duplicate component indicators"
            )

        # Every component indicator must belong to the force's live inputs.
        force_def = force_definition_by_code(self.force_code)
        if force_def is None:
            raise ValueError(f"unknown force code: {self.force_code}")
        live = set(force_def.live_indicator_codes)
        for comp in self.components:
            if comp.indicator_code not in live:
                raise ValueError(
                    f"{self.force_code}: indicator {comp.indicator_code} is "
                    f"not in the force's live_indicator_codes"
                )

        # Part 0.3: live-input config completeness — every force live input
        # MUST have a component role. No silent omission.
        component_codes = set(codes)
        missing_live = live - component_codes
        if missing_live:
            raise ValueError(
                f"{self.force_code}: live indicators without aggregation "
                f"component roles: {sorted(missing_live)}"
            )

        eligible = [
            c for c in self.components if c.role in IDENTITY_ELIGIBLE_ROLES
        ]
        penalties = [
            c for c in self.components
            if c.role is ForceIndicatorRole.vulnerability_penalty
        ]

        if self.level_mode is ForceDimensionMode.identity_copy:
            # IDENTITY_SINGLE: exactly one eligible component, no penalties.
            if len(eligible) != 1:
                raise ValueError(
                    f"{self.force_code}: IDENTITY_SINGLE level requires "
                    f"exactly one eligible component (CORE_CONDITION or "
                    f"PROXY_CONDITION), got {len(eligible)}"
                )
            if penalties:
                raise ValueError(
                    f"{self.force_code}: IDENTITY_SINGLE level cannot "
                    f"include VULNERABILITY_PENALTY components"
                )
            # Part 0.5: proxy-condition ceiling guard — a PROXY_CONDITION
            # eligible component requires the force's coverage_ceiling to be
            # PARTIAL. Coverage and strength remain independent — this guard
            # does NOT numerically penalize the score; it fails loudly in
            # config so proxy semantics are enforced structurally.
            scoring_component = eligible[0]
            if scoring_component.role is ForceIndicatorRole.proxy_condition:
                if force_def.coverage_ceiling is not ForceCoverageStatus.partial:
                    raise ValueError(
                        f"{self.force_code}: PROXY_CONDITION identity "
                        f"requires coverage_ceiling=PARTIAL (got "
                        f"{force_def.coverage_ceiling})"
                    )
        elif self.level_mode is ForceDimensionMode.condition_minus_penalty:
            # CONDITION_MINUS_PENALTY (Sprint 6.13, DEC-040): exactly one
            # eligible CORE_CONDITION component + at least one
            # VULNERABILITY_PENALTY component. level = clamp(core +
            # Σ(penalty - 50), 0, 100); every numeric component must be
            # present or the level defers (missing != neutral).
            if len(eligible) != 1:
                raise ValueError(
                    f"{self.force_code}: CONDITION_MINUS_PENALTY level "
                    f"requires exactly one CORE_CONDITION/PROXY_CONDITION "
                    f"component, got {len(eligible)}"
                )
            if not penalties:
                raise ValueError(
                    f"{self.force_code}: CONDITION_MINUS_PENALTY level "
                    f"requires at least one VULNERABILITY_PENALTY component"
                )
        elif self.level_mode is ForceDimensionMode.deferred:
            # DEFERRED_MULTI: no constraint on component count, but if there
            # are 2+ eligible components, that's the expected reason for
            # deferral. A single eligible component with deferred mode is also
            # valid (e.g. owner chose not to approve identity yet).
            pass

        # relative/momentum identity_copy requires level identity_copy too
        # (you can't copy a relative/momentum that doesn't exist).
        # V1 Mission 1: relative/momentum identity_copy NO LONGER requires
        # level identity_copy — dimension-only modules (type C) may publish a
        # relative/momentum dimension while the level stays deferred. The
        # INDICATORS_WITH_APPROVED_* gate below remains the real guard: only
        # indicators with an approved dimension methodology can be copied.

        # Part 0.6: dimension approval guard — relative/momentum identity_copy
        # must refer to an indicator whose CURRENT approved NormalizedSignal
        # methodology actually supports that dimension. For v0.1 this is the
        # WGI x3 only. Do NOT enable a dimension merely because a runtime
        # signal happens to contain a number.
        if self.relative_mode is ForceDimensionMode.identity_copy:
            for comp in eligible:
                if comp.indicator_code not in INDICATORS_WITH_APPROVED_RELATIVE:
                    raise ValueError(
                        f"{self.force_code}: relative identity_copy on "
                        f"{comp.indicator_code} is not approved — indicator "
                        f"has no approved relative normalization methodology"
                    )
        if self.momentum_mode is ForceDimensionMode.identity_copy:
            for comp in eligible:
                if comp.indicator_code not in INDICATORS_WITH_APPROVED_MOMENTUM:
                    raise ValueError(
                        f"{self.force_code}: momentum identity_copy on "
                        f"{comp.indicator_code} is not approved — indicator "
                        f"has no approved momentum normalization methodology"
                    )


# --- Aggregation mode helper -------------------------------------------------


def aggregation_mode(spec: ForceAggregationSpec) -> ForceAggregationMode:
    """Derive the aggregation mode from the spec.

    IDENTITY_SINGLE when level_mode is identity_copy (which enforces exactly
    one eligible component). DEFERRED_MULTI otherwise.
    """
    if spec.level_mode is ForceDimensionMode.identity_copy:
        return ForceAggregationMode.identity_single
    if spec.level_mode is ForceDimensionMode.condition_minus_penalty:
        return ForceAggregationMode.condition_minus_penalty
    if (
        spec.relative_mode is ForceDimensionMode.identity_copy
        or spec.momentum_mode is ForceDimensionMode.identity_copy
    ):
        return ForceAggregationMode.dimension_only
    return ForceAggregationMode.deferred_multi


# --- The 17-force approval matrix --------------------------------------------
#
# Every one of the 17 forces is represented explicitly. Forces with no live
# indicators have an empty components tuple and all dimensions deferred.
# Forces with only SUPPORTING_CONTEXT components use DEFERRED_MULTI.
# Forces with a single eligible component use IDENTITY_SINGLE.

_DEFERRED = ForceDimensionMode.deferred
_IDENTITY = ForceDimensionMode.identity_copy

# Part 0.4: real duplicate force-config detection. The specs are declared as
# a tuple FIRST, then validated for duplicate force_code values BEFORE
# constructing the dictionary (a dict comprehension would silently overwrite
# duplicates).
_FORCE_AGGREGATION_SPECS: tuple[ForceAggregationSpec, ...] = (
        # 1. Leadership capabilities — IDENTITY_SINGLE (PROXY_CONDITION),
        # PARTIAL ceiling. Sprint 6.21 (DEC-041): WGI Government
        # Effectiveness promoted to PROXY_CONDITION — institutional state
        # capacity as the measurable core of "how effectively it governs".
        # relative/momentum/confidence stay DEFERRED (level only).
        ForceAggregationSpec(
            force_code="leadership_capabilities",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="GOVERNMENT_EFFECTIVENESS_WGI_SCORE",
                    role=ForceIndicatorRole.proxy_condition,
                ),
            ),
            level_mode=_IDENTITY,
            relative_mode=_DEFERRED,
            momentum_mode=_DEFERRED,
            confidence_mode=_DEFERRED,
            notes=(
                "Sprint 6.21 (DEC-041): identity copies the WGI GE "
                "level_score. Institutional proxy — measures state capacity, "
                "never individual leaders. PARTIAL ceiling: one WGI "
                "dimension is not the whole leadership-capabilities concept."
            ),
        ),
        # 2. Education — IDENTITY_SINGLE (PROXY_CONDITION), PARTIAL ceiling
        # Sprint 6.4 (DEC-032): TERTIARY_ATTAINMENT_25_34 promoted to
        # PROXY_CONDITION. level_mode = identity_copy promotes Education to
        # the fourth executable force. relative/momentum/confidence stay
        # DEFERRED (DEC-032 approves only the level). coverage_ceiling stays
        # PARTIAL — one tertiary-attainment measure does not represent
        # complete Education.
        ForceAggregationSpec(
            force_code="education",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="TERTIARY_ATTAINMENT_25_34",
                    role=ForceIndicatorRole.proxy_condition,
                ),
            ),
            level_mode=_IDENTITY,
            relative_mode=_DEFERRED,
            momentum_mode=_DEFERRED,
            confidence_mode=_DEFERRED,
            notes=(
                "Sprint 6.4 (DEC-032): single OECD tertiary-attainment proxy "
                "condition; identity copies the indicator level_score "
                "(aligned raw percentage). relative/momentum/confidence "
                "stay deferred. coverage stays PARTIAL."
            ),
        ),
        # 3. Character / determination — no live indicators
        ForceAggregationSpec(
            force_code="character_determination",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="LABOUR_FORCE_PARTICIPATION_RATE",
                    role=ForceIndicatorRole.proxy_condition,
                ),
            ),
            level_mode=_IDENTITY,
            relative_mode=_DEFERRED,
            momentum_mode=_IDENTITY,
            confidence_mode=_DEFERRED,
            notes=(
                "PARTIAL: level = LFP percentile vs WDI universe "
                "(wdi_lfp_v1). Narrow economic-participation proxy - not a "
                "measure of character/determination."
            ),
        ),
        # 4. Rule of law — IDENTITY_SINGLE (CORE_CONDITION)
        ForceAggregationSpec(
            force_code="rule_of_law",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="RULE_OF_LAW_WGI_SCORE",
                    role=ForceIndicatorRole.core_condition,
                ),
            ),
            level_mode=_IDENTITY,
            relative_mode=_IDENTITY,
            momentum_mode=_IDENTITY,
            confidence_mode=_DEFERRED,
            notes="Single WGI core condition; identity inherits semantics.",
        ),
        # 5. Corruption — IDENTITY_SINGLE (CORE_CONDITION)
        ForceAggregationSpec(
            force_code="corruption",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="CONTROL_OF_CORRUPTION_WGI_SCORE",
                    role=ForceIndicatorRole.core_condition,
                ),
            ),
            level_mode=_IDENTITY,
            relative_mode=_IDENTITY,
            momentum_mode=_IDENTITY,
            confidence_mode=_DEFERRED,
            notes="Single WGI core condition; identity inherits semantics.",
        ),
        # 6. Resource allocation efficiency — no live indicators
        ForceAggregationSpec(
            force_code="resource_allocation_efficiency",
            components=(),
            level_mode=_DEFERRED,
            relative_mode=_DEFERRED,
            momentum_mode=_DEFERRED,
            confidence_mode=_DEFERRED,
            notes="No live indicators; concept definition needed first.",
        ),
        # 7. Global openness — no live indicators (trade data is candidate only)
        ForceAggregationSpec(
            force_code="global_openness",
            components=(),
            level_mode=_DEFERRED,
            relative_mode=_DEFERRED,
            momentum_mode=_DEFERRED,
            confidence_mode=_DEFERRED,
            notes="No live indicators; trade data is candidate context only.",
        ),
        # 8. Productivity / output growth — IDENTITY_SINGLE (PROXY_CONDITION),
        # PARTIAL ceiling. Sprint 6.14 (DEC-042 Option A — OWNER APPROVED):
        # OECD LPPH promoted to PROXY_CONDITION; level = mid-rank percentile
        # within the versioned OECD universe oecd_lpph_v1 (period-specific).
        # GDP growth stays SUPPORTING_CONTEXT. CHN/IND are not OECD members —
        # no reference distribution applies, they defer honestly.
        ForceAggregationSpec(
            force_code="productivity_output_growth",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="LABOUR_PRODUCTIVITY_PER_HOUR",
                    role=ForceIndicatorRole.proxy_condition,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="GDP_GROWTH",
                    role=ForceIndicatorRole.supporting_context,
                ),
            ),
            level_mode=_IDENTITY,
            relative_mode=_DEFERRED,
            momentum_mode=_IDENTITY,
            confidence_mode=_DEFERRED,
            notes=(
                "Sprint 6.14 (DEC-042): level = OECD reference percentile "
                "(Option A); momentum = own-history % change, primary 5y "
                "window (Option C). Distinct dimensions — a percentile move "
                "is not productivity growth."
            ),
        ),
        # 9. Cost competitiveness — 2 SUPPORTING_CONTEXT
        ForceAggregationSpec(
            force_code="cost_competitiveness",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="UNIT_LABOUR_COST_GROWTH",
                    role=ForceIndicatorRole.supporting_context,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="INFLATION_CPI",
                    role=ForceIndicatorRole.supporting_context,
                ),
            ),
            level_mode=_DEFERRED,
            relative_mode=_DEFERRED,
            momentum_mode=_DEFERRED,
            confidence_mode=_DEFERRED,
            notes="Level normalization deferred; 2 components.",
        ),
        # 10. Trade and capital flows — 4 SUPPORTING_CONTEXT
        ForceAggregationSpec(
            force_code="trade_capital_flows",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="EXPORTS_GDP",
                    role=ForceIndicatorRole.supporting_context,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="IMPORTS_GDP",
                    role=ForceIndicatorRole.supporting_context,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="TRADE_BALANCE",
                    role=ForceIndicatorRole.supporting_context,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="FDI_NET_INFLOWS_GDP",
                    role=ForceIndicatorRole.supporting_context,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="CURRENT_ACCOUNT_GDP",
                    role=ForceIndicatorRole.supporting_context,
                ),
            ),
            level_mode=_DEFERRED,
            relative_mode=_DEFERRED,
            momentum_mode=_DEFERRED,
            confidence_mode=_DEFERRED,
            notes="Level normalization deferred; 4 components.",
        ),
        # 11. Infrastructure and investment — SUPPORTING_CONTEXT
        ForceAggregationSpec(
            force_code="infrastructure_investment",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="GROSS_CAPITAL_FORMATION_GDP",
                    role=ForceIndicatorRole.supporting_context,
                ),
            ),
            level_mode=_DEFERRED,
            relative_mode=_DEFERRED,
            momentum_mode=_DEFERRED,
            confidence_mode=_DEFERRED,
            notes="Level normalization deferred.",
        ),
        # 12. Indebtedness — CONDITION_MINUS_PENALTY (Sprint 6.13, DEC-040)
        #     DSR = CORE_CONDITION, credit gap = VULNERABILITY_PENALTY,
        #     government debt = SUPPORTING_CONTEXT.
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
            level_mode=ForceDimensionMode.condition_minus_penalty,
            relative_mode=_DEFERRED,
            momentum_mode=_DEFERRED,
            confidence_mode=_DEFERRED,
            notes=(
                "level = clamp(DSR + (credit_gap - 50), 0, 100): the "
                "one-sided vulnerability curve can only subtract from the "
                "DSR condition score; neutral gap (50) contributes nothing. "
                "Both numeric components required — missing gap defers, it "
                "is never treated as neutral. Government debt stays "
                "SUPPORTING_CONTEXT (DEC-040)."
            ),
        ),
        # 13. Military strength — 2 SUPPORTING_CONTEXT, capped PARTIAL
        ForceAggregationSpec(
            force_code="military_strength",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="MILITARY_EXPENDITURE_USD",
                    role=ForceIndicatorRole.proxy_condition,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="MILITARY_EXPENDITURE_GDP",
                    role=ForceIndicatorRole.supporting_context,
                ),
            ),
            level_mode=_DEFERRED,
            relative_mode=_IDENTITY,
            momentum_mode=_DEFERRED,
            confidence_mode=_DEFERRED,
            notes=(
                "V1 Mission 1 (delegated working model): relative dimension "
                "= share of tracked-8 defence expenditure (RELATIVE_SHARE). "
                "Dimension-only — SIPRI expenditure is an INPUT measure of "
                "resources absorbed, never capability; level stays deferred."
            ),
        ),
        # 14. Wealth / opportunity / values gaps — IDENTITY_SINGLE
        # (PROXY_CONDITION), PARTIAL ceiling
        # Sprint 6.7 (DEC-034): WEALTH_SHARE_TOP_10 promoted to
        # PROXY_CONDITION. level_mode = identity_copy promotes Wealth-gap to
        # the fifth executable force. GINI_INDEX stays SUPPORTING_CONTEXT
        # (income inequality != wealth concentration; not averaged, not
        # combined). relative/momentum/confidence stay DEFERRED (DEC-034
        # approves only the level). coverage_ceiling stays PARTIAL — one
        # wealth-concentration measure does not represent complete
        # wealth/opportunity/values gaps.
        ForceAggregationSpec(
            force_code="wealth_opportunity_values_gaps",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="GINI_INDEX",
                    role=ForceIndicatorRole.supporting_context,
                ),
                ForceIndicatorComponentSpec(
                    indicator_code="WEALTH_SHARE_TOP_10",
                    role=ForceIndicatorRole.proxy_condition,
                ),
            ),
            level_mode=_IDENTITY,
            relative_mode=_DEFERRED,
            momentum_mode=_DEFERRED,
            confidence_mode=_DEFERRED,
            notes=(
                "Sprint 6.7 (DEC-034): single WID wealth-share proxy "
                "condition; identity copies the indicator level_score "
                "(100 * (1 - raw_share)). GINI_INDEX stays "
                "SUPPORTING_CONTEXT (income inequality != wealth "
                "concentration; not averaged, not combined). "
                "relative/momentum/confidence stay deferred. coverage "
                "stays PARTIAL."
            ),
        ),
        # 15. Internal conflict — IDENTITY_SINGLE (PROXY_CONDITION), PARTIAL
        ForceAggregationSpec(
            force_code="internal_conflict",
            components=(
                ForceIndicatorComponentSpec(
                    indicator_code="POLITICAL_STABILITY_WGI_SCORE",
                    role=ForceIndicatorRole.proxy_condition,
                ),
            ),
            level_mode=_IDENTITY,
            relative_mode=_IDENTITY,
            momentum_mode=_IDENTITY,
            confidence_mode=_DEFERRED,
            notes=(
                "Single WGI proxy condition; identity inherits semantics; "
                "coverage stays PARTIAL."
            ),
        ),
        # 16. Geography — no live indicators
        ForceAggregationSpec(
            force_code="geography",
            components=(),
            level_mode=_DEFERRED,
            relative_mode=_DEFERRED,
            momentum_mode=_DEFERRED,
            confidence_mode=_DEFERRED,
            notes="Mostly static; no time-series catalog indicator planned.",
        ),
        # 17. Acts of nature — no live indicators
    ForceAggregationSpec(
        force_code="acts_of_nature",
        components=(),
        level_mode=_DEFERRED,
        relative_mode=_DEFERRED,
        momentum_mode=_DEFERRED,
        confidence_mode=_DEFERRED,
        notes="No catalog indicator; candidate sources: EM-DAT, climate indices.",
    ),
)


def _build_config_dict(
    specs: tuple[ForceAggregationSpec, ...],
) -> dict[str, ForceAggregationSpec]:
    """Build the config dict with duplicate force_code detection.

    A dict comprehension would silently overwrite duplicates — this function
    fails loudly instead.
    """
    seen: set[str] = set()
    result: dict[str, ForceAggregationSpec] = {}
    for spec in specs:
        if spec.force_code in seen:
            raise ValueError(
                f"duplicate force aggregation config: {spec.force_code}"
            )
        seen.add(spec.force_code)
        result[spec.force_code] = spec
    return result


FORCE_AGGREGATION_CONFIGS: dict[str, ForceAggregationSpec] = _build_config_dict(
    _FORCE_AGGREGATION_SPECS
)


# --- Validation at import time -----------------------------------------------


def _validate_configs() -> None:
    """Validate the full config set at import time.

    - exactly 17 force definitions exist
- no unknown force codes in the aggregation configs
    - every force definition has an aggregation config (explicitness)
    - no duplicate force configs (dict construction already prevents this)
    """
    force_codes = {f.code for f in FORCE_DEFINITIONS}
    config_codes = set(FORCE_AGGREGATION_CONFIGS.keys())

    if len(FORCE_DEFINITIONS) != 17:
        raise ValueError(
            f"expected exactly 17 force definitions, got {len(FORCE_DEFINITIONS)}"
        )

    unknown = config_codes - force_codes
    if unknown:
        raise ValueError(f"unknown force codes in configs: {sorted(unknown)}")

    missing = force_codes - config_codes
    if missing:
        raise ValueError(
            f"force definitions without aggregation configs: {sorted(missing)}"
        )


_validate_configs()


# --- Version -----------------------------------------------------------------

FORCE_AGGREGATION_VERSION = "force-aggregation-v0.9"
