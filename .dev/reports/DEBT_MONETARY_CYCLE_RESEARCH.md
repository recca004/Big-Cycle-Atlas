# Debt & Monetary Cycle Research — v1.2

Generated: 2026-11-26T09:58:08.175226+00:00
Source dataset: JST Macrohistory R6 · BIS WS_TC/WS_CBPOL/WS_DER_OTC_TOV/WS_LBS_D_PUB · IMF COFER-SDMX-2.1 · PWT 11.0 · Maddison 2023
Registry: `validation-questions-v1.2` (v1.0/v1.1 rows preserved unchanged)
Evaluations are **retrospective diagnostics** on a previously-inspected holdout — no calibrated probabilities, AUC is discrimination not forecast accuracy.

## 1. Public versus private debt findings

| Predictor (1990–2020 holdout, 1y horizon) | ROC AUC | Base-rate-precision note |
|---|---:|---|
| **Public debt/GDP 5y change (H01-P1.0, registered)** | **0.363** | precision below ~3.4% base rate |
| **Private credit/GDP 5y change (H01B-P1.0)** | **0.719** | precision 0.06 at p80 warning |

Public and private debt are different measurements with opposite pre-crisis
behaviour: public debt/GDP is often flat or falling during private booms and
surges AFTER crises via bailouts and automatic stabilisers. The H01-P1.0
negative result applies only to the tested public-debt proposition; it is not
evidence that all debt-cycle theory is false.

## 2. Private-credit crisis diagnostics (H01B-P1.0)

| Predictor | 1y AUC | 5y AUC | 1y PR-AUC | warn share | AUC 95% bootstrap CI (year-block) | events |
|---|---:|---:|---:|---:|---:|---:|
| Private credit/GDP, 5-year change (tloans/gdp) | 0.719 | 0.591 | 0.093 | 40.3% | 0.525–0.848 | 19 |
| Private credit/GDP level (tloans/gdp) | 0.623 | 0.502 | 0.082 | 82.0% | 0.278–0.738 | 19 |
| Household credit/GDP, 5-year change (thh/gdp) | 0.723 | 0.615 | 0.106 | 45.5% | 0.574–0.810 | 19 |
| Corporate credit/GDP, 5-year change (tbus/gdp) | 0.677 | 0.544 | 0.153 | 24.8% | 0.457–0.810 | 19 |
| Mortgage credit/GDP, 5-year change (tmort/gdp) | 0.696 | 0.613 | 0.133 | 52.8% | 0.372–0.783 | 19 |
| Credit/GDP gap vs trailing 10y trend (one-sided OLS) | 0.673 | 0.673 | 0.132 | 35.6% | 0.541–0.813 | 19 |
| Debt-service proxy (tloans/gdp x short rate; derived, not BIS DSR) | 0.767 | 0.463 | 0.158 | 28.1% | 0.585–0.920 | 19 |
| Real house price, 3-year growth (hpnom/cpi) | 0.706 | 0.599 | 0.076 | 26.3% | 0.570–0.875 | 19 |
| Real long-term rate (ltrate - CPI inflation) | 0.497 | 0.449 | 0.036 | 11.1% | 0.365–0.710 | 19 |
| Public debt/GDP, 5-year change (H01-P1.0 reference control) | 0.363 | 0.296 | 0.027 | 35.1% | 0.261–0.807 | 19 |
| Public interest burden proxy (debtgdp x long rate; derived) | 0.493 | 0.428 | 0.037 | 23.5% | 0.391–0.711 | 19 |
| Credit/GDP 5y change residualised on 5y real income growth (train-fit OLS) | 0.717 | 0.589 | 0.099 | 40.5% | 0.515–0.846 | 19 |

Warning rule: train percentile ≥ 0.80 (H01 convention, declared in-protocol).
Primary: `private_credit_gdp_5y_change`. The income-residualised variant keeps
AUC 0.717 — the association is not merely an income-growth reflection.

## 3. Clustered historical evaluation

