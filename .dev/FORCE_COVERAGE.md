# Big Cycle Forces — Data Coverage (2026-09-08, Milestone 5.4)

Data-gap report for the 17 Big Cycle forces. Coverage is **not** strength — no
force scores, weights, or phases exist yet (Milestone 5+). Definitions live in
`apps/api/app/cycle/force_definitions.py` (typed config layer, matching
docs/data-model.md and packages/shared `FORCES`); per-country coverage is
computed by `apps/api/app/services/force_coverage_service.py` and exposed at
`GET /api/countries/{iso3}/force-coverage`.

## Status meanings

| Status | Rule (deterministic) |
|---|---|
| available | All mapped live inputs have observations for the country (latest vintage) — unless the force declares a conceptual coverage_ceiling (see below) |
| partial | ≥1 live input has observations, ≥1 does not (e.g. CHN productivity: GDP growth yes, OECD productivity no) — OR every live input has data but the force is capped at PARTIAL by its ceiling |
| defined_not_sourced | No live input has data for the country, but live/candidate catalog indicators exist |
| missing | No defined usable input exists yet |

Candidate inputs never raise a status: promoting a candidate to live is a
deliberate owner config change. Catalog rows without SourceSeries are never
"live".

## Conceptual coverage ceiling (Milestone 5.3, DEC-009)

Some Big Cycle forces are broader than any single proxy. A ForceDefinition may
declare `coverage_ceiling = partial`: even when every currently mapped live
input has complete data, the force reports **PARTIAL**, never AVAILABLE,
because the mapping is an explicitly incomplete proxy for the conceptual force.

- **Wealth / opportunity / values gaps** — capped at PARTIAL (live input: GINI_INDEX). Gini measures income inequality only; wealth inequality, opportunity gaps, and values/social gaps remain missing.
- **Internal conflict** — capped at PARTIAL (live input: POLITICAL_STABILITY_WGI_SCORE). The WGI series is an institutional/conflict-risk proxy; it does not measure every form of domestic conflict. Status change from AVAILABLE → PARTIAL in M5.3 is a **methodology correction, not a regression**.
- **Military strength** — capped at PARTIAL (M5.4; live inputs: MILITARY_EXPENDITURE_USD + MILITARY_EXPENDITURE_GDP, WB series republishing the SIPRI Military Expenditure Database). SIPRI describes military expenditure as an INPUT measure — resources absorbed by the military — not a measure of capability or security. Personnel capability, equipment quality/quantity, technology, logistics, readiness, combat experience, alliances/force projection, and nuclear capability are not measured, so spending alone can never make this force AVAILABLE.

Default is `coverage_ceiling = None` (unchanged behavior); rule_of_law,
corruption, productivity, cost competitiveness, indebtedness, trade, and
infrastructure are deliberately NOT capped.

## Deliberately unassigned catalog indicators

- GDP_CURRENT_USD, GDP_PER_CAPITA — economic scale / normalization context, not direct force inputs (may later feed relative power)
- POPULATION — normalization denominator
- UNEMPLOYMENT_RATE — relates to opportunity gaps only via a proxy judgment; left unassigned rather than guessed

## Per-force gap report

