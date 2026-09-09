# Data Sources

World Bank, BIS, and OECD are connected end-to-end (adapter → ingestion → persistence → frontend); all three are in `testing` status. No source is `active` yet.

## World Bank

- Adapter: working
- Mappings: 15 (central config in `apps/api/app/data_sources/world_bank_mappings.py`, seeded as SourceSeries; 3 GDP + 5 trade/investment from Milestone 5.1 + 3 WGI governance scores from Milestone 5.2 + Gini and CPI from Milestone 5.3 + 2 SIPRI-derived military-expenditure series from Milestone 5.4)
- Persistence: working (`persist_observations` — identity resolution, duplicate skip, revision handling; DB-enforced identity uniqueness via `uq_observations_identity`)
- Revision handling: working (changed values create a new immutable vintage + IndicatorRevision; history preserved)
- IngestionRun: working (one run per indicator import, recorded with status/counts/errors; transient-retry wrapper batches network/5xx failures into the same run)
- Imported countries: all 8 tracked (USA, CHN, CHE, DEU, FRA, GBR, JPN, IND)
- Imported indicators: 15 — GDP_GROWTH, GDP_CURRENT_USD, GDP_PER_CAPITA (2015–2025, 264 obs) + EXPORTS_GDP, IMPORTS_GDP, TRADE_BALANCE, CURRENT_ACCOUNT_GDP, GROSS_CAPITAL_FORMATION_GDP (2000–2025, 1031 obs; 40/40 series success) + RULE_OF_LAW_WGI_SCORE, CONTROL_OF_CORRUPTION_WGI_SCORE, POLITICAL_STABILITY_WGI_SCORE (1996–2024, 624 obs; 24/24 series success) + GINI_INDEX (1990–2025 request range, 187 obs; 8/8 series success) + INFLATION_CPI (1990–2025, 287 obs; 8/8 series success) + MILITARY_EXPENDITURE_USD, MILITARY_EXPENDITURE_GDP (1990–2024, 560 obs; 16/16 series success, M5.4). Only legitimate gaps: 2025 values missing for USA/JPN exports/imports/external-balance/GCF and CHN GCF (not yet published); WGI 1997/1999/2001 absent (WGI's historical biennial years); Gini is published irregularly — missing years are gaps, never forward-filled or zero-filled; military series currently published through 2024. TRADE_BALANCE uses the World Bank's *published* external balance (NE.RSB.GNFS.ZS) — not derived from exports − imports.
- Gini coverage matrix (verified live 2026-09-08, request range 1990–2025): all 8 countries YES but irregular — USA 35 obs (1990–2024, latest 41.8), CHE 21 (1992–2022, 33.8), DEU 32 (1991–2022, 33.7), FRA 29 (1996–2023, 31.8), GBR 32 (1990–2021, 32.4), JPN 13 (2008–2020, 32.3), CHN 20 (1990–2022, 36.0), IND 5 (1993–2022, 25.5). Stale latest years are acceptable and displayed as "Latest available: {year}" in the UI — never labeled "current". Gini is the income-inequality proxy for the Wealth / opportunity / values gaps force, which is capped at PARTIAL (DEC-009). **Sprint 5.17 (DEC-024) welfare-concept clarification:** SI.POV.GINI (World Bank PIP) mixes income-based surveys (high-income economies: USA/CHE/DEU/FRA/GBR/JPN via LIS/EU-SILC, after-tax income) and consumption-based surveys (CHN/IND and most low-/middle-income countries). OWID: "consumption tends to be more evenly distributed than income" — consumption Gini is systematically LOWER than income Gini for the same true inequality (visible in tracked_8: IND consumption median 27.7 vs USA income median 40.8). **The WB API does NOT expose a per-observation welfare-concept tag** — no defensible automated adjustment is possible from the data alone. Verdict: DEFER_GINI_LEVEL — GINI_INDEX stays MONOTONIC_NEGATIVE (direction confirmed, DEC-018) with NO numeric curve; `100 - Gini` NOT approved; tracked_8 calibration permanently rejected (25.5–43.7 is a narrow subset of the world 20.2–71.1, 171 countries, 2430 country-year obs). **Sprint 5.17.1 economy-filter clarification:** the read-only profile's global universe filter now uses the AUTHORITATIVE WB country-metadata endpoint (`/v2/country`, `region.id != "NA"` => real economy) instead of a hand-written `aggregate_codes` blacklist that wrongly listed ZAF (South Africa) and PSE (West Bank and Gaza) as aggregates. 217 real economies identified; ZAF RETAINED (7 obs, 54.1–65), PSE RETAINED (9 obs, 33.7–36.4); corrected counts 2430 obs / 171 countries / 1963–2025 (same as Sprint 5.17 — the old blacklist was ineffective due to a 2-letter vs 3-letter code mismatch, so the bug was methodological, not numerical). If the metadata cannot be retrieved the GLOBAL profile STOPS — no fallback to the blacklist. DEC-024 verdict UNCHANGED. Welfare-concept wording: "provider-methodology / country-level welfare-concept classification" — the API does NOT expose a per-observation welfare-concept tag; no invented adjustments.
- CPI semantics: FP.CPI.TOTL.ZG is annual average consumer price inflation (annual %), WDI source 2, verified 2026-09-08. The catalog's INFLATION_CPI frequency was corrected from the aspirational 'monthly' placeholder to 'annual' to match (name "Inflation (CPI)" and unit "percent" were already clean; strength_direction stays contextual). CPI is a domestic price-pressure input for Cost competitiveness — not a relative-competitiveness measure by itself (needs exchange rates and partner-country price/cost comparisons). Latest values: CHE 0.15% (2025), USA 2.95% (2024), DEU 2.17%, GBR 3.88%, JPN 3.17%, IND 2.40%, CHN 0.06% (2025).
- Military expenditure (M5.4): MS.MIL.XPND.CD ("Military expenditure (current USD)") and MS.MIL.XPND.GD.ZS ("Military expenditure (% of GDP)") are WDI series (source 2) whose **underlying source is the SIPRI Military Expenditure Database** (sourceOrganization: "SIPRI Military Expenditure Database, Stockholm International Peace Research Institute (SIPRI), uri: https://www.sipri.org/databases"), verified against official WB API v2 metadata on 2026-09-08. No direct SIPRI adapter exists and the SIPRI Excel workbook is not downloaded or rehosted — the pipeline ingests only the WB-republished series (source_key `world_bank`). Licensing: the World Bank distributes its open data catalog under Creative Commons Attribution 4.0 International (CC-BY 4.0) by default (https://datacatalog.worldbank.org/public-licenses); the WB data pages identify these republished series as CC BY 4.0. Attribution is recorded here; this is documentation, not legal advice. SIPRI semantics: military expenditure is an **input measure** — resources absorbed by the military — not a measure of military capability or security; both catalog entries are strength_direction contextual and the Military strength force is capped at PARTIAL (DEC-009/DEC-011).
- Military coverage matrix (verified live 2026-09-08, request range 1990–2025, published through 2024): all 8 countries YES for both series, 35 obs each (1990–2024), complete histories. Latest (2024) USD: USA $997.31B, CHN $313.66B, IND $86.13B, DEU $88.46B, GBR $81.76B, FRA $64.68B, JPN $55.27B, CHE $6.72B. Latest (2024) % of GDP: USA 3.42%, GBR 2.28%, IND 2.27%, FRA 2.05%, DEU 1.89%, JPN 1.37%, CHN 1.71%, CHE 0.72%.
- Coverage matrix for the 3 WGI governance-score series (verified live 2026-09-08, 1996–2024): all 8 countries YES for all 3 series — 26 observations each (1996–2024 minus 1997/1999/2001). Latest (2024): RL — CHE 87.32, DEU 84.95, JPN 82.98, GBR 78.82, FRA 73.81, USA 73.52, IND 56.29, CHN 46.99; CC — CHE 88.48, DEU 83.75, GBR 78.41, JPN 75.32, FRA 72.51, USA 69.86, CHN 49.65, IND 41.88; PV — JPN 85.27, CHE 82.65, GBR 70.30, DEU 68.02, USA 64.27, CHN 63.28, FRA 61.77, IND 52.47.
- WGI methodology + uncertainty: the mapped series are the current WDI 2025-revision absolute governance scores (0–100, larger = better governance; score = linear transformation of the estimate using hypothetical worst/base-case countries; "Worldwide Governance Indicators, 2025 Revision"). Legacy RL.EST/CC.EST/PV.EST no longer exist in current WDI. Perception-based composites with measurement uncertainty: the dedicated WGI source (WB source id 3) publishes, per dimension, standard errors (GOV_WGI_RL.SE), 90% CI bounds for the governance score (GOV_WGI_RL.SC_LB/SC_UB), and number of underlying sources (GOV_WGI_RL.SR). **Verified live 2026-09-09 (Sprint 5.13 read-only probe, DEC-022; still NOT imported):** all four uncertainty series exist for all 8 tracked countries for every score year 1996–2024 (208 obs per series = 8 × 26; biennial gaps 1997/1999/2001 only; no 2025 values yet), with PERFECT one-to-one year alignment to the score series; LB/UB are 90% CI bounds on the SAME 0–100 governance-score scale as the imported score (LB ≤ score ≤ UB for all 624 tracked_8 points, symmetric, UB clamped at 100 — e.g. CHE CC 2020 UB = 100.0); SE is on the underlying ESTIMATE scale (~0.15–0.25) and empirically width ≈ 56.5 × SE (NOT 65.8 × SE, so SE does not reconstruct the published bounds); SR is integer-valued count data (observed range 4–16). Selected initial input set for future measurement-confidence work: LB + UB + SR (SE deferred — DEC-022). **Storage/persistence foundation implemented 2026-09-09 (Sprint 5.14):** the dedicated `indicator_diagnostics` table exists (Alembic `e3a7c94b1d51`, applied to the dev DB), with an immutable-vintage persistence path and an exact-period lookup helper, both tied to the expected provider-series identity (WB dedicated WGI source id 3). **LIVE INGESTION COMPLETE 2026-09-09 (Sprint 5.15):** the 9 diagnostic series (GOV_WGI_{RL,CC,PV}.SC_LB/.SC_UB/.SR) are IMPORTED into `indicator_diagnostics` via the dedicated source-3 fetch path (`app/data_sources/world_bank_wgi_diagnostics.py` — explicit `source=3` parameter + response `sourceid`/`indicator.id`/`countryiso3code` validated against the expected spec) and the separate batch CLI `scripts/ingest_wgi_diagnostics.py` (never through the canonical observation importer; each import recorded as an IngestionRun with data_kind="indicator_diagnostic"). Live results: 1872 rows = exactly the expected 8 countries × 3 indicators × 3 kinds × 26 score years (624 per kind, 624 per indicator, 234 per country; 1996–2024 with the biennial gaps 1997/1999/2001 only), all vintage 1, 0 duplicate identities; post-import read-only validation: LB ≤ score ≤ UB for all 624/624 latest-vintage score points, SR all integer-valued (observed range 4–16), perfect one-to-one score-year alignment; idempotent re-run verified (CHE RL all kinds: 0 inserted / 78 skipped / 0 revised); NO canonical pollution — Indicator count 25 / SourceSeries 19 / Observation 5647 unchanged, diagnostics create no SourceSeries/Observation rows. No confidence formula exists; the diagnostics are confidence INPUT DATA only. WGI values are source indicators, never Atlas force scores.
- Frontend exposure: working (`/country/{iso3}` shows latest values + GDP growth history for all 8 countries + Trade & Investment section (latest exports/imports/trade balance/current account/GCF, % of GDP) + Governance section (latest WGI Rule of Law / Control of Corruption / Political Stability, XX.XX / 100, with the perception/uncertainty caption) + Inequality section (latest Gini index with "Latest available: {year}" staleness label and the income-inequality-only caption; new in 5.3) + Military section (latest military expenditure in current US$ compact form and % of GDP, year, "Source: World Bank · Underlying source: SIPRI", input-proxy caption; new in 5.4); `/countries` and homepage cards show data coverage via enriched `GET /api/countries`)
- Status: testing
- Import CLI: `uv run --no-sync python scripts/ingest_world_bank.py --all-countries --all-mapped --start 2000 --end 2025` (from apps/api; `--country ISO3` / `--indicator CODE` for single runs). WGI: `uv run --no-sync python scripts/ingest_world_bank.py --all-countries --indicator RULE_OF_LAW_WGI_SCORE --start 1996 --end 2025` (repeat per WGI indicator). Gini/CPI: `uv run --no-sync python scripts/ingest_world_bank.py --all-countries --indicator GINI_INDEX --start 1990 --end 2025` (repeat with INFLATION_CPI). Military: `uv run --no-sync python scripts/ingest_world_bank.py --all-countries --indicator MILITARY_EXPENDITURE_USD --start 1990 --end 2025` (repeat with MILITARY_EXPENDITURE_GDP)
- WGI diagnostic import CLI (auxiliary path, separate from the canonical importer): `uv run --no-sync python scripts/ingest_wgi_diagnostics.py --all-countries --all-indicators --all-kinds --start 1996 --end 2025` (from apps/api; persists ONLY into indicator_diagnostics, never observations)
- Coverage/health check: `uv run --no-sync python scripts/coverage_report.py` (from apps/api)
- Last tested: 2026-09-09 (Sprint 5.15: WGI diagnostics LB/UB/SR × 8 countries × 3 indicators, 1996–2025 request range, 72/72 series success, 1872 diagnostics rows inserted; idempotent CHE RL re-run 0 inserted / 78 skipped / 0 revised; 0 duplicate identity groups. M5.4 before that: military USD + %GDP × 8 countries, 16/16 series success, 560 observations)
- Known quirks: transient WB HTTP failures observed (the batch CLI retries network/5xx up to 3 attempts; 4xx/parse/mapping errors fail immediately and are recorded as failed runs); machine's python.exe lacks OPENSSL_Applink → adapter loads CA bundle from memory (`cadata`); `uv sync` needs `--system-certs` in this sandbox; never run two batch imports concurrently (identity uniqueness now enforced at DB level).

| Canonical indicator | WB code | WB name | Unit |
|---|---|---|---|
| GDP_GROWTH | NY.GDP.MKTP.KD.ZG | GDP growth (annual %) | annual % |
| GDP_CURRENT_USD | NY.GDP.MKTP.CD | GDP (current US$) | current US$ |
| GDP_PER_CAPITA | NY.GDP.PCAP.CD | GDP per capita (current US$) | current US$ per person |
| EXPORTS_GDP | NE.EXP.GNFS.ZS | Exports of goods and services (% of GDP) | % of GDP |
| IMPORTS_GDP | NE.IMP.GNFS.ZS | Imports of goods and services (% of GDP) | % of GDP |
| TRADE_BALANCE | NE.RSB.GNFS.ZS | External balance on goods and services (% of GDP) | % of GDP |
| CURRENT_ACCOUNT_GDP | BN.CAB.XOKA.GD.ZS | Current account balance (% of GDP) | % of GDP |
| GROSS_CAPITAL_FORMATION_GDP | NE.GDI.TOTL.ZS | Gross capital formation (% of GDP) | % of GDP |
| RULE_OF_LAW_WGI_SCORE | GOV_WGI_RL_SC | Rule of Law - Governance score (0-100) | score 0-100 |
| CONTROL_OF_CORRUPTION_WGI_SCORE | GOV_WGI_CC_SC | Control of Corruption - Governance score (0-100) | score 0-100 |
| POLITICAL_STABILITY_WGI_SCORE | GOV_WGI_PV_SC | Political Stability - Governance score (0-100) | score 0-100 |
| GINI_INDEX | SI.POV.GINI | Gini index | index (0-100) |
| INFLATION_CPI | FP.CPI.TOTL.ZG | Inflation, consumer prices (annual %) | annual % |
| MILITARY_EXPENDITURE_USD | MS.MIL.XPND.CD | Military expenditure (current USD) | current US$ |
| MILITARY_EXPENDITURE_GDP | MS.MIL.XPND.GD.ZS | Military expenditure (% of GDP) | % of GDP |

All five trade/investment codes, all three WGI codes, the Gini/CPI codes, and
the two SIPRI-derived military codes were verified against official WB API v2
indicator metadata on 2026-09-08 (name, source = World Development
Indicators, concept match; military sourceOrganization = SIPRI Military
Expenditure Database). TRADE_BALANCE
maps the published external balance (goods + services), consistent in scope
with EXPORTS_GDP/IMPORTS_GDP — no derived observations. The WGI codes are the
current 2025-revision series (legacy RL.EST/CC.EST/PV.EST no longer exist in
WDI); higher = better governance, and raw stored values are never reversed —
CONTROL_OF_CORRUPTION measures control of corruption, so higher means less
corruption. GINI_INDEX stores the published 0–100 index raw (never rescaled
to 0–1, never forward-filled); higher Gini = more inequality
(strength_direction negative). INFLATION_CPI maps the annual CPI inflation
series (the catalog frequency placeholder 'monthly' was corrected to 'annual'
in M5.3 — documented, not silent). The military codes store published values
raw; both are strength_direction contextual — more spending does not
mechanically equal stronger military capability, and Military strength is
capped at PARTIAL (DEC-009 ceiling, see DEC-011).

Mappings are seeded idempotently into the `source_series` table.

## BIS (Bank for International Settlements)

- Adapter: working (`apps/api/app/data_sources/bis.py`, offline-tested; live smoke verified 2026-09-08)
- Official mechanism: BIS Stats API v1 (SDMX RESTful subset), documented at https://stats.bis.org/api-doc/v1/ and browseable via https://data.bis.org (bulk download: https://data.bis.org/bulkdownload). No undocumented/internal browser APIs used.
- API base: `https://stats.bis.org/api/v1`
- Authentication: none (public)
- Endpoint used: `GET /data/{dataflow}/{key}/all?format=csv[&startPeriod=YYYY-Q1&endPeriod=YYYY-Q4]` → SDMX-CSV text (`TIME_PERIOD` = "YYYY-QN", `OBS_VALUE`); without `format=csv` the default response is SDMX 2.1 XML
- Key format: country dimension uses **ISO2** codes (US, CH, CN, …) — ISO3 returns HTTP 404; `BIS_ISO2_BY_ISO3` in `bis_mappings.py` maps the 8 tracked countries
- Datasets identified: `WS_CREDIT_GAP` (credit-to-GDP gaps, quarterly), `WS_DSR` (debt service ratios, quarterly); both cover all 8 tracked countries (coverage matrix: all YES, verified live 2026-09-08)
- External identity: `"{dataflow_id}/{sdmx_key_template}"` (e.g. `WS_CREDIT_GAP/Q.{cc}.P.A.C`) — the dataflow alone is not a series identity (WS_CREDIT_GAP also carries the ratio CG_DTYPE=A and trend CG_DTYPE=B families); `{cc}` stays a placeholder because SourceSeries is shared across countries
- Mapped concepts: 2 (central config in `apps/api/app/data_sources/bis_mappings.py`; canonical codes CREDIT_TO_GDP_GAP / DEBT_SERVICE_RATIO owner-approved 2026-09-08, seeded in the 17-indicator catalog)
- Frequencies: quarterly for both datasets; quarterly identity is preserved via `observation_date` = quarter start (Q1→01-01, Q2→04-01, Q3→07-01, Q4→10-01); `period` stays the year — no DTO schema change needed (persistence maps observation_date → period_start)
- Parsing safeguards: every CSV row is validated against the mapping's expected dimensions (FREQ=Q, sector=P, TC_LENDERS=A, CG_DTYPE=C for the gap; FREQ=Q, sector=P for DSR) and the expected ISO2 country; violations raise `DataSourceParseError` instead of being silently relabelled. Null/empty `OBS_VALUE` rows are skipped, never zero-filled. UNIT_MEASURE codes (770/367) are not interpreted — not verified against the official BIS codelist.
- DSR methodological caution (BIS): debt-service payments as a proportion of income; DSR level comparisons across countries are less meaningful than changes relative to each country's own history — normalize within-country, not across countries.
- Persistence: working (`scripts/ingest_bis.py` → BISAdapter → run_ingestion → persist_observations; SourceSeries resolution via the `{cc}` external_code identity, country lives on Observation)
- Frontend exposure: working (`/country/{iso3}` Debt & credit section: latest gap + DSR, 8-quarter history tables, quarter labels; observations carry `source_key`)
- Status: testing
- Import CLI: `$env:PYTHONPATH='.'; uv run --no-sync python scripts/ingest_bis.py --all-countries --all-mapped --start 2000 --end 2025` (from apps/api; `--country ISO3` / `--indicator CODE` for single runs)
- Live smoke (read-only): `PYTHONPATH=. uv run --no-sync python scripts/bis_smoke.py CHE` (from apps/api)
- Last tested: 2026-09-08 (full import: 8 countries × 2 indicators, 2000 Q1→2025 Q4, 104 quarters each = 1664 observations inserted; idempotent re-run 0 inserted / 1664 skipped / 0 revised; 0 duplicate identity groups). Latest credit gap 2025 Q4: CHE −17.04, USA −11.54, CHN −7.69, DEU −3.96, FRA −15.11, GBR −17.82, JPN +6.78, IND +1.74.

| Canonical indicator | BIS dataflow | BIS series key | Unit (BIS terminology) |
|---|---|---|---|
| CREDIT_TO_GDP_GAP | WS_CREDIT_GAP | Q.{cc}.P.A.C | percentage of GDP |
| DEBT_SERVICE_RATIO | WS_DSR | Q.{cc}.P | per cent |

## IMF (International Monetary Fund) — Sprint 5.19 IMPLEMENTED

- Adapter: working (`apps/api/app/data_sources/imf_weo.py`, 21 offline mocked tests; live import verified 2026-09-10)
- Official mechanism: IMF SDMX 3.0 API (`https://api.imf.org/external/sdmx/3.0`) — **public, NO subscription key needed** (Sprint 5.18 incorrectly stated a key was required). DataMapper API exists but was NOT used (no historical/forecast flag).
- Dataflow: `IMF.RES/WEO` version `9.0.0`. URL format: `/data/dataflow/IMF.RES/WEO/+/{key}` (slash-separated, NOT comma).
- Historical/forecast filtering: `LATEST_ACTUAL_ANNUAL_DATA` attribute in each observation's raw payload. Filter rule: persist only `observation_status == "actual"` (year ≤ boundary). No forecast values persisted.
- Verified indicator: `GGXWDG_NGDP` — "General government gross debt", unit "Percent of GDP", source "World Economic Outlook (April 2026)", dataset WEO. Matches DEC-008 (general government, gross, % of GDP) — NOT WB central-government `GC.DOD.TOTL.GD.ZS`
- Canonical: `GOVERNMENT_DEBT_GDP`
- Tracked_8 coverage: ALL 8 (USA 2001–2025, CHN 1995–2024, CHE 1990–2025, DEU 1991–2025, FRA 1980–2024, GBR 1980–2025, JPN 1980–2024, IND 1991–2025)
- Imported data: 297 observations inserted (CHE 36, CHN 30, DEU 35, FRA 45, GBR 46, IND 35, JPN 45, USA 25). Max years matched provider-reported `LATEST_ACTUAL_ANNUAL_DATA`. No forecast years persisted.
- Idempotency: second full import = 0 inserted / 297 skipped / 0 revised. Idempotent for current vintage.
- Revision/vintage: covered by shared `persist_observations` infrastructure (`test_observation_revisions.py`). IMF adapter produces DTOs; persistence layer handles revisions, vintages, supersession links.
- Import CLI: `$env:PYTHONPATH='.'; uv run --no-sync python scripts/ingest_imf_weo.py --all-countries --all-mapped` (from apps/api; `--country ISO3` / `--indicator CODE` for single runs)
- Status: testing

## WID (World Inequality Database) — Sprint 5.20 IMPLEMENTED, Sprint 5.20.1 hardened

- Adapter: working (`apps/api/app/data_sources/wid.py`, offline tests with in-memory zip fixture)
- Official mechanism: four documented access paths (https://wid.world/codes-dictionary/):
  1. Website graphing tools (manual exploration)
  2. Specific-series download from the DATA section (https://wid.world/data/)
  3. **Bulk download** (full dataset from https://wid.world/bulk_download/wid_all_data.zip — 882 MB, 848 CSV files, no API key needed; verified live 2026-09-10)
  4. **R/Stata packages** using webservice at `https://rfap9nitz6.execute-api.eu-west-1.amazonaws.com/prod/` (requires `x-api-key` header, base64-encoded key bundled in R package `sysdata.rda`)
- Data format: CSV via bulk download (`country;variable;percentile;year;value;age;pop;data_quality`); JSON via webservice
- Country identity: 2-letter ISO codes (US, CN, CH, DE, FR, GB, JP, IN)
- Verified wealth indicator: `shweal` (share of `hweal` = net personal wealth); percentile `p90p100` = top 10% share, `p99p100` = top 1% share; values are fractions (0–1); annual
- **Sprint 5.19 canonical series correction**: `shwealj992` (age=992 adults, pop=`j` = equal-split adults) — NOT pop=`i` (individuals). Pop=`j` is the ONLY series available for all 8 tracked countries. Pop=`i` exists only for USA and GBR.
- **Sprint 5.19 coverage audit** (shwealj992, p90p100 + p99p100): all 8 countries have data 1980–2024. Modern-era coverage is good; pre-1900 gaps are expected for WID's long-run series.
- **Sprint 5.19 extrapolation counts** (data_quality=2): USA 0, CHN 0, CHE 0, DEU 24, FRA 80, GBR 93, JPN 0, IND 0. Three countries (DEU, FRA, GBR) have significant extrapolation. Interpolation counts (data_quality=1): DEU 1, IND 4; all others 0.
- **Sprint 5.20 data_quality policy (DEC-027)**: DEFER filtering — import ALL rows, preserve data_quality in raw_payload, do NOT delete provider data using an inferred code meaning. WID does NOT provide an official code dictionary. The Sprint 5.19 recommendation to exclude data_quality=2 is RETRACTED.
- **Sprint 5.20.1 raw provenance hardening**: `raw_payload` now carries both `data_quality_raw` (the raw provider CSV field, stripped of surrounding whitespace) and `data_quality` (the typed convenience value: int or None). The provider representation is preserved for traceability — unknown codes such as "A" stay "A" (not None-or-zero); empty string stays "". DEC-027 NO-filtering policy unchanged.
- **Sprint 6.6.2 raw-preservation guard fix**: the previous [0,1] range
  rejection (Sprint 5.20) is RETRACTED. [0,1] is the COMPLEMENT_0_100
  normalization domain, NOT a WID ingestion validity domain. A finite
  provider value outside [0,1] is preserved as the immutable raw
  Observation.value; whether Atlas can normalize it is a later-layer
  question (NormalizationDataError if scoring is attempted). The adapter
  still rejects: empty value, non-numeric text, NaN, +inf, -inf, wrong
  variable/percentile/age/pop/country identity.
- Ceiling: does NOT lift DEC-009 PARTIAL ceiling (wealth share addresses wealth inequality only, not opportunity or values/social gaps)
- Imported data: 670 observations across 8 countries (shwealj992, p90p100, pop=j). Idempotency verified (0 inserted / 117 skipped on USA re-import).
- Status: testing (Sprint 5.20 IMPLEMENTED)

## OECD (Organisation for Economic Co-operation and Development)

- Adapter: working (`apps/api/app/data_sources/oecd.py`, 14 offline mocked tests; live read-only smoke verified 2026-09-08)
- Official mechanism: OECD SDMX REST API (public), documented at https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html (SDMX v1-style exact-key data queries). Official Data Explorer / SDMX documentation only — the web UI was not scraped, no private/internal requests reverse-engineered.
- API base: `https://sdmx.oecd.org/public/rest`
- Authentication: none (public; documented rate limit ~60 queries/hour — any future batch import must throttle, not retry-storm)
- Endpoint used: `GET /data/{agency_id},{dataflow_id},{version}/{key}?format=csvfilewithlabels[&startPeriod=...&endPeriod=...]` → SDMX-CSV (`TIME_PERIOD` = "YYYY" (annual) or "YYYY-QN" (quarterly), `OBS_VALUE`, plus `OBS_STATUS`/`UNIT_MULT`/`DECIMALS` flags preserved in raw_payload)
- Key format: REF_AREA (country) is the FIRST key dimension and uses **ISO3** codes identical to Big Cycle Atlas codes for all 8 tracked countries — no alias translation needed (`OECD_REF_AREA_BY_ISO3` documents the verified 1:1 identity; unlike BIS, which requires ISO2)
- Verified API findings (2026-09-08): the v2 API's `c[...]` filter parameters are silently broken server-side (observed returning wrong-country rows) — only v1-style exact dot-keys work, and every returned row is still dimension-validated because a correct request is not proof of a correct response; the `DF_PDB_LV` dataflow is broken server-side ("Object reference not set to an instance of an object") — `DF_PDB` is used instead
- Datasets identified: `OECD.SDD.TPS/DSD_PDB@DF_PDB` v2.0 (annual Productivity Database) and `OECD.SDD.TPS/DSD_PDB@DF_PDB_ULC_Q` v1.0 (quarterly unit labour costs)
- External identity: `"{dataflow_id}/{sdmx_key_template}"` with `{cc}` as the REF_AREA placeholder (e.g. `DSD_PDB@DF_PDB/{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP`) — country-independent so a single SourceSeries row could later be shared across countries. **Sprint 5.20.1**: the education attainment identity uses the exact serialized form `agency,dataflow,version/key` (e.g. `OECD.EDU.IMEP,DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA,1.0/{cc}...`) — the previous `EAG_LSO_NEAC/...` abbreviation (forced by varchar(100)) is retired; the column is now varchar(255) (Alembic `a8f3c2d1e5b7`)
- Mapped concepts: 2 — owner-approved 2026-09-08 and seeded (central config in `apps/api/app/data_sources/oecd_mappings.py`; canonical indicators in the 19-indicator catalog; 2 SourceSeries rows with `{cc}` placeholder identities)
- Frequencies: annual (2024 → observation_date 2024-01-01) and quarterly (BIS convention: Q1→01-01, Q2→04-01, Q3→07-01, Q4→10-01); `period` stays the year
- Coverage matrix for the two selected series (verified live 2026-09-08 via exact-key queries): USA YES (prod 1987–2025; ULC 1956-Q1–2025-Q3), CHE YES (1991–2025; 1996-Q1–2025-Q4), DEU YES (1991–2025; 1992-Q1–2026-Q1), FRA YES (1970–2025; 1950-Q1–2026-Q1), GBR YES (1980–2024; 1993-Q2–2025-Q4), JPN YES (1970–2024; 1981-Q1–2026-Q1), CHN NO, IND NO — CHN and IND have no observations in these selected OECD dataflows
- No-data handling: a no-observation key answers HTTP 404 with body `NoRecordsFound` (verified live) → `DataSourceNoDataError` → `run_ingestion` records the run as a zero-data SUCCESS with `run_metadata.no_data=true` — a known no-coverage country is never a failed run or an ingestion outage
- Rate limit: OECD documents ~60 queries/hour. The batch CLI is strictly sequential with a 1-second delay between live requests; HTTP 4xx (including 429) is never retried. Observed live: two 429 bursts mid-batch; the remainder was completed with single-series re-imports after the window cooled.
- Cautions: the ULC index family (ULCE/IX, base 2015) is deliberately NOT mapped — absolute index levels must never be compared directly between countries as economic levels; growth (GY, per cent per annum) was chosen because it is meaningful through time and for later normalisation. Productivity levels are USD-PPP and cross-country comparable. PRICE_BASE=LR: the code and the selected constant-price series are verified live, but the exact official LR label still requires OECD metadata confirmation — no reference-year wording is claimed.
- Parsing safeguards: every CSV row is validated against REF_AREA + all mapped dimensions (FREQ, MEASURE, ACTIVITY, UNIT_MEASURE, PRICE_BASE, TRANSFORMATION, ASSET_CODE / ADJUSTMENT, CONVERSION_TYPE); violations raise `DataSourceParseError`. Null/empty `OBS_VALUE` rows are skipped, never zero-filled. No invented release dates (release_date stays None).
- Persistence: working (`scripts/ingest_oecd.py` → OECDAdapter → run_ingestion → persist_observations; SourceSeries resolution via the `{cc}` external_code identity, country lives on Observation; transient retry max 3 attempts, network/5xx only, short backoff)
- Imported countries: 6 covered (USA, CHE, DEU, FRA, GBR, JPN — both indicators); CHN and IND imported as legitimate no-data (clean no-data runs, no rows)
- Imported data (1990–2025 request range, actual DB coverage): productivity 212 annual observations (CHE 35: 1991–2025, DEU 35: 1991–2025, FRA 36: 1990–2025, GBR 35: 1990–2024, JPN 35: 1990–2024, USA 36: 1990–2025) + ULC 818 quarterly observations (CHE 120: 1996-Q1–2025-Q4, DEU 136: 1992-Q1–2025-Q4, FRA 144: 1990-Q1–2025-Q4, GBR 131: 1993-Q2–2025-Q4, JPN 144: 1990-Q1–2025-Q4, USA 143: 1990-Q1–2025-Q3) = 1030 OECD observations, all vintage 1; idempotent re-import verified (0 inserted / 155 skipped CHE, 0 inserted / 179 skipped USA, batch-wide 0 inserted / 531 skipped for ULC; 0 revised); 0 duplicate identity groups
- Frontend exposure: working (`/country/{iso3}` Productivity & Competitiveness section: latest labour productivity (USD PPP/hour) + ULC growth (% p.a.) with quarter labels, 8-row annual productivity history, 8-quarter ULC history, per-observation source labels; CHN/IND show a safe "No OECD productivity data available" empty state, never zeros)
- Status: testing
- Import CLI: `$env:PYTHONPATH='.'; uv run --no-sync python scripts/ingest_oecd.py --all-countries --all-mapped --start 1990 --end 2025` (from apps/api; `--country ISO3` / `--indicator CODE` for single runs)
- Live smoke (read-only): `$env:PYTHONPATH='.'; uv run --no-sync python scripts/oecd_smoke.py CHE` (from apps/api) — CHE productivity 2019–2025: 7 observations, latest 2025 = 90.5178 USD/hour (PPP)
- Last tested: 2026-09-08 (full 8-country batch: 12 data-bearing series imported, 4 no-data skips (CHN/IND × 2), 5 HTTP-429 failures retried successfully as single-series imports after cooldown; OECD IngestionRuns: 28 success / 5 failed — the failures are all HTTP 429 rate-limit responses)

| Canonical indicator | OECD dataflow | OECD key template | Unit | Frequency |
|---|---|---|---|---|
| LABOUR_PRODUCTIVITY_PER_HOUR | DSD_PDB@DF_PDB v2.0 | {cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP | US dollars per hour, PPP converted | annual |
| UNIT_LABOUR_COST_GROWTH | DSD_PDB@DF_PDB_ULC_Q v1.0 | {cc}.Q.ULCE._T.PA.V.GY.S.NC | percent per annum | quarterly |

Planned sources and their adapter files:

| Source | Adapter file | Indicators planned | Status |
|---|---|---|---|
| World Bank | apps/api/app/data_sources/world_bank.py | GDP growth, education, debt indicators | testing |
| BIS | apps/api/app/data_sources/bis.py | Credit gaps, debt service ratios | testing (end-to-end) |
| OECD | apps/api/app/data_sources/oecd.py | Productivity, unit labour costs (PISA later) | testing (end-to-end) |
| FRED / ALFRED | apps/api/app/data_sources/fred.py | US macro series (ALFRED for vintage data) | planned |
| Eurostat | apps/api/app/data_sources/eurostat.py | EU indicators | planned |
| ECB | apps/api/app/data_sources/ecb.py | Euro area indicators | planned |
| SNB | apps/api/app/data_sources/snb.py | Swiss indicators | planned |
| UN Comtrade | apps/api/app/data_sources/comtrade.py | Trade flows | planned |

Template for each connected source (fill in when it goes to `testing`/`active`):

```
## Source name
- API base:
- Authentication:
- Endpoints used:
- Indicators retrieved:
- Countries available:
- Update frequency:
- Rate limit:
- Transformation notes:
- Last tested:
- Status: planned | testing | active | broken
```