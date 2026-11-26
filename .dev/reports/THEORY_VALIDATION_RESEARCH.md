# Big Cycle Atlas — 50-Question Scientific Validation Research Report

- Generated: `2026-11-26T09:57:59.064572Z`
- Verified source-code commit: `b92788c1593299b57268182f294d9fd48a2bfe46`
- Active registry version: `validation-questions-v1.2` (preserved versions: `validation-questions-v1.0, validation-questions-v1.1, validation-questions-v1.2`)
- Wording provenance: `atlas_derived_v1` — Atlas-authored canonical wording v1 (never represented as original verbatim Ray Dalio wording)

## 1. Executive Summary & Scientific Boundaries

Big Cycle Atlas separates **engineering/data implementation coverage** from **empirical scientific validation** across all 50 registered research questions (Q01–Q50). Importing a dataset, rendering a chart, or exposing an API endpoint never marks a theoretical claim as validated.

### Current Status Distribution (`validation-questions-v1.1`)

| Axis | Status | Questions |
|---|---|---:|
| Implementation | `data_available` | 17 |
| Implementation | `evaluation_implemented` | 3 |
| Implementation | `not_implemented` | 4 |
| Implementation | `partially_implemented` | 21 |
| Implementation | `research_method_implemented` | 5 |
| Scientific validation | `currently_untestable` | 25 |
| Scientific validation | `evaluated_with_no_clear_conclusion` | 2 |
| Scientific validation | `exploratory_findings` | 1 |
| Scientific validation | `insufficient_evidence` | 7 |
| Scientific validation | `untested` | 15 |

## 2. Investigation of the Three Contradictory Findings (`evidence_inconsistent_with_registered_claim`)

Exact question codes with `evidence_inconsistent_with_registered_claim`: **`Q11`**, **`Q14`**, and **`Q17`**.

All three link to protocol `H01-P1.0` (`debtgdp_5y_change_univariate`, chronological holdout split at `1990` on Jordà–Schularick–Taylor Macrohistory Database `R6`, 18 advanced economies, `1870–2020`, `2,668` covered country-years, `88` systemic banking-crisis onsets). Per scientific protocol rules, **`H01-P1.0` and all contradictory evaluation records are preserved unchanged**.

### 2.1 Exact Reproduction of `H01-P1.0` (`debtgdp` 5-year change)

| Horizon | Total samples | Train (<1990) | Test (1990–2020) | Held-out events | Base rate | Held-out AUC | Top-p80 precision | Confusion at train-p80 (TP/FP/FN/TN) |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1y | 2326 | 1770 | 556 | 19 | 3.42% | 0.3628 | 1.54% | `3 / 192 / 16 / 345` |
| 2y | 2308 | 1752 | 556 | 19 | 3.42% | 0.3815 | 1.50% | `3 / 197 / 16 / 340` |
| 5y | 2254 | 1700 | 554 | 19 | 3.43% | 0.2962 | 0.88% | `2 / 224 / 17 / 311` |

### 2.2 Forensic Audit Checks Across Q11, Q14, and Q17

1. **Units & underlying data verification:** In JST R6, `debtgdp` is the **public (general government) debt-to-GDP ratio** expressed as a decimal ratio (e.g. USA `1945 = 1.134`, `1980 = 0.325`, `2007 = 0.626`, `2010 = 0.912`, `2020 = 1.281`), whereas `tloans` and `gdp` are in nominal local currency (`tloans / gdp` = private bank loans to the non-financial private sector as a ratio of GDP, e.g. USA `2000 = 0.504`, `2007 = 0.620`). Interest rates (`stir`, `ltrate`) are in percent per annum.
2. **Look-ahead bias check:** `build_samples()` strictly enforces `origin = outcome_year - horizon_years` (`origin < outcome_year`), so post-crisis years never enter the predictor calculation numerically. However, two structural temporal limitations exist: (a) JST R6 is a **retrospective 2022 academic release** rather than real-time vintage data, and (b) annual dating means for `horizon = 1` and a late-year crisis onset, year `t-1` macro aggregates were not published until `t`.
3. **Cross-country event dependence (clustering):** Held-out post-1990 events (`n = 19`) are **heavily clustered in two international crisis waves**, not 19 statistically independent trials:
   - **1990** (1 events): `ITA`
   - **1991** (4 events): `CHE, FIN, GBR, SWE`
   - **1997** (1 events): `JPN`
   - **2007** (2 events): `GBR, USA`
   - **2008** (11 events): `BEL, CHE, DEU, DNK, ESP, FRA, IRL, ITA, NLD, PRT, SWE`
   Thirteen of the 19 held-out crisis onsets (`68.4%`) occurred in `2007–2008` (Global Financial Crisis) and 4 (`21.1%`) in `1991` (Nordic/European banking crises).
4. **Non-stationary quantile threshold drift:** `H01-P1.0` maps test predictors against the `1870–1989` training distribution (`score >= 0.80`). Because peacetime public debt rose secularly after 1975, `score >= 0.80` flagged **`35.1%` (1y), `36.0%` (2y), and `40.8%` (5y)** of post-1990 observations rather than 20%.
5. **Alternative predictor & mechanism test on the exact same 1990–2020 holdout:**

| Candidate predictor (JST R6, split=1990) | 1y AUC | 2y AUC | 5y AUC | 1y p80 flagged % | 1y p80 precision |
|---|---:|---:|---:|---:|---:|
| Public `debtgdp` 5y change (`H01-P1.0` registered) | 0.3627 | 0.3815 | 0.2961 | 35.1% | 1.54% |
| Public `debtgdp` level (threshold diagnostic) | 0.3651 | 0.3941 | 0.4403 | 35.5% | 2.53% |
| Private `tloans/gdp` 5y change (credit boom diagnostic) | 0.7212 | 0.7021 | 0.5902 | 40.3% | 5.80% |
| Private `tloans/gdp` level (financial depth diagnostic) | 0.6230 | 0.6049 | 0.5024 | 82.0% | 3.73% |

### 2.3 Verdict by Question

- **`Q11` (Do rising debt burdens increase the probability of a subsequent systemic banking crisis?):**
  - **Primary causes:** **Overly broad registered claim** + **genuine contradictory evidence against unconditional public-debt growth** + **protocol/definition mismatch**.
  - **Explanation:** `H01-P1.0`'s prose definition referenced private-credit burdens, but its primary coded predictor was `debtgdp` (public debt/GDP) — and `v1.0` even mislabelled the Q11 chart as private credit (fixed in `v1.1`). Empirically, public debt/GDP is often flat or falling during pre-crisis private credit/housing booms (`2002–2007` in `ESP, IRL, GBR, USA`) due to cyclical revenue windfalls, and surges *after* banking crises via bailouts and recession deficits (`AUC 0.30–0.38 < 0.50`). Thus unconditional public-debt growth genuinely fails to predict banking crises.
- **`Q14` (Is there a reproducible debt-to-GDP threshold associated with later crises?):**
  - **Primary causes:** **Weak research method for level thresholds** + **genuine contradictory evidence against time-invariant historical thresholds**.
  - **Explanation:** `H01-P1.0` tested 5-year *changes*, not level cutoffs. When `debtgdp` *levels* are evaluated on the same holdout, AUC remains below random (`0.365 / 0.394 / 0.440`), and when private `tloans/gdp` *levels* are evaluated, secular financial deepening causes `82.0%` of post-1990 observations to exceed the pre-1990 80th percentile (`5y AUC = 0.502`). No universal time-invariant debt-to-GDP threshold is supported.
- **`Q17` (Does rapid private credit expansion precede financial crises independently of income growth?):**
  - **Primary causes:** **Implementation/attribution defect in protocol mapping** + **measurement/clustering limitations**.
  - **Explanation:** `Q17` inherited `evidence_inconsistent_with_registered_claim` from `H01-P1.0` even though `H01-P1.0` tested public `debtgdp` and **never evaluated private credit** (`tloans/gdp`, `CREDIT_PRIVATE_NF_GDP`, or `CREDIT_TO_GDP_GAP`). On the exact same 1990–2020 JST holdout, 5-year private bank-loan/GDP growth (`tloans/gdp`) achieves retrospective AUC `0.721` (1y) and `0.702` (2y). Per scientific rules, `H01-P1.0` is not altered ex-post to make `Q17` pass; instead `Q17`'s preserved contradictory status is documented alongside the recommendation to pre-register `H01B` specifically for private credit with crisis-cluster controls.

## 3. Evaluation of the Exploratory Finding (`Q08`)

- **Question:** `Q08` — *"Which observations would support the theory and which observations would falsify or weaken it?"*
- **Reproduced measurements:** `4` versioned hypothesis protocols (`H01-P1.0`, `H02-P0.1`, `H03-P0.1`, `H04-P0.1`), `7` versioned theory entries separating original Dalio concepts from Atlas operational constructs, `1,666` append-only prediction-ledger entries, `1,666` realised outcomes, `2` append-only evaluation records, and `88` verified JST systemic banking-crisis onsets across `2,668` covered country-years.
- **Effect direction & interpretation:** Demonstrates operationally that the Atlas falsification architecture records and retains negative findings (`H01-P1.0` `v2` = `no_evidence_of_improved_predictive_value`) rather than filtering or re-weighting until a claim appears supported.
- **Uncertainty & limitations:** Only one outcome family (systemic banking crises in 18 advanced economies) has populated independent event labels; `H02`, `H03`, and `H04` remain `untestable_with_current_evidence`.
- **Requirements for stronger conclusions:** Independent outcome registries for (i) sovereign/currency crises, (ii) persistent productivity/institutional deterioration, (iii) interstate rivalry/conflict (`COW`/`UCDP`), and (iv) point-in-time vintage cutoffs (`ALFRED`).

## 4. Prioritised Missing-Dataset Dependency Matrix (Remaining 46 Questions)

Following Workstream B imports (`imf_cofer`, `bis_fx_turnover`, `bis_lbs`, `bis_credit_policy`, `pwt` 11.0, `maddison` 2023 — adding `+42,567` `research_observations` rows for a new total of `154,113`), reserve-currency, FX-turnover, cross-border banking, sectoral credit, policy-rate, TFP/human-capital, and pre-1900 GDP gaps have been closed at the data layer. The highest-leverage remaining missing dependencies are:

