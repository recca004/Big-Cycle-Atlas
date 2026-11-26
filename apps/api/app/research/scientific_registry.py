"""Versioned scientific-theory, protocol and timescale definitions."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

THEORY_REGISTRY_VERSION = "theory-registry-v1.0"
HYPOTHESIS_REGISTRY_VERSION = "hypothesis-registry-v1.0"
TIMESCALE_REGISTRY_VERSION = "timescale-registry-v1.0"


def canonical_checksum(payload: Any) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TheoryEntry:
    theory_code: str
    source_title: str
    source_author: str
    source_edition: str | None
    chapter_section: str | None
    publication_date: str | None
    concept: str
    atlas_interpretation: str
    framework_differences: str | None
    measurement_limitations: str
    framework_scope: str
    atlas_operational: bool
    testable_status: str
    def payload(self) -> dict[str, Any]: return asdict(self)


THEORY_ENTRIES = (
    TheoryEntry("dalio_big_cycle", "Principles for Dealing with the Changing World Order: Why Nations Succeed and Fail", "Ray Dalio", "Avid Reader Press / Simon & Schuster hardcover (ISBN 978-1-9821-6027-2)", "Chapter 1, 'The Big Cycle in a Tiny Nutshell'", "2021-11-30", "A broad historical cycle in which monetary, domestic-order and external-order arrangements rise, interact, break down and are replaced.", "A research framing for measuring related debt, institutional, international-power and conflict evidence — not a validated stage law.", "Atlas separates measured national condition, international power and independent outcomes; it does not adopt a deterministic sequence or calendar advancement.", "The author's narrative synthesis does not specify a unique dataset, frequency, threshold or falsification rule. Atlas's modern panel is far shorter than the claimed historical cycle.", "historical_big_cycle", False, "insufficient_evidence"),
    TheoryEntry("dalio_money_credit_debt_cycle", "Principles for Dealing with the Changing World Order: Why Nations Succeed and Fail", "Ray Dalio", "Avid Reader Press / Simon & Schuster hardcover (ISBN 978-1-9821-6027-2)", "Part I, Chapter 3, 'The Big Cycle of Money, Credit, Debt, and Economic Activity'", "2021-11-30", "Debt, credit, money creation and repayment burdens interact over short debt cycles and longer financial/order cycles.", "Testable as debt, credit, debt-service, external-position and independently defined crisis relationships at annual/quarterly horizons.", "Atlas keeps private debt, public debt and debt-service measures separate and evaluates against independent crisis chronologies.", "Public-debt and external-debt coverage are incomplete; historical release timing is not yet available for most macro predictors.", "debt_monetary_cycle", False, "exploratory_association_possible"),
    TheoryEntry("dalio_internal_order_cycle", "Principles for Dealing with the Changing World Order: Why Nations Succeed and Fail", "Ray Dalio", "Avid Reader Press / Simon & Schuster hardcover (ISBN 978-1-9821-6027-2)", "Part I, Chapter 5, 'The Big Cycle of Internal Order and Disorder'", "2021-11-30", "Internal cohesion, institutional quality, wealth/opportunity gaps and productive capacity strengthen or weaken together over time.", "Institutional deterioration is evaluated as a predictor of later investment/productivity weakness, not as a stage countdown.", "Atlas currently uses partial WGI, education, inequality and productivity proxies; it does not claim complete institutional measurement.", "Values gaps, political conflict and structural institutional change are only partially observed; causal attribution remains unsupported.", "internal_order", False, "exploratory_association_possible"),
    TheoryEntry("dalio_external_order_cycle", "Principles for Dealing with the Changing World Order: Why Nations Succeed and Fail", "Ray Dalio", "Avid Reader Press / Simon & Schuster hardcover (ISBN 978-1-9821-6027-2)", "Part I, Chapter 6, 'The Big Cycle of External Order and Disorder'", "2021-11-30", "Relative international power, rivalry and order transitions are linked to changes in economic, trade, financial, military and monetary influence.", "Atlas publishes separated international-power measures and asks whether convergence predicts independently dated rivalry/crisis events.", "Atlas does not combine power dimensions into a leadership ranking or predict a transition date.", "Reserve shares, international banking, conflict outcomes and pre-1900 entities remain incomplete.", "external_order", False, "insufficient_evidence"),
    TheoryEntry("atlas_17_forces", "Big Cycle Atlas methodology registry", "Cognition / Big Cycle Atlas", "normalization-v1.4 / force-aggregation-v1.0", "apps/api/app/cycle/force_definitions.py", None, "Seventeen Atlas force concepts operationalize dimensions of national condition and influence using approved source indicators.", "An Atlas operational measurement framework with partial coverage ceilings and explicit unscored dimensions.", "The 17 Atlas forces are not a one-to-one quotation of the author's determinants and do not imply the author's approval.", "Several forces remain context-only or dimension-only; incomplete proxies are never silently treated as complete concepts.", "atlas_operational_framework", True, "descriptive_monitoring"),
    TheoryEntry("atlas_eight_stages", "Big Cycle Atlas experimental cycle classifier", "Cognition / Big Cycle Atlas", "cycle-classifier experimental model layer", "apps/api/app/research/cycle.py", None, "Eight Atlas labels used by the experimental national-condition classifier (including RISE, PEAK and DECLINE variants).", "A labelled Atlas operational framework for current/research-state classification only.", "Not represented as the author's original stage structure and not a validated long historical Big Cycle stage map.", "Stage thresholds are sensitivity-tested assumptions; classified periods are retrospective and not release-date-safe.", "atlas_operational_framework", True, "experimental_classifier"),
    TheoryEntry("cycle_duration_approximately_75_years", "Principles for Dealing with the Changing World Order: Why Nations Succeed and Fail", "Ray Dalio", "Avid Reader Press / Simon & Schuster hardcover (ISBN 978-1-9821-6027-2)", "Long-term debt/capital-cycle discussion; exact wording and edition context require page-level citation", "2021-11-30", "An approximate roughly-75-year duration is proposed for long debt/capital-cycle dynamics, with substantial variation.", "A falsifiable duration hypothesis candidate only. Atlas does not use it to advance stages, produce countdowns or date an order transition.", "The claim is not treated as a universal Big Cycle duration and the source context is narrower than a complete civilizational cycle.", "Atlas lacks independent, consistently dated full cycles and boundary-stable entities needed to estimate duration. No numeric duration estimate is currently defensible.", "testable_claim_candidate", False, "untestable_with_current_evidence"),
)


TIMESCALES = (
    {"timescale_code": "short_economic_financial", "label": "Short economic and financial cycle", "candidate_window_years": [1, 5], "candidate_measurements": ["growth", "inflation", "credit conditions", "debt service", "employment", "monetary conditions"], "independent_outcomes": ["recession", "banking crisis", "currency crisis", "sovereign debt crisis"], "status": "candidate_definition_not_natural_law"},
    {"timescale_code": "medium_institutional_financial", "label": "Medium institutional and financial cycle", "candidate_window_years": [5, 25], "candidate_measurements": ["credit expansion", "institutional changes", "investment", "wealth distribution", "productivity", "structural economic change"], "independent_outcomes": ["institutional deterioration", "financial stress", "persistent productivity weakness"], "status": "candidate_definition_not_natural_law"},
    {"timescale_code": "long_historical_big_cycle", "label": "Long historical Big Cycle", "candidate_window_years": [25, 500], "candidate_measurements": ["relative international power", "monetary influence", "military resources", "trade influence", "institutional change", "international order transitions"], "independent_outcomes": ["international order transition", "leadership transition", "external-order breakdown"], "status": "candidate_definition_not_natural_law"},
)


HYPOTHESIS_PROTOCOLS = (
    {
        "hypothesis_code": "H01", "protocol_version": "H01-P1.0",
        "protocol_type": "retrospective_research_protocol",
        "title": "Debt/credit burdens and subsequent systemic banking crises",
        "definition": "Higher private-credit burden and weaker external positions are associated with higher later systemic-banking-crisis onset risk.",
        "scientific_rationale": "Long debt-cycle mechanisms predict repayment stress before financial-system breakdown.",
        "target_outcome": "source-defined systemic banking crisis onset (initially JST crisisJST=1)",
        "research_population": {"population_code": "jst_extended_research_v1", "entity_type": "country", "selection_rule": "predefined JST R6 source coverage; outcomes were not used to select countries"},
        "predictor_variables": {"primary": ["debtgdp"], "secondary": ["ca", "tloans", "money", "stir"], "transformation": "lagged level and five-year change; source units preserved"},
        "information_cutoff_rules": {"execution_mode": "retrospective_latest_vintage", "strict_release_safety": False, "leakage_guard": "predictor period < outcome year; dataset-version fixed to JST R6"},
        "forecast_horizons": {"years": [1, 2, 5], "event": "onset only; ongoing-crisis state is separate"},
        "measurement_method": {"model": "univariate percentile-score benchmark", "benchmark": "country-year base rate", "split": "chronological train/test at 1990"},
        "training_periods": {"start": 1870, "end": 1989}, "validation_periods": {"type": "held_out_chronological_test", "start": 1990, "end": 2020},
        "test_population": {"included_entities": "JST R6 covered countries", "minimum_entity_years": 20},
        "evaluation_metrics": ["auc", "base_rate", "crisis_precision_at_top_quintile", "true_positive_rate", "false_positive_rate"],
        "minimum_evidence": {"minimum_test_events": 10, "minimum_entities": 10},
        "falsification_criteria": "No out-of-sample discrimination above base rate or an exploratory-only result is evidence inconsistent with predictive value.",
        "known_limitations": ["retrospective dataset, not real-time vintages", "annual onset only", "correlated crisis episodes", "JST covers advanced economies only", "IMF 2026 dataset unavailable at implementation time"],
        "protocol_status": "exploratory",
    },
    {
        "hypothesis_code": "H02", "protocol_version": "H02-P0.1",
        "protocol_type": "exploratory_analysis",
        "title": "Institutional deterioration and later investment/productivity weakness",
        "definition": "WGI deterioration and inequality/institutional proxies are candidates for predicting later investment or productivity weakness.",
        "scientific_rationale": "Internal-order theory links institutional cohesion to productive capacity.",
        "target_outcome": "independently defined persistent productivity/investment weakness (outcome registry not yet populated)",
        "research_population": {"population_code": "primary_observatory_v1"}, "predictor_variables": {"candidates": ["RULE_OF_LAW_WGI_SCORE", "CONTROL_OF_CORRUPTION_WGI_SCORE", "POLITICAL_STABILITY_WGI_SCORE", "GINI_INDEX"]},
        "information_cutoff_rules": {"strict_release_safety": False}, "forecast_horizons": {"years": [5, 10]},
        "measurement_method": {"status": "outcome definition required before evaluation"}, "training_periods": {}, "validation_periods": {}, "test_population": {},
        "evaluation_metrics": [], "minimum_evidence": {"status": "not_met"}, "falsification_criteria": "Unavailable outcome evidence means untestable, not supported.", "known_limitations": ["no approved outcome registry yet"], "protocol_status": "untestable_with_current_evidence",
    },
    {
        "hypothesis_code": "H03", "protocol_version": "H03-P0.1",
        "protocol_type": "exploratory_analysis",
        "title": "Relative international-power convergence and rivalry/crisis risk",
        "definition": "Power convergence between major states may precede independently dated rivalry, conflict or order-transition episodes.",
        "scientific_rationale": "External-order theory proposes challenger/incumbent transitions.",
        "target_outcome": "independent rivalry, conflict or order-transition outcome registry (not populated)",
        "research_population": {"population_code": "primary_observatory_v1"}, "predictor_variables": {"candidates": ["global GDP share", "trade share", "military share", "financial depth", "reserve share"]},
        "information_cutoff_rules": {"strict_release_safety": False}, "forecast_horizons": {"years": [5, 10, 20]},
        "measurement_method": {"status": "outcome registry required"}, "training_periods": {}, "validation_periods": {}, "test_population": {},
        "evaluation_metrics": [], "minimum_evidence": {"status": "not_met"}, "falsification_criteria": "No independent outcome evidence means untestable.", "known_limitations": ["reserve/cross-border banking/conflict outcomes missing"], "protocol_status": "untestable_with_current_evidence",
    },
    {
        "hypothesis_code": "H04", "protocol_version": "H04-P0.1",
        "protocol_type": "exploratory_analysis",
        "title": "Recurring long sequences of monetary, domestic and external order changes",
        "definition": "Historical orders may recur through a long sequence spanning decades to centuries.",
        "scientific_rationale": "The broad Big Cycle claim motivates separated long-run measurements.",
        "target_outcome": "independently dated complete order-transition cycles (not populated)",
        "research_population": {"population_code": "historical_entities_future_v0"}, "predictor_variables": {"status": "undefined"},
        "information_cutoff_rules": {"strict_release_safety": False}, "forecast_horizons": {"years": [25, 500]},
        "measurement_method": {"status": "insufficient independent chronology"}, "training_periods": {}, "validation_periods": {}, "test_population": {},
        "evaluation_metrics": [], "minimum_evidence": {"status": "not_met"}, "falsification_criteria": "Current evidence cannot test a universal duration or deterministic sequence.", "known_limitations": ["no consistent multi-century entities or outcomes"], "protocol_status": "untestable_with_current_evidence",
    },
)


DATASET_RIGHTS = (
    {"source_key": "jst_macrohistory", "dataset_version": "R6", "license_code": "CC-BY-NC-SA-4.0", "attribution_required": True, "raw_redistribution": "noncommercial_sharealike_review", "derived_publication": "noncommercial_with_attribution", "commercial_use": "prohibited", "share_alike": True, "publication_status": "review_required", "rights_reference": "https://www.macrohistory.net/database/ and JST_documentationR6.pdf", "notes": "R6 documentation grants no-cost noncommercial academic use/share with attribution and identical terms; public release remains pending legal review."},
    {"source_key": "imf_laeven_valencia_banking_crises", "dataset_version": "WP-2026-094", "license_code": None, "attribution_required": True, "raw_redistribution": "review_required", "derived_publication": "review_required", "commercial_use": "review_required", "share_alike": False, "publication_status": "unavailable_access_blocked", "rights_reference": "https://www.imf.org/en/publications/wp/issues/2026/05/14/systemic-banking-crises-database-1970-2025-576036", "notes": "Laeven & Valencia (May 15, 2026, WP/26/94, DOI 10.5089/9798229045971.001); official wp2694.zip returned HTTP 403/404 without local bundle."},
    {"source_key": "alfred_fred", "dataset_version": "api-v1", "license_code": "FRED API terms", "attribution_required": True, "raw_redistribution": "review_required", "derived_publication": "review_required", "commercial_use": "review_required", "share_alike": False, "publication_status": "credential_blocked", "rights_reference": "https://fred.stlouisfed.org/docs/api/fred/", "notes": "Vintage endpoints require a registered 32-character API key; no key is configured."},
    {"source_key": "imf_cofer", "dataset_version": "COFER-SDMX-2.1", "license_code": "IMF-Terms-of-Use", "attribution_required": True, "raw_redistribution": "noncommercial_with_attribution", "derived_publication": "permitted_with_attribution", "commercial_use": "restricted", "share_alike": False, "publication_status": "permitted_noncommercial", "rights_reference": "https://www.imf.org/en/about/copyright-and-terms", "notes": "IMF COFER retrieved from official IMF SDMX 2.1 API; non-commercial research redistribution permitted with IMF attribution."},
    {"source_key": "bis_fx_turnover", "dataset_version": "WS_DER_OTC_TOV", "license_code": "BIS-Terms", "attribution_required": True, "raw_redistribution": "permitted_with_attribution", "derived_publication": "permitted_with_attribution", "commercial_use": "review_required", "share_alike": False, "publication_status": "permitted_with_attribution", "rights_reference": "https://www.bis.org/terms_conditions.htm", "notes": "BIS Triennial Central Bank Survey FX turnover; free to use and reproduce for research with BIS source citation."},
    {"source_key": "bis_lbs", "dataset_version": "WS_LBS_D_PUB", "license_code": "BIS-Terms", "attribution_required": True, "raw_redistribution": "permitted_with_attribution", "derived_publication": "permitted_with_attribution", "commercial_use": "review_required", "share_alike": False, "publication_status": "permitted_with_attribution", "rights_reference": "https://www.bis.org/terms_conditions.htm", "notes": "BIS Locational Banking Statistics public aggregates; free research reproduction with BIS attribution."},
    {"source_key": "bis_credit_policy", "dataset_version": "WS_TC_CBPOL", "license_code": "BIS-Terms", "attribution_required": True, "raw_redistribution": "permitted_with_attribution", "derived_publication": "permitted_with_attribution", "commercial_use": "review_required", "share_alike": False, "publication_status": "permitted_with_attribution", "rights_reference": "https://www.bis.org/terms_conditions.htm", "notes": "BIS Total Credit (WS_TC) and Policy Rates (WS_CBPOL); underlying national-source series subject to BIS citation terms."},
    {"source_key": "pwt", "dataset_version": "11.0", "license_code": "CC-BY-4.0", "attribution_required": True, "raw_redistribution": "permitted_with_attribution", "derived_publication": "permitted_with_attribution", "commercial_use": "permitted_with_attribution", "share_alike": False, "publication_status": "permitted_open_license", "rights_reference": "https://doi.org/10.34894/FABVLR", "notes": "Penn World Table 11.0 by Feenstra, Inklaar & Timmer (GGDC), licensed CC BY 4.0; cite AER 2015 + PWT 11.0 DOI."},
    {"source_key": "maddison", "dataset_version": "2023", "license_code": "CC-BY-4.0", "attribution_required": True, "raw_redistribution": "permitted_with_attribution", "derived_publication": "permitted_with_attribution", "commercial_use": "permitted_with_attribution", "share_alike": False, "publication_status": "permitted_open_license", "rights_reference": "https://doi.org/10.34894/INZBF2", "notes": "Maddison Project Database 2023 by Bolt & van Zanden (GGDC), licensed CC BY 4.0; 20-country panel imported (>=12 countries) and original country sources cited when graphed."},
)
