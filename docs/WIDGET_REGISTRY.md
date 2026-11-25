# Widget Registry

Generated from `src/features/widgets/index.ts` — 54 registered widget types.

| ID | Name | Category | Default | Min | Data requirement |
|---|---|---|---|---|---|
| `gdp` | GDP | economic | 3×3 | 2×2 | GDP_CURRENT_USD observations via /api/countries/{iso3}/observations |
| `gdp-per-capita` | GDP per capita | economic | 3×3 | 2×2 | GDP_PER_CAPITA observations via /api/countries/{iso3}/observations |
| `gdp-growth` | GDP growth | economic | 3×3 | 2×2 | GDP_GROWTH observations via /api/countries/{iso3}/observations |
| `inflation` | Inflation | economic | 3×3 | 2×2 | INFLATION_CPI observations via /api/countries/{iso3}/observations |
| `population` | Population | economic | 3×3 | 2×2 | POPULATION observations via /api/countries/{iso3}/observations |
| `unemployment` | Unemployment | economic | 3×3 | 2×2 | UNEMPLOYMENT_RATE observations via /api/countries/{iso3}/observations |
| `productivity` | Productivity | economic | 3×3 | 2×2 | LABOUR_PRODUCTIVITY_PER_HOUR observations via /api/countries/{iso3}/observations |
| `unit-labour-costs` | Unit labour costs | economic | 3×3 | 2×2 | UNIT_LABOUR_COST_GROWTH observations via /api/countries/{iso3}/observations |
| `government-debt` | Government debt | economic | 3×3 | 2×2 | GOVERNMENT_DEBT_GDP observations via /api/countries/{iso3}/observations |
| `debt-service-ratio` | Debt service ratio | economic | 3×3 | 2×2 | DEBT_SERVICE_RATIO observations via /api/countries/{iso3}/observations |
| `credit-gap` | Credit-to-GDP gap | economic | 3×3 | 2×2 | CREDIT_TO_GDP_GAP observations via /api/countries/{iso3}/observations |
| `gross-capital-formation` | Gross capital formation | economic | 3×3 | 2×2 | GROSS_CAPITAL_FORMATION_GDP observations via /api/countries/{iso3}/observations |
| `exports` | Exports | trade | 3×3 | 2×2 | EXPORTS_GDP observations via /api/countries/{iso3}/observations |
| `imports` | Imports | trade | 3×3 | 2×2 | IMPORTS_GDP observations via /api/countries/{iso3}/observations |
| `trade-balance` | Trade balance | trade | 3×3 | 2×2 | TRADE_BALANCE observations via /api/countries/{iso3}/observations |
| `current-account` | Current account | trade | 3×3 | 2×2 | CURRENT_ACCOUNT_GDP observations via /api/countries/{iso3}/observations |
| `trade-openness` | Trade openness | trade | 4×3 | 3×2 | none — explicit unavailable state |
| `historical-trade-comparison` | Trade comparison | trade | 6×4 | 4×3 | EXPORTS_GDP observations via /api/countries/{iso3}/observations |
| `rule-of-law` | Rule of law | governance | 3×3 | 2×2 | RULE_OF_LAW_WGI_SCORE observations via /api/countries/{iso3}/observations |
| `control-of-corruption` | Control of corruption | governance | 3×3 | 2×2 | CONTROL_OF_CORRUPTION_WGI_SCORE observations via /api/countries/{iso3}/observations |
| `political-stability` | Political stability | governance | 3×3 | 2×2 | POLITICAL_STABILITY_WGI_SCORE observations via /api/countries/{iso3}/observations |
| `education` | Education | governance | 3×3 | 2×2 | TERTIARY_ATTAINMENT_25_34 observations via /api/countries/{iso3}/observations |
| `wealth-inequality` | Wealth inequality | governance | 3×3 | 2×2 | WEALTH_SHARE_TOP_10 observations via /api/countries/{iso3}/observations |
| `gini-index` | Gini index | governance | 3×3 | 2×2 | GINI_INDEX observations via /api/countries/{iso3}/observations |
| `internal-conflict-proxy` | Internal conflict proxy | governance | 3×3 | 2×2 | POLITICAL_STABILITY_WGI_SCORE observations via /api/countries/{iso3}/observations |
| `governance-uncertainty` | Governance uncertainty | governance | 6×4 | 4×3 | GET /api/countries/{iso3}/indicators/{code}/uncertainty + observations |
| `force-score` | Force score | strength | 4×3 | 3×2 | GET /api/countries/{iso3}/force-scores |
| `all-forces` | All 17 forces | strength | 6×5 | 4×3 | force-coverage + force-scores endpoints |
| `force-coverage` | Force coverage | strength | 4×5 | 3×3 | GET /api/countries/{iso3}/force-coverage |
| `force-comparison` | Force comparison | strength | 4×3 | 3×2 | none — explicit unavailable state |
| `absolute-strength` | Absolute strength | strength | 4×3 | 3×2 | none — explicit unavailable state |
| `relative-strength` | Relative strength | strength | 4×3 | 3×2 | none — explicit unavailable state |
| `momentum-score` | Momentum (composite) | strength | 4×3 | 3×2 | none — explicit unavailable state |
| `confidence-score` | Confidence | strength | 4×3 | 3×2 | none — explicit unavailable state |
| `big-cycle-position` | Big Cycle position | strength | 4×3 | 3×2 | none — explicit unavailable state |
| `big-cycle-timeline` | Big Cycle timeline | strength | 4×3 | 3×2 | none — explicit unavailable state |
| `phase-history` | Phase history | strength | 4×3 | 3×2 | none — explicit unavailable state |
| `indicator-chart` | Indicator chart | data | 6×4 | 4×3 | observations endpoint |
| `scatter-plot` | Scatter plot | data | 4×3 | 3×2 | none — explicit unavailable state |
| `radar-chart` | Radar chart | data | 4×3 | 3×2 | none — explicit unavailable state |
| `heatmap` | Heatmap | data | 4×3 | 3×2 | none — explicit unavailable state |
| `data-table` | Data table | data | 6×4 | 4×3 | observations endpoint |
| `country-ranking` | Country ranking | data | 5×4 | 4×3 | observations endpoint × 8 countries |
| `coverage-matrix` | Coverage matrix | data | 5×4 | 4×3 | GET /api/countries + observations |
| `source-status` | Source details | data | 4×4 | 3×3 | GET /api/data/sources |
| `observation-revisions` | Revision history | data | 4×3 | 3×2 | none — explicit unavailable state |
| `data-freshness` | Data freshness | data | 4×3 | 3×2 | none — explicit unavailable state |
| `ingestion-status` | Ingestion status | data | 5×4 | 4×3 | GET /api/data/ingestion-runs |
| `api-status` | API status | research | 3×2 | 2×2 | GET /health |
| `model-version` | Model version | research | 3×3 | 2×2 | static metadata |
| `research-progress` | Research completion | research | 5×5 | 4×3 | static metadata synced with force_aggregation_definitions.py |
| `cycle-history` | Big Cycle history (experimental) | research | 8×4 | 5×3 | GET /api/research/countries/{iso3}/cycle/history |
| `force-history` | Force history | research | 6×4 | 4×3 | GET /api/countries/{iso3}/forces/{force}/history |
| `historical-validation` | Historical validation | research | 5×4 | 4×3 | GET /api/research/countries/{iso3}/availability + /api/research/execution-modes |

