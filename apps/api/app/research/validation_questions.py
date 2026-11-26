"""Canonical 50-question Big Cycle validation registry.

The source wording for the legacy assessment was not present in the repository.
This registry is therefore Atlas-authored canonical wording v1, derived from the
mission's category definitions. The complete wording is versioned and immutable;
future wording corrections must use a new registry version.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

VALIDATION_REGISTRY_VERSION = "validation-questions-v1.2"
VALIDATION_METHODOLOGY_VERSION = "validation-methodology-v1.2"

IMPLEMENTATION_STATUSES = {
    "not_implemented",
    "partially_implemented",
    "data_available",
    "research_method_implemented",
    "evaluation_implemented",
}

VALIDATION_STATUSES = {
    "untested",
    "currently_untestable",
    "insufficient_evidence",
    "exploratory_findings",
    "evaluated_with_no_clear_conclusion",
    "evidence_supporting_registered_claim",
    "evidence_inconsistent_with_registered_claim",
    "independent_replication_required",
}


@dataclass(frozen=True)
class ValidationQuestionDef:
    question_code: str
    category: str
    original_question: str
    short_title: str
    theory_claims: tuple[str, ...]
    related_forces: tuple[str, ...]
    related_power_measures: tuple[str, ...]
    required_datasets: tuple[dict[str, Any], ...]
    available_datasets: tuple[dict[str, Any], ...]
    missing_datasets: tuple[dict[str, Any], ...]
    historical_coverage: dict[str, Any]
    country_coverage: dict[str, Any]
    existing_research_methods: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    contradictory_evidence: tuple[str, ...]
    alternative_explanations: tuple[str, ...]
    falsification_criteria: str
    scientific_limitations: tuple[str, ...]
    source_references: tuple[dict[str, str], ...]
    implementation_status: str
    research_validation_status: str
    current_answer: str
    related_hypotheses: tuple[str, ...] = ()
    chart: dict[str, str] | None = None
    previous_implementation_status: str = "unavailable_prior_assessment"

    def payload(self) -> dict[str, Any]:
        data = asdict(self)
        data["registry_version"] = VALIDATION_REGISTRY_VERSION
        data["methodology_version"] = VALIDATION_METHODOLOGY_VERSION
        return data


def _src(label: str, url: str) -> dict[str, str]:
    return {"label": label, "url": url}


def _items(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (dict, str)):
        return (value,)
    return tuple(value)


def _ds(source_key: str, dataset: str, role: str, **extra: Any) -> dict[str, Any]:
    return {"source_key": source_key, "dataset": dataset, "role": role, **extra}


def _missing(source_key: str, dataset: str, reason: str) -> dict[str, str]:
    return {"source_key": source_key, "dataset": dataset, "reason": reason}


CORE_REFERENCES = (
    _src("Ray Dalio, Principles for Dealing with the Changing World Order", "https://www.principles.com/the-changing-world-order"),
    _src("Atlas theory registry", "/api/research/foundation/theory-registry"),
)
JST_REFERENCE = _src("Jordà-Schularick-Taylor Macrohistory Database R6", "https://www.macrohistory.net/database/")
BIS_REFERENCE = _src("BIS debt-service and credit-gap statistics", "https://data.bis.org/")
WB_REFERENCE = _src("World Bank World Development Indicators", "https://databank.worldbank.org/source/world-development-indicators")
ALFRED_REFERENCE = _src("ALFRED/FRED vintage documentation", "https://fred.stlouisfed.org/docs/api/fred/alfred.html")
IMF_CRISIS_REFERENCE = _src("IMF systemic banking-crises publication", "https://www.imf.org/en/publications/wp/issues/2026/05/14/systemic-banking-crises-database-1970-2025-576036")

JST_DATA = (
    _ds("jst_macrohistory", "R6", "long historical research panel", variables=["debtgdp", "tloans", "thh", "tbus", "ca", "money", "cpi", "stir", "ltrate", "expenditure", "revenue", "crisisJST"]),
)
COFER_DATA = (
    _ds("imf_cofer", "COFER-SDMX-2.1", "official FX reserve shares & claims (1995-2026Q2; currency-level)"),
)
BIS_FX_DATA = (
    _ds("bis_fx_turnover", "WS_DER_OTC_TOV", "BIS Triennial FX turnover shares 1989-2025 (including INR)"),
)
BIS_LBS_DATA = (
    _ds("bis_lbs", "WS_LBS_D_PUB", "BIS cross-border bank claims by currency and reporting jurisdiction"),
)
BIS_SECTOR_CREDIT_DATA = (
    _ds("bis_credit_policy", "WS_TC_CBPOL", "BIS sectoral credit (govt, private, household, corporate) & policy rates"),
)
PWT_DATA = (
    _ds("pwt", "11.0", "Penn World Table 11.0 output, worker/hour productivity, capital, human capital & TFP (1950-2023)"),
)
MADDISON_DATA = (
    _ds("maddison", "2023", "Maddison Project Database 2023 historical GDP per capita in 2011 intl $ (1500-2022)"),
)
PRIMARY_MACRO = (
    _ds("world_bank", "current WDI import", "primary Observatory indicators"),
    _ds("imf", "current WEO import", "primary Observatory indicators"),
    _ds("bis", "current BIS import", "debt-service and credit-gap indicators"),
    _ds("oecd", "current OECD import", "productivity, education and labour-cost indicators"),
    _ds("wid", "current WID import", "wealth inequality indicators"),
)


def q(
    code: str,
    category: str,
    text: str,
    title: str,
    *,
    theories: tuple[str, ...] = ("dalio_big_cycle",),
    forces: tuple[str, ...] = (),
    powers: tuple[str, ...] = (),
    required: tuple[dict[str, Any], ...] = (),
    available: tuple[dict[str, Any], ...] = (),
    missing: tuple[dict[str, Any], ...] = (),
    history: dict[str, Any] | None = None,
    countries: dict[str, Any] | None = None,
    methods: tuple[str, ...] = (),
    support: tuple[str, ...] = (),
    contra: tuple[str, ...] = (),
    alternatives: tuple[str, ...] = (),
    falsification: str = "A registered test must fail to outperform its declared baseline or produce no independent evidence.",
    limitations: tuple[str, ...] = (),
    refs: tuple[dict[str, str], ...] = CORE_REFERENCES,
    implementation: str = "not_implemented",
    validation: str = "untested",
    answer: str = "Unanswered with the current Atlas evidence.",
    hypotheses: tuple[str, ...] = (),
    chart: dict[str, str] | None = None,
) -> ValidationQuestionDef:
    if implementation not in IMPLEMENTATION_STATUSES:
        raise ValueError(f"invalid implementation status {implementation}")
    if validation not in VALIDATION_STATUSES:
        raise ValueError(f"invalid validation status {validation}")
    return ValidationQuestionDef(
        question_code=code,
        category=category,
        original_question=text,
        short_title=title,
        theory_claims=_items(theories),
        related_forces=_items(forces),
        related_power_measures=_items(powers),
        required_datasets=_items(required),
        available_datasets=_items(available),
        missing_datasets=_items(missing),
        historical_coverage=history or {"status": "not_assessed"},
        country_coverage=countries or {"status": "not_assessed"},
        existing_research_methods=_items(methods),
        supporting_evidence=_items(support),
        contradictory_evidence=_items(contra),
        alternative_explanations=_items(alternatives),
        falsification_criteria=falsification,
        scientific_limitations=_items(limitations),
        source_references=_items(refs),
        implementation_status=implementation,
        research_validation_status=validation,
        current_answer=answer,
        related_hypotheses=_items(hypotheses),
        chart=chart,
    )


VALIDATION_QUESTIONS: tuple[ValidationQuestionDef, ...] = (
    q("Q01", "core_theory", "What is the original Big Cycle theory, which claims does it make, and which claims can Atlas operationalise?", "Original theory scope",
      required=(_ds("theory_registry", "primary-source registry", "claim definition"),),
      available=(_ds("theory_registry", "theory-registry-v1.0", "seven versioned claim/framework entries"),),
      history={"status": "not_data_bound", "note": "Theory-definition question"}, countries={"status": "not_data_bound"},
      methods=("versioned theory registry", "explicit Atlas/original-framework separation"),
      support=("The registry separates Dalio concepts from Atlas's 17-force and eight-stage operational frameworks.",),
      contra=(), alternatives=("Narrative theories can be useful without a unique measurable representation.",),
      falsification="The registry is adequate only if a reviewer can distinguish original claims, Atlas interpretations and unsupported operational assumptions.",
      limitations=("The source text is a narrative synthesis rather than a statistical specification.",),
      implementation="research_method_implemented", validation="insufficient_evidence",
      answer="Atlas now records the theory and operational differences; it does not claim the theory is proven."),

    q("Q02", "core_theory", "How long is the proposed Big Cycle, and is the approximately 75-year claim supported across independently dated historical cycles?", "Cycle duration",
      required=(_ds("historical_entities", "multi-century boundary-stable entity panel", "duration estimation"), _ds("independent_order_transitions", "dated cycle boundaries", "outcome labels")),
      available=JST_DATA + MADDISON_DATA, missing=(_missing("historical_entities", "boundary-stable sovereign/empire registry", "modern country codes only"), _missing("historical_order_transitions", "dated order transitions", "no verified chronology")),
      history={"achieved": "Maddison 1500-2022 (reconstructed) + JST 1870-2020", "required": "multiple independently dated boundary-stable order transitions"},
      countries={"achieved": "20 research countries", "required": "independent historical entities and modern countries"},
      methods=("registered candidate duration claim", "three-timescale separation"),
      support=("The duration claim is registered as a hypothesis candidate rather than a constant.", "Maddison 2023 extends output context pre-1870 without implying cycle stages."),
      contra=("GDP per capita history alone does not date order transitions, and no boundary-stable order-transition chronology is imported.",),
      alternatives=("Different debt, internal-order and external-order clocks may have different durations.",),
      limitations=("No independent full-cycle onset/boundary chronology.", "Entity boundaries and modern GDP definitions change."),
      refs=CORE_REFERENCES + (JST_REFERENCE,), implementation="partially_implemented", validation="currently_untestable",
      answer="Currently untestable; no Atlas countdown or stage advancement uses the duration claim.", hypotheses=("H04",)),

    q("Q03", "core_theory", "What stages does the original framework describe, and how do those stages differ from the eight Atlas operational stages?", "Original vs Atlas stages",
      required=(_ds("theory_registry", "edition-level source mapping", "framework comparison"), _ds("cycle_model", "Atlas stage definitions", "operational comparison")),
      available=(_ds("theory_registry", "theory-registry-v1.0", "stage separation"), _ds("atlas_cycle_model", "experimental classifier", "current operational stages")),
      history={"status": "model_metadata"}, countries={"status": "not_data_bound"},
      methods=("theory registry", "experimental classifier labelled as Atlas operational framework"),
      support=("The eight Atlas stages are explicitly marked Atlas-operational rather than Dalio-original.",),
      contra=("No edition-level mapping establishes a one-to-one stage structure.",),
      alternatives=("Stage labels may be heuristic states rather than historical facts.",),
      limitations=("Atlas model labels are retrospective and not validated long-cycle stages.",),
      implementation="partially_implemented", validation="insufficient_evidence",
      answer="The frameworks are separated, but a validated original-stage mapping is not established."),

    q("Q04", "core_theory", "What evidence marks transitions from one proposed stage to another rather than ordinary short-cycle changes?", "Stage transition evidence",
      required=(_ds("independent_stage_transitions", "source-defined transitions", "outcomes"), _ds("long_historical_panel", "multi-century predictors", "transition features")),
      available=JST_DATA + (_ds("atlas_cycle_model", "experimental national-condition models", "candidate transition classifications"),),
      missing=(_missing("historical_order_transitions", "independent stage/onset chronology", "not imported"),),
      history={"achieved": "JST 1870-2020", "limitation": "no independent stage labels"},
      countries={"achieved": "18 JST entities", "primary": "8 Observatory countries"},
      methods=("timescale separation", "leakage-aware prediction ledger", "candidate cycle transition diagnostics"),
      support=("The prediction/outcome ledger can preserve candidate transition evidence separately from model labels.",),
      contra=("Atlas stage labels come from the model under study and are not independent outcomes.",),
      alternatives=("Transitions may reflect common shocks, data revisions or model thresholds rather than cycle stages.",),
      limitations=("No independent stage-transition registry.", "No strict release-safe historical predictors."),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H04",)),

    q("Q05", "core_theory", "Can countries move backward, skip, repeat, or remain on a plateau within the proposed cycle?", "Reversals and plateaus",
      required=(_ds("independent_stage_transitions", "reversal/plateau outcomes", "labels"), _ds("long_historical_panel", "long-run predictors", "evidence")),
      available=JST_DATA, missing=(_missing("independent_stage_transitions", "source-defined stage labels", "no verified dataset"),),
      history={"achieved": "annual JST predictors", "missing": "independent stage state sequence"},
      countries={"achieved": "18 JST entities"},
      methods=("separate onset/ongoing outcome states", "candidate timescales"),
      support=("The crisis registry demonstrates onset and coverage can be represented independently.",),
      contra=("No verified stage sequence exists to test reversals or plateaus.",),
      alternatives=("Apparent reversals may be data revisions, boundary changes or model noise.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H04",)),

    q("Q06", "core_theory", "Do the claimed monetary, internal-order and external-order cycles interact in a measurable sequence?", "Three-cycle interaction",
      theories=("dalio_money_credit_debt_cycle", "dalio_internal_order_cycle", "dalio_external_order_cycle"),
      required=(_ds("multi_timescale_panel", "debt+institutional+external predictors", "features"), _ds("independent_order_transitions", "outcome chronology", "validation")),
      available=JST_DATA + PRIMARY_MACRO + COFER_DATA + BIS_FX_DATA,
      missing=(_missing("vdem", "institutional histories", "not imported"), _missing("cow", "conflict/order outcomes", "not imported"), _missing("independent_order_transitions", "order-transition chronology", "not imported")),
      history={"achieved": "JST 1870-2020, modern 1960-2026 macro, COFER 1995-2026Q2"},
      countries={"achieved": "8 primary + 18 JST entities + currency areas"},
      methods=("three registered timescales", "separate H01-H04 protocols"),
      support=("Debt, internal-order and external-order hypotheses are separately registered.",),
      contra=("No joint sequence test or independent long-order outcome exists yet.",),
      alternatives=("The sub-cycles may interact without a fixed ordering or may be driven by common shocks.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H01", "H02", "H03", "H04")),

    q("Q07", "core_theory", "Does the theory apply to all countries, only major powers, or only specific institutional and economic regimes?", "Country applicability",
      required=(_ds("global_reference_population", "eligibility rules", "population"), _ds("historical_entities", "boundary-aware panel", "scope")),
      available=(_ds("primary_observatory_v1", "8 countries", "interface population"), _ds("jst_extended_research_v1", "18 advanced economies", "historical research panel")),
      missing=(_missing("global_reference_population", "30-40 country eligible panel", "target not reached"), _missing("historical_entities", "pre-modern entities", "not imported")),
      history={"achieved": "JST advanced economies only"}, countries={"achieved": "26 memberships across two populations"},
      methods=("versioned population registry", "documented eligibility statuses"),
      support=("Primary and extended populations are not conflated.",),
      contra=("Current evidence is concentrated in eight modern countries and 18 advanced JST economies.",),
      alternatives=("Mechanisms may differ across development level, reserve status, regime and geography.",),
      implementation="partially_implemented", validation="insufficient_evidence"),

    q("Q08", "core_theory", "Which observations would support the theory and which observations would falsify or weaken it?", "Support and falsification",
      required=(_ds("hypothesis_protocols", "registered falsification rules", "protocol"), _ds("independent_outcomes", "outcome registry", "test labels")),
      available=(_ds("hypothesis_protocols", "H01-H04", "protocol registry"), _ds("crisis_registry", "JST banking crises", "one independent outcome family")),
      missing=(_missing("independent_order_transitions", "long-cycle outcomes", "not imported"), _missing("institutional_outcomes", "persistent deterioration labels", "not imported")),
      history={"status": "protocol_metadata"}, countries={"status": "population_dependent"},
      methods=("versioned hypotheses", "explicit falsification criteria", "negative-result states"),
      support=("H01 already preserves a negative evaluation instead of reclassifying it as success.",),
      contra=("Only one outcome family is populated, so broad theory falsification is impossible.",),
      alternatives=("Failure of one predictor does not falsify the full narrative theory.",),
      implementation="research_method_implemented", validation="insufficient_evidence",
      answer="Research method is implemented (registered falsification criteria, append-only evaluations preserving negative results); H01-P1.0 and H01B-P1.0 have been executed. But a scientific answer to WHICH observations support or falsify the theory requires populated independent outcome registries beyond one banking-crisis family — operational machinery alone is not an empirical finding.",
      hypotheses=("H01", "H01B", "H02", "H03", "H04")),

    q("Q09", "core_theory", "Are the Atlas force scores and experimental stage classifications suitable evidence for the historical Big Cycle claim?", "Atlas models as evidence",
      forces=("all_17_forces",), required=(_ds("force_methodology", "approved measurement methods", "features"), _ds("independent_outcomes", "external validation", "labels")),
      available=(_ds("atlas_force_engine", "17-force methodology", "national-condition inputs"), _ds("atlas_cycle_model", "experimental classifications", "model outputs")),
      missing=(_missing("independent_stage_transitions", "external stage labels", "not imported"), _missing("strict_historical_vintages", "provider release evidence", "mostly unavailable")),
      history={"achieved": "modern mixed-frequency Atlas panel", "limitation": "not long-cycle validated"},
      countries={"achieved": "8 primary Observatory countries"},
      methods=("evidence-status registry", "methodology/version separation", "retrospective-only labels"),
      support=("The system labels outputs experimental and keeps them out of the research-outcome registry.",),
      contra=("Using model-generated stages as evidence for the same stage theory would be circular.",),
      alternatives=("Atlas scores can be predictors for independent outcomes but not truth labels.",),
      implementation="research_method_implemented", validation="insufficient_evidence"),

    q("Q10", "core_theory", "How much historical depth, entity continuity and independent outcome coverage is required before the theory can be tested?", "Required historical depth",
      required=(_ds("multi_century_panel", "boundary-aware entities", "coverage"), _ds("independent_order_transitions", "multiple complete transitions", "outcomes")),
      available=JST_DATA + MADDISON_DATA + PWT_DATA + (_ds("research_population", "26 memberships", "coverage registry"),),
      missing=(_missing("historical_entities", "boundary-stable entity registry", "not populated"), _missing("independent_order_transitions", "long-cycle outcomes", "not imported")),
      history={"achieved": "Maddison 1500-2022, JST 1870-2020, PWT 1950-2023", "required": "boundary-stable entities and multiple dated order transitions"},
      countries={"achieved": "20 research countries", "required": "documented eligibility across entity types"},
      methods=("historical coverage reporting", "three-timescale architecture"),
      support=("The registry states achieved multi-dataset coverage instead of claiming adequate long-cycle outcome depth.",),
      contra=("Historical GDP reconstructions do not provide independent order-transition outcomes.",),
      alternatives=("Proxy depth may support sub-cycle tests even when the complete Big Cycle remains untestable.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H04",)),

    q("Q11", "debt_money", "Do rising debt burdens increase the probability of a subsequent systemic banking crisis?", "Debt burdens and crises",
      theories=("dalio_money_credit_debt_cycle",), forces=("indebtedness",),
      required=(_ds("debt_panel", "public/private debt predictors", "features"), _ds("independent_crisis_outcomes", "banking-crisis onsets", "outcome")),
      available=JST_DATA + BIS_SECTOR_CREDIT_DATA + (_ds("crisis_registry", "88 JST systemic banking onsets", "independent outcomes"),),
      missing=(_missing("imf_laeven_valencia_banking_crises", "WP-2026-094", "official ZIP HTTP 403/404; local-file importer ready"), _missing("alfred_fred", "historical vintages", "BCA_FRED_API_KEY required")),
      history={"achieved": "1870-2020 retrospective JST R6 + BIS sectoral credit 1947-2026Q1", "release_safety": "dataset-level only"},
      countries={"achieved": "18 JST advanced economies + 8 primary countries"},
      methods=("H01-P1.0 chronological holdout", "1/2/5-year onset horizons", "base-rate and AUC benchmarks", "append-only prediction ledger"),
      support=("A complete leakage-aware protocol was registered and executed.", "Diagnostic contrast shows private bank-loan/GDP 5y growth (tloans/gdp) reaches retrospective AUC 0.721 (1y) and 0.702 (2y), confirming public vs private debt must never be conflated."),
      contra=("Registered H01-P1.0 tested public debtgdp 5-year change: held-out AUC was 0.363 (1y), 0.381 (2y), 0.296 (5y) and top-p80 precision (1.54%/1.50%/0.88%) fell below the ~3.42% base rate because public debt typically surges after banking crises rather than before them.",),
      alternatives=("Pre-crisis private credit booms improve fiscal balances before banking crises, while public debt surges post-crisis via bailouts and automatic stabilisers.",),
      falsification="No improvement over the unconditional base rate or discrimination near/below random ordering is evidence inconsistent with predictive value.",
      limitations=("H01-P1.0 evaluated public debtgdp rather than private tloans/gdp; protocol is preserved unchanged.", "13 of 19 post-1990 test events cluster in 2007-2008 and 4 in 1991.", "Secular post-1990 debt drift pushed 35.1%-40.8% of test rows above the pre-1990 80th percentile."),
      refs=CORE_REFERENCES + (JST_REFERENCE, IMF_CRISIS_REFERENCE, ALFRED_REFERENCE),
      implementation="evaluation_implemented", validation="evaluated_with_no_clear_conclusion",
      answer="Scoped correction (v1.2): the registered H01-P1.0 test contradicted one specific operationalized proposition — 5-year PUBLIC debt/GDP change as a crisis predictor (AUC 0.363/0.381/0.296). That negative result does not falsify the broader debt-cycle claim: H01B-P1.0 found positive retrospective discrimination for PRIVATE credit expansion (tloans/gdp 5y change AUC 0.719, income-residualised 0.717), and public debt characteristically surges AFTER crises via bailouts and automatic stabilisers. The broad registered claim remains only partially tested.",
      hypotheses=("H01", "H01B"), chart={"kind": "research_observation", "source_key": "jst_macrohistory", "dataset_version": "R6", "variable_code": "debtgdp", "entity_code": "USA", "label": "JST public debt / GDP — USA"}),

    q("Q12", "debt_money", "Do public, private non-financial, household and corporate debt measures provide different warning signals?", "Debt composition",
      theories=("dalio_money_credit_debt_cycle",), forces=("indebtedness",),
      required=(_ds("sectoral_debt_panel", "public/household/corporate debt", "features"), _ds("independent_crisis_outcomes", "crisis outcomes", "evaluation")),
      available=JST_DATA + BIS_SECTOR_CREDIT_DATA + (_ds("imf", "government debt", "public debt"), _ds("bis", "private-sector DSR/credit gap", "private burden")),
      missing=(_missing("debt_ownership", "holder composition", "not imported"),),
      history={"achieved": "JST 1870-2020 (debtgdp, tloans, thh, tbus) + BIS WS_TC 1947-2026Q1 (G, P, H, N)"},
      countries={"achieved": "8 primary + 18 JST entities"},
      methods=("separate source-versioned public, private, household and corporate series", "market vs nominal valuation separation"),
      support=("BIS WS_TC quarterly sectoral debt (general government, private non-financial, households, non-financial corporations) and JST sectoral loans (thh, tbus) are now imported separately.",),
      contra=("No pre-registered multi-sector holdout protocol has been executed yet.",),
      alternatives=("Different sectors transmit stress through distinct banking, household-consumption and sovereign-funding channels.",),
      implementation="data_available", validation="insufficient_evidence", hypotheses=("H01",),
      chart={"kind": "research_observation", "source_key": "bis_credit_policy", "dataset_version": "WS_TC_CBPOL", "variable_code": "CREDIT_PRIVATE_NF_GDP", "entity_code": "USA", "label": "BIS private non-financial credit (% of GDP) — USA"}),

    q("Q13", "debt_money", "Do debt-service burdens predict financial crises better than debt-to-GDP levels?", "Debt-service burden",
      forces=("indebtedness",), required=(_ds("bis_dsr", "sectoral DSR", "predictors"), _ds("independent_crisis_outcomes", "crisis onsets", "labels")),
      available=(_ds("bis", "DEBT_SERVICE_RATIO", "925 rows, 8 countries, 1999-2026"), _ds("jst_macrohistory", "debtgdp and loans", "long retrospective proxies"), _ds("crisis_registry", "88 banking onsets", "outcomes")),
      missing=(_missing("bis_dsr_extended_panel", "30-40 country DSR", "not imported"), _missing("real_time_dsr_vintages", "release-time DSR", "not available")),
      history={"achieved": "BIS 1999-2026; JST retrospective proxy to 1870"},
      countries={"achieved": "8 modern countries"},
      methods=("BIS indicator import", "own-history debt-condition methodology", "H01 debt benchmark on JST"),
      support=("Modern DSR coverage exists and is separate from levels.",),
      contra=("No crisis comparison has tested DSR against debt-to-GDP directly.",),
      alternatives=("DSR may reflect interest-rate cycles and credit composition rather than long-cycle vulnerability.",),
      refs=CORE_REFERENCES + (JST_REFERENCE, BIS_REFERENCE),
      implementation="data_available", validation="untested", hypotheses=("H01",)),

    q("Q14", "debt_money", "Is there a reproducible debt-to-GDP threshold associated with later crises?", "Debt threshold",
      forces=("indebtedness",), required=(_ds("debt_threshold_panel", "pre-registered candidate thresholds", "features"), _ds("independent_crisis_outcomes", "crisis onsets", "labels")),
      available=JST_DATA + BIS_SECTOR_CREDIT_DATA + (_ds("imf", "government debt", "public debt"), _ds("world_bank", "domestic private credit", "private debt"), _ds("crisis_registry", "banking onsets", "outcomes")),
      missing=(_missing("untouched_threshold_holdout", "post-inspection confirmatory sample", "1990-2020 already used for diagnostics"),),
      history={"achieved": "JST 1870-2020; BIS WS_TC 1947-2026Q1; modern IMF/WB"},
      countries={"achieved": "18 JST + 8 primary"},
      methods=("H01T-P1.0 dedicated threshold heterogeneity protocol", "pooled vs within-country train-p80 level thresholds", "peg/non-peg regime split", "gold/interwar/Bretton-Woods/fiat era split", "no ex-post threshold mining"),
      support=("H01T-P1.0 ran dedicated level-threshold diagnostics instead of reusing change-based results.",),
      contra=("Public debtgdp level held-out AUC is 0.365 with 35.5% of test years flagged above the pooled pre-1990 p80 (0.72); private tloans/gdp pooled p80 (0.68) flags 82.0% of test years at AUC 0.623; country-specific p80 values span 0.18-1.70 (public, CV 0.55) and 0.32-1.26 (private, CV 0.39), so no single level is portable.",),
      alternatives=("Vulnerability varies with growth, interest rates, currency denomination, debt ownership, monetary regime and financial development.",),
      limitations=("H01-P1.0 formally tested 5-year changes rather than fixed level cutoffs.", "Level thresholds are non-stationary across monetary eras (fiat-era tloans/gdp AUC 0.633 vs interwar 0.470).", "No untouched confirmatory holdout remains in JST R6."),
      implementation="evaluation_implemented", validation="evaluated_with_no_clear_conclusion",
      answer="H01T-P1.0 evaluated level thresholds directly: no reproducible UNIVERSAL debt-to-GDP crisis threshold exists — pooled p80 levels discriminate at/below chance for public debt and over-flag for private credit, while per-country thresholds differ by ~5x. Thresholds appear conditional on country, era and monetary regime; that heterogeneity, not a single cutoff, is the supported research direction.",
      hypotheses=("H01", "H01T")),

    q("Q15", "debt_money", "Do external debt and foreign-currency debt create vulnerability beyond domestic debt?", "External and FX debt",
      theories=("dalio_money_credit_debt_cycle",), forces=("indebtedness", "trade_capital_flows"),
      required=(_ds("external_debt", "external/FX debt", "predictors"), _ds("currency_debt_outcomes", "currency and sovereign outcomes", "labels")),
      available=JST_DATA + BIS_LBS_DATA + (_ds("world_bank", "current-account and trade indicators", "external-position proxies"),),
      missing=(_missing("external_debt", "borrower external and FX debt stocks", "not imported"), _missing("currency_sovereign_crises", "verified outcomes", "not imported")),
      history={"achieved": "JST external proxies + BIS LBS cross-border claims 1977Q4-2026Q2"},
      countries={"achieved": "18 JST + 8 primary"},
      methods=("source-defined variable registry"),
      support=("JST current-account/FX variables and BIS cross-border banking claims are imported.",),
      contra=("Borrower-side external/FX debt stocks and currency/sovereign crisis labels remain absent.",),
      alternatives=("Reserve-currency issuers may face different constraints than borrowers in foreign currency.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H01",)),

    q("Q16", "debt_money", "Does rapid monetary expansion precede inflation, currency pressure or financial instability?", "Monetary expansion",
      theories=("dalio_money_credit_debt_cycle",), forces=("indebtedness", "trade_capital_flows"),
      required=(_ds("money_panel", "money growth", "predictors"), _ds("independent_currency_inflation_outcomes", "outcomes", "labels")),
      available=JST_DATA + (_ds("world_bank", "BROAD_MONEY_GDP and INFLATION_CPI", "modern money/inflation indicators"),),
      missing=(_missing("currency_crisis_registry", "independent currency onsets", "not imported"), _missing("inflation_regime_outcomes", "independent high-inflation episodes", "not imported"), _missing("alfred_fred", "money vintages", "API key required")),
      history={"achieved": "JST money 1870-2020; WDI modern"},
      countries={"achieved": "18 JST + 8 primary"},
      methods=("source-versioned research observations"),
      support=("JST `money` and WDI broad-money/inflation series exist.",),
      contra=("No registered outcome evaluation has been run.",),
      alternatives=("Money growth can follow credit demand, policy regime or financial deepening rather than cause instability.",),
      implementation="data_available", validation="untested", hypotheses=("H01",)),

    q("Q17", "debt_money", "Does rapid private credit expansion precede financial crises independently of income growth?", "Credit expansion",
      forces=("indebtedness",), required=(_ds("credit_panel", "private credit", "predictors"), _ds("independent_crisis_outcomes", "crisis onsets", "labels")),
      available=JST_DATA + BIS_SECTOR_CREDIT_DATA + (_ds("world_bank", "DOMESTIC_CREDIT_PRIVATE_GDP", "modern credit"), _ds("bis", "CREDIT_TO_GDP_GAP", "modern gap"), _ds("crisis_registry", "JST banking onsets", "outcomes")),
      missing=(_missing("real_time_credit_vintages", "release-safe credit revisions", "not available"),),
      history={"achieved": "JST 1870-2020; BIS WS_TC 1947-2026Q1; BIS credit-gap 1957-2026"},
      countries={"achieved": "18 JST + 8 modern"},
      methods=("H01B-P1.0 dedicated private-credit protocol", "clustered diagnostics (LOEO/LOCO/time-blocks/ex-2007-08/year-block bootstrap)", "income-growth residualisation", "BIS credit-gap import"),
      support=("H01B-P1.0 evaluated the tloans/gdp 5y change on the 1990-2020 holdout: AUC 0.719 (1y, year-block bootstrap CI 0.52-0.85), 0.702 (2y), 0.591 (5y); residualising on 5y real income growth leaves AUC 0.717, so the association is not merely an income-growth reflection. Household (0.723), corporate (0.677), mortgage (0.696) credit growth and the derived debt-service proxy (0.767) show consistent positive discrimination.",),
      contra=("The pre-registered H01-P1.0 evaluation tested public debtgdp 5-year change rather than private tloans/gdp and failed (AUC 0.363/0.381/0.296) — that negative result belongs to public debt only. The 1990-2020 holdout was already used for predictor inspection, so H01B results are retrospective diagnostics, not confirmatory; only 3 independent post-1990 crisis episodes exist (1984-91, 1997, 2007-08).",),
      alternatives=("Credit growth can reflect financial deepening, denominator contractions or synchronized global credit waves (13/19 test crises occurred in 2007-2008); ex-2007-08 and leave-one-episode-out diagnostics quantify this dependence.",),
      limitations=("Attribution audit (v1.2): the prior contradictory status was inherited from a public-debt protocol — an attribution defect now corrected. The public-debt experiment (H01-P1.0) stands unchanged; the private-credit exploratory diagnostic and the dedicated H01B-P1.0 retrospective evaluation are reported separately. Confirmatory status requires an untouched outcome sample (post-2020 or an independent registry such as IMF WP-2026-094)."),
      answer="Attribution corrected: H01-P1.0's negative result applies only to public debt. Under dedicated protocol H01B-P1.0, private-credit expansion shows positive retrospective association with banking-crisis onset that survives income-growth residualisation and clustered diagnostics — classified exploratory because the holdout is no longer untouched and only 3 independent episodes remain.",
      implementation="evaluation_implemented", validation="exploratory_findings", hypotheses=("H01", "H01B")),

    q("Q18", "debt_money", "Do changes in short- and long-term interest rates predict debt stress or crisis onset?", "Interest-rate stress",
      forces=("indebtedness",), required=(_ds("rate_panel", "short/long rates", "predictors"), _ds("independent_crisis_outcomes", "crisis onsets", "labels")),
      available=JST_DATA + BIS_SECTOR_CREDIT_DATA + (_ds("crisis_registry", "JST banking onsets", "outcomes"),),
      missing=(_missing("policy_rate_vintages", "release-safe central-bank rate vintages", "not imported"), _missing("debt_stress_outcomes", "non-crisis debt stress labels", "not defined")),
      history={"achieved": "JST stir/ltrate 1870-2020 + BIS WS_CBPOL policy rates 1945-2026"},
      countries={"achieved": "18 JST + 8 primary + EUR"},
      methods=("source-versioned historical rates and central-bank policy rates"),
      support=("JST `stir`, `ltrate`, `bill_rate`, `bond_rate` and BIS `POLICY_RATE_PCT` (with DEU/FRA -> EUR 1999 break preserved) are imported.",),
      contra=("No registered interest-rate protocol or evaluation exists.",),
      alternatives=("Rate changes can be policy responses to stress rather than independent predictors.",),
      implementation="data_available", validation="untested", hypotheses=("H01",),
      chart={"kind": "research_observation", "source_key": "bis_credit_policy", "dataset_version": "WS_TC_CBPOL", "variable_code": "POLICY_RATE_PCT", "entity_code": "USA", "label": "BIS central bank policy rate (%) — USA"}),

    q("Q19", "debt_money", "Does reserve-currency status reduce debt vulnerability or delay adjustment?", "Reserve-currency status",
      theories=("dalio_money_credit_debt_cycle", "dalio_external_order_cycle"), powers=("reserve_currency_status",),
      required=(_ds("imf_cofer", "reserve currency shares", "status"), _ds("debt_crisis_panel", "debt/crisis outcomes", "evaluation")),
      available=COFER_DATA + BIS_FX_DATA + BIS_LBS_DATA + (_ds("currency_research_entities", "currency-area registry", "entity model"),),
      missing=(_missing("pre_1995_reserve_shares", "long-run pre-1995 official reserve currency composition", "not imported"), _missing("reserve_issuer_outcomes", "issuer-specific adjustment outcomes", "not defined")),
      history={"achieved": "COFER 1995-2026Q2, BIS FX turnover 1989-2025, BIS LBS 1977Q4-2026Q2"},
      countries={"achieved": "Currency entities (USD, EUR, CNY, GBP, JPY, CHF, INR in FX turnover, DEM/FRF pre-1999)"},
      methods=("currency-area entity separation", "documented COFER methodology breaks"),
      support=("Official IMF COFER reserve shares, BIS FX turnover shares and BIS cross-border banking currency shares are now imported separately from country scores.",),
      contra=("Modern COFER spans one dominant USD regime (1995-2026) and cannot by itself identify multi-regime reserve transitions or causal debt insulation.",),
      alternatives=("Demand for safe assets, institutional depth, capital-account openness and network effects confound reserve-issuer debt outcomes.",),
      implementation="data_available", validation="insufficient_evidence", hypotheses=("H01", "H03"),
      chart={"kind": "research_observation", "source_key": "imf_cofer", "dataset_version": "COFER-SDMX-2.1", "variable_code": "COFER_RESERVE_SHARE_PCT", "entity_code": "USD", "label": "IMF COFER official FX reserve share (%) — USD"}),

    q("Q20", "debt_money", "Does financial-market depth amplify or absorb debt and credit shocks?", "Financial depth",
      forces=("indebtedness",), powers=("financial_centre_strength",),
      required=(_ds("financial_depth", "market/banking depth", "predictors"), _ds("crisis_outcomes", "independent outcomes", "labels")),
      available=(_ds("world_bank", "stock-market capitalisation/private credit/broad money", "financial-depth proxies"), JST_DATA[0], BIS_LBS_DATA[0]),
      missing=(_missing("financial_stress_outcomes", "non-crisis stress labels", "not imported"),),
      history={"achieved": "modern 1980-2025, BIS LBS 1977Q4-2026Q2, JST 1870-2020"},
      countries={"achieved": "8 primary + 18 JST"},
      methods=("separate domestic depth and cross-border banking measures"),
      support=("Domestic market depth and BIS cross-border banking intermediation are tracked separately from reserve status.",),
      contra=("No test distinguishes shock absorption from amplification.",),
      alternatives=("Depth can support resilience or enable greater leverage depending on institutions and regulation.",),
      implementation="data_available", validation="untested", hypotheses=("H01",)),

    q("Q21", "debt_money", "Does debt ownership structure change the probability or severity of crises?", "Debt ownership",
      forces=("indebtedness",), required=(_ds("debt_ownership", "domestic/foreign/public/private holders", "predictors"), _ds("crisis_outcomes", "crisis outcomes", "labels")),
      available=(_ds("imf", "government debt stock", "debt level only"),),
      missing=(_missing("debt_ownership", "holder composition", "not imported"), _missing("sovereign_bondholder_data", "ownership shares", "not imported")),
      history={"status": "missing"}, countries={"status": "missing"},
      methods=("missing-data registry"),
      contra=("No holder-composition observations are imported.",),
      alternatives=("Domestic ownership may stabilize funding while concentrating losses domestically.",),
      implementation="not_implemented", validation="currently_untestable", hypotheses=("H01",)),

    q("Q22", "debt_money", "Are currency crises preceded by distinct external, monetary or reserve pressures?", "Currency crises",
      theories=("dalio_money_credit_debt_cycle",), forces=("trade_capital_flows",), powers=("reserve_currency_status",),
      required=(_ds("currency_crisis_outcomes", "independent currency onsets", "labels"), _ds("external_monetary_panel", "external/reserve predictors", "features")),
      available=JST_DATA + COFER_DATA + (_ds("world_bank", "REER/current-account/trade series", "external proxies"),),
      missing=(_missing("currency_crisis_registry", "verified currency-crisis chronology", "not imported"), _missing("fx_reserves", "country FX reserve adequacy", "not imported")),
      history={"achieved": "JST exchange-rate/CA 1870-2020 + COFER global shares 1995-2026Q2", "missing": "currency crisis outcomes"},
      countries={"achieved": "18 JST entities"},
      methods=("separate crisis-type registry"),
      support=("The outcome registry supports currency-crisis event types.",),
      contra=("No currency-crisis events are imported.",),
      alternatives=("Exchange-rate regimes and capital controls may dominate domestic debt signals.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H01",)),

    q("Q23", "debt_money", "Are sovereign debt crises preceded by measurable fiscal and external vulnerabilities?", "Sovereign debt crises",
      theories=("dalio_money_credit_debt_cycle",), forces=("indebtedness",),
      required=(_ds("sovereign_crisis_outcomes", "sovereign default/debt crises", "labels"), _ds("fiscal_external_panel", "debt/revenue/external predictors", "features")),
      available=JST_DATA + (_ds("imf", "government debt", "public debt"),),
      missing=(_missing("sovereign_crisis_registry", "verified sovereign-crisis chronology", "not imported"), _missing("sovereign_defaults", "default/restructuring data", "not imported")),
      history={"achieved": "JST fiscal/debt variables", "missing": "sovereign outcomes"},
      countries={"achieved": "18 JST entities"},
      methods=("separate crisis-type registry"),
      support=("JST includes debt, expenditure, revenue and external variables.",),
      contra=("No sovereign-crisis outcome labels are populated.",),
      alternatives=("Sovereign crises can depend on debt currency, maturity, political choice and access to official support.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H01",)),

    q("Q24", "debt_money", "Do debt restructurings and defaults follow identifiable debt and repayment patterns?", "Restructurings and defaults",
      forces=("indebtedness",), required=(_ds("restructuring_defaults", "independent default/restructuring events", "labels"), _ds("debt_service_panel", "repayment burden", "features")),
      available=(_ds("bis", "DSR and credit gap", "repayment-burden predictors"), _ds("imf", "government debt", "stock proxy")),
      missing=(_missing("sovereign_defaults", "default/restructuring chronology", "not imported"), _missing("private_debt_restructuring", "corporate/household restructuring", "not imported")),
      history={"achieved": "modern predictors only", "missing": "outcomes"},
      countries={"achieved": "8 modern countries"},
      methods=("outcome-registry event types reserved"),
      contra=("No default/restructuring events are imported.",),
      alternatives=("Defaults can be strategic or politically constrained, not only mechanically driven by burdens.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H01",)),

    q("Q25", "debt_money", "Does debt vulnerability depend on growth, inflation, institutional quality and external conditions rather than a universal threshold?", "Conditional debt vulnerability",
      theories=("dalio_money_credit_debt_cycle", "dalio_internal_order_cycle"), forces=("indebtedness", "rule_of_law", "productivity_output_growth"),
      required=(_ds("multivariate_debt_panel", "debt+growth+institutions+external conditions", "features"), _ds("independent_crisis_outcomes", "crisis outcomes", "labels")),
      available=JST_DATA + PRIMARY_MACRO + (_ds("crisis_registry", "JST banking crises", "outcomes"),),
      missing=(_missing("multivariate_h01_protocol", "pre-registered conditional model", "not implemented"), _missing("currency_sovereign_outcomes", "other crisis labels", "not imported")),
      history={"achieved": "long JST panel plus modern indicators"},
      countries={"achieved": "18 JST + 8 primary"},
      methods=("registered simple benchmark", "candidate multivariate protocol fields"),
      support=("JST/WB/OECD/IMF/BIS variables can support a conditional design.",),
      contra=("The univariate result argues against universal-threshold claims, but the conditional hypothesis remains untested.",),
      alternatives=("Conditional relationships may reflect policy response or selection of which countries borrow.",),
      implementation="research_method_implemented", validation="untested", hypotheses=("H01", "H02")),

    q("Q26", "internal_conflict", "Does institutional deterioration predict later weakness in investment or productivity?", "Institutions and productivity",
      theories=("dalio_internal_order_cycle",), forces=("rule_of_law", "corruption", "leadership_capabilities", "productivity_output_growth"),
      required=(_ds("institutional_panel", "institutional measures", "predictors"), _ds("persistent_weakness_outcomes", "investment/productivity weakness labels", "outcomes")),
      available=(_ds("world_bank", "WGI + investment series", "predictors"), _ds("oecd", "productivity series", "candidate outcome proxy")),
      missing=(_missing("persistent_weakness_registry", "independent productivity/investment deterioration labels", "not defined"), _missing("vdem", "institutional histories", "not imported")),
      history={"achieved": "WGI 1996-2025; OECD productivity 1970-2025"},
      countries={"achieved": "8 primary countries"},
      methods=("H02-P0.1 exploratory protocol"),
      support=("Predictors and candidate outcome variables exist.",),
      contra=("No independent outcome registry or held-out evaluation exists.",),
      alternatives=("Productivity weakness may cause institutional deterioration rather than follow it.",),
      refs=CORE_REFERENCES + (WB_REFERENCE,),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H02",)),

    q("Q27", "internal_conflict", "Do income and wealth inequality predict later political instability or weaker economic performance?", "Inequality and instability",
      theories=("dalio_internal_order_cycle",), forces=("wealth_opportunity_values_gaps", "internal_conflict"),
      required=(_ds("inequality_panel", "income/wealth distribution", "predictors"), _ds("instability_growth_outcomes", "independent outcomes", "labels")),
      available=(_ds("world_bank", "GINI_INDEX", "income inequality"), _ds("wid", "WEALTH_SHARE_TOP_10", "wealth inequality"), _ds("oecd", "productivity", "economic outcome proxy")),
      missing=(_missing("protest_conflict_outcomes", "verified instability events", "not imported"), _missing("persistent_weakness_registry", "economic weakness labels", "not defined")),
      history={"achieved": "wealth share to 1800 for selected series; Gini irregular"},
      countries={"achieved": "8 primary countries"},
      methods=("separate inequality source definitions"),
      support=("Income and wealth measures are preserved separately.",),
      contra=("No independent instability outcome evaluation exists.",),
      alternatives=("Instability and inequality can be jointly caused by shocks, institutions or elite conflict.",),
      implementation="data_available", validation="untested", hypotheses=("H02",)),

    q("Q28", "internal_conflict", "Does political polarisation precede internal conflict, institutional breakdown or policy instability?", "Political polarisation",
      theories=("dalio_internal_order_cycle",), forces=("internal_conflict", "leadership_capabilities"),
      required=(_ds("polarisation_panel", "polarisation measures", "predictors"), _ds("internal_conflict_outcomes", "verified conflict/breakdown outcomes", "labels")),
      available=(_ds("world_bank", "POLITICAL_STABILITY_WGI_SCORE", "perception proxy"),),
      missing=(_missing("vdem", "polarisation/institutional measures", "not imported"), _missing("ucdp_acled", "event outcomes", "access/licensing not resolved")),
      history={"achieved": "WGI 1996-2025 only"},
      countries={"achieved": "8 primary countries"},
      methods=("source-definition separation"),
      support=("A perception-based stability proxy is tracked.",),
      contra=("WGI perception scores are not counts of protests or breakdown events.",),
      alternatives=("Polarisation can be a symptom of underlying economic or institutional stress.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H02",)),

    q("Q29", "internal_conflict", "Do regime characteristics predict how countries manage debt, shocks or economic transitions?", "Regime characteristics",
      theories=("dalio_internal_order_cycle",), forces=("rule_of_law", "leadership_capabilities"),
      required=(_ds("regime_panel", "regime/institutional classifications", "features"), _ds("debt_shock_outcomes", "independent outcomes", "labels")),
      available=(_ds("world_bank", "WGI governance scores", "partial institutional proxies"),),
      missing=(_missing("vdem", "regime and institutional characteristics", "not imported"), _missing("policy_response_outcomes", "shock-management labels", "not defined")),
      history={"achieved": "WGI 1996-2025"},
      countries={"achieved": "8 primary countries"},
      methods=("hypothesis fields reserved for institutional predictors"),
      support=("Governance proxies are tracked without assuming regime superiority.",),
      contra=("No regime outcome test is possible with current evidence.",),
      alternatives=("Economic structure, external constraints and geopolitical support may dominate regime labels.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H02",)),

    q("Q30", "internal_conflict", "Do independently recorded protests, unrest or civil conflict provide useful internal-order outcomes?", "Recorded unrest outcomes",
      theories=("dalio_internal_order_cycle",), forces=("internal_conflict",),
      required=(_ds("ucdp_acled", "event-level unrest/conflict", "outcomes"), _ds("internal_order_predictors", "institutional/economic predictors", "features")),
      available=(_ds("crisis_registry", "event/coverage schema", "reusable outcome contract"),),
      missing=(_missing("ucdp", "conflict events", "not imported"), _missing("acled", "protest/conflict events", "not imported; licensing/access review needed")),
      history={"status": "schema only"}, countries={"status": "schema only"},
      methods=("independent outcome registry supports non-crisis event types"),
      support=("The registry is reusable beyond banking crises.",),
      contra=("No unrest/conflict outcomes are populated.",),
      alternatives=("Recorded unrest depends on reporting coverage and state repression as well as underlying grievance.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H02",)),

    q("Q31", "internal_conflict", "Do widening wealth and opportunity gaps precede internal-order deterioration?", "Wealth and opportunity gaps",
      theories=("dalio_internal_order_cycle",), forces=("wealth_opportunity_values_gaps", "education"),
      required=(_ds("distribution_panel", "wealth/opportunity measures", "predictors"), _ds("internal_order_outcomes", "independent outcomes", "labels")),
      available=(_ds("wid", "WEALTH_SHARE_TOP_10", "wealth concentration"), _ds("world_bank", "GINI and education", "income/opportunity proxies"), _ds("oecd", "attainment", "opportunity proxy")),
      missing=(_missing("internal_order_outcomes", "verified deterioration events", "not imported"), _missing("opportunity_mobility", "intergenerational mobility", "not imported")),
      history={"achieved": "WID wealth history plus modern WDI/OECD"},
      countries={"achieved": "8 primary countries"},
      methods=("source-defined inequality measures"),
      support=("Long WID wealth-share history exists.",),
      contra=("No internal-order outcome labels are available for evaluation.",),
      alternatives=("Opportunity gaps may persist without observed instability; political response mediates outcomes.",),
      implementation="data_available", validation="untested", hypotheses=("H02",)),

    q("Q32", "internal_conflict", "Do education and human-capital changes predict resilience to internal or economic stress?", "Human-capital resilience",
      theories=("dalio_internal_order_cycle",), forces=("education", "productivity_output_growth"),
      required=(_ds("education_panel", "attainment/enrollment/researchers", "predictors"), _ds("stress_resilience_outcomes", "independent outcomes", "labels")),
      available=(_ds("oecd", "tertiary attainment", "education stock"), _ds("world_bank", "enrollment/researchers", "education inputs")),
      missing=(_missing("barro_lee", "long education attainment", "not imported"), _missing("stress_resilience_registry", "recovery/resilience labels", "not defined")),
      history={"achieved": "1970-2025 modern coverage with sparse CHN/IND"},
      countries={"achieved": "8 primary countries"},
      methods=("coverage-aware education measures"),
      support=("Education inputs and attainment are imported separately.",),
      contra=("No resilience outcome evaluation exists.",),
      alternatives=("Education may proxy broader development rather than directly produce resilience.",),
      implementation="data_available", validation="untested", hypotheses=("H02",)),

    q("Q33", "internal_conflict", "Do declining investment and productivity precede broader institutional deterioration?", "Investment and productivity decline",
      theories=("dalio_internal_order_cycle",), forces=("productivity_output_growth", "infrastructure_investment", "resource_allocation_efficiency"),
      required=(_ds("investment_productivity_panel", "predictors/outcomes", "features"), _ds("institutional_outcomes", "independent deterioration labels", "outcomes")),
      available=(_ds("world_bank", "GROSS_CAPITAL_FORMATION_GDP", "investment"), _ds("oecd", "LABOUR_PRODUCTIVITY_PER_HOUR", "productivity"), _ds("world_bank", "WGI", "institutional proxy")),
      missing=(_missing("institutional_deterioration_registry", "independent outcome labels", "not defined")),
      history={"achieved": "investment 1960-2025; productivity 1970-2025"},
      countries={"achieved": "8 primary countries"},
      methods=("H02 candidate predictor/outcome fields"),
      support=("Investment and productivity series exist.",),
      contra=("No independent institutional deterioration chronology exists; reverse causality is plausible.",),
      alternatives=("Economic decline may cause institutional stress rather than precede it.",),
      implementation="data_available", validation="untested", hypotheses=("H02",)),

    q("Q34", "internal_conflict", "Are some political systems systematically better at managing debt burdens and economic shocks?", "Political systems and stress",
      theories=("dalio_internal_order_cycle",), forces=("leadership_capabilities", "rule_of_law", "indebtedness"),
      required=(_ds("regime_panel", "political-system measures", "features"), _ds("debt_shock_outcomes", "independent outcomes", "labels")),
      available=(_ds("world_bank", "WGI proxies", "partial governance measures"), _ds("bis", "DSR/credit gap", "debt burden")),
      missing=(_missing("vdem", "regime characteristics", "not imported"), _missing("policy_response_outcomes", "shock/debt-management outcomes", "not defined")),
      history={"achieved": "modern WGI/BIS only"},
      countries={"achieved": "8 primary countries"},
      methods=("non-normative source registry"),
      contra=("No evidence supports a universal political-system claim.",),
      alternatives=("Outcomes may reflect income, external position, institutions or luck rather than regime type.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H02",)),

    q("Q35", "internal_conflict", "Can internal conflict be distinguished from ordinary political competition using reproducible outcome definitions?", "Internal conflict definition",
      theories=("dalio_internal_order_cycle",), forces=("internal_conflict",),
      required=(_ds("conflict_outcome_definitions", "event typology and thresholds", "labels"), _ds("event_sources", "UCDP/ACLED or equivalent", "evidence")),
      available=(_ds("crisis_registry", "event-state/coverage model", "reusable schema"), _ds("world_bank", "POLITICAL_STABILITY_WGI_SCORE", "perception proxy")),
      missing=(_missing("ucdp_acled", "verified conflict/protest event data", "not imported")),
      history={"status": "schema only"}, countries={"status": "schema only"},
      methods=("event onset/state/coverage separation"),
      support=("Unknown coverage and non-events are represented explicitly.",),
      contra=("Perception scores cannot substitute for recorded conflict events.",),
      alternatives=("Election disputes and peaceful competition must remain outside crisis labels unless source definitions say otherwise.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H02",)),

    q("Q36", "external_rivalry", "Does convergence in relative international power precede rivalry, conflict or crisis risk?", "Power convergence and rivalry",
      theories=("dalio_external_order_cycle",), powers=("economic_output", "international_trade", "military_strength", "financial_centre_strength"),
      required=(_ds("relative_power_panel", "separated power measures", "features"), _ds("rivalry_conflict_outcomes", "independent outcomes", "labels")),
      available=(_ds("world_bank", "GDP/trade/military/financial proxies", "power measures"), COFER_DATA[0], BIS_FX_DATA[0], BIS_LBS_DATA[0], _ds("power_registry", "measure definitions", "methodology")),
      missing=(_missing("cow", "rivalry/conflict outcomes", "not imported"), _missing("historical_power_transitions", "transition outcomes", "not imported")),
      history={"achieved": "modern power shares 1960-2025 + COFER/BIS currency & banking panels"},
      countries={"achieved": "8 primary countries + global denominators + currency areas"},
      methods=("H03-P0.1 exploratory protocol", "separated power-measure registry"),
      support=("Power dimensions and currency shares are tracked without collapsing into a universal score.",),
      contra=("No independent rivalry or transition outcomes exist.",),
      alternatives=("Rivalry may be triggered by security commitments, ideology or shocks rather than power convergence alone.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H03",)),

    q("Q37", "external_rivalry", "Do changes in global economic-output shares predict changes in international influence?", "Output shares and influence",
      theories=("dalio_external_order_cycle",), powers=("economic_output",),
      required=(_ds("global_output_shares", "denominator-safe shares", "features"), _ds("influence_outcomes", "independent influence/order outcomes", "labels")),
      available=(_ds("world_bank", "GDP current/PPP/real + global denominators", "output shares"), PWT_DATA[0], MADDISON_DATA[0], _ds("power_registry", "economic_output definitions", "methodology")),
      missing=(_missing("influence_outcomes", "independent influence/order transitions", "not imported"),),
      history={"achieved": "WDI global shares 1960-2025; PWT 1950-2023; Maddison 1500-2022"},
      countries={"achieved": "8 primary + 20 research countries + world denominators"},
      methods=("denominator-safe global-share calculations", "PPP benchmark separation"),
      support=("Multiple output definitions (current USD, WDI PPP, constant 2015 USD, PWT 2021 PPP, Maddison 2011 intl $) are preserved separately.",),
      contra=("Output shares alone do not establish political or institutional influence.",),
      alternatives=("Trade, finance, institutions and alliances may mediate economic scale.",),
      implementation="data_available", validation="untested", hypotheses=("H03",), chart={"kind": "indicator", "indicator_code": "GDP_PPP_CURRENT_INTL", "entity_code": "USA", "label": "PPP GDP — USA"}),

    q("Q38", "external_rivalry", "Do global trade shares and bilateral dependence predict rivalry or cooperation?", "Trade shares and dependence",
      theories=("dalio_external_order_cycle",), forces=("trade_capital_flows", "global_openness"), powers=("international_trade",),
      required=(_ds("trade_share_panel", "global and bilateral trade", "features"), _ds("rivalry_cooperation_outcomes", "independent outcomes", "labels")),
      available=(_ds("world_bank", "merchandise/services exports and imports", "global trade shares"), _ds("jst_macrohistory", "exports/imports", "historical trade proxies")),
      missing=(_missing("un_comtrade", "bilateral trade", "planned provider not imported"), _missing("rivalry_outcomes", "independent rivalry/cooperation labels", "not imported")),
      history={"achieved": "modern 1980-2025; JST historical proxy"},
      countries={"achieved": "8 primary + 18 JST"},
      methods=("denominator-safe trade-share measures"),
      support=("Global trade-share inputs exist for the primary panel.",),
      contra=("Bilateral dependence and outcomes are missing.",),
      alternatives=("Trade can restrain conflict or create leverage and vulnerability; direction is not assumed.",),
      implementation="data_available", validation="untested", hypotheses=("H03",)),

    q("Q39", "external_rivalry", "Do reserve-currency shares predict monetary influence and adjustment capacity?", "Reserve shares and influence",
      theories=("dalio_money_credit_debt_cycle", "dalio_external_order_cycle"), powers=("reserve_currency_status",),
      required=(_ds("imf_cofer", "reserve currency shares", "features"), _ds("monetary_influence_outcomes", "independent outcomes", "labels")),
      available=COFER_DATA + BIS_FX_DATA + BIS_LBS_DATA + (_ds("currency_research_entities", "currency-area definitions", "schema"),),
      missing=(_missing("monetary_transition_outcomes", "independent monetary-order transition labels", "not imported"), _missing("pre_1995_reserve_shares", "pre-1995 reserve currency archive", "not imported")),
      history={"achieved": "COFER 1995-2026Q2; BIS FX turnover 1989-2025; BIS LBS 1977Q4-2026Q2"},
      countries={"achieved": "Currency areas (USD, EUR, CNY, GBP, JPY, CHF, INR in FX turnover, DEM/FRF 1989-1998)"},
      methods=("currency-area separation", "methodology-break preservation"),
      support=("Reserve shares, FX turnover shares and cross-border bank-claim currency shares are imported with EUR kept at currency-area level and INR kept non-zero-imputed where unreported.",),
      contra=("Independent monetary-order transition outcomes are not populated.",),
      alternatives=("Reserve status may lag real economic output and reflect financial openness, legal trust and network effects.",),
      implementation="data_available", validation="currently_untestable", hypotheses=("H03",),
      chart={"kind": "research_observation", "source_key": "bis_fx_turnover", "dataset_version": "WS_DER_OTC_TOV", "variable_code": "FX_TURNOVER_SHARE_200PCT", "entity_code": "USD", "label": "BIS Triennial FX turnover share (200% sum) — USD"}),

    q("Q40", "external_rivalry", "Do military resource measures predict external-order transitions better than military expenditure alone?", "Military resources",
      theories=("dalio_external_order_cycle",), forces=("military_strength",), powers=("military_strength",),
      required=(_ds("military_capability_panel", "personnel/material/expenditure", "features"), _ds("external_transition_outcomes", "order-transition outcomes", "labels")),
      available=(_ds("world_bank", "SIPRI-derived military expenditure", "resource proxy"),),
      missing=(_missing("cow_nmc", "Correlates of War capabilities", "not imported"), _missing("sipri_full", "direct military resource data", "not imported"), _missing("external_order_transitions", "independent outcomes", "not imported")),
      history={"achieved": "modern military expenditure 1960-2025"},
      countries={"achieved": "8 primary countries"},
      methods=("expenditure kept separate from capability"),
      support=("Military spending is explicitly labelled a resource proxy, not capability.",),
      contra=("No capability or transition outcomes exist for evaluation.",),
      alternatives=("Technology, alliances, geography and readiness can dominate spending.",),
      implementation="data_available", validation="untested", hypotheses=("H03",)),

    q("Q41", "external_rivalry", "Do international banking and financial-centre activity predict monetary or financial influence?", "Financial-centre activity",
      theories=("dalio_external_order_cycle",), powers=("financial_centre_strength", "reserve_currency_status"),
      required=(_ds("international_banking", "cross-border claims and centre activity", "features"), _ds("financial_influence_outcomes", "independent outcomes", "labels")),
      available=BIS_LBS_DATA + BIS_FX_DATA + (_ds("world_bank", "listed-market capitalisation, private credit, broad money", "domestic depth proxies"),),
      missing=(_missing("financial_influence_outcomes", "independent financial-order outcome labels", "not defined"),),
      history={"achieved": "BIS LBS cross-border banking 1977Q4-2026Q2 + BIS FX turnover 1989-2025 + modern domestic depth"},
      countries={"achieved": "8 primary countries + global BIS reporting total"},
      methods=("domestic market depth separated from cross-border banking intermediation"),
      support=("BIS LBS shows UK leads cross-border banking share (14.3% in 2026Q2) while US leads equity market cap, demonstrating why stock-market cap/GDP is an incomplete financial-centre measure.",),
      contra=("No independent financial-influence outcome labels exist for predictive testing.",),
      alternatives=("Financial influence may depend on legal jurisdiction, clearing infrastructure, currency networks and capital-account openness.",),
      implementation="data_available", validation="currently_untestable", hypotheses=("H03",),
      chart={"kind": "research_observation", "source_key": "bis_lbs", "dataset_version": "WS_LBS_D_PUB", "variable_code": "LBS_REPORTING_CLAIMS_SHARE_PCT", "entity_code": "GBR", "label": "BIS cross-border bank claims share (%) — GBR"}),

    q("Q42", "external_rivalry", "Do alliances and bloc formation change the probability of rivalry or conflict?", "Alliances and blocs",
      theories=("dalio_external_order_cycle",), required=(_ds("alliance_panel", "alliance/bloc histories", "features"), _ds("conflict_outcomes", "independent rivalry/conflict outcomes", "labels")),
      available=(),
      missing=(_missing("cow_alliances", "alliance histories", "not imported"), _missing("ucdp_cow", "conflict outcomes", "not imported")),
      history={"status": "missing"}, countries={"status": "missing"},
      methods=("external-order hypothesis registered without outcome evidence"),
      contra=("No alliance or conflict observations are imported.",),
      alternatives=("Alliances may deter conflict, provoke balancing, or merely reflect pre-existing alignment.",),
      implementation="not_implemented", validation="currently_untestable", hypotheses=("H03",)),

    q("Q43", "external_rivalry", "Are historical power transitions associated with identifiable economic, financial and military sequences?", "Historical power transitions",
      theories=("dalio_external_order_cycle", "dalio_big_cycle"), powers=("economic_output", "international_trade", "military_strength", "financial_centre_strength", "reserve_currency_status"),
      required=(_ds("historical_power_panel", "multi-century power measures", "features"), _ds("power_transition_outcomes", "independent transitions", "labels")),
      available=JST_DATA + MADDISON_DATA + PWT_DATA + (_ds("world_bank", "modern power proxies", "post-1960 evidence"),),
      missing=(_missing("cow_nmc", "historical capabilities", "not imported"), _missing("historical_order_transitions", "dated transitions", "not imported")),
      history={"achieved": "Maddison 1500-2022, JST 1870-2020, PWT 1950-2023, modern shares"},
      countries={"achieved": "20 research countries + 8 primary"},
      methods=("separate long-cycle research layer"),
      support=("Maddison, JST and PWT provide long economic/financial context.",),
      contra=("No independently dated transition outcomes or historical military capability series are imported.",),
      alternatives=("Sequences may differ across monetary, industrial and military eras.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H03", "H04")),

    q("Q44", "external_rivalry", "Can concentration or multipolarity in power measures be quantified without a universal national power score?", "Power concentration",
      theories=("dalio_external_order_cycle",), powers=("economic_output", "international_trade", "military_strength", "financial_centre_strength", "innovation_technology"),
      required=(_ds("compatible_reference_population", "global denominators", "features"), _ds("power_measure_registry", "separated dimensions", "methodology")),
      available=(_ds("power_registry", "separated measure definitions", "methodology"), _ds("world_bank", "global denominator series", "share calculations"), COFER_DATA[0], BIS_LBS_DATA[0]),
      missing=(_missing("concentration_metric_protocol", "registered HHI/shares method across complete global universe", "not implemented"),),
      history={"achieved": "modern denominator-safe global shares + currency/banking denominators"},
      countries={"achieved": "8 primary + world/BIS/COFER denominators"},
      methods=("separate dimensions", "no universal power composite"),
      support=("The design explicitly avoids a manufactured national power score.",),
      contra=("Concentration across only 8 tracked countries cannot compute a full global Herfindahl index without rest-of-world country shares.",),
      alternatives=("Different dimensions imply different concentration patterns (e.g. multipolar PPP GDP vs concentrated USD FX/reserve role).",),
      implementation="research_method_implemented", validation="untested", hypotheses=("H03",)),

    q("Q45", "external_rivalry", "Can shared international leadership or distributed influence persist without a single hegemonic transition?", "Shared leadership",
      theories=("dalio_external_order_cycle", "dalio_big_cycle"), powers=("economic_output", "international_trade", "financial_centre_strength", "reserve_currency_status"),
      required=(_ds("distributed_power_panel", "multi-dimensional shares", "features"), _ds("leadership_outcomes", "independent order/leadership labels", "outcomes")),
      available=(_ds("power_registry", "separated measures", "methodology"), _ds("world_bank", "modern shares", "partial predictors")),
      missing=(_missing("leadership_transition_outcomes", "independent order labels", "not imported"), _missing("institutional_influence", "international institutional roles", "not imported")),
      history={"status": "modern partial panel"},
      countries={"status": "requires global reference population"},
      methods=("distributed measures rather than a single score"),
      support=("The schema allows distributed influence and unclassified states.",),
      contra=("No outcome chronology can test hegemonic versus shared leadership.",),
      alternatives=("Institutional delegation and regional blocs can sustain shared influence.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H03", "H04")),

    q("Q46", "technology_shocks", "Do R&D expenditure, patent activity and research capacity predict durable technological advantage?", "Innovation inputs and outputs",
      theories=("dalio_external_order_cycle",), forces=("education", "infrastructure_investment"), powers=("innovation_technology",),
      required=(_ds("innovation_panel", "R&D/patents/researchers", "features"), _ds("technology_outcomes", "durable advantage labels", "outcomes")),
      available=(_ds("world_bank", "R&D, patents, researchers, high-tech exports", "innovation proxies"),),
      missing=(_missing("wipo_full", "patent quality/family data", "not imported"), _missing("technology_advantage_outcomes", "independent leadership labels", "not defined")),
      history={"achieved": "modern innovation coverage; high-tech exports only 2007-2024"},
      countries={"achieved": "8 primary countries"},
      methods=("separated innovation input/output measures"),
      support=("Input, output and trade proxies are tracked separately.",),
      contra=("No durable-advantage outcome or long-run evaluation exists.",),
      alternatives=("Patent counts and R&D intensity may not capture diffusion, quality or state-led capability.",),
      implementation="data_available", validation="untested", hypotheses=("H03",)),

    q("Q47", "technology_shocks", "Do productivity and human-capital measures predict long-run economic resilience?", "Productivity and human capital",
      theories=("dalio_internal_order_cycle",), forces=("productivity_output_growth", "education"),
      required=(_ds("productivity_human_capital", "productivity/attainment/research", "features"), _ds("resilience_outcomes", "independent resilience labels", "outcomes")),
      available=PWT_DATA + (_ds("oecd", "labour productivity and tertiary attainment", "human-capital/productivity"), _ds("world_bank", "education and researchers", "human-capital inputs")),
      missing=(_missing("resilience_outcomes", "independent resilience outcome labels", "not defined"),),
      history={"achieved": "PWT 11.0 (1950-2023 real GDP, worker/hour productivity, capital, hc, ctfp/rtfpna) + OECD 1970-2025"},
      countries={"achieved": "20 research countries + 8 primary"},
      methods=("separate PWT 2021 PPP, PWT constant national-accounts and OECD-relative productivity definitions"),
      support=("PWT 11.0 real GDP, GDP per worker, GDP per hour (where hours exist), capital stock, human capital index and TFP are imported without combining incompatible PPP bases.",),
      contra=("No independent long-run resilience outcome test exists.",),
      alternatives=("Resilience may reflect macro buffers, institutions or external demand rather than measured human capital alone.",),
      implementation="data_available", validation="untested", hypotheses=("H02", "H03"),
      chart={"kind": "research_observation", "source_key": "pwt", "dataset_version": "11.0", "variable_code": "PWT_CTFP_USA1", "entity_code": "CHN", "label": "PWT 11.0 TFP relative to USA (USA=1) — CHN"}),

    q("Q48", "technology_shocks", "Can AI adoption be measured separately from general technology indicators and does it change power or productivity outcomes?", "AI adoption",
      theories=("dalio_external_order_cycle",), powers=("innovation_technology",),
      required=(_ds("ai_adoption", "comparable AI adoption measures", "features"), _ds("productivity_power_outcomes", "independent outcomes", "labels")),
      available=(),
      missing=(_missing("ai_adoption", "comparable AI usage/capability data", "not imported"), _missing("ai_histories", "long-run AI data", "not available before actual observations")),
      history={"status": "missing", "constraint": "no invented pre-observation AI history"},
      countries={"status": "missing"},
      methods=("separate AI/general-technology rule"),
      contra=("No comparable AI observations are imported.",),
      alternatives=("AI may diffuse unevenly and affect sectors differently; aggregate power effects are not assumed.",),
      implementation="not_implemented", validation="currently_untestable", hypotheses=("H03",)),

    q("Q49", "technology_shocks", "Do energy production, consumption and dependence constrain economic and external power?", "Energy constraint",
      theories=("dalio_big_cycle",), forces=("resource_allocation_efficiency", "geography"), powers=("economic_output",),
      required=(_ds("energy_panel", "production/consumption/dependence", "features"), _ds("power_growth_outcomes", "independent outcomes", "labels")),
      available=(_ds("jst_macrohistory", "long-run economic variables", "indirect context"),),
      missing=(_missing("energy_balances", "IEA/WB energy production/consumption/imports", "not imported"), _missing("resource_outcomes", "independent constraint/shock labels", "not defined")),
      history={"status": "missing direct energy data"},
      countries={"status": "missing"},
      methods=("resource constraints kept separate from general economic output"),
      contra=("No direct energy balance series are imported.",),
      alternatives=("Energy constraints depend on technology, substitution, trade access and prices.",),
      implementation="not_implemented", validation="currently_untestable", hypotheses=("H03", "H04")),

    q("Q50", "technology_shocks", "Do pandemics, natural disasters and resource shocks alter short-, medium- or long-cycle trajectories?", "Pandemics and shocks",
      theories=("dalio_big_cycle",), forces=("acts_of_nature", "geography"),
      required=(_ds("shock_outcomes", "EM-DAT/UCDP/pandemic/resource events", "outcomes"), _ds("cycle_panel", "pre/post shock predictors", "features")),
      available=(_ds("world_bank", "NATURAL_DISASTER_AFFECTED_PCT", "1990-2009 average exposure context"), _ds("crisis_registry", "event/coverage schema", "reusable outcome contract")),
      missing=(_missing("em_dat", "annual disaster events", "not imported"), _missing("pandemic_outcomes", "comparable pandemic histories", "not imported"), _missing("resource_shocks", "independent shock labels", "not imported")),
      history={"achieved": "one structural exposure value per country", "missing": "event chronology"},
      countries={"achieved": "8 primary countries"},
      methods=("separate timescales and event registry"),
      support=("Natural-disaster exposure is labelled a context measure, not a score.",),
      contra=("No shock-event outcomes or causal trajectory evaluation exists.",),
      alternatives=("Shock effects depend on resilience, policy response and global spillovers.",),
      implementation="partially_implemented", validation="currently_untestable", hypotheses=("H04",)),
)

assert len(VALIDATION_QUESTIONS) == 50
assert [q.question_code for q in VALIDATION_QUESTIONS] == [f"Q{i:02d}" for i in range(1, 51)]