| Priority | Missing source / outcome dependency | Dependent questions | Count | Scientific bottleneck addressed |
|---:|---|---|---:|---|
| 1 | `vdem` | Q06, Q26, Q28, Q29, Q34 | 5 | Historical polarization, regime characteristics & institutional change predictors |
| 2 | `historical_entities` | Q02, Q07, Q10 | 3 | Pre-modern & boundary-changing polity continuity rules |
| 3 | `historical_order_transitions` | Q02, Q04, Q43 | 3 | Independent long-cycle stage & international-order transition labels (H04) |
| 4 | `independent_order_transitions` | Q06, Q08, Q10 | 3 | External cycle boundary chronology for duration & sequence tests |
| 5 | `alfred_fred` | Q11, Q16 | 2 | Point-in-time vintage release dates (`BCA_FRED_API_KEY` local setup ready) |
| 6 | `cow` | Q06, Q36 | 2 | Interstate dispute/rivalry outcomes for external-order hypothesis H03 |
| 7 | `cow_nmc` | Q40, Q43 | 2 | Historical military personnel/material capability beyond spending |
| 8 | `currency_crisis_registry` | Q16, Q22 | 2 | Independent currency-crisis onset chronology |
| 9 | `debt_ownership` | Q12, Q21 | 2 | Specialized outcome or predictor registry |
| 10 | `independent_stage_transitions` | Q05, Q09 | 2 | External stage benchmarks to test reversals and plateaus |
| 11 | `persistent_weakness_registry` | Q26, Q27 | 2 | Pre-registered persistent productivity/investment slump labels (H02) |
| 12 | `policy_response_outcomes` | Q29, Q34 | 2 | Specialized outcome or predictor registry |
| 13 | `pre_1995_reserve_shares` | Q19, Q39 | 2 | Specialized outcome or predictor registry |
| 14 | `sovereign_defaults` | Q23, Q24 | 2 | Independent sovereign default & restructuring event chronology |
| 15 | `ucdp_acled` | Q28, Q35 | 2 | Recorded internal conflict & protest event counts (distinct from WGI perceptions) |
| 16 | `acled` | Q30 | 1 | Specialized outcome or predictor registry |
| 17 | `ai_adoption` | Q48 | 1 | Specialized outcome or predictor registry |
| 18 | `ai_histories` | Q48 | 1 | Specialized outcome or predictor registry |

## 5. Registered Hypothesis Protocols & Evaluation Records

### `H01` (`H01-P1.0`) — Debt/credit burdens and subsequent systemic banking crises
- **Status:** `exploratory` (`retrospective_research_protocol`)
- **Definition:** Higher private-credit burden and weaker external positions are associated with higher later systemic-banking-crisis onset risk.
- **Target outcome:** source-defined systemic banking crisis onset (initially JST crisisJST=1)
- **Predictors:** `{"primary": ["debtgdp"], "secondary": ["ca", "tloans", "money", "stir"], "transformation": "lagged level and five-year change; source units preserved"}`
- **Horizons:** `{"years": [1, 2, 5], "event": "onset only; ongoing-crisis state is separate"}` · **Cutoff rules:** `{"execution_mode": "retrospective_latest_vintage", "strict_release_safety": false, "leakage_guard": "predictor period < outcome year; dataset-version fixed to JST R6"}`
- **Falsification criteria:** No out-of-sample discrimination above base rate or an exploratory-only result is evidence inconsistent with predictive value.

### `H01B` (`H01B-P1.0`) — Private-credit expansion and subsequent systemic banking crises
- **Status:** `exploratory` (`retrospective_research_protocol`)
- **Definition:** Private non-financial credit expansion (distinct from public debt) is associated with higher later systemic-banking-crisis onset risk.
- **Target outcome:** source-defined systemic banking crisis onset (JST crisisJST=1), same registry as H01-P1.0
- **Predictors:** `{"primary": ["tloans/gdp five-year change"], "candidates": ["tloans/gdp level", "thh/gdp five-year change", "tbus/gdp five-year change", "tmort/gdp five-year change", "credit-to-GDP gap vs trailing 10y trend", "debt-service proxy (tloans/gdp x stir)", "real house-price 3y growth", "real long-term rate"], "controls": ["debtgdp five-year change (H01-P1.0 reference)", "public interest burden proxy", "income-residualised credit growth"], "transformation": "lagged level and changes measured strictly before outcome year; source units preserved"}`
- **Horizons:** `{"years": [1, 2, 5], "event": "onset only"}` · **Cutoff rules:** `{"execution_mode": "retrospective_latest_vintage", "strict_release_safety": false, "leakage_guard": "predictor period < outcome year; dataset-version fixed to JST R6", "holdout_integrity_disclosure": "The 1990-2020 holdout was already used for exploratory private-credit predictor inspection during the H01-P1.0 forensic audit; it is NOT an untouched confirmatory holdout for predictor selection. All results are retrospective diagnostics."}`
- **Falsification criteria:** No out-of-sample discrimination above the public-debt control or base rate is evidence inconsistent with private-credit predictive value; positive retrospective discrimination remains exploratory, not confirmatory.

### `H01T` (`H01T-P1.0`) — Debt/GDP level thresholds and crisis heterogeneity
- **Status:** `exploratory` (`retrospective_research_protocol`)
- **Definition:** Dedicated research into whether debt-to-GDP LEVEL thresholds (public or private) carry reproducible crisis information — across countries, eras, monetary regimes and debt type — instead of the H01-P1.0 change-based test.
- **Target outcome:** source-defined systemic banking crisis onset (JST crisisJST=1)
- **Predictors:** `{"candidates": ["debtgdp level", "tloans/gdp level"], "transformation": "lagged level at origin; pooled train p80 vs per-country p80 thresholds; regime and era splits"}`
- **Horizons:** `{"years": [1]}` · **Cutoff rules:** `{"execution_mode": "retrospective_latest_vintage", "strict_release_safety": false, "leakage_guard": "thresholds estimated on pre-1990 train only; no threshold fitted to maximise test performance"}`
- **Falsification criteria:** If no level threshold reproduces above-chance discrimination out of sample and per-country thresholds are not portable, the universal-threshold claim is unsupported; conditional heterogeneity then defines the open research question rather than a falsified result.

### `H02` (`H02-P0.1`) — Institutional deterioration and later investment/productivity weakness
- **Status:** `untestable_with_current_evidence` (`exploratory_analysis`)
- **Definition:** WGI deterioration and inequality/institutional proxies are candidates for predicting later investment or productivity weakness.
- **Target outcome:** independently defined persistent productivity/investment weakness (outcome registry not yet populated)
- **Predictors:** `{"candidates": ["RULE_OF_LAW_WGI_SCORE", "CONTROL_OF_CORRUPTION_WGI_SCORE", "POLITICAL_STABILITY_WGI_SCORE", "GINI_INDEX"]}`
- **Horizons:** `{"years": [5, 10]}` · **Cutoff rules:** `{"strict_release_safety": false}`
- **Falsification criteria:** Unavailable outcome evidence means untestable, not supported.

### `H03` (`H03-P0.1`) — Relative international-power convergence and rivalry/crisis risk
- **Status:** `untestable_with_current_evidence` (`exploratory_analysis`)
- **Definition:** Power convergence between major states may precede independently dated rivalry, conflict or order-transition episodes.
- **Target outcome:** independent rivalry, conflict or order-transition outcome registry (not populated)
- **Predictors:** `{"candidates": ["global GDP share", "trade share", "military share", "financial depth", "reserve share"]}`
- **Horizons:** `{"years": [5, 10, 20]}` · **Cutoff rules:** `{"strict_release_safety": false}`
- **Falsification criteria:** No independent outcome evidence means untestable.

### `H04` (`H04-P0.1`) — Recurring long sequences of monetary, domestic and external order changes
- **Status:** `untestable_with_current_evidence` (`exploratory_analysis`)
- **Definition:** Historical orders may recur through a long sequence spanning decades to centuries.
- **Target outcome:** independently dated complete order-transition cycles (not populated)
- **Predictors:** `{"status": "undefined"}`
- **Horizons:** `{"years": [25, 500]}` · **Cutoff rules:** `{"strict_release_safety": false}`
- **Falsification criteria:** Current evidence cannot test a universal duration or deterministic sequence.

### Preserved Evaluation Ledger

| Evaluation key | Hypothesis | Model | Result state |
|---|---|---|---|
| `H01-P1.0:retrospective_chronological_holdout:1990:jst-r6` | `H01` (`H01-P1.0`) | `debtgdp_5y_change_univariate` `v1` | `exploratory_association` |
| `H01-P1.0:retrospective_chronological_holdout:1990:jst-r6:v2` | `H01` (`H01-P1.0`) | `debtgdp_5y_change_univariate` `v1` | `no_evidence_of_improved_predictive_value` |
| `H01B-P1.0:retrospective_clustered_diagnostic:1990:jst-r6:v1` | `H01B` (`H01B-P1.0`) | `private_credit_family_univariate` `v1` | `exploratory_association_retrospective_diagnostic` |
| `H01T-P1.0:retrospective_threshold_diagnostic:1990:jst-r6:v1` | `H01T` (`H01T-P1.0`) | `debt_level_threshold_heterogeneity` `v1` | `diagnostic` |

## 6. Recommended Next Pre-Registered Experiments

1. **`H01B-P1.0` (Sectoral Private Credit vs Public Debt):** Pre-register a 3-way comparison of 5-year changes in private bank loans/GDP (`JST tloans/gdp` and `BIS CREDIT_PRIVATE_NF_GDP`), debt-service ratios (`BIS DEBT_SERVICE_RATIO`), and public debt/GDP (`JST debtgdp`) using year-clustered / block-bootstrapped standard errors so the 2007–2008 global crisis cluster is weighted as one correlated wave rather than 13 independent events.
2. **`H02-P1.0` (Governance & Subsequent TFP Slowdowns):** Pre-register an outcome definition for persistent 10-year TFP growth slowdowns using newly imported Penn World Table 11.0 `PWT_RTFPNA_2021_1` across the 20-country panel, tested against lagged WGI institutional changes (`1996–2013` origins -> `2006–2023` outcomes).
3. **`H01C-P1.0` (Interest-Rate Tightening × High Private Debt Interaction):** Test whether the interaction of `BIS POLICY_RATE_PCT` / `JST stir` tightening with elevated private-debt levels improves crisis-onset discrimination over unconditional debt levels (`Q18`, `Q25`).
4. **Real-Time Vintage Verification (`ALFRED`):** Once `BCA_FRED_API_KEY` is supplied locally, compare real-time first-release US macro predictors against final revised series around `1990`, `2001`, `2007`, and `2020`.

## 7. Complete 50-Question Canonical Registry Audit (Q01–Q50)

