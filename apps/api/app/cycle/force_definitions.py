"""The 17 Big Cycle forces and their data-coverage definitions.

Authoritative wording: docs/data-model.md (names) and packages/shared/src/index.ts
(FORCES keys) — both preserved verbatim here. Do not rename forces casually.

This module is a typed CONFIGURATION layer, not a scoring engine. It contains no
weights, no normalization parameters, and no score formulas — those live in
the separately versioned normalization (normalization-v0.7) and force
aggregation (force-aggregation-v0.2) layers. Coverage is not strength: a force
marked "available" means the mapped live indicators have observations, nothing
more. Four force-level identity/proxy signals are executable via IDENTITY_SINGLE
(Rule of law, Corruption, Internal conflict proxy, Education proxy); 13/17
forces are intentionally unscored.

Mapping discipline:
- live_indicator_codes — canonical indicators with a defensible, direct
  conceptual relationship to the force, currently sourced (or intended as the
  first inputs once sourced).
- candidate_indicator_codes — catalog indicators that plausibly feed the force
  but are not yet promoted to live inputs. Promotion is a deliberate owner
  decision, never automatic.
- Deliberately UNASSIGNED catalog indicators (documented, not mapped):
  GDP_CURRENT_USD and GDP_PER_CAPITA (economic scale / normalization context,
  not a direct force input), POPULATION (normalization denominator), and
  UNEMPLOYMENT_RATE (relates to opportunity gaps only via a proxy judgment —
  left unassigned rather than guessed).

No Force / ForceIndicatorMapping tables exist yet; the future persistence
decision is deferred until the conceptual mapping is validated (see
.dev/FORCE_COVERAGE.md).
"""
from dataclasses import dataclass
from enum import Enum


class ForceCoverageStatus(str, Enum):
    """Deterministic data-coverage status. Coverage is not strength."""

    available = "available"
    partial = "partial"
    defined_not_sourced = "defined_not_sourced"
    missing = "missing"


@dataclass(frozen=True)
class ForceDefinition:
    code: str
    name: str
    description: str
    live_indicator_codes: tuple[str, ...] = ()
    candidate_indicator_codes: tuple[str, ...] = ()
    coverage_notes: str = ""
    # Conceptual cap on the coverage status: when set, a force whose mapped
    # live inputs are an explicitly incomplete proxy for the full concept can
    # never report "available", even with complete data for those inputs
    # (e.g. Gini measures income inequality only, not the whole wealth/
    # opportunity/values-gaps force). None = no ceiling (default, unchanged).
    coverage_ceiling: ForceCoverageStatus | None = None