| # | Force | Live indicators | Catalog-only candidates | Missing concepts | Recommended source(s) | Priority |
|---|---|---|---|---|---|---|
| 1 | Leadership capabilities | — | — | capabilities/quality of leadership (qualitative) | expert assessment (owner-curated, later milestone) | LOW |
| 2 | Education | — | TERTIARY_ENROLLMENT, SECONDARY_ENROLLMENT | attainment, test scores, years of schooling | 5.1 audit resolved 2026-09-08 (DEC-007, Option C): keep the age-specific/attainment concepts — do NOT redefine to WB gross enrollment ratios; pursue OECD attainment (tertiary) / WB net enrollment SE.SEC.NENR (secondary) in a future sprint | MEDIUM (awaiting better indicators) |
| 3 | Character / determination | — | — | resourcefulness/determination (qualitative) | expert assessment | LOW |
| 4 | Rule of law | RULE_OF_LAW_WGI_SCORE (WB WGI 2025 revision, 1996–2024, all 8 countries) | — | — | Done for M5.2. Perception-based composite; source indicator, not a force score | DONE (LOW) |
| 5 | Corruption | CONTROL_OF_CORRUPTION_WGI_SCORE (WB WGI 2025 revision, 1996–2024, all 8 countries) | — | — | Done for M5.2. Source is Control of Corruption: HIGHER = stronger control / less corruption; raw value never reversed. Perception-based composite | DONE (LOW) |
| 6 | Resource allocation efficiency | — | — | capital/labor misallocation measures | needs concept definition first (credit-gap variants are mapped to Indebtedness) | LOW |
| 7 | Global openness | — | — | openness to trade/capital/people/ideas | WB trade data (exports/imports/trade balance/current account) is now live and available as a future openness input candidate — deliberately NOT promoted: trade alone does not cover capital, people, and ideas; a narrower trade-based proxy methodology needs owner approval first | MEDIUM |
| 8 | Productivity / output growth | GDP_GROWTH (WB), LABOUR_PRODUCTIVITY_PER_HOUR (OECD) | RND_EXPENDITURE_GDP | multi-factor productivity | World Bank/OECD R&D later; current live set is solid | DONE (LOW) |
| 9 | Cost competitiveness | UNIT_LABOUR_COST_GROWTH (OECD), INFLATION_CPI (WB, 1990–2024/2025) | — | relative price levels; exchange rates and partner-country price/cost comparisons | Done for M5.3: OECD-6 AVAILABLE (ULC + CPI), CHN/IND PARTIAL (CPI only — OECD ULC unavailable). CPI is a domestic price-pressure input, not a relative-competitiveness measure by itself | DONE (LOW) |
| 10 | Trade and capital flows | EXPORTS_GDP, IMPORTS_GDP, TRADE_BALANCE, CURRENT_ACCOUNT_GDP (all WB, 2000–2025) | — | bilateral flows, capital flow measures beyond the current account | UN Comtrade / capital-flow data later | DONE (LOW) |
| 11 | Infrastructure and investment | GROSS_CAPITAL_FORMATION_GDP (WB, 2000–2025) | — | infrastructure quality (GCF measures investment effort, not quality) | quality indices later | DONE (MEDIUM) |
| 12 | Indebtedness | CREDIT_TO_GDP_GAP (BIS), DEBT_SERVICE_RATIO (BIS) | GOVERNMENT_DEBT_GDP | household/corporate debt split; public-sector debt input | 5.1 audit resolved 2026-09-08 (DEC-008): owner keeps the general-government concept — do NOT use WB GC.DOD.TOTL.GD.ZS (central government only); a genuine general-government source (e.g. IMF WEO) is evaluated in a future sprint | MEDIUM |
| 13 | Military strength | MILITARY_EXPENDITURE_USD, MILITARY_EXPENDITURE_GDP (WB republishing SIPRI, 1990–2024, all 8 countries) — capped at PARTIAL (DEC-009, M5.4) | — | personnel capability, equipment quality/quantity, technology, logistics, readiness, combat experience, alliances/force projection, nuclear capability | Done for M5.4 as a spending-input proxy (no direct SIPRI adapter — WDI republish is the pipeline); future strengthening would need capability data, not more spending series | DONE for M5.4 — stays PARTIAL (LOW) |
| 14 | Wealth / opportunity / values gaps | GINI_INDEX (WB, irregular, country-varying latest year 2020–2024) — capped at PARTIAL (DEC-009) | — | wealth inequality, equality of opportunity, values/social gaps (Gini covers income inequality only) | Done for M5.3 as income-inequality proxy; future strengthening: wealth/income shares (WID), unemployment/opportunity measures, social polarization indicators | DONE for M5.3 — stays PARTIAL (LOW) |
| 15 | Internal conflict | POLITICAL_STABILITY_WGI_SCORE (WB WGI 2025 revision, 1996–2024, all 8 countries) — capped at PARTIAL (DEC-009, M5.3) | — | polarization, protests, distributional tension (not covered by the WGI proxy) | Initial proxy: WGI Political Stability and Absence of Violence/Terrorism — an institutional/conflict-risk measure, NOT every form of domestic conflict; later ACLED / event data may strengthen this force | DONE — stays PARTIAL (LOW) |
| 16 | Geography | — | — | natural endowments, location (mostly static) | static reference data, not time-series ingestion | LOW |
| 17 | Acts of nature | — | — | disaster/pandemic/climate exposure | EM-DAT, climate indices | LOW |

