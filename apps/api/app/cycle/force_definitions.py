"""The 17 Big Cycle forces and their data-coverage definitions.

Authoritative wording: docs/data-model.md (names) and packages/shared/src/index.ts
(FORCES keys) — both preserved verbatim here. Do not rename forces casually.

This module is a typed CONFIGURATION layer, not a scoring engine. It contains no
weights, no normalization parameters, and no score formulas — those live in
the separately versioned normalization (normalization-v0.8) and force
aggregation (force-aggregation-v0.3) layers. Coverage is not strength: a force
marked "available" means the mapped live indicators have observations, nothing
more. Five force-level identity/proxy signals are executable via IDENTITY_SINGLE
(Rule of law, Corruption, Internal conflict proxy, Education proxy, Wealth-gap
proxy); 12/17 forces are intentionally unscored.

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
        live_indicator_codes=("GOVERNMENT_EFFECTIVENESS_WGI_SCORE",),
        coverage_ceiling=ForceCoverageStatus.partial,
        coverage_notes=(
            "WGI Government Effectiveness (2025 revision, 0-100) is the "
            "institutional proxy: quality of public services, civil service, "
            "policy formulation and implementation. It measures state "
            "capacity, not individual leaders — no subjective leader "
            "ratings. Capped PARTIAL: one governance dimension is not the "
            "whole leadership-capabilities concept (Sprint 6.21, DEC-041)."
        ),
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
        coverage_ceiling=ForceCoverageStatus.partial,
        live_indicator_codes=("LABOUR_FORCE_PARTICIPATION_RATE",),
        coverage_notes=(
            "PARTIAL proxy (V1 Mission 1, delegated working model): the "
            "executable component measures RELATIVE ECONOMIC PARTICIPATION "
            "— labour force participation rate (ILO modeled, ages 15+) "
            "scored as a WDI-universe percentile. This is a narrow, labeled "
            "proxy for economic participation only; it is NOT a measurement "
            "of national character or determination. Resourcefulness, "
            "entrepreneurship and innovation dimensions remain unmeasured. "
            "PARTIAL ceiling enforced; higher participation is not "
            "universally positive (documented limitation)."
        ),
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
        live_indicator_codes=(
            "GROSS_CAPITAL_FORMATION_GDP",
            "GDP_GROWTH",
            "LABOUR_PRODUCTIVITY_PER_HOUR",
        ),
        coverage_ceiling=ForceCoverageStatus.partial,
        coverage_notes=(
            "Investment & resource-allocation CONTEXT profile (Mission 4 §17): "
            "investment effort (GCF % of GDP), output growth, and labour "
            "productivity describe the input side — none of them measures "
            "allocation efficiency itself, and all three overlap productivity / "
            "infrastructure inputs by design (documented, not deduplicated)."
        ),
    ),
    ForceDefinition(
        code="global_openness",
        name="Global openness",
        description="Openness to trade, capital, people, and ideas.",
        live_indicator_codes=(
            "EXPORTS_GDP",
            "IMPORTS_GDP",
            "TRADE_BALANCE",
            "CURRENT_ACCOUNT_GDP",
            "FDI_NET_INFLOWS_GDP",
        ),
        # Size context is deliberately candidate-only: GDP_CURRENT_USD and
        # POPULATION are unassigned scale context in the normalization
        # registry, never force inputs.
        candidate_indicator_codes=("POPULATION", "GDP_CURRENT_USD"),
        coverage_ceiling=ForceCoverageStatus.partial,
        coverage_notes=(
            "Descriptive openness CONTEXT profile (Mission 4 §16): trade "
            "intensity (exports+imports % of GDP, exposed as derived "
            "TRADE_OPENNESS_GDP), external balance, current account, FDI "
            "inflows, plus population/GDP size context as candidates. Trade "
            "intensity is NOT strength (DEC-035) and these inputs overlap "
            "trade_capital_flows deliberately. The full force (capital, "
            "people, ideas) remains unmeasurable — no level score is claimed."
        ),
    ),
    ForceDefinition(
        code="productivity_output_growth",
        name="Productivity / output growth",
        description="Growth of output and productivity of the economy.",
        live_indicator_codes=("GDP_GROWTH", "LABOUR_PRODUCTIVITY_PER_HOUR"),
        candidate_indicator_codes=("RND_EXPENDITURE_GDP",),
        coverage_ceiling=ForceCoverageStatus.partial,
        coverage_notes=(
            "OECD labour productivity per hour (6/8 countries — CHN/IND are "
            "not OECD members and cannot receive an OECD-calibrated score). "
            "Sprint 6.14 (DEC-042 Option A — owner approved): level = "
            "mid-rank percentile within the versioned OECD universe "
            "oecd_lpph_v1, period-specific. Capped PARTIAL: OECD relative "
            "productivity position only — not the whole "
            "productivity/output-growth force, not a global percentile."
        ),
    ),
    ForceDefinition(
        code="cost_competitiveness",
        name="Cost competitiveness",
        coverage_ceiling=ForceCoverageStatus.partial,
        description="Relative cost position of the country's producers versus competitors.",
        live_indicator_codes=("REER_INDEX", "UNIT_LABOUR_COST_GROWTH", "INFLATION_CPI"),
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
            "FDI_NET_INFLOWS_GDP",
        ),
        coverage_notes=(
            "World Bank WDI live (2000–2025, all 8 countries): exports/imports of "
            "goods and services, the published external balance (direct provider "
            "series for trade balance — not derived), and the current account. "
            "FDI net inflows (%GDP) live 1990+ all 8 countries (V1 Mission 1). "
            "Capital-flow measures beyond the current account and bilateral flows "
            "(UN Comtrade) come later."
        ),
    ),
    ForceDefinition(
        code="infrastructure_investment",
        name="Infrastructure and investment",
        description="Level and quality of infrastructure and fixed investment.",
        live_indicator_codes=("GROSS_CAPITAL_FORMATION_GDP", "BROADBAND_PER_100"),
        coverage_notes=(
            "World Bank gross capital formation live (2000–2025, all 8 countries) "
            "+ fixed broadband per 100 (Mission 2). Investment effort + digital "
            "coverage context — NOT infrastructure quality."
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
            "in the normalization registry). Sprint 6.13 (DEC-040, ratified) "
            "added a score: CONDITION_MINUS_PENALTY composition, level = "
            "clamp(DSR + (credit_gap - 50), 0, 100), force-aggregation-v0.4."
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
        live_indicator_codes=("NATURAL_DISASTER_AFFECTED_PCT",),
        coverage_ceiling=ForceCoverageStatus.partial,
        coverage_notes=(
            "Verified structural exposure context (Mission 4 §18): WB "
            "EN.CLC.MDAT.ZS, an EM-DAT-derived % of population affected by "
            "droughts/floods/extreme temperatures averaged over 1990-2009 "
            "(published at 2009 only — no annual series). Pandemic and "
            "climate-change exposure have no legally accessible provider "
            "series ingested yet; missing values mean 'not published', never "
            "'zero events'."
        ),
    ),
)


def force_definition_by_code(code: str) -> ForceDefinition | None:
    for force in FORCE_DEFINITIONS:
        if force.code == code:
            return force
    return None