FORCE_DEFINITIONS: tuple[ForceDefinition, ...] = (
    ForceDefinition(
        code="leadership_capabilities",
        name="Leadership capabilities",
        description="Capabilities of the country's leadership and how effectively it governs.",
        coverage_notes="No catalog indicator exists; requires a qualitative or expert-assessment source.",
    ),
    ForceDefinition(
        code="education",
        name="Education",
        description="Quality and reach of the country's education system and human capital.",
        live_indicator_codes=("TERTIARY_ATTAINMENT_25_34",),
        candidate_indicator_codes=("TERTIARY_ENROLLMENT", "SECONDARY_ENROLLMENT"),
        coverage_ceiling=ForceCoverageStatus.partial,
        coverage_notes=(
            "Live input: OECD tertiary attainment age 25-34 (ISCED 5-8, "
            "% of population, annual, Sprint 5.20). Attainment != enrollment. "
            "CHN has only 1 data point (2010); IND has 8 sparse data points. "
            "Still missing: secondary attainment/enrollment, learning "
            "outcomes/test scores, education quality, years of schooling, "
            "skills. One tertiary series cannot make Education AVAILABLE — "
            "capped at PARTIAL."
        ),
    ),
    ForceDefinition(
        code="character_determination",
        name="Character / determination",
        description="Resourcefulness and determination of the population.",
        coverage_notes="No catalog indicator exists; requires qualitative assessment.",
    ),
    ForceDefinition(
        code="rule_of_law",
        name="Rule of law",
        description="Respect for law and contracts; objective measurement of legal system quality.",
        live_indicator_codes=("RULE_OF_LAW_WGI_SCORE",),
        coverage_notes=(
            "World Bank WGI Rule of Law governance score (2025 revision, 0-100 "
            "absolute scale) live 1996-2024 for all 8 countries. Perception-based "
            "composite with measurement uncertainty (90% CI bounds and number of "
            "sources exist as separate WGI series, not yet imported). This is a "
            "SOURCE indicator for the force, not an Atlas force score."
        ),
    ),
    ForceDefinition(
        code="corruption",
        name="Corruption",
        description="Prevalence of corruption and rent-seeking behavior.",
        live_indicator_codes=("CONTROL_OF_CORRUPTION_WGI_SCORE",),
        coverage_notes=(
            "Source is WGI 'Control of Corruption' (2025 revision, 0-100): HIGHER "
            "means stronger control of corruption / less corruption — the raw "
            "stored value is never reversed or reinterpreted. Perception-based "
            "composite with measurement uncertainty. This is a SOURCE indicator, "
            "not an Atlas force score."
        ),
    ),
    ForceDefinition(
        code="resource_allocation_efficiency",
        name="Resource allocation efficiency",
        description="How efficiently capital, labor, and talent are allocated across the economy.",
        coverage_notes="No catalog indicator assigned; capital-misallocation measures (e.g. credit gap vs trend) are currently mapped to Indebtedness instead.",
    ),
    ForceDefinition(
        code="global_openness",
        name="Global openness",
        description="Openness to trade, capital, people, and ideas.",
        coverage_notes=(
            "Not yet measurable as defined: the force covers openness to trade, "
            "capital, people, AND ideas. World Bank trade data (exports, imports, "
            "trade balance, current account) is now imported and available as a "
            "future openness input candidate, but it deliberately does not raise "
            "this force's status — a narrower proxy methodology needs owner "
            "approval first."
        ),
    ),
    ForceDefinition(
        code="productivity_output_growth",
        name="Productivity / output growth",
        description="Growth of output and productivity of the economy.",
        live_indicator_codes=("GDP_GROWTH", "LABOUR_PRODUCTIVITY_PER_HOUR"),
        candidate_indicator_codes=("RND_EXPENDITURE_GDP",),
        coverage_notes="GDP growth (level of output growth) plus labour productivity per hour. R&D expenditure is an innovation input candidate, not a direct productivity measure.",
    ),
    ForceDefinition(
        code="cost_competitiveness",
        name="Cost competitiveness",
        description="Relative cost position of the country's producers versus competitors.",
        live_indicator_codes=("UNIT_LABOUR_COST_GROWTH", "INFLATION_CPI"),
        coverage_notes=(
            "ULC growth is relative-cost meaningful; CPI inflation is a domestic "
            "price-pressure input. Relative international competitiveness "
            "ultimately needs exchange rates and partner-country price/cost "
            "comparisons — CPI alone (e.g. CHN/IND without OECD ULC) makes this "
            "force partial, never available."
        ),
    ),
    ForceDefinition(
        code="trade_capital_flows",
        name="Trade and capital flows",
        description="Size and balance of the country's trade and cross-border capital flows.",
        live_indicator_codes=(
            "EXPORTS_GDP",
            "IMPORTS_GDP",
            "TRADE_BALANCE",
            "CURRENT_ACCOUNT_GDP",
        ),
        coverage_notes=(
            "World Bank WDI live (2000–2025, all 8 countries): exports/imports of "
            "goods and services, the published external balance (direct provider "
            "series for trade balance — not derived), and the current account. "
            "Capital-flow measures beyond the current account and bilateral flows "
            "(UN Comtrade) come later."
        ),
    ),
    ForceDefinition(
        code="infrastructure_investment",
        name="Infrastructure and investment",
        description="Level and quality of infrastructure and fixed investment.",
        live_indicator_codes=("GROSS_CAPITAL_FORMATION_GDP",),
        coverage_notes=(
            "World Bank gross capital formation live (2000–2025, all 8 countries). "
            "It measures investment effort, not infrastructure quality — quality "
            "indices come later."
        ),
    ),
    ForceDefinition(
        code="indebtedness",
        name="Indebtedness",
        description="Level and trajectory of debt burdens across sectors.",
        live_indicator_codes=("CREDIT_TO_GDP_GAP", "DEBT_SERVICE_RATIO", "GOVERNMENT_DEBT_GDP"),
        coverage_notes=(
            "Private-sector credit gap + debt service (BIS) + general-government "
            "gross debt (IMF WEO, Sprint 5.19). Government debt is a raw level "
            "input only — no monotonic 'higher debt = weaker' curve is approved; "
            "debt sustainability depends on interest cost, currency, maturity, "
            "fiscal capacity, monetary sovereignty, and growth (CONTEXTUAL_DEFERRED "
            "in the normalization registry). No Indebtedness force score exists."
        ),
    ),
    ForceDefinition(
        code="military_strength",
        name="Military strength",
        description="Military capability relative to potential adversaries.",
        live_indicator_codes=("MILITARY_EXPENDITURE_USD", "MILITARY_EXPENDITURE_GDP"),
        coverage_ceiling=ForceCoverageStatus.partial,
        coverage_notes=(
            "Live inputs are spending measures only (World Bank MS.MIL.XPND.CD / "
            "MS.MIL.XPND.GD.ZS, underlying source: SIPRI Military Expenditure "
            "Database). SIPRI describes military expenditure as an INPUT measure - "
            "resources absorbed by the military - not a measure of military "
            "capability or security. Personnel capability, equipment quality and "
            "quantity, technology, logistics, readiness, combat experience, "
            "alliances/force projection, and nuclear capability are not measured, "
            "so spending alone can never make this force AVAILABLE (DEC-009 "
            "ceiling)."
        ),
    ),
    ForceDefinition(
        code="wealth_opportunity_values_gaps",
        name="Wealth / opportunity / values gaps",
        description="Gaps in wealth, opportunity, and values within the country.",
        live_indicator_codes=("GINI_INDEX", "WEALTH_SHARE_TOP_10"),
        coverage_ceiling=ForceCoverageStatus.partial,
        coverage_notes=(
            "Live inputs: World Bank Gini index (income inequality, irregular) "
            "+ WID top 10% net personal wealth share (wealth concentration, "
            "annual, Sprint 5.20). Both are distributional measures — "
            "opportunity gaps and values/social polarization remain missing. "
            "The force is capped at PARTIAL until its conceptual scope is "
            "better covered. WID data_quality column preserved but NOT used "
            "for filtering (official semantics unverified)."
        ),
    ),
    ForceDefinition(
        code="internal_conflict",
        name="Internal conflict",
        description="Degree of internal conflict — rich vs poor, left vs right, religion, ethnicity.",
        live_indicator_codes=("POLITICAL_STABILITY_WGI_SCORE",),
        coverage_ceiling=ForceCoverageStatus.partial,
        coverage_notes=(
            "Initial institutional/conflict-risk proxy: WGI 'Political Stability "
            "and Absence of Violence/Terrorism' governance score (2025 revision, "
            "0-100) live 1996-2024 for all 8 countries. It does NOT measure every "
            "form of domestic conflict (polarization, protests, distributional "
            "tension) — the force is capped at PARTIAL while this proxy is the "
            "only input; later ACLED / event data may strengthen it. "
            "Perception-based composite with measurement uncertainty. SOURCE "
            "indicator, not an Atlas force score."
        ),
    ),
    ForceDefinition(
        code="geography",
        name="Geography",
        description="Natural endowments, location, and geographic conditions.",
        coverage_notes="Mostly static; no time-series catalog indicator planned.",
    ),
    ForceDefinition(
        code="acts_of_nature",
        name="Acts of nature",
        description="Exposure to natural disasters, pandemics, and climate events.",
        coverage_notes="No catalog indicator exists; candidate sources: EM-DAT, climate indices.",
    ),
)


def force_definition_by_code(code: str) -> ForceDefinition | None:
    for force in FORCE_DEFINITIONS:
        if force.code == code:
            return force
    return None