## Current per-country coverage (live data, 2026-09-08, after Milestone 5.4)

| Country | Available | Partial | Defined not sourced | Missing |
|---|---|---|---|---|
| USA, CHE, DEU, FRA, GBR, JPN | Productivity / output growth, Cost competitiveness (ULC + CPI), Rule of law, Corruption, Trade and capital flows, Infrastructure and investment, Indebtedness (7) | Wealth / opportunity / values gaps (Gini, ceiling), Internal conflict (ceiling), Military strength (spending proxy, ceiling) (3) | Education (1) | 6 |
| CHN, IND | Rule of law, Corruption, Trade and capital flows, Infrastructure and investment, Indebtedness (5) | Productivity / output growth (GDP growth only), Cost competitiveness (CPI only, no OECD ULC), Wealth / opportunity / values gaps (Gini, ceiling), Internal conflict (ceiling), Military strength (spending proxy, ceiling) (5) | Education (1) | 6 |

(OECD covers 6 of 8 tracked countries; CHN/IND are legitimate OECD no-data —
this is why their Cost competitiveness is partial from CPI alone. WGI, WB
Gini/CPI, and the SIPRI-derived WB military series cover all 8 countries.
Wealth gaps, Internal conflict, and Military strength are PARTIAL by the
DEC-009 ceiling even where all their live inputs have data. Counts derive
from live DB state; nothing is hardcoded.)

## WGI methodology + uncertainty (Milestone 5.2, 2026-09-08)

The three governance forces use the **current WDI 2025-revision WGI series**
(DEC-006): `GOV_WGI_RL_SC` / `GOV_WGI_CC_SC` / `GOV_WGI_PV_SC` — absolute
governance scores 0–100, larger = better governance. The legacy `RL.EST` /
`CC.EST` / `PV.EST` codes no longer exist in current WDI and are NOT used.
Verified against official WB API metadata (2026-09-08): the score is a linear
transformation of the estimate using hypothetical worst-case and base-case
countries ("Worldwide Governance Indicators, 2025 Revision").

These are **source indicators, not Atlas force scores** — no force scoring,
weights, or phases exist. WGI is perception-based and carries measurement
uncertainty: the dedicated WGI source (WB source id 3) publishes, per
dimension, standard errors (`GOV_WGI_RL.SE`), 90% confidence-interval bounds
for the governance score (`GOV_WGI_RL.SC_LB` / `GOV_WGI_RL.SC_UB`), and number
of underlying sources (`GOV_WGI_RL.SR`). These uncertainty series are NOT
imported yet — they are the intended input for future force-confidence work.
Never treat WGI as perfectly measured.

## Semantic audits (Milestone 5.1, 2026-09-08 — outcomes resolved 2026-09-08)

**Education — RESOLVED: Option C (DEC-007).** The WB gross enrollment ratios
(SE.TER.ENRR / SE.SEC.ENRR) do not match the canonical age-specific concepts;
the owner chose better-matching indicators over redefining the catalog. No
education persistence; the catalog keeps TERTIARY_ENROLLMENT /
SECONDARY_ENROLLMENT as candidates until OECD attainment / WB net-enrollment
mappings are approved in a future sprint.

**Government debt — RESOLVED: keep general-government (DEC-008).** WB
GC.DOD.TOTL.GD.ZS is central-government debt, narrower than the canonical
general-government concept; the owner declined the rename and the proxy. A
genuine general-government source (e.g. IMF WEO) is evaluated in a future
sprint; GOVERNMENT_DEBT_GDP stays a catalog-only candidate.