## Config fields per widget

### `gdp` — GDP

Latest GDP value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"GDP_CURRENT_USD"`
- `title` (text)

### `gdp-per-capita` — GDP per capita

Latest GDP per capita value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"GDP_PER_CAPITA"`
- `title` (text)

### `gdp-growth` — GDP growth

Latest GDP growth value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"GDP_GROWTH"`
- `title` (text)

### `inflation` — Inflation

Latest Inflation (CPI) value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"INFLATION_CPI"`
- `title` (text)

### `population` — Population

Latest Population value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"POPULATION"`
- `title` (text)

### `unemployment` — Unemployment

Latest Unemployment value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"UNEMPLOYMENT_RATE"`
- `title` (text)

### `productivity` — Productivity

Latest Labour productivity value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"LABOUR_PRODUCTIVITY_PER_HOUR"`
- `title` (text)

### `unit-labour-costs` — Unit labour costs

Latest Unit labour cost growth value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"UNIT_LABOUR_COST_GROWTH"`
- `title` (text)

### `government-debt` — Government debt

Latest Government debt value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"GOVERNMENT_DEBT_GDP"`
- `title` (text)

### `debt-service-ratio` — Debt service ratio

Latest Debt service ratio value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"DEBT_SERVICE_RATIO"`
- `title` (text)

### `credit-gap` — Credit-to-GDP gap

Latest Credit-to-GDP gap value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"CREDIT_TO_GDP_GAP"`
- `title` (text)

### `gross-capital-formation` — Gross capital formation

Latest Gross capital formation value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"GROSS_CAPITAL_FORMATION_GDP"`
- `title` (text)

