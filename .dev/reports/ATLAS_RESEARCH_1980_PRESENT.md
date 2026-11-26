# Big Cycle Atlas — economic research handover, 1980–present

Generated: 2026-11-26T09:57:59.064572Z
Base commit: `b92788c1593299b57268182f294d9fd48a2bfe46`
Methodology: `normalization-v1.4`, `force-aggregation-v1.0`, experimental cycle classifier v1

## 1. Executive economic summary

Big Cycle Atlas exports actual production evidence, not a demonstration dataset. Raw macroeconomic observations already cover 1960 onward for several scale measures, while evidence-gated cycle classifications currently begin around 1995–1996 because the approved force inputs do not support earlier scores.

Largest tracked economy: **USA**; second: **CHN**. Highest domestic-condition score: **CHE**. International power is reported separately from domestic condition.

## 2. Database inventory

| Table / object | Count |
|---|---:|
| `countries` | 8 |
| `indicators` | 46 |
| `data_sources` | 19 |
| `source_series` | 46 |
| `observations_all_vintages` | 21178 |
| `reference_observations` | 24377 |
| `market_instruments` | 35 |
| `market_observations` | 96090 |
| `indicator_revisions` | 2776 |
| `indicator_diagnostics` | 3855 |
| `ingestion_runs` | 1503 |
| `research_observations` | 154113 |
| `crisis_events` | 88 |
| `crisis_coverage_rows` | 2668 |
| `theory_registry_entries` | 7 |
| `hypothesis_protocols` | 6 |
| `prediction_ledger_entries` | 1666 |
| `prediction_outcomes` | 1666 |
| `evaluation_results` | 4 |
| `population_memberships` | 26 |
| `dataset_rights` | 9 |
| `evidence_status_entries` | 12 |
| `validation_questions` | 50 |
| `validation_question_versions_stored` | 150 |
| `distinct_observation_identities` | 18402 |
| `latest_vintage_rows` | 18402 |

## 3. Historical coverage assessment

- Raw indicator coverage: `export/indicator_coverage.csv` (361 country/provider/indicator records).
- Full latest-vintage country-indicator history: `export/country_indicator_history.csv` (18402 latest-vintage observations).
- GDP, GDP per capita and population extend to 1960 for all tracked countries.
- Several trade and capital-flow measures reach 1970 or earlier.
- Government debt starts 1980 or later; labour participation starts 1990; WGI starts 1996; productivity is country-dependent.
- Verified stage classifications do not begin in 1980; earliest supported model classifications are listed below.

### Earliest verified classifications

| Model | Country | First classified period | Stage |
|---|---|---:|---|
| `model_a_equal` | USA | 1995-Q4 | RISE |
| `model_a_equal` | CHN | 1996-Q4 | RISE |
| `model_a_equal` | IND | 1996-Q4 | RISE |
| `model_a_equal` | JPN | 1996-Q4 | PEAK |
| `model_a_equal` | DEU | 1995-Q4 | RISE |
| `model_a_equal` | GBR | 1996-Q4 | PEAK |
| `model_a_equal` | FRA | 1995-Q4 | RISE |
| `model_a_equal` | CHE | 1995-Q4 | RISE |
| `model_b_domain` | USA | 1995-Q4 | RISE |
| `model_b_domain` | CHN | 1996-Q4 | PEAK |
| `model_b_domain` | IND | 1996-Q4 | RISE |
| `model_b_domain` | JPN | 1996-Q4 | RISE |
| `model_b_domain` | DEU | 1995-Q4 | RISE |
| `model_b_domain` | GBR | 1996-Q4 | PEAK |
| `model_b_domain` | FRA | 1995-Q4 | RISE |
| `model_b_domain` | CHE | 1995-Q4 | RISE |
| `model_c_overlap` | USA | 1995-Q4 | RISE |
| `model_c_overlap` | CHN | 1996-Q4 | PEAK |
| `model_c_overlap` | IND | 1996-Q4 | RISE |
| `model_c_overlap` | JPN | 1996-Q4 | RISE |
| `model_c_overlap` | DEU | 1995-Q4 | RISE |
| `model_c_overlap` | GBR | 1996-Q4 | PEAK |
| `model_c_overlap` | FRA | 1995-Q4 | RISE |
| `model_c_overlap` | CHE | 1995-Q4 | RISE |
| `model_d_comparable` | USA | 1996-Q4 | PEAK |
| `model_d_comparable` | CHN | 1996-Q4 | RISE |
| `model_d_comparable` | IND | 1996-Q4 | RISE |
| `model_d_comparable` | JPN | 1996-Q4 | PEAK |
| `model_d_comparable` | DEU | 1996-Q4 | PEAK |
| `model_d_comparable` | GBR | 1996-Q4 | PEAK |
| `model_d_comparable` | FRA | 1996-Q4 | PEAK |
| `model_d_comparable` | CHE | 1996-Q4 | PEAK |