**Global openness — deliberately not promoted (unchanged).** Trade data
(exports, imports, trade balance, current account) is live but kept as
candidate context only: trade alone does not cover openness to capital,
people, and ideas. No openness ratio is derived and no status change occurs
without owner approval of a narrower proxy methodology.

## Sprint 5.18 audit — high-value gap source contracts (DEC-025, 2026-09-10)

Read-only, official-source-only research on three high-value data-gap
tracks. No ingestion, persistence, normalization, or scoring changes.
Distinct readiness verdicts per track. **Sprint 5.19 corrections in
bold below — see DEC-025 "Sprint 5.19 verification corrections" for the
full record.**

### Track A — IMF WEO general-government gross debt: IMPLEMENTED (Sprint 5.19)

- Indicator `GGXWDG_NGDP` verified: "General government gross debt", %
  of GDP, WEO. Matches DEC-008 (general government, gross) — NOT WB
  central-government `GC.DOD.TOTL.GD.ZS`.
- Two API paths: DataMapper (public, no auth, flat JSON, no vintage flag)
  and SDMX 3.0 (**public, NO key needed** — Sprint 5.18 incorrectly
  stated a key was required; `LATEST_ACTUAL_ANNUAL_DATA` attribute marks
  historical vs forecast).
- Tracked_8: ALL 8 covered (USA 2001–2025, CHN 1995–2024, CHE 1990–2025,
  DEU 1991–2025, FRA 1980–2024, GBR 1980–2025, JPN 1980–2024, IND
  1991–2025). **297 observations imported via SDMX 3.0, historical-only.**
- Vintage risk: DataMapper mixes historical + forecast with no flag;
  **SDMX 3.0 with `LATEST_ACTUAL_ANNUAL_DATA` filtering implemented — no
  forecast values persisted.**
- **Idempotent re-import verified: 0 inserted / 297 skipped / 0 revised.**
- Verdict: **IMPLEMENTED in Sprint 5.19.** GOVERNMENT_DEBT_GDP now has
  live data.

### Track B — Education Option C: PARTIAL (Sprint 5.19 corrections)

- **WB SE.SEC.NENR** (secondary net enrollment): STALE — USA/CHE/DEU/GBR
  last data 2017, JPN last 2016, CHN has NO data at all. WB metadata
  states "Reference period: 1970–2019". NOT recommended as a live input.
- **OECD tertiary attainment** — Sprint 5.19 verified the correct
  dataflow: `DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA` (NOT `_MIGR`),
  agency `OECD.EDU.IMEP`, v1.0. Series: SEX=`_T`, AGE=`Y25T64` (NOT
  `Y25T34`), ATTAINMENT_LEV=`ISCED11A_5T8`, UNIT=`PT_POP_SEX_AGE`
  (percentages, NOT fractions), FREQ=`A` (annual, NOT triennial A3).
  **Coverage: 8/8** (NOT 5/8) — but CHN (2 data points) and IND (6 data
  points) are extremely sparse. USA/CHE/DEU/FRA/GBR/JPN have good annual
  coverage (1981–2025 / 1989–2025 / 1989–2025 / 1981–2024 / 1997–2025 /
  1997–2025).
- Verdict: `EDUCATION_IMPLEMENTABLE_PARTIAL` — implementable for 6/8
  countries with good coverage. CHN and IND too sparse for reliable
  time-series use. Education force stays defined_not_sourced / partial.

### Track C — WID wealth: VERIFIED (Sprint 5.19 corrections)

- Access: bulk download (no key, 882 MB) or R-package webservice (API key
  required). No scraping needed.
- Indicator: `shweal` (share of net personal wealth), `p90p100` = top 10%
  wealth share. Annual, fractions (0–1), 2-letter ISO country codes.
  **Canonical series: `shwealj992` (pop=`j` = equal-split adults, NOT
  pop=`i` = individuals). Pop=`j` is the only series for all 8 countries.**
- Tracked_8: all 8 have data 1980–2024. **Extrapolation counts
  (data_quality=2): DEU 24, FRA 80, GBR 93; all others 0. Recommend
  excluding data_quality=2 during ingestion.**
- Ceiling: does NOT lift DEC-009 PARTIAL — wealth share addresses wealth
  inequality only, not opportunity or values/social gaps.