### `exports` — Exports

Latest Exports value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"EXPORTS_GDP"`
- `title` (text)

### `imports` — Imports

Latest Imports value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"IMPORTS_GDP"`
- `title` (text)

### `trade-balance` — Trade balance

Latest Trade balance value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"TRADE_BALANCE"`
- `title` (text)

### `current-account` — Current account

Latest Current account value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"CURRENT_ACCOUNT_GDP"`
- `title` (text)

### `trade-openness` — Trade openness

TRADE_OPENNESS_GDP exists as a derived descriptive ratio (DEC-038) but is not yet exposed via the API. It is trade intensity — not a strength score (DEC-035/039).

- `reason` (text) — default `"TRADE_OPENNESS_GDP exists as a derived descriptive ratio (DEC-038) but is not yet exposed via the API. It is trade intensity — not a strength score (DEC-035/039)."`
- `methodologyStatus` (text) — default `"Derived formula approved (trade-openness-gdp-v1); API endpoint pending."`

### `historical-trade-comparison` — Trade comparison

Historical Exports chart.

- `countries` (countries) — default `["USA","CHN","DEU"]`
- `indicator` (indicator) — default `"EXPORTS_GDP"`
- `chartType` (chart-type) — default `"line"`
- `showLegend` (boolean) — default `true`
- `title` (text)

### `rule-of-law` — Rule of law

Latest Rule of law value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"RULE_OF_LAW_WGI_SCORE"`
- `title` (text)

### `control-of-corruption` — Control of corruption

Latest Control of corruption value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"CONTROL_OF_CORRUPTION_WGI_SCORE"`
- `title` (text)

### `political-stability` — Political stability

Latest Political stability value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"POLITICAL_STABILITY_WGI_SCORE"`
- `title` (text)

### `education` — Education

Latest Tertiary attainment (25–34) value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"TERTIARY_ATTAINMENT_25_34"`
- `title` (text)

### `wealth-inequality` — Wealth inequality

Latest Top 10% wealth share value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"WEALTH_SHARE_TOP_10"`
- `title` (text)

### `gini-index` — Gini index

Latest Gini index value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"GINI_INDEX"`
- `title` (text)

### `internal-conflict-proxy` — Internal conflict proxy