| Code | Category | Implementation | Scientific status | Evidence rows | Missing deps | Hypotheses |
|---|---|---|---|---:|---:|---|
| Q01 | `core_theory` | `research_method_implemented` | `insufficient_evidence` | 1 | 0 | — |
| Q02 | `core_theory` | `partially_implemented` | `currently_untestable` | 14 | 2 | H04 |
| Q03 | `core_theory` | `partially_implemented` | `insufficient_evidence` | 2 | 0 | — |
| Q04 | `core_theory` | `partially_implemented` | `currently_untestable` | 13 | 1 | H04 |
| Q05 | `core_theory` | `partially_implemented` | `currently_untestable` | 12 | 1 | H04 |
| Q06 | `core_theory` | `partially_implemented` | `currently_untestable` | 63 | 3 | H01;H02;H03;H04 |
| Q07 | `core_theory` | `partially_implemented` | `insufficient_evidence` | 2 | 2 | — |
| Q08 | `core_theory` | `research_method_implemented` | `insufficient_evidence` | 3 | 2 | H01;H01B;H02;H03;H04 |
| Q09 | `core_theory` | `research_method_implemented` | `insufficient_evidence` | 2 | 2 | — |
| Q10 | `core_theory` | `partially_implemented` | `currently_untestable` | 27 | 2 | H04 |
| Q11 | `debt_money` | `evaluation_implemented` | `evaluated_with_no_clear_conclusion` | 20 | 2 | H01;H01B |
| Q12 | `debt_money` | `data_available` | `insufficient_evidence` | 21 | 1 | H01 |
| Q13 | `debt_money` | `data_available` | `untested` | 4 | 2 | H01 |
| Q14 | `debt_money` | `evaluation_implemented` | `evaluated_with_no_clear_conclusion` | 60 | 1 | H01;H01T |
| Q15 | `debt_money` | `partially_implemented` | `currently_untestable` | 55 | 2 | H01 |
| Q16 | `debt_money` | `data_available` | `untested` | 51 | 3 | H01 |
| Q17 | `debt_money` | `evaluation_implemented` | `exploratory_findings` | 61 | 1 | H01;H01B |
| Q18 | `debt_money` | `data_available` | `untested` | 20 | 2 | H01 |
| Q19 | `debt_money` | `data_available` | `insufficient_evidence` | 10 | 2 | H01;H03 |
| Q20 | `debt_money` | `data_available` | `untested` | 55 | 1 | H01 |
| Q21 | `debt_money` | `not_implemented` | `currently_untestable` | 1 | 2 | H01 |
| Q22 | `debt_money` | `partially_implemented` | `currently_untestable` | 54 | 2 | H01 |
| Q23 | `debt_money` | `partially_implemented` | `currently_untestable` | 13 | 2 | H01 |
| Q24 | `debt_money` | `partially_implemented` | `currently_untestable` | 3 | 2 | H01 |
| Q25 | `debt_money` | `research_method_implemented` | `untested` | 60 | 2 | H01;H02 |
| Q26 | `internal_conflict` | `partially_implemented` | `currently_untestable` | 42 | 2 | H02 |
| Q27 | `internal_conflict` | `data_available` | `untested` | 43 | 2 | H02 |
| Q28 | `internal_conflict` | `partially_implemented` | `currently_untestable` | 39 | 2 | H02 |
| Q29 | `internal_conflict` | `partially_implemented` | `currently_untestable` | 39 | 2 | H02 |
| Q30 | `internal_conflict` | `partially_implemented` | `currently_untestable` | 2 | 2 | H02 |
| Q31 | `internal_conflict` | `data_available` | `untested` | 43 | 2 | H02 |
| Q32 | `internal_conflict` | `data_available` | `untested` | 42 | 2 | H02 |
| Q33 | `internal_conflict` | `data_available` | `untested` | 81 | 1 | H02 |
| Q34 | `internal_conflict` | `partially_implemented` | `currently_untestable` | 41 | 2 | H02 |
| Q35 | `internal_conflict` | `partially_implemented` | `currently_untestable` | 41 | 1 | H02 |
| Q36 | `external_rivalry` | `partially_implemented` | `currently_untestable` | 49 | 2 | H03 |
| Q37 | `external_rivalry` | `data_available` | `untested` | 53 | 1 | H03 |
| Q38 | `external_rivalry` | `data_available` | `untested` | 39 | 2 | H03 |
| Q39 | `external_rivalry` | `data_available` | `currently_untestable` | 10 | 2 | H03 |
| Q40 | `external_rivalry` | `data_available` | `untested` | 39 | 3 | H03 |
| Q41 | `external_rivalry` | `data_available` | `currently_untestable` | 45 | 1 | H03 |
| Q42 | `external_rivalry` | `not_implemented` | `currently_untestable` | 0 | 2 | H03 |
| Q43 | `external_rivalry` | `partially_implemented` | `currently_untestable` | 64 | 2 | H03;H04 |
| Q44 | `external_rivalry` | `research_method_implemented` | `untested` | 47 | 1 | H03 |
| Q45 | `external_rivalry` | `partially_implemented` | `currently_untestable` | 40 | 2 | H03;H04 |
| Q46 | `technology_shocks` | `data_available` | `untested` | 39 | 2 | H03 |
| Q47 | `technology_shocks` | `data_available` | `untested` | 53 | 1 | H02;H03 |
| Q48 | `technology_shocks` | `not_implemented` | `currently_untestable` | 0 | 2 | H03 |
| Q49 | `technology_shocks` | `not_implemented` | `currently_untestable` | 0 | 2 | H03;H04 |
| Q50 | `technology_shocks` | `partially_implemented` | `currently_untestable` | 41 | 3 | H04 |

## 8. Full Per-Question Specifications & Findings

### Q01 — Original theory scope
- **Exact registered wording (`atlas_derived_v1`):** What is the original Big Cycle theory, which claims does it make, and which claims can Atlas operationalise?
- **Theory category:** `core_theory` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `None registered`
- **Implementation status:** `research_method_implemented` · **Scientific status:** `insufficient_evidence`
- **Current documented answer:** Atlas now records the theory and operational differences; it does not claim the theory is proven.
- **Research methods:** versioned theory registry; explicit Atlas/original-framework separation
- **Required datasets:** `theory_registry` (primary-source registry: claim definition)
- **Available datasets (1 observed evidence summary rows):** `theory_registry` (theory-registry-v1.0: seven versioned claim/framework entries)
- **Missing datasets:** None
- **Supporting evidence:** The registry separates Dalio concepts from Atlas's 17-force and eight-stage operational frameworks.
- **Contradictory evidence:** None
- **Alternative explanations:** Narrative theories can be useful without a unique measurable representation.
- **Falsification criteria:** The registry is adequate only if a reviewer can distinguish original claims, Atlas interpretations and unsupported operational assumptions.
- **Remaining limitations:** The source text is a narrative synthesis rather than a statistical specification.