## 4. Eight-country economic comparison

| Country | Domestic condition | Stage | Direction | Coverage | GDP | Tracked GDP share | Military expenditure | Tracked military share | Tracked trade share |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| Switzerland (CHE) | 68.08 | EARLY_DECLINE | declining | 67.4% | $1,043,529,899,251 | 1.45% | $7,591,405,901 | 0.44% | 5.26% |
| China (CHN) | 51.15 | DECLINE | declining | 65.2% | $19,498,039,388,043 | 27.03% | $335,524,155,624 | 19.48% | 25.36% |
| Germany (DEU) | 58.72 | DECLINE | declining | 67.4% | $5,050,922,925,047 | 7.0% | $113,585,948,605 | 6.6% | 13.59% |
| France (FRA) | 54.96 | DECLINE | declining | 67.4% | $3,366,315,927,447 | 4.67% | $68,007,580,714 | 3.95% | 7.75% |
| United Kingdom (GBR) | 58.25 | DECLINE | declining | 65.2% | $4,002,587,541,846 | 5.55% | $88,977,496,940 | 5.17% | 8.57% |
| India (IND) | 37.90 | LATE_PEAK | rising | 65.2% | $3,956,067,115,772 | 5.49% | $92,057,013,588 | 5.35% | 6.27% |
| Japan (JPN) | 54.01 | RISE | steady | 65.2% | $4,435,162,999,977 | 6.15% | $62,158,093,812 | 3.61% | 6.82% |
| United States (USA) | 57.99 | RISE | rising | 67.4% | $30,769,700,000,000 | 42.66% | $954,387,000,000 | 55.41% | 26.38% |

Tracked shares use the eight Atlas countries as the denominator and are not global shares.

## 5. Seventeen-force evidence

See `export/force_measurements.csv` for the 136-row country-force matrix and `export/force_methodology.json` for approved definitions, live inputs, candidate indicators, ceilings and aggregation semantics. Only approved executable scores are numerical; context and dimension profiles are deliberately not presented as fabricated force scores.

Key methodology constraints:

- Leadership is represented by WGI government effectiveness, not individual leaders.
- Character is represented by relative economic participation, not national character.
- Productivity is an OECD-reference percentile where available, not a global percentile.
- Indebtedness uses an approved own-history debt-service/credit-gap composition.
- Military expenditure is resources absorbed by defence, not total capability.
- Geography remains structural context; acts of nature remain incomplete hazard evidence.

## 6. International power evidence

See `export/power_measure_registry.json`, `export/global_power_shares.csv`, `export/power_measures.csv` and `export/power_measure_history.csv`. The registry separates economic output, trade, military resources, innovation, education, financial depth and reserve-currency entities; it does not define a composite power ranking.

### Latest verified global shares

