# Big Cycle Atlas — economic research handover, 1980–present

Generated: 2026-11-25T20:57:36.438304Z  
Commit: `3ecd2c1e5aae0342081c517b4e508d4fbc7ef528`  
Methodology: `normalization-v1.4`, `force-aggregation-v1.0`, experimental cycle classifier v1

## 1. Executive economic summary

Big Cycle Atlas exports actual production evidence, not a demonstration dataset. Raw macroeconomic observations already cover 1960 onward for several scale measures, while evidence-gated cycle classifications currently begin around 1995–1996 because the approved force inputs do not support earlier scores.

Largest tracked economy: **USA**; second: **CHN**. Highest domestic-condition score: **CHE**. International power is reported separately from domestic condition.

## 2. Database inventory

| Table / object | Count |
|---|---:|
| `countries` | 8 |
| `indicators` | 33 |
| `data_sources` | 10 |
| `source_series` | 33 |
| `observations_all_vintages` | 17170 |
| `reference_observations` | 23928 |
| `market_instruments` | 35 |
| `market_observations` | 96090 |
| `indicator_revisions` | 2776 |
| `indicator_diagnostics` | 3855 |
| `ingestion_runs` | 1479 |
| `distinct_observation_identities` | 14394 |
| `latest_vintage_rows` | 14394 |

## 3. Historical coverage assessment

- Raw indicator coverage: `export/indicator_coverage.csv` (259 country/provider/indicator records).
- Full latest-vintage country-indicator history: `export/country_indicator_history.csv` (14394 latest-vintage observations).
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

See `export/power_measures.csv` and `export/power_measure_history.csv`. The production measurement set uses latest-vintage GDP, GDP per capita, growth, exports/imports, current account, military expenditure, R&D, labour productivity, government debt, population, REER, rule of law and tertiary attainment.

## 7. USA–China measured comparison

| Indicator | USA baseline | China baseline | USA latest | China latest | China/USA baseline | China/USA latest | Unit |
|---|---:|---:|---:|---:|---:|---:|---|
| `GDP_CURRENT_USD` | 2857307000000.0 | 191487500000.0 | 30769700000000.0 | 19498039388042.6 | 0.067 | 0.634 | USD |
| `POPULATION` | 227225000.0 | 981235000.0 | 341784857.0 | 1406585000.0 | 4.318 | 4.115 | count |
| `EXPORTS_GDP` | 9.82645547013324 | 10.1341967491351 | 10.97469647515 | 21.0711983566772 | 1.031 | 1.920 | percent |
| `IMPORTS_GDP` | 10.2833892192894 | 11.406859455578 | 14.0413208226783 | 16.8851895085539 | 1.109 | 1.203 | percent |
| `CURRENT_ACCOUNT_GDP` | 0.0744407233804418 | — | -3.8254126624569 | 3.76972243689338 | — | -0.985 | percent |
| `MILITARY_EXPENDITURE_USD` | 143688354872.676 | — | 954387000000.0 | 335524155624.44 | — | 0.352 | current US$ |
| `MILITARY_EXPENDITURE_GDP` | 5.1535374665 | — | 3.1173079811 | 1.7247233166 | — | 0.553 | percent of GDP |
| `RND_EXPENDITURE_GDP` | — | — | 3.44716 | 2.57729 | — | 0.748 | percent |
| `LABOUR_PRODUCTIVITY_PER_HOUR` | — | — | 85.60236428340167 | — | — | — | US dollars per hour, PPP converted |
| `GOVERNMENT_DEBT_GDP` | — | — | 124.376732 | 98.608625 | — | 0.793 | percent |

Ratios are direct raw-measurement ratios and are only meaningful for compatible units and reference populations. A change in ratio indicates convergence/divergence in that measurement, not a complete leadership transition.

## 8. Four-model Big Cycle comparison

| Model | Countries with latest score | Latest classified periods | Notes |
|---|---:|---:|---|
| `model_a_equal` | 8 | 8 | equal-force benchmark — reference only |
| `model_b_domain` | 8 | 8 | equal weight per populated domain |
| `model_c_overlap` | 8 | 8 | declared overlap groups share one weight |
| `model_d_comparable` | 8 | 8 | forces present in all 8 tracked countries |

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

See `export/forecast_readiness.json`. The existing evidence gates remain active; no unsupported transition probability, countdown or leadership-transfer date is emitted.

## 10. Data quality findings

See `export/data_quality_findings.csv`. Material gaps are reported as gaps, not corrected silently or converted to zero.

| Finding | Records |
|---|---:|
| `large_period_gaps` | 14 |
| `starts_after_1980` | 121 |

## 11. Scientific limitations

- Historical calculations use latest-vintage observations and are retrospective research, not release-date-safe backtests.
- Raw scale measures may extend to 1960, but the cycle engine remains constrained by coverage, minimum observations and hysteresis.
- Military spending is an input resource, not full military capability.
- OECD productivity percentiles are explicitly OECD-reference measurements and are not global percentiles.
- Financial-centre and reserve-currency dimensions remain materially incomplete.
- Country-boundary changes (especially Germany) require explicit interpretation before joining historical regimes.

## 12. Recommended next research priorities

1. Add Maddison/PWT real-output and capital history as separate labelled historical methods.
2. Add SIPRI direct military expenditure records for provenance and global-share denominators.
3. Add verified financial-centre/capital-market and reserve-currency reference series.
4. Add country-boundary discontinuity metadata for Germany and other territorial changes.
5. Preserve evidence gates before attempting any leadership-transition forecast.