### Q02 — Cycle duration
- **Exact registered wording (`atlas_derived_v1`):** How long is the proposed Big Cycle, and is the approximately 75-year claim supported across independently dated historical cycles?
- **Theory category:** `core_theory` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H04`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Currently untestable; no Atlas countdown or stage advancement uses the duration claim.
- **Research methods:** registered candidate duration claim; three-timescale separation
- **Required datasets:** `historical_entities` (multi-century boundary-stable entity panel: duration estimation); `independent_order_transitions` (dated cycle boundaries: outcome labels)
- **Available datasets (14 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `maddison` (2023: Maddison Project Database 2023 historical GDP per capita in 2011 intl $ (1500-2022))
- **Missing datasets:** `historical_entities` (boundary-stable sovereign/empire registry: modern country codes only); `historical_order_transitions` (dated order transitions: no verified chronology)
- **Supporting evidence:** The duration claim is registered as a hypothesis candidate rather than a constant.; Maddison 2023 extends output context pre-1870 without implying cycle stages.
- **Contradictory evidence:** GDP per capita history alone does not date order transitions, and no boundary-stable order-transition chronology is imported.
- **Alternative explanations:** Different debt, internal-order and external-order clocks may have different durations.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** No independent full-cycle onset/boundary chronology.; Entity boundaries and modern GDP definitions change.

### Q03 — Original vs Atlas stages
- **Exact registered wording (`atlas_derived_v1`):** What stages does the original framework describe, and how do those stages differ from the eight Atlas operational stages?
- **Theory category:** `core_theory` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `None registered`
- **Implementation status:** `partially_implemented` · **Scientific status:** `insufficient_evidence`
- **Current documented answer:** The frameworks are separated, but a validated original-stage mapping is not established.
- **Research methods:** theory registry; experimental classifier labelled as Atlas operational framework
- **Required datasets:** `theory_registry` (edition-level source mapping: framework comparison); `cycle_model` (Atlas stage definitions: operational comparison)
- **Available datasets (2 observed evidence summary rows):** `theory_registry` (theory-registry-v1.0: stage separation); `atlas_cycle_model` (experimental classifier: current operational stages)
- **Missing datasets:** None
- **Supporting evidence:** The eight Atlas stages are explicitly marked Atlas-operational rather than Dalio-original.
- **Contradictory evidence:** No edition-level mapping establishes a one-to-one stage structure.
- **Alternative explanations:** Stage labels may be heuristic states rather than historical facts.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Atlas model labels are retrospective and not validated long-cycle stages.

### Q04 — Stage transition evidence
- **Exact registered wording (`atlas_derived_v1`):** What evidence marks transitions from one proposed stage to another rather than ordinary short-cycle changes?
- **Theory category:** `core_theory` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H04`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** timescale separation; leakage-aware prediction ledger; candidate cycle transition diagnostics
- **Required datasets:** `independent_stage_transitions` (source-defined transitions: outcomes); `long_historical_panel` (multi-century predictors: transition features)
- **Available datasets (13 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `atlas_cycle_model` (experimental national-condition models: candidate transition classifications)
- **Missing datasets:** `historical_order_transitions` (independent stage/onset chronology: not imported)
- **Supporting evidence:** The prediction/outcome ledger can preserve candidate transition evidence separately from model labels.
- **Contradictory evidence:** Atlas stage labels come from the model under study and are not independent outcomes.
- **Alternative explanations:** Transitions may reflect common shocks, data revisions or model thresholds rather than cycle stages.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** No independent stage-transition registry.; No strict release-safe historical predictors.

### Q05 — Reversals and plateaus
- **Exact registered wording (`atlas_derived_v1`):** Can countries move backward, skip, repeat, or remain on a plateau within the proposed cycle?
- **Theory category:** `core_theory` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H04`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** separate onset/ongoing outcome states; candidate timescales
- **Required datasets:** `independent_stage_transitions` (reversal/plateau outcomes: labels); `long_historical_panel` (long-run predictors: evidence)
- **Available datasets (12 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel)
- **Missing datasets:** `independent_stage_transitions` (source-defined stage labels: no verified dataset)
- **Supporting evidence:** The crisis registry demonstrates onset and coverage can be represented independently.
- **Contradictory evidence:** No verified stage sequence exists to test reversals or plateaus.
- **Alternative explanations:** Apparent reversals may be data revisions, boundary changes or model noise.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q06 — Three-cycle interaction
- **Exact registered wording (`atlas_derived_v1`):** Do the claimed monetary, internal-order and external-order cycles interact in a measurable sequence?
- **Theory category:** `core_theory` · **Registered claims:** `dalio_money_credit_debt_cycle, dalio_internal_order_cycle, dalio_external_order_cycle`
- **Testable hypotheses:** `H01, H02, H03, H04`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** three registered timescales; separate H01-H04 protocols
- **Required datasets:** `multi_timescale_panel` (debt+institutional+external predictors: features); `independent_order_transitions` (outcome chronology: validation)
- **Available datasets (63 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `world_bank` (current WDI import: primary Observatory indicators); `imf` (current WEO import: primary Observatory indicators); `bis` (current BIS import: debt-service and credit-gap indicators); `oecd` (current OECD import: productivity, education and labour-cost indicators); `wid` (current WID import: wealth inequality indicators); `imf_cofer` (COFER-SDMX-2.1: official FX reserve shares & claims (1995-2026Q2; currency-level)); `bis_fx_turnover` (WS_DER_OTC_TOV: BIS Triennial FX turnover shares 1989-2025 (including INR))
- **Missing datasets:** `vdem` (institutional histories: not imported); `cow` (conflict/order outcomes: not imported); `independent_order_transitions` (order-transition chronology: not imported)
- **Supporting evidence:** Debt, internal-order and external-order hypotheses are separately registered.
- **Contradictory evidence:** No joint sequence test or independent long-order outcome exists yet.
- **Alternative explanations:** The sub-cycles may interact without a fixed ordering or may be driven by common shocks.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q07 — Country applicability
- **Exact registered wording (`atlas_derived_v1`):** Does the theory apply to all countries, only major powers, or only specific institutional and economic regimes?
- **Theory category:** `core_theory` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `None registered`
- **Implementation status:** `partially_implemented` · **Scientific status:** `insufficient_evidence`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** versioned population registry; documented eligibility statuses
- **Required datasets:** `global_reference_population` (eligibility rules: population); `historical_entities` (boundary-aware panel: scope)
- **Available datasets (2 observed evidence summary rows):** `primary_observatory_v1` (8 countries: interface population); `jst_extended_research_v1` (18 advanced economies: historical research panel)
- **Missing datasets:** `global_reference_population` (30-40 country eligible panel: target not reached); `historical_entities` (pre-modern entities: not imported)
- **Supporting evidence:** Primary and extended populations are not conflated.
- **Contradictory evidence:** Current evidence is concentrated in eight modern countries and 18 advanced JST economies.
- **Alternative explanations:** Mechanisms may differ across development level, reserve status, regime and geography.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q08 — Support and falsification
- **Exact registered wording (`atlas_derived_v1`):** Which observations would support the theory and which observations would falsify or weaken it?
- **Theory category:** `core_theory` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H01, H01B, H02, H03, H04`
- **Implementation status:** `research_method_implemented` · **Scientific status:** `insufficient_evidence`
- **Current documented answer:** Research method is implemented (registered falsification criteria, append-only evaluations preserving negative results); H01-P1.0 and H01B-P1.0 have been executed. But a scientific answer to WHICH observations support or falsify the theory requires populated independent outcome registries beyond one banking-crisis family — operational machinery alone is not an empirical finding.
- **Research methods:** versioned hypotheses; explicit falsification criteria; negative-result states
- **Required datasets:** `hypothesis_protocols` (registered falsification rules: protocol); `independent_outcomes` (outcome registry: test labels)
- **Available datasets (3 observed evidence summary rows):** `hypothesis_protocols` (H01-H04: protocol registry); `crisis_registry` (JST banking crises: one independent outcome family)
- **Missing datasets:** `independent_order_transitions` (long-cycle outcomes: not imported); `institutional_outcomes` (persistent deterioration labels: not imported)
- **Supporting evidence:** H01 already preserves a negative evaluation instead of reclassifying it as success.
- **Contradictory evidence:** Only one outcome family is populated, so broad theory falsification is impossible.
- **Alternative explanations:** Failure of one predictor does not falsify the full narrative theory.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q09 — Atlas models as evidence
- **Exact registered wording (`atlas_derived_v1`):** Are the Atlas force scores and experimental stage classifications suitable evidence for the historical Big Cycle claim?
- **Theory category:** `core_theory` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `None registered`
- **Implementation status:** `research_method_implemented` · **Scientific status:** `insufficient_evidence`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** evidence-status registry; methodology/version separation; retrospective-only labels
- **Required datasets:** `force_methodology` (approved measurement methods: features); `independent_outcomes` (external validation: labels)
- **Available datasets (2 observed evidence summary rows):** `atlas_force_engine` (17-force methodology: national-condition inputs); `atlas_cycle_model` (experimental classifications: model outputs)
- **Missing datasets:** `independent_stage_transitions` (external stage labels: not imported); `strict_historical_vintages` (provider release evidence: mostly unavailable)
- **Supporting evidence:** The system labels outputs experimental and keeps them out of the research-outcome registry.
- **Contradictory evidence:** Using model-generated stages as evidence for the same stage theory would be circular.
- **Alternative explanations:** Atlas scores can be predictors for independent outcomes but not truth labels.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q10 — Required historical depth
- **Exact registered wording (`atlas_derived_v1`):** How much historical depth, entity continuity and independent outcome coverage is required before the theory can be tested?
- **Theory category:** `core_theory` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H04`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** historical coverage reporting; three-timescale architecture
- **Required datasets:** `multi_century_panel` (boundary-aware entities: coverage); `independent_order_transitions` (multiple complete transitions: outcomes)
- **Available datasets (27 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `maddison` (2023: Maddison Project Database 2023 historical GDP per capita in 2011 intl $ (1500-2022)); `pwt` (11.0: Penn World Table 11.0 output, worker/hour productivity, capital, human capital & TFP (1950-2023)); `research_population` (26 memberships: coverage registry)
- **Missing datasets:** `historical_entities` (boundary-stable entity registry: not populated); `independent_order_transitions` (long-cycle outcomes: not imported)
- **Supporting evidence:** The registry states achieved multi-dataset coverage instead of claiming adequate long-cycle outcome depth.
- **Contradictory evidence:** Historical GDP reconstructions do not provide independent order-transition outcomes.
- **Alternative explanations:** Proxy depth may support sub-cycle tests even when the complete Big Cycle remains untestable.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q11 — Debt burdens and crises
- **Exact registered wording (`atlas_derived_v1`):** Do rising debt burdens increase the probability of a subsequent systemic banking crisis?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_money_credit_debt_cycle`
- **Testable hypotheses:** `H01, H01B`
- **Implementation status:** `evaluation_implemented` · **Scientific status:** `evaluated_with_no_clear_conclusion`
- **Current documented answer:** Scoped correction (v1.2): the registered H01-P1.0 test contradicted one specific operationalized proposition — 5-year PUBLIC debt/GDP change as a crisis predictor (AUC 0.363/0.381/0.296). That negative result does not falsify the broader debt-cycle claim: H01B-P1.0 found positive retrospective discrimination for PRIVATE credit expansion (tloans/gdp 5y change AUC 0.719, income-residualised 0.717), and public debt characteristically surges AFTER crises via bailouts and automatic stabilisers. The broad registered claim remains only partially tested.
- **Research methods:** H01-P1.0 chronological holdout; 1/2/5-year onset horizons; base-rate and AUC benchmarks; append-only prediction ledger
- **Required datasets:** `debt_panel` (public/private debt predictors: features); `independent_crisis_outcomes` (banking-crisis onsets: outcome)
- **Available datasets (20 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `bis_credit_policy` (WS_TC_CBPOL: BIS sectoral credit (govt, private, household, corporate) & policy rates); `crisis_registry` (88 JST systemic banking onsets: independent outcomes)
- **Missing datasets:** `imf_laeven_valencia_banking_crises` (WP-2026-094: official ZIP HTTP 403/404; local-file importer ready); `alfred_fred` (historical vintages: BCA_FRED_API_KEY required)
- **Supporting evidence:** A complete leakage-aware protocol was registered and executed.; Diagnostic contrast shows private bank-loan/GDP 5y growth (tloans/gdp) reaches retrospective AUC 0.721 (1y) and 0.702 (2y), confirming public vs private debt must never be conflated.
- **Contradictory evidence:** Registered H01-P1.0 tested public debtgdp 5-year change: held-out AUC was 0.363 (1y), 0.381 (2y), 0.296 (5y) and top-p80 precision (1.54%/1.50%/0.88%) fell below the ~3.42% base rate because public debt typically surges after banking crises rather than before them.
- **Alternative explanations:** Pre-crisis private credit booms improve fiscal balances before banking crises, while public debt surges post-crisis via bailouts and automatic stabilisers.
- **Falsification criteria:** No improvement over the unconditional base rate or discrimination near/below random ordering is evidence inconsistent with predictive value.
- **Remaining limitations:** H01-P1.0 evaluated public debtgdp rather than private tloans/gdp; protocol is preserved unchanged.; 13 of 19 post-1990 test events cluster in 2007-2008 and 4 in 1991.; Secular post-1990 debt drift pushed 35.1%-40.8% of test rows above the pre-1990 80th percentile.

### Q12 — Debt composition
- **Exact registered wording (`atlas_derived_v1`):** Do public, private non-financial, household and corporate debt measures provide different warning signals?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_money_credit_debt_cycle`
- **Testable hypotheses:** `H01`
- **Implementation status:** `data_available` · **Scientific status:** `insufficient_evidence`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** separate source-versioned public, private, household and corporate series; market vs nominal valuation separation
- **Required datasets:** `sectoral_debt_panel` (public/household/corporate debt: features); `independent_crisis_outcomes` (crisis outcomes: evaluation)
- **Available datasets (21 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `bis_credit_policy` (WS_TC_CBPOL: BIS sectoral credit (govt, private, household, corporate) & policy rates); `imf` (government debt: public debt); `bis` (private-sector DSR/credit gap: private burden)
- **Missing datasets:** `debt_ownership` (holder composition: not imported)
- **Supporting evidence:** BIS WS_TC quarterly sectoral debt (general government, private non-financial, households, non-financial corporations) and JST sectoral loans (thh, tbus) are now imported separately.
- **Contradictory evidence:** No pre-registered multi-sector holdout protocol has been executed yet.
- **Alternative explanations:** Different sectors transmit stress through distinct banking, household-consumption and sovereign-funding channels.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q13 — Debt-service burden
- **Exact registered wording (`atlas_derived_v1`):** Do debt-service burdens predict financial crises better than debt-to-GDP levels?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H01`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** BIS indicator import; own-history debt-condition methodology; H01 debt benchmark on JST
- **Required datasets:** `bis_dsr` (sectoral DSR: predictors); `independent_crisis_outcomes` (crisis onsets: labels)
- **Available datasets (4 observed evidence summary rows):** `bis` (DEBT_SERVICE_RATIO: 925 rows, 8 countries, 1999-2026); `jst_macrohistory` (debtgdp and loans: long retrospective proxies); `crisis_registry` (88 banking onsets: outcomes)
- **Missing datasets:** `bis_dsr_extended_panel` (30-40 country DSR: not imported); `real_time_dsr_vintages` (release-time DSR: not available)
- **Supporting evidence:** Modern DSR coverage exists and is separate from levels.
- **Contradictory evidence:** No crisis comparison has tested DSR against debt-to-GDP directly.
- **Alternative explanations:** DSR may reflect interest-rate cycles and credit composition rather than long-cycle vulnerability.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q14 — Debt threshold
- **Exact registered wording (`atlas_derived_v1`):** Is there a reproducible debt-to-GDP threshold associated with later crises?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H01, H01T`
- **Implementation status:** `evaluation_implemented` · **Scientific status:** `evaluated_with_no_clear_conclusion`
- **Current documented answer:** H01T-P1.0 evaluated level thresholds directly: no reproducible UNIVERSAL debt-to-GDP crisis threshold exists — pooled p80 levels discriminate at/below chance for public debt and over-flag for private credit, while per-country thresholds differ by ~5x. Thresholds appear conditional on country, era and monetary regime; that heterogeneity, not a single cutoff, is the supported research direction.
- **Research methods:** H01T-P1.0 dedicated threshold heterogeneity protocol; pooled vs within-country train-p80 level thresholds; peg/non-peg regime split; gold/interwar/Bretton-Woods/fiat era split; no ex-post threshold mining
- **Required datasets:** `debt_threshold_panel` (pre-registered candidate thresholds: features); `independent_crisis_outcomes` (crisis onsets: labels)
- **Available datasets (60 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `bis_credit_policy` (WS_TC_CBPOL: BIS sectoral credit (govt, private, household, corporate) & policy rates); `imf` (government debt: public debt); `world_bank` (domestic private credit: private debt); `crisis_registry` (banking onsets: outcomes)
- **Missing datasets:** `untouched_threshold_holdout` (post-inspection confirmatory sample: 1990-2020 already used for diagnostics)
- **Supporting evidence:** H01T-P1.0 ran dedicated level-threshold diagnostics instead of reusing change-based results.
- **Contradictory evidence:** Public debtgdp level held-out AUC is 0.365 with 35.5% of test years flagged above the pooled pre-1990 p80 (0.72); private tloans/gdp pooled p80 (0.68) flags 82.0% of test years at AUC 0.623; country-specific p80 values span 0.18-1.70 (public, CV 0.55) and 0.32-1.26 (private, CV 0.39), so no single level is portable.
- **Alternative explanations:** Vulnerability varies with growth, interest rates, currency denomination, debt ownership, monetary regime and financial development.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** H01-P1.0 formally tested 5-year changes rather than fixed level cutoffs.; Level thresholds are non-stationary across monetary eras (fiat-era tloans/gdp AUC 0.633 vs interwar 0.470).; No untouched confirmatory holdout remains in JST R6.

### Q15 — External and FX debt
- **Exact registered wording (`atlas_derived_v1`):** Do external debt and foreign-currency debt create vulnerability beyond domestic debt?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_money_credit_debt_cycle`
- **Testable hypotheses:** `H01`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** source-defined variable registry
- **Required datasets:** `external_debt` (external/FX debt: predictors); `currency_debt_outcomes` (currency and sovereign outcomes: labels)
- **Available datasets (55 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `bis_lbs` (WS_LBS_D_PUB: BIS cross-border bank claims by currency and reporting jurisdiction); `world_bank` (current-account and trade indicators: external-position proxies)
- **Missing datasets:** `external_debt` (borrower external and FX debt stocks: not imported); `currency_sovereign_crises` (verified outcomes: not imported)
- **Supporting evidence:** JST current-account/FX variables and BIS cross-border banking claims are imported.
- **Contradictory evidence:** Borrower-side external/FX debt stocks and currency/sovereign crisis labels remain absent.
- **Alternative explanations:** Reserve-currency issuers may face different constraints than borrowers in foreign currency.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q16 — Monetary expansion
- **Exact registered wording (`atlas_derived_v1`):** Does rapid monetary expansion precede inflation, currency pressure or financial instability?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_money_credit_debt_cycle`
- **Testable hypotheses:** `H01`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** source-versioned research observations
- **Required datasets:** `money_panel` (money growth: predictors); `independent_currency_inflation_outcomes` (outcomes: labels)
- **Available datasets (51 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `world_bank` (BROAD_MONEY_GDP and INFLATION_CPI: modern money/inflation indicators)
- **Missing datasets:** `currency_crisis_registry` (independent currency onsets: not imported); `inflation_regime_outcomes` (independent high-inflation episodes: not imported); `alfred_fred` (money vintages: API key required)
- **Supporting evidence:** JST `money` and WDI broad-money/inflation series exist.
- **Contradictory evidence:** No registered outcome evaluation has been run.
- **Alternative explanations:** Money growth can follow credit demand, policy regime or financial deepening rather than cause instability.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q17 — Credit expansion
- **Exact registered wording (`atlas_derived_v1`):** Does rapid private credit expansion precede financial crises independently of income growth?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H01, H01B`
- **Implementation status:** `evaluation_implemented` · **Scientific status:** `exploratory_findings`
- **Current documented answer:** Attribution corrected: H01-P1.0's negative result applies only to public debt. Under dedicated protocol H01B-P1.0, private-credit expansion shows positive retrospective association with banking-crisis onset that survives income-growth residualisation and clustered diagnostics — classified exploratory because the holdout is no longer untouched and only 3 independent episodes remain.
- **Research methods:** H01B-P1.0 dedicated private-credit protocol; clustered diagnostics (LOEO/LOCO/time-blocks/ex-2007-08/year-block bootstrap); income-growth residualisation; BIS credit-gap import
- **Required datasets:** `credit_panel` (private credit: predictors); `independent_crisis_outcomes` (crisis onsets: labels)
- **Available datasets (61 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `bis_credit_policy` (WS_TC_CBPOL: BIS sectoral credit (govt, private, household, corporate) & policy rates); `world_bank` (DOMESTIC_CREDIT_PRIVATE_GDP: modern credit); `bis` (CREDIT_TO_GDP_GAP: modern gap); `crisis_registry` (JST banking onsets: outcomes)
- **Missing datasets:** `real_time_credit_vintages` (release-safe credit revisions: not available)
- **Supporting evidence:** H01B-P1.0 evaluated the tloans/gdp 5y change on the 1990-2020 holdout: AUC 0.719 (1y, year-block bootstrap CI 0.52-0.85), 0.702 (2y), 0.591 (5y); residualising on 5y real income growth leaves AUC 0.717, so the association is not merely an income-growth reflection. Household (0.723), corporate (0.677), mortgage (0.696) credit growth and the derived debt-service proxy (0.767) show consistent positive discrimination.
- **Contradictory evidence:** The pre-registered H01-P1.0 evaluation tested public debtgdp 5-year change rather than private tloans/gdp and failed (AUC 0.363/0.381/0.296) — that negative result belongs to public debt only. The 1990-2020 holdout was already used for predictor inspection, so H01B results are retrospective diagnostics, not confirmatory; only 3 independent post-1990 crisis episodes exist (1984-91, 1997, 2007-08).
- **Alternative explanations:** Credit growth can reflect financial deepening, denominator contractions or synchronized global credit waves (13/19 test crises occurred in 2007-2008); ex-2007-08 and leave-one-episode-out diagnostics quantify this dependence.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Attribution audit (v1.2): the prior contradictory status was inherited from a public-debt protocol — an attribution defect now corrected. The public-debt experiment (H01-P1.0) stands unchanged; the private-credit exploratory diagnostic and the dedicated H01B-P1.0 retrospective evaluation are reported separately. Confirmatory status requires an untouched outcome sample (post-2020 or an independent registry such as IMF WP-2026-094).

### Q18 — Interest-rate stress
- **Exact registered wording (`atlas_derived_v1`):** Do changes in short- and long-term interest rates predict debt stress or crisis onset?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H01`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** source-versioned historical rates and central-bank policy rates
- **Required datasets:** `rate_panel` (short/long rates: predictors); `independent_crisis_outcomes` (crisis onsets: labels)
- **Available datasets (20 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `bis_credit_policy` (WS_TC_CBPOL: BIS sectoral credit (govt, private, household, corporate) & policy rates); `crisis_registry` (JST banking onsets: outcomes)
- **Missing datasets:** `policy_rate_vintages` (release-safe central-bank rate vintages: not imported); `debt_stress_outcomes` (non-crisis debt stress labels: not defined)
- **Supporting evidence:** JST `stir`, `ltrate`, `bill_rate`, `bond_rate` and BIS `POLICY_RATE_PCT` (with DEU/FRA -> EUR 1999 break preserved) are imported.
- **Contradictory evidence:** No registered interest-rate protocol or evaluation exists.
- **Alternative explanations:** Rate changes can be policy responses to stress rather than independent predictors.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q19 — Reserve-currency status
- **Exact registered wording (`atlas_derived_v1`):** Does reserve-currency status reduce debt vulnerability or delay adjustment?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_money_credit_debt_cycle, dalio_external_order_cycle`
- **Testable hypotheses:** `H01, H03`
- **Implementation status:** `data_available` · **Scientific status:** `insufficient_evidence`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** currency-area entity separation; documented COFER methodology breaks
- **Required datasets:** `imf_cofer` (reserve currency shares: status); `debt_crisis_panel` (debt/crisis outcomes: evaluation)
- **Available datasets (10 observed evidence summary rows):** `imf_cofer` (COFER-SDMX-2.1: official FX reserve shares & claims (1995-2026Q2; currency-level)); `bis_fx_turnover` (WS_DER_OTC_TOV: BIS Triennial FX turnover shares 1989-2025 (including INR)); `bis_lbs` (WS_LBS_D_PUB: BIS cross-border bank claims by currency and reporting jurisdiction); `currency_research_entities` (currency-area registry: entity model)
- **Missing datasets:** `pre_1995_reserve_shares` (long-run pre-1995 official reserve currency composition: not imported); `reserve_issuer_outcomes` (issuer-specific adjustment outcomes: not defined)
- **Supporting evidence:** Official IMF COFER reserve shares, BIS FX turnover shares and BIS cross-border banking currency shares are now imported separately from country scores.
- **Contradictory evidence:** Modern COFER spans one dominant USD regime (1995-2026) and cannot by itself identify multi-regime reserve transitions or causal debt insulation.
- **Alternative explanations:** Demand for safe assets, institutional depth, capital-account openness and network effects confound reserve-issuer debt outcomes.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q20 — Financial depth
- **Exact registered wording (`atlas_derived_v1`):** Does financial-market depth amplify or absorb debt and credit shocks?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H01`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** separate domestic depth and cross-border banking measures
- **Required datasets:** `financial_depth` (market/banking depth: predictors); `crisis_outcomes` (independent outcomes: labels)
- **Available datasets (55 observed evidence summary rows):** `world_bank` (stock-market capitalisation/private credit/broad money: financial-depth proxies); `jst_macrohistory` (R6: long historical research panel); `bis_lbs` (WS_LBS_D_PUB: BIS cross-border bank claims by currency and reporting jurisdiction)
- **Missing datasets:** `financial_stress_outcomes` (non-crisis stress labels: not imported)
- **Supporting evidence:** Domestic market depth and BIS cross-border banking intermediation are tracked separately from reserve status.
- **Contradictory evidence:** No test distinguishes shock absorption from amplification.
- **Alternative explanations:** Depth can support resilience or enable greater leverage depending on institutions and regulation.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q21 — Debt ownership
- **Exact registered wording (`atlas_derived_v1`):** Does debt ownership structure change the probability or severity of crises?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H01`
- **Implementation status:** `not_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** missing-data registry
- **Required datasets:** `debt_ownership` (domestic/foreign/public/private holders: predictors); `crisis_outcomes` (crisis outcomes: labels)
- **Available datasets (1 observed evidence summary rows):** `imf` (government debt stock: debt level only)
- **Missing datasets:** `debt_ownership` (holder composition: not imported); `sovereign_bondholder_data` (ownership shares: not imported)
- **Supporting evidence:** None
- **Contradictory evidence:** No holder-composition observations are imported.
- **Alternative explanations:** Domestic ownership may stabilize funding while concentrating losses domestically.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q22 — Currency crises
- **Exact registered wording (`atlas_derived_v1`):** Are currency crises preceded by distinct external, monetary or reserve pressures?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_money_credit_debt_cycle`
- **Testable hypotheses:** `H01`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** separate crisis-type registry
- **Required datasets:** `currency_crisis_outcomes` (independent currency onsets: labels); `external_monetary_panel` (external/reserve predictors: features)
- **Available datasets (54 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `imf_cofer` (COFER-SDMX-2.1: official FX reserve shares & claims (1995-2026Q2; currency-level)); `world_bank` (REER/current-account/trade series: external proxies)
- **Missing datasets:** `currency_crisis_registry` (verified currency-crisis chronology: not imported); `fx_reserves` (country FX reserve adequacy: not imported)
- **Supporting evidence:** The outcome registry supports currency-crisis event types.
- **Contradictory evidence:** No currency-crisis events are imported.
- **Alternative explanations:** Exchange-rate regimes and capital controls may dominate domestic debt signals.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q23 — Sovereign debt crises
- **Exact registered wording (`atlas_derived_v1`):** Are sovereign debt crises preceded by measurable fiscal and external vulnerabilities?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_money_credit_debt_cycle`
- **Testable hypotheses:** `H01`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** separate crisis-type registry
- **Required datasets:** `sovereign_crisis_outcomes` (sovereign default/debt crises: labels); `fiscal_external_panel` (debt/revenue/external predictors: features)
- **Available datasets (13 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `imf` (government debt: public debt)
- **Missing datasets:** `sovereign_crisis_registry` (verified sovereign-crisis chronology: not imported); `sovereign_defaults` (default/restructuring data: not imported)
- **Supporting evidence:** JST includes debt, expenditure, revenue and external variables.
- **Contradictory evidence:** No sovereign-crisis outcome labels are populated.
- **Alternative explanations:** Sovereign crises can depend on debt currency, maturity, political choice and access to official support.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q24 — Restructurings and defaults
- **Exact registered wording (`atlas_derived_v1`):** Do debt restructurings and defaults follow identifiable debt and repayment patterns?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H01`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** outcome-registry event types reserved
- **Required datasets:** `restructuring_defaults` (independent default/restructuring events: labels); `debt_service_panel` (repayment burden: features)
- **Available datasets (3 observed evidence summary rows):** `bis` (DSR and credit gap: repayment-burden predictors); `imf` (government debt: stock proxy)
- **Missing datasets:** `sovereign_defaults` (default/restructuring chronology: not imported); `private_debt_restructuring` (corporate/household restructuring: not imported)
- **Supporting evidence:** None
- **Contradictory evidence:** No default/restructuring events are imported.
- **Alternative explanations:** Defaults can be strategic or politically constrained, not only mechanically driven by burdens.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q25 — Conditional debt vulnerability
- **Exact registered wording (`atlas_derived_v1`):** Does debt vulnerability depend on growth, inflation, institutional quality and external conditions rather than a universal threshold?
- **Theory category:** `debt_money` · **Registered claims:** `dalio_money_credit_debt_cycle, dalio_internal_order_cycle`
- **Testable hypotheses:** `H01, H02`
- **Implementation status:** `research_method_implemented` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** registered simple benchmark; candidate multivariate protocol fields
- **Required datasets:** `multivariate_debt_panel` (debt+growth+institutions+external conditions: features); `independent_crisis_outcomes` (crisis outcomes: labels)
- **Available datasets (60 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `world_bank` (current WDI import: primary Observatory indicators); `imf` (current WEO import: primary Observatory indicators); `bis` (current BIS import: debt-service and credit-gap indicators); `oecd` (current OECD import: productivity, education and labour-cost indicators); `wid` (current WID import: wealth inequality indicators); `crisis_registry` (JST banking crises: outcomes)
- **Missing datasets:** `multivariate_h01_protocol` (pre-registered conditional model: not implemented); `currency_sovereign_outcomes` (other crisis labels: not imported)
- **Supporting evidence:** JST/WB/OECD/IMF/BIS variables can support a conditional design.
- **Contradictory evidence:** The univariate result argues against universal-threshold claims, but the conditional hypothesis remains untested.
- **Alternative explanations:** Conditional relationships may reflect policy response or selection of which countries borrow.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q26 — Institutions and productivity
- **Exact registered wording (`atlas_derived_v1`):** Does institutional deterioration predict later weakness in investment or productivity?
- **Theory category:** `internal_conflict` · **Registered claims:** `dalio_internal_order_cycle`
- **Testable hypotheses:** `H02`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** H02-P0.1 exploratory protocol
- **Required datasets:** `institutional_panel` (institutional measures: predictors); `persistent_weakness_outcomes` (investment/productivity weakness labels: outcomes)
- **Available datasets (42 observed evidence summary rows):** `world_bank` (WGI + investment series: predictors); `oecd` (productivity series: candidate outcome proxy)
- **Missing datasets:** `persistent_weakness_registry` (independent productivity/investment deterioration labels: not defined); `vdem` (institutional histories: not imported)
- **Supporting evidence:** Predictors and candidate outcome variables exist.
- **Contradictory evidence:** No independent outcome registry or held-out evaluation exists.
- **Alternative explanations:** Productivity weakness may cause institutional deterioration rather than follow it.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q27 — Inequality and instability
- **Exact registered wording (`atlas_derived_v1`):** Do income and wealth inequality predict later political instability or weaker economic performance?
- **Theory category:** `internal_conflict` · **Registered claims:** `dalio_internal_order_cycle`
- **Testable hypotheses:** `H02`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** separate inequality source definitions
- **Required datasets:** `inequality_panel` (income/wealth distribution: predictors); `instability_growth_outcomes` (independent outcomes: labels)
- **Available datasets (43 observed evidence summary rows):** `world_bank` (GINI_INDEX: income inequality); `wid` (WEALTH_SHARE_TOP_10: wealth inequality); `oecd` (productivity: economic outcome proxy)
- **Missing datasets:** `protest_conflict_outcomes` (verified instability events: not imported); `persistent_weakness_registry` (economic weakness labels: not defined)
- **Supporting evidence:** Income and wealth measures are preserved separately.
- **Contradictory evidence:** No independent instability outcome evaluation exists.
- **Alternative explanations:** Instability and inequality can be jointly caused by shocks, institutions or elite conflict.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q28 — Political polarisation
- **Exact registered wording (`atlas_derived_v1`):** Does political polarisation precede internal conflict, institutional breakdown or policy instability?
- **Theory category:** `internal_conflict` · **Registered claims:** `dalio_internal_order_cycle`
- **Testable hypotheses:** `H02`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** source-definition separation
- **Required datasets:** `polarisation_panel` (polarisation measures: predictors); `internal_conflict_outcomes` (verified conflict/breakdown outcomes: labels)
- **Available datasets (39 observed evidence summary rows):** `world_bank` (POLITICAL_STABILITY_WGI_SCORE: perception proxy)
- **Missing datasets:** `vdem` (polarisation/institutional measures: not imported); `ucdp_acled` (event outcomes: access/licensing not resolved)
- **Supporting evidence:** A perception-based stability proxy is tracked.
- **Contradictory evidence:** WGI perception scores are not counts of protests or breakdown events.
- **Alternative explanations:** Polarisation can be a symptom of underlying economic or institutional stress.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q29 — Regime characteristics
- **Exact registered wording (`atlas_derived_v1`):** Do regime characteristics predict how countries manage debt, shocks or economic transitions?
- **Theory category:** `internal_conflict` · **Registered claims:** `dalio_internal_order_cycle`
- **Testable hypotheses:** `H02`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** hypothesis fields reserved for institutional predictors
- **Required datasets:** `regime_panel` (regime/institutional classifications: features); `debt_shock_outcomes` (independent outcomes: labels)
- **Available datasets (39 observed evidence summary rows):** `world_bank` (WGI governance scores: partial institutional proxies)
- **Missing datasets:** `vdem` (regime and institutional characteristics: not imported); `policy_response_outcomes` (shock-management labels: not defined)
- **Supporting evidence:** Governance proxies are tracked without assuming regime superiority.
- **Contradictory evidence:** No regime outcome test is possible with current evidence.
- **Alternative explanations:** Economic structure, external constraints and geopolitical support may dominate regime labels.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q30 — Recorded unrest outcomes
- **Exact registered wording (`atlas_derived_v1`):** Do independently recorded protests, unrest or civil conflict provide useful internal-order outcomes?
- **Theory category:** `internal_conflict` · **Registered claims:** `dalio_internal_order_cycle`
- **Testable hypotheses:** `H02`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** independent outcome registry supports non-crisis event types
- **Required datasets:** `ucdp_acled` (event-level unrest/conflict: outcomes); `internal_order_predictors` (institutional/economic predictors: features)
- **Available datasets (2 observed evidence summary rows):** `crisis_registry` (event/coverage schema: reusable outcome contract)
- **Missing datasets:** `ucdp` (conflict events: not imported); `acled` (protest/conflict events: not imported; licensing/access review needed)
- **Supporting evidence:** The registry is reusable beyond banking crises.
- **Contradictory evidence:** No unrest/conflict outcomes are populated.
- **Alternative explanations:** Recorded unrest depends on reporting coverage and state repression as well as underlying grievance.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q31 — Wealth and opportunity gaps
- **Exact registered wording (`atlas_derived_v1`):** Do widening wealth and opportunity gaps precede internal-order deterioration?
- **Theory category:** `internal_conflict` · **Registered claims:** `dalio_internal_order_cycle`
- **Testable hypotheses:** `H02`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** source-defined inequality measures
- **Required datasets:** `distribution_panel` (wealth/opportunity measures: predictors); `internal_order_outcomes` (independent outcomes: labels)
- **Available datasets (43 observed evidence summary rows):** `wid` (WEALTH_SHARE_TOP_10: wealth concentration); `world_bank` (GINI and education: income/opportunity proxies); `oecd` (attainment: opportunity proxy)
- **Missing datasets:** `internal_order_outcomes` (verified deterioration events: not imported); `opportunity_mobility` (intergenerational mobility: not imported)
- **Supporting evidence:** Long WID wealth-share history exists.
- **Contradictory evidence:** No internal-order outcome labels are available for evaluation.
- **Alternative explanations:** Opportunity gaps may persist without observed instability; political response mediates outcomes.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q32 — Human-capital resilience
- **Exact registered wording (`atlas_derived_v1`):** Do education and human-capital changes predict resilience to internal or economic stress?
- **Theory category:** `internal_conflict` · **Registered claims:** `dalio_internal_order_cycle`
- **Testable hypotheses:** `H02`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** coverage-aware education measures
- **Required datasets:** `education_panel` (attainment/enrollment/researchers: predictors); `stress_resilience_outcomes` (independent outcomes: labels)
- **Available datasets (42 observed evidence summary rows):** `oecd` (tertiary attainment: education stock); `world_bank` (enrollment/researchers: education inputs)
- **Missing datasets:** `barro_lee` (long education attainment: not imported); `stress_resilience_registry` (recovery/resilience labels: not defined)
- **Supporting evidence:** Education inputs and attainment are imported separately.
- **Contradictory evidence:** No resilience outcome evaluation exists.
- **Alternative explanations:** Education may proxy broader development rather than directly produce resilience.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q33 — Investment and productivity decline
- **Exact registered wording (`atlas_derived_v1`):** Do declining investment and productivity precede broader institutional deterioration?
- **Theory category:** `internal_conflict` · **Registered claims:** `dalio_internal_order_cycle`
- **Testable hypotheses:** `H02`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** H02 candidate predictor/outcome fields
- **Required datasets:** `investment_productivity_panel` (predictors/outcomes: features); `institutional_outcomes` (independent deterioration labels: outcomes)
- **Available datasets (81 observed evidence summary rows):** `world_bank` (GROSS_CAPITAL_FORMATION_GDP: investment); `oecd` (LABOUR_PRODUCTIVITY_PER_HOUR: productivity); `world_bank` (WGI: institutional proxy)
- **Missing datasets:** `institutional_deterioration_registry` (independent outcome labels: not defined)
- **Supporting evidence:** Investment and productivity series exist.
- **Contradictory evidence:** No independent institutional deterioration chronology exists; reverse causality is plausible.
- **Alternative explanations:** Economic decline may cause institutional stress rather than precede it.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q34 — Political systems and stress
- **Exact registered wording (`atlas_derived_v1`):** Are some political systems systematically better at managing debt burdens and economic shocks?
- **Theory category:** `internal_conflict` · **Registered claims:** `dalio_internal_order_cycle`
- **Testable hypotheses:** `H02`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** non-normative source registry
- **Required datasets:** `regime_panel` (political-system measures: features); `debt_shock_outcomes` (independent outcomes: labels)
- **Available datasets (41 observed evidence summary rows):** `world_bank` (WGI proxies: partial governance measures); `bis` (DSR/credit gap: debt burden)
- **Missing datasets:** `vdem` (regime characteristics: not imported); `policy_response_outcomes` (shock/debt-management outcomes: not defined)
- **Supporting evidence:** None
- **Contradictory evidence:** No evidence supports a universal political-system claim.
- **Alternative explanations:** Outcomes may reflect income, external position, institutions or luck rather than regime type.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q35 — Internal conflict definition
- **Exact registered wording (`atlas_derived_v1`):** Can internal conflict be distinguished from ordinary political competition using reproducible outcome definitions?
- **Theory category:** `internal_conflict` · **Registered claims:** `dalio_internal_order_cycle`
- **Testable hypotheses:** `H02`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** event onset/state/coverage separation
- **Required datasets:** `conflict_outcome_definitions` (event typology and thresholds: labels); `event_sources` (UCDP/ACLED or equivalent: evidence)
- **Available datasets (41 observed evidence summary rows):** `crisis_registry` (event-state/coverage model: reusable schema); `world_bank` (POLITICAL_STABILITY_WGI_SCORE: perception proxy)
- **Missing datasets:** `ucdp_acled` (verified conflict/protest event data: not imported)
- **Supporting evidence:** Unknown coverage and non-events are represented explicitly.
- **Contradictory evidence:** Perception scores cannot substitute for recorded conflict events.
- **Alternative explanations:** Election disputes and peaceful competition must remain outside crisis labels unless source definitions say otherwise.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q36 — Power convergence and rivalry
- **Exact registered wording (`atlas_derived_v1`):** Does convergence in relative international power precede rivalry, conflict or crisis risk?
- **Theory category:** `external_rivalry` · **Registered claims:** `dalio_external_order_cycle`
- **Testable hypotheses:** `H03`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** H03-P0.1 exploratory protocol; separated power-measure registry
- **Required datasets:** `relative_power_panel` (separated power measures: features); `rivalry_conflict_outcomes` (independent outcomes: labels)
- **Available datasets (49 observed evidence summary rows):** `world_bank` (GDP/trade/military/financial proxies: power measures); `imf_cofer` (COFER-SDMX-2.1: official FX reserve shares & claims (1995-2026Q2; currency-level)); `bis_fx_turnover` (WS_DER_OTC_TOV: BIS Triennial FX turnover shares 1989-2025 (including INR)); `bis_lbs` (WS_LBS_D_PUB: BIS cross-border bank claims by currency and reporting jurisdiction); `power_registry` (measure definitions: methodology)
- **Missing datasets:** `cow` (rivalry/conflict outcomes: not imported); `historical_power_transitions` (transition outcomes: not imported)
- **Supporting evidence:** Power dimensions and currency shares are tracked without collapsing into a universal score.
- **Contradictory evidence:** No independent rivalry or transition outcomes exist.
- **Alternative explanations:** Rivalry may be triggered by security commitments, ideology or shocks rather than power convergence alone.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q37 — Output shares and influence
- **Exact registered wording (`atlas_derived_v1`):** Do changes in global economic-output shares predict changes in international influence?
- **Theory category:** `external_rivalry` · **Registered claims:** `dalio_external_order_cycle`
- **Testable hypotheses:** `H03`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** denominator-safe global-share calculations; PPP benchmark separation
- **Required datasets:** `global_output_shares` (denominator-safe shares: features); `influence_outcomes` (independent influence/order outcomes: labels)
- **Available datasets (53 observed evidence summary rows):** `world_bank` (GDP current/PPP/real + global denominators: output shares); `pwt` (11.0: Penn World Table 11.0 output, worker/hour productivity, capital, human capital & TFP (1950-2023)); `maddison` (2023: Maddison Project Database 2023 historical GDP per capita in 2011 intl $ (1500-2022)); `power_registry` (economic_output definitions: methodology)
- **Missing datasets:** `influence_outcomes` (independent influence/order transitions: not imported)
- **Supporting evidence:** Multiple output definitions (current USD, WDI PPP, constant 2015 USD, PWT 2021 PPP, Maddison 2011 intl $) are preserved separately.
- **Contradictory evidence:** Output shares alone do not establish political or institutional influence.
- **Alternative explanations:** Trade, finance, institutions and alliances may mediate economic scale.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q38 — Trade shares and dependence
- **Exact registered wording (`atlas_derived_v1`):** Do global trade shares and bilateral dependence predict rivalry or cooperation?
- **Theory category:** `external_rivalry` · **Registered claims:** `dalio_external_order_cycle`
- **Testable hypotheses:** `H03`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** denominator-safe trade-share measures
- **Required datasets:** `trade_share_panel` (global and bilateral trade: features); `rivalry_cooperation_outcomes` (independent outcomes: labels)
- **Available datasets (39 observed evidence summary rows):** `world_bank` (merchandise/services exports and imports: global trade shares); `jst_macrohistory` (exports/imports: historical trade proxies)
- **Missing datasets:** `un_comtrade` (bilateral trade: planned provider not imported); `rivalry_outcomes` (independent rivalry/cooperation labels: not imported)
- **Supporting evidence:** Global trade-share inputs exist for the primary panel.
- **Contradictory evidence:** Bilateral dependence and outcomes are missing.
- **Alternative explanations:** Trade can restrain conflict or create leverage and vulnerability; direction is not assumed.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q39 — Reserve shares and influence
- **Exact registered wording (`atlas_derived_v1`):** Do reserve-currency shares predict monetary influence and adjustment capacity?
- **Theory category:** `external_rivalry` · **Registered claims:** `dalio_money_credit_debt_cycle, dalio_external_order_cycle`
- **Testable hypotheses:** `H03`
- **Implementation status:** `data_available` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** currency-area separation; methodology-break preservation
- **Required datasets:** `imf_cofer` (reserve currency shares: features); `monetary_influence_outcomes` (independent outcomes: labels)
- **Available datasets (10 observed evidence summary rows):** `imf_cofer` (COFER-SDMX-2.1: official FX reserve shares & claims (1995-2026Q2; currency-level)); `bis_fx_turnover` (WS_DER_OTC_TOV: BIS Triennial FX turnover shares 1989-2025 (including INR)); `bis_lbs` (WS_LBS_D_PUB: BIS cross-border bank claims by currency and reporting jurisdiction); `currency_research_entities` (currency-area definitions: schema)
- **Missing datasets:** `monetary_transition_outcomes` (independent monetary-order transition labels: not imported); `pre_1995_reserve_shares` (pre-1995 reserve currency archive: not imported)
- **Supporting evidence:** Reserve shares, FX turnover shares and cross-border bank-claim currency shares are imported with EUR kept at currency-area level and INR kept non-zero-imputed where unreported.
- **Contradictory evidence:** Independent monetary-order transition outcomes are not populated.
- **Alternative explanations:** Reserve status may lag real economic output and reflect financial openness, legal trust and network effects.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q40 — Military resources
- **Exact registered wording (`atlas_derived_v1`):** Do military resource measures predict external-order transitions better than military expenditure alone?
- **Theory category:** `external_rivalry` · **Registered claims:** `dalio_external_order_cycle`
- **Testable hypotheses:** `H03`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** expenditure kept separate from capability
- **Required datasets:** `military_capability_panel` (personnel/material/expenditure: features); `external_transition_outcomes` (order-transition outcomes: labels)
- **Available datasets (39 observed evidence summary rows):** `world_bank` (SIPRI-derived military expenditure: resource proxy)
- **Missing datasets:** `cow_nmc` (Correlates of War capabilities: not imported); `sipri_full` (direct military resource data: not imported); `external_order_transitions` (independent outcomes: not imported)
- **Supporting evidence:** Military spending is explicitly labelled a resource proxy, not capability.
- **Contradictory evidence:** No capability or transition outcomes exist for evaluation.
- **Alternative explanations:** Technology, alliances, geography and readiness can dominate spending.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q41 — Financial-centre activity
- **Exact registered wording (`atlas_derived_v1`):** Do international banking and financial-centre activity predict monetary or financial influence?
- **Theory category:** `external_rivalry` · **Registered claims:** `dalio_external_order_cycle`
- **Testable hypotheses:** `H03`
- **Implementation status:** `data_available` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** domestic market depth separated from cross-border banking intermediation
- **Required datasets:** `international_banking` (cross-border claims and centre activity: features); `financial_influence_outcomes` (independent outcomes: labels)
- **Available datasets (45 observed evidence summary rows):** `bis_lbs` (WS_LBS_D_PUB: BIS cross-border bank claims by currency and reporting jurisdiction); `bis_fx_turnover` (WS_DER_OTC_TOV: BIS Triennial FX turnover shares 1989-2025 (including INR)); `world_bank` (listed-market capitalisation, private credit, broad money: domestic depth proxies)
- **Missing datasets:** `financial_influence_outcomes` (independent financial-order outcome labels: not defined)
- **Supporting evidence:** BIS LBS shows UK leads cross-border banking share (14.3% in 2026Q2) while US leads equity market cap, demonstrating why stock-market cap/GDP is an incomplete financial-centre measure.
- **Contradictory evidence:** No independent financial-influence outcome labels exist for predictive testing.
- **Alternative explanations:** Financial influence may depend on legal jurisdiction, clearing infrastructure, currency networks and capital-account openness.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q42 — Alliances and blocs
- **Exact registered wording (`atlas_derived_v1`):** Do alliances and bloc formation change the probability of rivalry or conflict?
- **Theory category:** `external_rivalry` · **Registered claims:** `dalio_external_order_cycle`
- **Testable hypotheses:** `H03`
- **Implementation status:** `not_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** external-order hypothesis registered without outcome evidence
- **Required datasets:** `alliance_panel` (alliance/bloc histories: features); `conflict_outcomes` (independent rivalry/conflict outcomes: labels)
- **Available datasets (0 observed evidence summary rows):** None
- **Missing datasets:** `cow_alliances` (alliance histories: not imported); `ucdp_cow` (conflict outcomes: not imported)
- **Supporting evidence:** None
- **Contradictory evidence:** No alliance or conflict observations are imported.
- **Alternative explanations:** Alliances may deter conflict, provoke balancing, or merely reflect pre-existing alignment.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q43 — Historical power transitions
- **Exact registered wording (`atlas_derived_v1`):** Are historical power transitions associated with identifiable economic, financial and military sequences?
- **Theory category:** `external_rivalry` · **Registered claims:** `dalio_external_order_cycle, dalio_big_cycle`
- **Testable hypotheses:** `H03, H04`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** separate long-cycle research layer
- **Required datasets:** `historical_power_panel` (multi-century power measures: features); `power_transition_outcomes` (independent transitions: labels)
- **Available datasets (64 observed evidence summary rows):** `jst_macrohistory` (R6: long historical research panel); `maddison` (2023: Maddison Project Database 2023 historical GDP per capita in 2011 intl $ (1500-2022)); `pwt` (11.0: Penn World Table 11.0 output, worker/hour productivity, capital, human capital & TFP (1950-2023)); `world_bank` (modern power proxies: post-1960 evidence)
- **Missing datasets:** `cow_nmc` (historical capabilities: not imported); `historical_order_transitions` (dated transitions: not imported)
- **Supporting evidence:** Maddison, JST and PWT provide long economic/financial context.
- **Contradictory evidence:** No independently dated transition outcomes or historical military capability series are imported.
- **Alternative explanations:** Sequences may differ across monetary, industrial and military eras.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q44 — Power concentration
- **Exact registered wording (`atlas_derived_v1`):** Can concentration or multipolarity in power measures be quantified without a universal national power score?
- **Theory category:** `external_rivalry` · **Registered claims:** `dalio_external_order_cycle`
- **Testable hypotheses:** `H03`
- **Implementation status:** `research_method_implemented` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** separate dimensions; no universal power composite
- **Required datasets:** `compatible_reference_population` (global denominators: features); `power_measure_registry` (separated dimensions: methodology)
- **Available datasets (47 observed evidence summary rows):** `power_registry` (separated measure definitions: methodology); `world_bank` (global denominator series: share calculations); `imf_cofer` (COFER-SDMX-2.1: official FX reserve shares & claims (1995-2026Q2; currency-level)); `bis_lbs` (WS_LBS_D_PUB: BIS cross-border bank claims by currency and reporting jurisdiction)
- **Missing datasets:** `concentration_metric_protocol` (registered HHI/shares method across complete global universe: not implemented)
- **Supporting evidence:** The design explicitly avoids a manufactured national power score.
- **Contradictory evidence:** Concentration across only 8 tracked countries cannot compute a full global Herfindahl index without rest-of-world country shares.
- **Alternative explanations:** Different dimensions imply different concentration patterns (e.g. multipolar PPP GDP vs concentrated USD FX/reserve role).
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q45 — Shared leadership
- **Exact registered wording (`atlas_derived_v1`):** Can shared international leadership or distributed influence persist without a single hegemonic transition?
- **Theory category:** `external_rivalry` · **Registered claims:** `dalio_external_order_cycle, dalio_big_cycle`
- **Testable hypotheses:** `H03, H04`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** distributed measures rather than a single score
- **Required datasets:** `distributed_power_panel` (multi-dimensional shares: features); `leadership_outcomes` (independent order/leadership labels: outcomes)
- **Available datasets (40 observed evidence summary rows):** `power_registry` (separated measures: methodology); `world_bank` (modern shares: partial predictors)
- **Missing datasets:** `leadership_transition_outcomes` (independent order labels: not imported); `institutional_influence` (international institutional roles: not imported)
- **Supporting evidence:** The schema allows distributed influence and unclassified states.
- **Contradictory evidence:** No outcome chronology can test hegemonic versus shared leadership.
- **Alternative explanations:** Institutional delegation and regional blocs can sustain shared influence.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q46 — Innovation inputs and outputs
- **Exact registered wording (`atlas_derived_v1`):** Do R&D expenditure, patent activity and research capacity predict durable technological advantage?
- **Theory category:** `technology_shocks` · **Registered claims:** `dalio_external_order_cycle`
- **Testable hypotheses:** `H03`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** separated innovation input/output measures
- **Required datasets:** `innovation_panel` (R&D/patents/researchers: features); `technology_outcomes` (durable advantage labels: outcomes)
- **Available datasets (39 observed evidence summary rows):** `world_bank` (R&D, patents, researchers, high-tech exports: innovation proxies)
- **Missing datasets:** `wipo_full` (patent quality/family data: not imported); `technology_advantage_outcomes` (independent leadership labels: not defined)
- **Supporting evidence:** Input, output and trade proxies are tracked separately.
- **Contradictory evidence:** No durable-advantage outcome or long-run evaluation exists.
- **Alternative explanations:** Patent counts and R&D intensity may not capture diffusion, quality or state-led capability.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q47 — Productivity and human capital
- **Exact registered wording (`atlas_derived_v1`):** Do productivity and human-capital measures predict long-run economic resilience?
- **Theory category:** `technology_shocks` · **Registered claims:** `dalio_internal_order_cycle`
- **Testable hypotheses:** `H02, H03`
- **Implementation status:** `data_available` · **Scientific status:** `untested`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** separate PWT 2021 PPP, PWT constant national-accounts and OECD-relative productivity definitions
- **Required datasets:** `productivity_human_capital` (productivity/attainment/research: features); `resilience_outcomes` (independent resilience labels: outcomes)
- **Available datasets (53 observed evidence summary rows):** `pwt` (11.0: Penn World Table 11.0 output, worker/hour productivity, capital, human capital & TFP (1950-2023)); `oecd` (labour productivity and tertiary attainment: human-capital/productivity); `world_bank` (education and researchers: human-capital inputs)
- **Missing datasets:** `resilience_outcomes` (independent resilience outcome labels: not defined)
- **Supporting evidence:** PWT 11.0 real GDP, GDP per worker, GDP per hour (where hours exist), capital stock, human capital index and TFP are imported without combining incompatible PPP bases.
- **Contradictory evidence:** No independent long-run resilience outcome test exists.
- **Alternative explanations:** Resilience may reflect macro buffers, institutions or external demand rather than measured human capital alone.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q48 — AI adoption
- **Exact registered wording (`atlas_derived_v1`):** Can AI adoption be measured separately from general technology indicators and does it change power or productivity outcomes?
- **Theory category:** `technology_shocks` · **Registered claims:** `dalio_external_order_cycle`
- **Testable hypotheses:** `H03`
- **Implementation status:** `not_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** separate AI/general-technology rule
- **Required datasets:** `ai_adoption` (comparable AI adoption measures: features); `productivity_power_outcomes` (independent outcomes: labels)
- **Available datasets (0 observed evidence summary rows):** None
- **Missing datasets:** `ai_adoption` (comparable AI usage/capability data: not imported); `ai_histories` (long-run AI data: not available before actual observations)
- **Supporting evidence:** None
- **Contradictory evidence:** No comparable AI observations are imported.
- **Alternative explanations:** AI may diffuse unevenly and affect sectors differently; aggregate power effects are not assumed.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q49 — Energy constraint
- **Exact registered wording (`atlas_derived_v1`):** Do energy production, consumption and dependence constrain economic and external power?
- **Theory category:** `technology_shocks` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H03, H04`
- **Implementation status:** `not_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** resource constraints kept separate from general economic output
- **Required datasets:** `energy_panel` (production/consumption/dependence: features); `power_growth_outcomes` (independent outcomes: labels)
- **Available datasets (0 observed evidence summary rows):** `jst_macrohistory` (long-run economic variables: indirect context)
- **Missing datasets:** `energy_balances` (IEA/WB energy production/consumption/imports: not imported); `resource_outcomes` (independent constraint/shock labels: not defined)
- **Supporting evidence:** None
- **Contradictory evidence:** No direct energy balance series are imported.
- **Alternative explanations:** Energy constraints depend on technology, substitution, trade access and prices.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply

### Q50 — Pandemics and shocks
- **Exact registered wording (`atlas_derived_v1`):** Do pandemics, natural disasters and resource shocks alter short-, medium- or long-cycle trajectories?
- **Theory category:** `technology_shocks` · **Registered claims:** `dalio_big_cycle`
- **Testable hypotheses:** `H04`
- **Implementation status:** `partially_implemented` · **Scientific status:** `currently_untestable`
- **Current documented answer:** Unanswered with the current Atlas evidence.
- **Research methods:** separate timescales and event registry
- **Required datasets:** `shock_outcomes` (EM-DAT/UCDP/pandemic/resource events: outcomes); `cycle_panel` (pre/post shock predictors: features)
- **Available datasets (41 observed evidence summary rows):** `world_bank` (NATURAL_DISASTER_AFFECTED_PCT: 1990-2009 average exposure context); `crisis_registry` (event/coverage schema: reusable outcome contract)
- **Missing datasets:** `em_dat` (annual disaster events: not imported); `pandemic_outcomes` (comparable pandemic histories: not imported); `resource_shocks` (independent shock labels: not imported)
- **Supporting evidence:** Natural-disaster exposure is labelled a context measure, not a score.
- **Contradictory evidence:** No shock-event outcomes or causal trajectory evaluation exists.
- **Alternative explanations:** Shock effects depend on resilience, policy response and global spillovers.
- **Falsification criteria:** A registered test must fail to outperform its declared baseline or produce no independent evidence.
- **Remaining limitations:** Coverage and outcome constraints apply