| Country | Measurement | Observation period | Global share |
|---|---|---:|---:|
| USA | `GDP_CURRENT_USD` | 2025-01-01 | 26.00% |
| USA | `GDP_PPP_CURRENT_INTL` | 2025-01-01 | 14.57% |
| USA | `GDP_REAL_CONSTANT_USD` | 2025-01-01 | 23.30% |
| USA | `MERCHANDISE_EXPORTS_USD` | 2025-01-01 | 8.28% |
| USA | `MERCHANDISE_IMPORTS_USD` | 2025-01-01 | 13.14% |
| USA | `MILITARY_EXPENDITURE_USD` | 2025-01-01 | 33.42% |
| USA | `PATENT_APPLICATIONS_RESIDENT` | 2024-01-01 | 10.00% |
| USA | `HIGH_TECHNOLOGY_EXPORTS_USD` | 2023-01-01 | 5.83% |
| CHN | `GDP_CURRENT_USD` | 2025-01-01 | 16.47% |
| CHN | `GDP_PPP_CURRENT_INTL` | 2025-01-01 | 19.54% |
| CHN | `GDP_REAL_CONSTANT_USD` | 2025-01-01 | 19.47% |
| CHN | `MERCHANDISE_EXPORTS_USD` | 2025-01-01 | 14.29% |
| CHN | `MERCHANDISE_IMPORTS_USD` | 2025-01-01 | 9.68% |
| CHN | `MILITARY_EXPENDITURE_USD` | 2025-01-01 | 11.75% |
| CHN | `PATENT_APPLICATIONS_RESIDENT` | 2024-01-01 | 61.87% |
| CHN | `HIGH_TECHNOLOGY_EXPORTS_USD` | 2023-01-01 | 23.08% |
| IND | `GDP_CURRENT_USD` | 2025-01-01 | 3.34% |
| IND | `GDP_PPP_CURRENT_INTL` | 2025-01-01 | 8.14% |
| IND | `GDP_REAL_CONSTANT_USD` | 2025-01-01 | 3.71% |
| IND | `MERCHANDISE_EXPORTS_USD` | 2025-01-01 | 1.69% |
| IND | `MERCHANDISE_IMPORTS_USD` | 2025-01-01 | 2.82% |
| IND | `MILITARY_EXPENDITURE_USD` | 2025-01-01 | 3.22% |
| IND | `PATENT_APPLICATIONS_RESIDENT` | 2024-01-01 | 2.34% |
| IND | `HIGH_TECHNOLOGY_EXPORTS_USD` | 2023-01-01 | 1.15% |

Global shares use provider world aggregates (`WLD`) as denominators and are distinct from the eight-country tracked shares shown above. Currency-level official reserve shares (`IMF COFER`), FX turnover shares (`BIS Triennial Survey`, including `INR` at 1.95% in 2025) and cross-border banking shares (`BIS Locational Banking Statistics`) are exported in `export/reserve_currency_history.csv`; `EUR` shares remain on the shared Eurosystem currency area and `INR` is never zero-imputed in COFER.

## 7. USA–China–India measured comparison

| Indicator | Common baseline | USA baseline | China baseline | Common latest | USA latest | China latest | China/USA baseline | China/USA latest | Unit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `GDP_CURRENT_USD` | 1980 | 2857307000000.0 | 191487500000.0 | 2025 | 30769700000000.0 | 19498039388042.6 | 0.067 | 0.634 | USD |
| `GDP_PPP_CURRENT_INTL` | 1990 | 5963144000000.0 | 1124647401358.64 | 2025 | 30769700000000.0 | 41259823532528.0 | 0.189 | 1.341 | current international $ |
| `GDP_REAL_CONSTANT_USD` | 1980 | 7062521475379.06 | 428434994544.795 | 2025 | 23222782186839.4 | 19401316126585.1 | 0.061 | 0.835 | constant 2015 US$ |
| `POPULATION` | 1980 | 227225000.0 | 981235000.0 | 2025 | 341784857.0 | 1406585000.0 | 4.318 | 4.115 | count |
| `MERCHANDISE_EXPORTS_USD` | 1980 | 225566000000.0 | 18099000000.0 | 2025 | 2185220000000.0 | 3771842000000.0 | 0.080 | 1.726 | current US$ |
| `MERCHANDISE_IMPORTS_USD` | 1980 | 256985000000.0 | 19941000000.0 | 2025 | 3506554000000.0 | 2582896000000.0 | 0.078 | 0.737 | current US$ |
| `COMMERCIAL_SERVICE_EXPORTS_USD` | 1982 | 50850000000.0 | 2476000000.0 | 2025 | 1212381000000.0 | 383154067120.32 | 0.049 | 0.316 | current US$ |
| `COMMERCIAL_SERVICE_IMPORTS_USD` | 1982 | 37130000000.0 | 1865000000.0 | 2025 | 884705000000.0 | 619603232786.67 | 0.050 | 0.700 | current US$ |
| `EXPORTS_GDP` | 1980 | 9.82645547013324 | 10.1341967491351 | 2024 | 10.97469647515 | 20.4428283665891 | 1.031 | 1.863 | percent |
| `IMPORTS_GDP` | 1980 | 10.2833892192894 | 11.406859455578 | 2024 | 14.0413208226783 | 17.5132317706653 | 1.109 | 1.247 | percent |
| `CURRENT_ACCOUNT_GDP` | 1982 | -0.347121184979076 | 2.76132699309013 | 2025 | -3.8254126624569 | 3.76972243689338 | -7.955 | -0.985 | percent |
| `MILITARY_EXPENDITURE_USD` | 1989 | 321866558808.32 | 11251332630.388 | 2025 | 954387000000.0 | 335524155624.44 | 0.035 | 0.352 | current US$ |
| `MILITARY_EXPENDITURE_GDP` | 1989 | 5.871206008 | 2.4471013153 | 2025 | 3.1173079811 | 1.7247233166 | 0.417 | 0.553 | percent of GDP |
| `RND_EXPENDITURE_GDP` | 1996 | 2.45013 | 0.56014 | 2023 | 3.44716 | 2.57729 | 0.229 | 0.748 | percent |
| `PATENT_APPLICATIONS_RESIDENT` | 1985 | 63673.0 | 4065.0 | 2024 | 270295.0 | 1672001.0 | 0.064 | 6.186 | applications |
| `RESEARCHERS_PER_MILLION` | 1996 | 3206.67656 | 447.0994 | 2022 | 4937.49441 | 1849.23669 | 0.139 | 0.375 | per million people |
| `HIGH_TECHNOLOGY_EXPORTS_USD` | 2007 | 240663518341.0 | 343558973511.0 | 2024 | 232906639404.0 | 856764726389.0 | 1.428 | 3.679 | current US$ |
| `LABOUR_PRODUCTIVITY_PER_HOUR` | — | — | — | — | — | — | — | — |  |
| `GOVERNMENT_DEBT_GDP` | 2001 | 53.488708 | 24.187029 | 2025 | 124.376732 | 98.608625 | 0.452 | 0.793 | percent |
| `STOCK_MARKET_CAP_GDP` | 2003 | 124.5260586831 | 30.4636713403437 | 2025 | 224.04464850161 | 79.540605039043 | 0.245 | 0.355 | % of GDP |
| `DOMESTIC_CREDIT_PRIVATE_GDP` | 1980 | 94.3548659876566 | 52.5338903757861 | 2024 | 195.875075677875 | 194.312528264561 | 0.557 | 0.992 | % of GDP |
| `BROAD_MONEY_GDP` | 1980 | 69.5063918577878 | 36.3622516700394 | 2024 | 98.7562585226237 | 227.669028630796 | 0.523 | 2.305 | % of GDP |