- Verdict: `WID_IMPLEMENTABLE` — exclude extrapolations (data_quality=2),
  force stays PARTIAL. READY for Sprint 5.21.

## Top next data priorities (ranked by force gaps filled, post-5.19)

1. **OECD tertiary attainment (PARTIAL, Sprint 5.20)** — would add the
   first live input to Education (currently defined_not_sourced). 6/8
   good coverage, 2/8 sparse. Annual (not triennial as previously
   stated). WB SE.SEC.NENR deferred (stale).
2. **WID wealth shares (IMPLEMENTABLE, Sprint 5.21)** — would add a
   wealth-distribution input to Wealth / opportunity / values gaps
   (currently Gini income-inequality only). Force stays PARTIAL.
   Exclude data_quality=2 (extrapolations).
3. **Force Layer + Methodology (Sprint 5.22)** — normalization design,
   weight design, force aggregation. Requires methodology work before
   force scores can be created.
4. **ACLED / event data (LOW-MEDIUM)** — would move Internal conflict
   beyond its PARTIAL ceiling.
5. **Military capability data (LOW)** — would move Military strength
   beyond its PARTIAL ceiling; no more spending series will lift the
   ceiling.

FRED/ALFRED (US-only, 1 of 8 countries) and other new providers are deferred:
they fill fewer force gaps per unit of work than extending WB.

## Future persistence decision

No Force / ForceIndicatorMapping DB tables yet — intentional (validate the
conceptual mapping first). When the mapping stabilizes: a `forces` table plus
a config-driven `force_indicator_mappings` table (docs/data-model.md) replaces
the Python config; the coverage service and API schema stay unchanged.

## Normalization Readiness (Milestone 5.4 audit — consumed by Sprint 5.5)

Inventory of every live indicator (19 SourceSeries, latest-vintage data in the
DB) with the properties the normalization/scoring phase will need. This is an
audit of what exists, not a design: no transformation, weight, or score formula
is decided here. **The design now exists: `.dev/NORMALIZATION.md` (Sprint 5.5,
2026-09-09) classifies every series below into per-dimension normalization
families; the typed registry lives in
`apps/api/app/cycle/normalization_definitions.py`.**