Held-out test episodes: 3 independent crisis episodes
(E08_1984_1991 (9 onsets); E09_1997_1997 (1 onsets); E10_2007_2008 (13 onsets)).
Only **3** independent post-1990 episodes exist; 13/19 events are the 2007–2008
wave. Uncertainty intervals use year-block bootstrap so co-moving crises are
not counted as independent evidence.

Leave-one-episode-out / leave-one-country-out / decade blocks / ex-2007–2008
sensitivity for the primary predictor: `{
  "leave_one_episode_out": {
    "E01_1870_1878": {
      "dropped_years": [
        1870,
        1871,
        1873,
        1876,
        1877,
        1878
      ],
      "dropped_events": 10,
      "n": 556,
      "auc": 0.7191022248358326
    },
    "E02_1882_1893": {
      "dropped_years": [
        1882,
        1883,
        1885,
        1887,
        1889,
        1890,
        1891,
        1893
      ],
      "dropped_events": 14,
      "n": 556,
      "auc": 0.7191022248358326
    },
    "E03_1899_1901": {
      "dropped_years": [
        1899,
        1900,
        1901
      ],
      "dropped_events": 4,
      "n": 556,
      "auc": 0.7191022248358326
    },
    "E04_1907_1913": {
      "dropped_years": [
        1907,
        1908,
        1910,
        1913
      ],
      "dropped_events": 8,
      "n": 556,
      "auc": 0.7191022248358326
    },
    "E05_1920_1935": {
      "dropped_years": [
        1920,
        1921,
        1922,
        1923,
        1924,
        1925,
        1927,
        1930,
        1931,
        1934,
        1935
      ],
      "dropped_events": 26,
      "n": 556,
      "auc": 0.7191022248358326
    },
    "E06_1939_1939": {
      "dropped_years": [
        1939
      ],
      "dropped_events": 1,
      "n": 556,
      "auc": 0.7191022248358326
    },
    "E07_1974_1977": {
      "dropped_years": [
        1974,
        1977
      ],
      "dropped_events": 2,
      "n": 556,
      "auc": 0.7191022248358326
    },
    "E08_1984_1991": {
      "dropped_years": [
        1984,
        1987,
        1988,
        1989,
        1990,
        1991
      ],
      "dropped_events": 9,
      "n": 520,
      "auc": 0.6957227555053642
    },
    "E09_1997_1997": {
      "dropped_years": [
        1997
      ],
      "dropped_events": 1,
      "n": 538,
      "auc": 0.7263888888888889
    },
    "E10_2007_2008": {
      "dropped_years": [
        2007,
        2008
      ],
      "dropped_events": 13,
      "n": 520,
      "auc": 0.7597276264591439
    }
  },
  "leave_one_country_out_auc_min_max": [
    0.6993978693839741,
    0.7438088976550515
  ],
  "leave_one_country_out": {
    "AUS": {
      "n": 525,
      "auc": 0.7348658206781776
    },
    "BEL": {
      "n": 525,
      "auc": 0.7235919351303967
    },
    "CAN": {
      "n": 525,
      "auc": 0.7163511545662575
    },
    "CHE": {
      "n": 525,
      "auc": 0.7360467809170912
    },
    "DEU": {
      "n": 525,
      "auc": 0.7438088976550515
    },
    "DNK": {
      "n": 525,
      "auc": 0.7088538242384397
    },
    "ESP": {
      "n": 525,
      "auc": 0.7094564979180363
    },
    "FIN": {
      "n": 525,
      "auc": 0.7135108481262328
    },
    "FRA": {
      "n": 525,
      "auc": 0.7187157571772956
    },
    "GBR": {
      "n": 525,
      "auc": 0.6998031496062992
    },
    "IRL": {
      "n": 525,
      "auc": 0.7059500328731098
    },
    "ITA": {
      "n": 525,
      "auc": 0.7289254284390921
    },
    "JPN": {
      "n": 527,
      "auc": 0.7237502728661864
    },
    "NLD": {
      "n": 525,
      "auc": 0.7215647600262984
    },
    "NOR": {
      "n": 525,
      "auc": 0.7208237986270023
    },
    "PRT": {
      "n": 525,
      "auc": 0.7212360289283366
    },
    "SWE": {
      "n": 525,
      "auc": 0.6993978693839741
    },
    "USA": {
      "n": 525,
      "auc": 0.71772956388341
    }
  },
  "time_blocks": {
    "1990-1999": {
      "n": 180,
      "events": 6,
      "base_rate": 0.03333333333333333,
      "auc": 0.814176245210728
    },
    "2000-2009": {
      "n": 180,
      "events": 13,
      "base_rate": 0.07222222222222222,
      "auc": 0.59120221096269
    },
    "2010-2020": {
      "n": 196,
      "events": 0,
      "base_rate": 0.0,
      "auc": null
    }
  },
  "sensitivity": {
    "ex_2007_2008": {
      "n": 520,
      "events": 6,
      "auc": 0.7597276264591439
    }
  },
  "episodes_in_test": [
    "E08_1984_1991",
    "E09_1997_1997",
    "E10_2007_2008"
  ]
}`.