Ratios are direct raw-measurement ratios on common observation years and are only meaningful for compatible units and reference populations. A change in ratio indicates convergence/divergence in that measurement, not a complete leadership transition.

Decade and recent 1/3/5/10-year changes for USA, China and India are exported in `export/historical_period_comparison.csv`, and common-period ratio & gap convergence/divergence classifications (`narrowing`, `widening`, `stable`) are exported in `export/usa_chn_ind_gap_dynamics.csv`. India is therefore compared on the same measurement definitions rather than forced into a cycle-stage narrative.

## 8. Four-model experimental domestic-condition comparison

| Model | Countries with latest score | Latest classified periods | Notes |
|---|---:|---:|---|
| `model_a_equal` | 8 | 8 | equal-force benchmark — reference only |
| `model_b_domain` | 8 | 8 | equal weight per populated domain |
| `model_c_overlap` | 8 | 8 | declared overlap groups share one weight |
| `model_d_comparable` | 8 | 8 | forces present in all 8 tracked countries |

### Equivalence and actual inclusion audit

| Pair | Country-period comparisons | Exact score agreement | Near-exact score agreement | Exact stage agreement | Materially equivalent |
|---|---:|---:|---:|---:|---|
| `model_a_equal` vs `model_b_domain` | 368 | 33.7% | 33.7% | 56.2% | no |
| `model_a_equal` vs `model_c_overlap` | 368 | 33.7% | 33.7% | 56.2% | no |
| `model_a_equal` vs `model_d_comparable` | 368 | 44.8% | 44.8% | 78.5% | no |
| `model_b_domain` vs `model_c_overlap` | 368 | 70.9% | 100.0% | 100.0% | yes |
| `model_b_domain` vs `model_d_comparable` | 368 | 33.7% | 33.7% | 47.3% | no |
| `model_c_overlap` vs `model_d_comparable` | 368 | 33.7% | 33.7% | 47.3% | no |

`model_b_domain` versus `model_c_overlap`: 368 comparisons, 70.9% exact-score, 100.0% near-exact-score and 100.0% exact-stage agreement; **materially equivalent under the current force set**. Equivalent models are not independent confirmation. The current populated domain units collapse to the same four units as the declared overlap groups, so the intended weighting distinction produces identical effective weights; this is documented evidence, not a formula defect that should be hidden by artificial disagreement.