| Indicator | Direction | Frequency | Source | Cross-country comparable? | Time-series comparable? | Transformation likely needed later | Freshness caveat | Ceiling impact |
|---|---|---|---|---|---|---|---|---|
| GDP_GROWTH | positive | annual | WB | yes (common %-growth concept) | yes | smoothing/windowing for cycle work | annual, latest year lags | none (Productivity, uncapped) |
| GDP_CURRENT_USD | positive | annual | WB | contextual (nominal USD; PPP/deflation for welfare comparisons) | yes, but nominal (inflation confound) | scale/denominator or PPP adjustment | annual | none (deliberately unassigned) |
| GDP_PER_CAPITA | positive | annual | WB | contextual (nominal; PPP better) | yes, but nominal | likely log/PPP before any use | annual | none (deliberately unassigned) |
| EXPORTS_GDP | positive | annual | WB | yes (ratio) | yes | minimal — already % of GDP | annual; USA/JPN 2025 values missing (legitimate gaps) | none (Trade, uncapped) |
| IMPORTS_GDP | negative | annual | WB | yes (ratio) | yes | minimal | annual; USA/JPN 2025 missing | none |
| TRADE_BALANCE | positive | annual | WB | yes (ratio) | yes | contextual — sign/magnitude banding decision | annual; USA/JPN 2025 missing | none |
| CURRENT_ACCOUNT_GDP | positive | annual | WB | yes (ratio) | yes | contextual banding | annual; USA/JPN 2025 missing | none |
| GROSS_CAPITAL_FORMATION_GDP | positive | annual | WB | yes (ratio) | yes | measures investment effort, not quality | annual; CHN 2025 missing | none (Infrastructure, uncapped) |
| GINI_INDEX | negative | irregular | WB | yes (common 0–100 scale; survey-base differences remain) | yes within country, but irregular years | alignment policy for scoring windows — never forward-fill in the raw layer; interpolation would be a scoring-phase decision | latest year varies 2020–2024 by country — stale for some | wealth_opportunity_values_gaps capped PARTIAL |
| INFLATION_CPI | contextual | annual | WB | yes (annual % change) | yes | contextual — likely distance-from-band/target, not raw level | USA through 2024, others 2025 | none (Cost competitiveness, uncapped; CHN/IND partial by input mix, not ceiling) |
| MILITARY_EXPENDITURE_USD | contextual | annual | WB (SIPRI) | yes in current USD, but PPP adjustment matters for real resources | yes, but nominal (inflation confound) | PPP/deflation or share-of-world normalization; spending ≠ capability | annual, through 2024 | military_strength capped PARTIAL |
| MILITARY_EXPENDITURE_GDP | contextual | annual | WB (SIPRI) | yes (ratio) | yes | contextual burden banding; interaction with absolute spending is a scoring-phase decision | annual, through 2024 | military_strength capped PARTIAL |
| RULE_OF_LAW_WGI_SCORE | positive | annual | WB WGI | yes (2025-revision fixed 0–100 benchmark) | yes | minimal — already 0–100; perception uncertainty noted | 1996–2024; biennial gaps 1997/1999/2001 | none (Rule of law, uncapped) |
| CONTROL_OF_CORRUPTION_WGI_SCORE | positive | annual | WB WGI | yes | yes | minimal; never reverse the raw value | 1996–2024; biennial gaps | none |
| POLITICAL_STABILITY_WGI_SCORE | positive | annual | WB WGI | yes | yes | minimal | 1996–2024; biennial gaps | internal_conflict capped PARTIAL |
| CREDIT_TO_GDP_GAP | contextual | quarterly | BIS | yes (common methodology) | yes | contextual — sign/threshold banding | quarterly, 2000 Q1–2025 Q4 | none (Indebtedness, uncapped) |
| DEBT_SERVICE_RATIO | contextual | quarterly | BIS | contextual (income definitions differ; within-country history is the strong use) | yes | contextual banding | quarterly, 2000 Q1–2025 Q4 | none |
| LABOUR_PRODUCTIVITY_PER_HOUR | positive | annual | OECD | yes (USD PPP/hour built for comparison) | yes | levels vs growth decision (levels favor advanced economies; growth rates may be fairer) | annual; earliest year varies per country; CHN/IND not covered | none (Productivity uncapped; CHN/IND partial by input mix) |
| UNIT_LABOUR_COST_GROWTH | contextual | quarterly | OECD | yes (growth rates) | yes | relative-to-partners comparison later | quarterly; CHN/IND not covered | none (Cost competitiveness uncapped) |

Key findings for Sprint 5.5 (issues to design around — deliberately unresolved):

1. **Frequency mixing** — annual (WB/OECD annual), quarterly (BIS, OECD ULC),
   and irregular (Gini) series must be aligned to a common scoring period; the
   raw layer stays untouched.
2. **Nominal-USD confound** — GDP_CURRENT_USD, GDP_PER_CAPITA,
   MILITARY_EXPENDITURE_USD are nominal; PPP/deflation choices belong to the
   scoring design, not ingestion.
3. **Irregular Gini** — scoring windows must handle missing years without
   forward-filling; interpolation (if any) is a scoring-phase decision.
4. **Contextual directions dominate** — only some indicators have a naive
   positive/negative direction; several (CPI, credit gap, DSR, ULC growth,
   military spending, trade balance) need band/curve decisions in scoring.
5. **Perception-based inputs** — WGI scores carry measurement uncertainty
   (documented CI/SE series exist but are not imported).
6. **Ceiling-capped forces** — wealth gaps, internal conflict, and military
   strength can never reach AVAILABLE with current inputs regardless of how
   complete the data is (DEC-009); scoring must treat them as proxy-based.
7. **Legitimate coverage gaps** — USA/JPN 2025 trade-side values, CHN 2025 GCF,
   USA 2024 CPI, biennial WGI years, OECD absence for CHN/IND: these are real
   provider gaps, never zero-filled.