Threshold heterogeneity (H01T-P1.0): no reproducible universal debt-to-GDP
level threshold — pooled p80 discriminates at/below chance for public debt and
flags 82% of test years for private credit; per-country p80s span ~5×. See
`export/threshold_heterogeneity_evaluation.json`.

## 4. Monetary conditions across the eight primary countries

| Entity | Measured series coverage |
|---|---|
| USA | POLICY_RATE_PCT 1954–2026, cpi 1870–2020, ltrate 1870–2020, money 1870–2020, stir 1870–2020, xrusd 1870–2020 |
| CHN | POLICY_RATE_PCT 1996–2026 |
| CHE | POLICY_RATE_PCT 1946–2026, cpi 1870–2020, ltrate 1880–2020, money 1880–2020, stir 1870–2020, xrusd 1870–2020 |
| DEU | POLICY_RATE_PCT 1948–1998, cpi 1870–2020, ltrate 1870–2020, money 1870–2020, stir 1870–2020, xrusd 1870–2020 |
| FRA | POLICY_RATE_PCT 1945–1998, cpi 1870–2020, ltrate 1870–2020, money 1870–2020, stir 1870–2020, xrusd 1870–2020 |
| GBR | POLICY_RATE_PCT 1946–2026, cpi 1870–2020, ltrate 1870–2020, money 1870–2020, stir 1870–2020, xrusd 1870–2020 |
| JPN | POLICY_RATE_PCT 1946–2026, cpi 1870–2020, ltrate 1870–2020, money 1870–2020, stir 1879–2020, xrusd 1870–2020 |
| IND | POLICY_RATE_PCT 1946–2026 |

Real rates = nominal JST long rate minus contemporaneous CPI inflation
(derived, labelled). Nominal and real series are never conflated.

## 5. International currency influence

- **COFER reserve shares** (allocated reserves, latest):
  USD 56.7% (2026), EUR 20.6% (2026), DEM 13.8% (1998), OTHC 6.1% (2026), JPY 5.0% (2026), GBP 4.6% (2026), CAD 2.5% (2026), AUD 2.2% (2026), CNY 2.1% (2026), FRF 1.6% (1998), ECU 1.3% (1998), NLG 0.3% (1998), CHF 0.3% (2026)
- **BIS FX turnover** (200% currency-leg convention, latest):
  USD 89.1% (2025), DEM 30.5% (1998), EUR 28.5% (2025), JPY 16.9% (2025), GBP 10.2% (2025), CNY 8.6% (2025), CHF 6.3% (2025), FRF 5.0% (1998), INR 1.9% (2025)
- **BIS cross-border claims by currency** (latest):
  USD 46.3% (2026), EUR 31.7% (2026), JPY 4.6% (2026), GBP 4.3% (2026), CHF 1.2% (2026)

EUR is the shared euro-area currency — never attributed to DEU/FRA. INR is
measured directly only in FX turnover; it is absent from COFER and is NOT
zero-imputed. TFXRA_IMP imputed shares are exported but flagged as IMF
constructed estimates, not reported shares.