Actual included/excluded forces are exported in `export/actual_force_inclusion.csv`; effective weights are in `export/model_effective_weights.csv`. Indebtedness is configured as a candidate but produced 32 semantic exclusions because its approved score is own-history condition, not a cross-country comparable level.

### Current model agreement

| Country | Current stages | Unique stages | Composite score spread |
|---|---|---:|---:|
| USA | model_a_equal=PEAK; model_b_domain=RISE; model_c_overlap=RISE; model_d_comparable=EARLY_DECLINE | 3 | 3.15 |
| CHN | model_a_equal=LATE_PEAK; model_b_domain=DECLINE; model_c_overlap=DECLINE; model_d_comparable=LATE_PEAK | 2 | 3.44 |
| IND | model_a_equal=LATE_PEAK; model_b_domain=LATE_PEAK; model_c_overlap=LATE_PEAK; model_d_comparable=RISE | 2 | 8.36 |
| JPN | model_a_equal=PEAK; model_b_domain=RISE; model_c_overlap=RISE; model_d_comparable=LATE_RISE | 3 | 19.49 |
| DEU | model_a_equal=EARLY_DECLINE; model_b_domain=DECLINE; model_c_overlap=DECLINE; model_d_comparable=EARLY_DECLINE | 2 | 9.10 |
| GBR | model_a_equal=EARLY_DECLINE; model_b_domain=DECLINE; model_c_overlap=DECLINE; model_d_comparable=EARLY_DECLINE | 2 | 8.11 |
| FRA | model_a_equal=DECLINE; model_b_domain=DECLINE; model_c_overlap=DECLINE; model_d_comparable=DECLINE | 1 | 4.64 |
| CHE | model_a_equal=EARLY_DECLINE; model_b_domain=EARLY_DECLINE; model_c_overlap=EARLY_DECLINE; model_d_comparable=EARLY_DECLINE | 1 | 9.39 |

Detailed scores: `export/composite_results.csv`
Complete classifications: `export/cycle_history.csv`
Transitions: `export/cycle_transitions.csv` (219 recorded model-country transitions)

## 9. Forecast readiness

See `export/forecast_readiness.json` and `export/strict_historical_availability.json`. Raw observation vintages (21178) are stored data versions, not scored forecast samples. Atlas retrieval timestamps prove when data entered Atlas, not when providers published it historically. The corrected strict-eligible historical scored-period count is **0** until a release-date-safe scoring run exists; forecast probabilities remain unavailable.

## 10. Data quality findings

See `export/data_quality_findings.csv`. Material gaps are reported as gaps, not corrected silently or converted to zero.

| Finding | Records |
|---|---:|
| `large_period_gaps` | 16 |
| `starts_after_1980` | 155 |

## 11. Scientific limitations

- Historical calculations use latest-vintage observations and are retrospective research, not release-date-safe backtests.
- Raw scale measures may extend to 1960, but the cycle engine remains constrained by coverage, minimum observations and hysteresis.
- Military spending is an input resource, not full military capability.
- OECD productivity percentiles are explicitly OECD-reference measurements and are not global percentiles; Penn World Table 11.0 (2021 PPP) and Maddison 2023 (2011 international $) are exported separately in `export/historical_productivity_pwt_maddison.csv`.
- Official reserve-currency shares (IMF COFER 1995–2026Q2), BIS FX turnover (1989–2025) and BIS cross-border banking claims (1977Q4–2026Q2) are currency/centre measurements with documented methodology breaks, not national strength scores.
- Boundary metadata distinguishes current Germany from provider-labelled pre-1991 history and mainland-China coverage; provider definitions still limit historical joins.

## 12. Recommended next research priorities

1. Pre-register `H01B` testing private-sector credit growth (`JST tloans/gdp` and `BIS CREDIT_PRIVATE_NF_GDP`) with multi-country crisis-wave clustering controls.
2. Pre-register `H02` persistent productivity slowdown outcomes using PWT 11.0 `rtfpna` and WGI governance series.
3. Configure `BCA_FRED_API_KEY` locally to populate genuine ALFRED real-time vintage histories and unlock strict `as_of` cutoff tests.
4. Import official IMF WP/2026/094 (`wp2694.zip`) once accessible to expand banking-crisis coverage beyond the 18 JST economies.
5. Evaluate V-Dem, UCDP and Correlates of War licensing/access to address the 25+ untestable internal-conflict and external-rivalry questions.