Latest Political stability value for a country.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"POLITICAL_STABILITY_WGI_SCORE"`
- `title` (text)

### `governance-uncertainty` — Governance uncertainty

Published WGI 90% confidence band and source counts around the score. Provider-published only — no computed confidence (DEC-022/023).

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `"RULE_OF_LAW_WGI_SCORE"`
- `title` (text)

### `force-score` — Force score

Score dimensions for one force — approved dimensions only.

- `country` (country) — default `"USA"`
- `force` (force) — default `"rule_of_law"`
- `title` (text)

### `all-forces` — All 17 forces

Every force with coverage status and executable score dimensions.

- `country` (country) — default `"USA"`
- `title` (text)

### `force-coverage` — Force coverage

Coverage statuses for all 17 forces.

- `country` (country) — default `"USA"`
- `title` (text)

### `force-comparison` — Force comparison

Cross-country force comparison requires the force-score API (read-only, in progress) — only 5/17 forces have executable scores, and all are proxies or single indicators.

- `reason` (text) — default `"Cross-country force comparison requires the force-score API (read-only, in progress) — only 5/17 forces have executable scores, and all are proxies or single indicators."`
- `methodologyStatus` (text) — default `"5/17 executable; composite methodology undecided."`

### `absolute-strength` — Absolute strength

No national composite score exists — the force weighting and missing-force rules are undecided methodology questions (Milestone 6).

- `reason` (text) — default `"No national composite score exists — the force weighting and missing-force rules are undecided methodology questions (Milestone 6)."`
- `methodologyStatus` (text) — default `"Composite methodology not yet decided."`

### `relative-strength` — Relative strength

Relative-vs-peers composite requires the same undecided weighting methodology as absolute strength.

- `reason` (text) — default `"Relative-vs-peers composite requires the same undecided weighting methodology as absolute strength."`
- `methodologyStatus` (text)

### `momentum-score` — Momentum (composite)

Force momentum exists only for the WGI ×3; a composite momentum needs the undecided weighting methodology.

- `reason` (text) — default `"Force momentum exists only for the WGI ×3; a composite momentum needs the undecided weighting methodology."`
- `methodologyStatus` (text)

### `confidence-score` — Confidence

Numeric confidence is deferred (DEC-023 — no external calibration basis). Diagnostics data (CI bounds, source counts) is imported but unused.

- `reason` (text) — default `"Numeric confidence is deferred (DEC-023 — no external calibration basis). Diagnostics data (CI bounds, source counts) is imported but unused."`
- `methodologyStatus` (text) — default `"DEFER_NUMERIC_CONFIDENCE — qualitative diagnostics only."`

### `big-cycle-position` — Big Cycle position

Phase/stage derivation is Milestone 6 — no approved composition method, weighting, or transition rules exist yet.

- `reason` (text) — default `"Phase/stage derivation is Milestone 6 — no approved composition method, weighting, or transition rules exist yet."`
- `methodologyStatus` (text) — default `"Milestone 6 — methodology research not started."`

### `big-cycle-timeline` — Big Cycle timeline

Historical phase/stage series requires the cycle model (Milestone 6) plus release-date discipline (Milestone 9) before any historical claim.

- `reason` (text) — default `"Historical phase/stage series requires the cycle model (Milestone 6) plus release-date discipline (Milestone 9) before any historical claim."`
- `methodologyStatus` (text)

### `phase-history` — Phase history

Phase history requires an approved phase model — none exists yet.

- `reason` (text) — default `"Phase history requires an approved phase model — none exists yet."`
- `methodologyStatus` (text)

### `indicator-chart` — Indicator chart

Historical chart for any indicator across 1–8 countries.

- `countries` (countries) — default `["USA"]`
- `indicator` (indicator) — default `"GDP_GROWTH"`
- `chartType` (chart-type) — default `"line"`
- `showLegend` (boolean) — default `true`
- `title` (text)

### `scatter-plot` — Scatter plot

Two-indicator scatter requires a paired-observation endpoint not yet built.

- `reason` (text) — default `"Two-indicator scatter requires a paired-observation endpoint not yet built."`
- `methodologyStatus` (text)

### `radar-chart` — Radar chart

Force radar requires the force-score API plus ≥3 scored dimensions per country.

- `reason` (text) — default `"Force radar requires the force-score API plus ≥3 scored dimensions per country."`
- `methodologyStatus` (text)

### `heatmap` — Heatmap

Indicator × country heatmap requires a matrix endpoint not yet built.

- `reason` (text) — default `"Indicator × country heatmap requires a matrix endpoint not yet built."`
- `methodologyStatus` (text)

### `data-table` — Data table

Latest-vintage raw observations table.

- `country` (country) — default `"USA"`
- `indicator` (indicator) — default `""`
- `limit` (number) — default `12`
- `title` (text)

### `country-ranking` — Country ranking

Latest indicator value across all tracked countries.

- `indicator` (indicator) — default `"GDP_GROWTH"`
- `title` (text)

### `coverage-matrix` — Coverage matrix

Per-country indicator and observation coverage.

- `title` (text)

### `source-status` — Source details

Registered providers and their pipeline status.

- `title` (text)

### `observation-revisions` — Revision history

Per-observation revision chains exist (IndicatorRevision API) but no revisions have occurred yet — all data is vintage 1.

- `reason` (text) — default `"Per-observation revision chains exist (IndicatorRevision API) but no revisions have occurred yet — all data is vintage 1."`
- `methodologyStatus` (text)

### `data-freshness` — Data freshness

A freshness dashboard needs per-series release-date metadata the API does not expose yet.

- `reason` (text) — default `"A freshness dashboard needs per-series release-date metadata the API does not expose yet."`
- `methodologyStatus` (text)

### `ingestion-status` — Ingestion status

Recent ingestion runs and outcomes.

- `title` (text)

### `api-status` — API status

Backend liveness and database connectivity.

- `title` (text)

### `model-version` — Model version

Active normalization and force-aggregation versions.

- `title` (text)

### `research-progress` — Research completion

Per-force implementation status across all 17 forces.

- `title` (text)

### `cycle-history` — Big Cycle history (experimental)

Experimental composite conditions + stage markers from the research API. Retrospective; backtest_safe=false.

- `country` (country) — default `"USA"`
- `model` (text) — default `"model_b_domain"`
- `startYear` (number) — default `2000`
- `title` (text)

### `force-history` — Force history

Historical force level / relative / momentum dimensions — retrospective latest-vintage view.

- `country` (country) — default `"USA"`
- `force` (force) — default `"rule_of_law"`
- `startYear` (number) — default `1996`
- `title` (text)

### `historical-validation` — Historical validation

Availability evidence per country: strict eligibility, provider publication and atlas retrieval evidence, missing evidence, latest period.

- `country` (country) — default `"USA"`
- `title` (text)