## 6. Financial-centre evidence

BIS LBS reporting-centre cross-border claims (banking-office LOCATION, not
ownership): GBR 14.3% (2026), FRA 13.5% (2026), JPN 10.5% (2026), DEU 9.9% (2026), USA 9.4% (2026), CHN 4.3% (2026), CHE 2.1% (2026), IND 0.2% (2026).
Kept strictly separate from reserve-currency measures.

## 7. Historical productivity (PWT 11.0, 1950–2023)

Latest output per worker (2021 PPP USD): IRL 261,683 (2023), NOR 183,754 (2023), CHE 152,789 (2023), USA 149,427 (2023), BEL 134,479 (2023), AUS 123,701 (2023), DNK 122,422 (2023), NLD 122,006 (2023), SWE 115,573 (2023), FRA 115,500 (2023), ITA 114,414 (2023), DEU 110,161 (2023), CAN 107,261 (2023), ESP 104,827 (2023), FIN 104,232 (2023), GBR 103,596 (2023), JPN 81,041 (2023), PRT 74,187 (2023), CHN 41,185 (2023), IND 19,206 (2023).
Latest TFP relative to USA=1: NOR 1.08 (2023), IRL 1.04 (2023), DEU 1.02 (2023), USA 1.00 (2023), NLD 0.99 (2023), CHE 0.99 (2023), DNK 0.93 (2023), BEL 0.92 (2023), FRA 0.89 (2023), SWE 0.88 (2023), AUS 0.85 (2023), ESP 0.85 (2023), GBR 0.83 (2023), CAN 0.81 (2023), FIN 0.77 (2023), ITA 0.76 (2023), PRT 0.71 (2023), JPN 0.64 (2023), CHN 0.47 (2023), IND 0.40 (2023).

## 8. Historical economic power comparisons (Maddison 2023)

Panel share = share of the imported 20-entity panel GDP (GDPpc × population),
NOT a world share:

| Year | Top panel entities |
|---|---|
| 1500 | CHN 65%, FRA 13%, DEU 11%, ESP 4%, GBR 3% |
| 1700 | CHN 39%, IND 35%, FRA 7%, JPN 5%, DEU 4% |
| 1820 | CHN 49%, GBR 10%, FRA 8%, ITA 7%, DEU 7% |
| 1900 | USA 25%, CHN 16%, GBR 13%, IND 11%, DEU 10% |
| 1950 | USA 40%, GBR 10%, CHN 8%, DEU 7%, IND 6% |
| 1980 | USA 33%, JPN 12%, CHN 9%, DEU 9%, FRA 6% |
| 2020 | CHN 33%, USA 24%, IND 12%, JPN 6%, DEU 5% |

Modern codes do not represent historical empires (see
`entity_definition_notes` in `/api/research/foundation/historical-power/overview`).

## 9. Corrected validation-question statuses (v1.2)

| Question | v1.1 status | v1.2 status | Correction |
|---|---|---|---|
| Q08 | exploratory_findings | insufficient_evidence | Machinery ≠ finding |
| Q11 | evidence_inconsistent_with_registered_claim | evaluated_with_no_clear_conclusion | Scoped to tested public-debt proposition |
| Q14 | evidence_inconsistent_with_registered_claim | evaluated_with_no_clear_conclusion | H01T-P1.0 level diagnostics |
| Q17 | evidence_inconsistent_with_registered_claim | exploratory_findings | Attribution defect corrected (H01B-P1.0) |

## 10. Remaining scientific limitations

- 88 banking-crisis onsets in one outcome family; no independent
  non-banking registries (V-Dem, UCDP, COW, sovereign/currency crises) imported.
- Only 3 independent post-1990 episodes — clustered inference, not precision.
- Retrospective JST R6 vintage; `strict_eligible_periods` remains 0.
- IMF WP-2026-094 and ALFRED remain access-blocked; no substitute outcomes.
- H01B results are exploratory: the holdout informed predictor selection.
