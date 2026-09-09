# Decisions

## DEC-001 — npm workspaces as the package manager

Date: 2026-09-07
Status: Accepted

### Decision

Use npm workspaces (root package.json with `workspaces: ["apps/*", "packages/*"]`) rather than pnpm.

### Reason

npm 11 is already installed on the dev machine; pnpm is not. npm workspaces handle the monorepo layout without a global tool install.

### Impact

All frontend npm commands should be run via npm workspaces (e.g. `npm run build -w apps/web` from the repo root). CI (later) uses npm.

## DEC-002 — SQLAlchemy 2.0 async with psycopg driver

Date: 2026-09-07
Status: Accepted

### Decision

Backend ORM is SQLAlchemy 2.0 in async mode with the `psycopg` (v3) driver for PostgreSQL.

### Reason

Single mature ORM with typed models; psycopg v3 is the modern Postgres driver with async support.

### Impact

Requires Python 3.10+. Connection string in .env: `DATABASE_URL=postgresql+psycopg://...`.

## DEC-003 — Unit tests run against SQLite via dependency override

Date: 2026-09-07
Status: Accepted

### Decision

pytest runs the API against an in-memory SQLite database by overriding the get_session dependency. Real deployments use PostgreSQL.

### Reason

Allows the test suite to run without Docker/Postgres (Docker unavailable on the current dev machine). Service-layer code is driver-agnostic SQLAlchemy.

### Impact

Postgres-specific features (TimescaleDB, JSONB operators) must not be used in code paths covered only by SQLite tests. Once Docker is available, add an integration test profile against real Postgres.

## DEC-004 — packages/shared holds the canonical country list

Date: 2026-09-07
Status: Accepted

### Decision

The 8 initial countries (USA, CHN, CHE, DEU, FRA, GBR, JPN, IND) are defined once in packages/shared and consumed by both the backend seed script and the frontend.

### Reason

Single source of truth prevents drift between backend seed data and frontend display lists.

### Impact

Adding a country means editing packages/shared first, then re-seeding.

## DEC-005 — Frontend fetches countries client-side via NEXT_PUBLIC_API_URL

Date: 2026-09-07
Status: Accepted

### Decision

The /countries page fetches from the FastAPI backend in a client component using the NEXT_PUBLIC_API_URL environment variable. No Next.js rewrites/proxy yet.

### Reason

Simplest correct wiring for Milestone 1; avoids server-side fetch complexity before there is real data.

### Impact

API must be running for /countries to show data; the page shows an explicit error state when the API is unreachable. Server-side fetching can replace this later.

## DEC-006 — WGI governance indicators use the 2025-revision 0–100 score series

Date: 2026-09-08
Status: Accepted

### Decision

The three governance source indicators (Rule of Law, Control of Corruption, Political Stability) use the current WDI 2025-revision absolute governance score series — `GOV_WGI_RL_SC`, `GOV_WGI_CC_SC`, `GOV_WGI_PV_SC` (0–100, larger = better governance) — not the legacy `RL.EST`/`CC.EST`/`PV.EST` estimate series (approx. −2.5 to +2.5), which no longer exist in current WDI.

### Reason

Verified against official WB API metadata (2026-09-08): the score series are the revised 2025 methodology — intuitive 0–100 scale on a fixed benchmark framework, meaningful both across countries and through time. WGI metadata itself confirms the score is a linear transformation of the estimate using hypothetical worst/base-case countries.

### Impact

Mappings live in `world_bank_mappings.py`; canonical codes `RULE_OF_LAW_WGI_SCORE` / `CONTROL_OF_CORRUPTION_WGI_SCORE` / `POLITICAL_STABILITY_WGI_SCORE`, category Governance, strength positive. These are SOURCE indicators — never displayed or stored as Atlas force scores (no scoring exists). WGI uncertainty (90% CI bounds, standard errors, number of sources) exists as separate WGI series and is documented for later force-confidence work; not imported yet.

## DEC-007 — Education: Option C (better indicators), no redefinition

Date: 2026-09-08
Status: Accepted (owner decision)

### Decision

Keep the canonical education concepts (age-specific/attainment-style enrollment); do NOT redefine them to match WB gross enrollment ratios (SE.TER.ENRR / SE.SEC.ENRR, which can exceed 100%). Pursue better-matching indicators instead (e.g. OECD educational attainment for tertiary, WB net enrollment SE.SEC.NENR for secondary if an enrollment-rate concept is preferred).

### Reason

The M5.1 semantic audit showed the WB gross-ratio wording contradicts the canonical age-specific wording; silently redefining the concept to fit an available series would corrupt the catalog's semantics.

### Impact

No education persistence yet. Education remains defined_not_sourced until owner-approved OECD attainment (or equivalent) mappings are added in a future sprint.

## DEC-008 — Government debt: keep the general-government concept

Date: 2026-09-08
Status: Accepted (owner decision)

### Decision

Keep the intended general-government gross debt concept (IMF WEO basis) for GOVERNMENT_DEBT_GDP. Do NOT rename the canonical to central-government debt and do NOT silently accept WB GC.DOD.TOTL.GD.ZS (central government only) as a proxy. Seek a genuine general-government source.

### Reason

The M5.1 audit showed GC.DOD.TOTL.GD.ZS measures central (budgetary) government debt — narrower than the canonical concept. Narrowing the concept to fit an available series would misstate public indebtedness.

### Impact

No government-debt persistence yet. Candidate sources for general-government debt (e.g. IMF WEO; no free official API in the current connector set) are evaluated in a future sprint; GOVERNMENT_DEBT_GDP stays a catalog-only candidate for Indebtedness.

## DEC-009 — Conceptual coverage ceiling for proxy-only forces

Date: 2026-09-08
Status: Accepted (owner decision, Milestone 5.3)

### Decision

ForceDefinition may declare `coverage_ceiling = partial`: a force whose mapped live inputs are an explicitly incomplete proxy for the conceptual force reports PARTIAL even when all those inputs have complete data. Default is `None` (unchanged behavior for every other force). Applied to exactly two forces:

- **Wealth / opportunity / values gaps** — live input GINI_INDEX (WB Gini, income inequality only); wealth inequality, opportunity gaps, and values/social gaps remain missing.
- **Internal conflict** — live input POLITICAL_STABILITY_WGI_SCORE (WGI institutional/conflict-risk proxy); it does not measure every form of domestic conflict.

### Reason

Coverage statuses describe data availability, but some forces are conceptually broader than any single proxy. Importing Gini must not make the whole force AVAILABLE — that would overclaim what is measured. Internal conflict's reclassification from AVAILABLE to PARTIAL (M5.3) is a methodology correction, not a regression.

### Impact

`_force_status` in `force_coverage_service.py` caps "available" at the ceiling; the API schema is unchanged (statuses only). Rule of law, corruption, productivity, and indebtedness are deliberately NOT capped. The ceiling is lifted only when mapping coverage improves (e.g. WID wealth shares, ACLED event data) — a deliberate future owner decision.

## DEC-010 — INFLATION_CPI frequency corrected from 'monthly' placeholder to 'annual'

Date: 2026-09-08
Status: Accepted (Milestone 5.3)

### Decision

The canonical INFLATION_CPI catalog entry keeps its name ("Inflation (CPI)"), unit (percent), and strength_direction (contextual); its frequency metadata is corrected from the aspirational 'monthly' placeholder to 'annual' to match the verified WB series FP.CPI.TOTL.ZG ("Inflation, consumer prices (annual %)", WDI).

### Reason

The M1-era catalog entry predated any sourced data. The verified WB series is annual; the concept (consumer price inflation) matches cleanly. The correction is documented here, in DATA_SOURCES.md, and in the M5.3 report — not silent.

### Impact

The `/api/indicators?frequency=monthly` filter now returns only UNEMPLOYMENT_RATE. If a monthly CPI series is ever wanted, it requires a separate source series under the same canonical indicator — a future decision.
## DEC-011 — Military strength: spending proxy via WB-republished SIPRI series, capped at PARTIAL

Date: 2026-09-08
Status: Accepted (Milestone 5.4)

### Decision

The initial Military strength proxy uses the two WDI military-expenditure series — MS.MIL.XPND.CD (MILITARY_EXPENDITURE_USD) and MS.MIL.XPND.GD.ZS (MILITARY_EXPENDITURE_GDP) — whose underlying source is the SIPRI Military Expenditure Database. No direct SIPRI adapter is built and the SIPRI Excel workbook is never downloaded or rehosted; the existing World Bank pipeline (source_key `world_bank`) is used, with SIPRI attribution recorded in DATA_SOURCES.md. Both catalog indicators are strength_direction **contextual** (more spending does not mechanically equal more capability), and the Military strength force declares `coverage_ceiling = partial` (the DEC-009 mechanism): with data for a country it moves MISSING → PARTIAL and can never report AVAILABLE from spending alone.

### Reason

SIPRI explicitly describes military expenditure as an INPUT measure — resources absorbed by the military — not a measure of military capability or security. The force still lacks personnel capability, equipment quality/quantity, technology, logistics, readiness, combat experience, alliances/force projection, and nuclear capability. Making the force AVAILABLE from spending would overclaim what is measured.

### Impact

All 8 countries now have Military strength = PARTIAL (35 observations each per series, 1990–2024, vintage 1). Normalization (Sprint 5.5) must treat Military strength as proxy-based; no spending-vs-capability formula is designed here. Licensing note: WB open data defaults to CC-BY 4.0 (https://datacatalog.worldbank.org/public-licenses); recorded as documentation, not legal advice.

## DEC-012 — Normalization architecture: four separable score dimensions, quarterly clock, explicit families, no zero-fill, versioned calibration, not backtest-safe

Date: 2026-09-09
Status: Accepted (Milestone 5.5 design sprint)

### Decision

The 17-force scoring layer is designed around these permanent rules (full spec: `.dev/NORMALIZATION.md`; typed skeleton: `apps/api/app/cycle/normalization_definitions.py`):

1. **Four separable dimensions** — every derived signal keeps `level_score` (0–100, domestic condition), `relative_score` (0–100 or null, vs. the comparison universe), `momentum` (−100…+100, from change through time only, never inferred from level), and `confidence` (0–1, trust in the signal — never economic strength) as independent values. Combination happens only later, in an explicit versioned force aggregation.
2. **Quarterly scoring clock** — derived snapshots are YYYY-Q1…Q4; annual/irregular indicators align via as-of rules; raw observation dates are never altered.
3. **No zero-fill** — MISSING ≠ ZERO in data, types, and policy; stale or insufficiently covered forces are *unscored*, never scored 0.
4. **Explicit normalization families** — no universal z-score; every live indicator is classified into a per-dimension family (DIRECT_0_100, MONOTONIC_POSITIVE/NEGATIVE/SATURATING, TARGET_BAND, OWN_HISTORY, CROSS_SECTIONAL_RELATIVE, RELATIVE_SHARE) or is explicitly CONTEXTUAL_DEFERRED. WGI keeps its provider 0–100 absolute scale (never percentile-ranked); DSR uses OWN_HISTORY per the BIS caution (never cross-sectionally ranked); military spending and the trade-balance side stay contextual/deferred rather than given invented curves.
5. **Versioned calibration and reference universe** — model version bundles method, parameters, reference universe (initially `tracked_8`; n=8 is never treated as global truth), calibration window, momentum windows, freshness policy, and force-mapping version. Calibration never sees future data.
6. **Not backtest-safe** — without reliable release dates, historical normalization is CURRENT/RESEARCH scoring only; every signal carries `backtest_safe = False` until Milestone 9 (release-date discipline).

### Reason

Collapsing level, relative position, momentum, and confidence into one number would make Big Cycle phase calculation unverifiable and hide data-quality differences behind false precision. The current 8-country universe and unpopulated release dates are real constraints the architecture must encode rather than paper over.

### Impact

Sprint 5.5 publishes NO scores, weights, momentum values, or confidence numbers — `level_score`/`relative_score`/`momentum`/`confidence` remain Optional/None. Unresolved curve thresholds and parameters (freshness decay shapes, TARGET_BAND bands, confidence composition, force weights) are deliberately left open in NORMALIZATION.md Section 17 for the scoring sprint. The registry validates at import time and fails loudly if a live force input lacks a normalization spec.

## DEC-013 — Freshness decay shape: exponential, confirmed by owner

Date: 2026-09-09
Status: Accepted (owner confirmation after Sprint 5.6)

### Decision

The freshness decay shape between the full-confidence age and the unusable age is **exponential**: `factor = 0.5 ** ((age − full_confidence_periods) / (half_life_periods − full_confidence_periods))`. The Sprint 5.6 initial default (exponential, honoring the half-life definition for arbitrary thresholds) is confirmed as the settled model choice; `FreshnessDecayShape.linear` remains in the code as a parameterized alternative for tests and future model versions.

### Reason

Of the two implemented shapes, only the exponential honors the half-life definition ("the age at which the factor is ~0.5") for arbitrary threshold sets; the owner confirmed it after Sprint 5.6 shipped it as the executable default. Changing the shape or the Section 5 threshold values remains a model-version change (NORMALIZATION.md Section 17.1), never a silent edit.

### Impact

NORMALIZATION.md Section 17.1 is closed as a shape *decision* (parameter-value tuning may still evolve with a version bump). Freshness factors already emitted by Sprint 5.6 signals are unchanged. No code change required — this records an owner decision on an implemented default.

## DEC-014 — Sprint 5.7 direction: WGI momentum (OWN_HISTORY) next; relative scores and TARGET_BAND parameter design deferred

Date: 2026-09-09
Status: Accepted (owner choice of Sprint 5.7 direction)

### Decision

Sprint 5.7 extends the executable normalization path with **momentum for the WGI ×3** (RULE_OF_LAW_WGI_SCORE, CONTROL_OF_CORRUPTION_WGI_SCORE, POLITICAL_STABILITY_WGI_SCORE; OWN_HISTORY family, registry windows (3, 5) years), reusing the Sprint 5.6 alignment + freshness + dispatch machinery. CROSS_SECTIONAL_RELATIVE (tracked_8 robust statistics) and the TARGET_BAND/MONOTONIC parameter-design sprint remain the documented follow-ups, not this sprint. The momentum definition and sign conventions are specified in the Sprint 5.7 brief (NORMALIZATION.md Section 9 + Section 17.5, resolved for the WGI ×3 only).

### Reason

Momentum is the lowest-risk next dimension: same data, same as-of alignment, no reference-universe design, no curve thresholds. The WGI ×3 sign conventions are unambiguous (higher = better for all three), unlike contextual indicators (credit gap, Gini) whose conventions stay open until their momentum is implemented.

### Impact

Sprint 5.7 will be the second executable score dimension. Momentum for the other 15 indicators, relative scores, confidence, and force aggregation all remain unimplemented after 5.7.

## DEC-015 — Period-complete alignment eligibility (Part 0, before any momentum)

Date: 2026-09-09
Status: Accepted (owner-directed hardening, implemented 2026-09-09)

### Decision

As-of alignment eligibility changes from `period_start <= as_of_date` to **`effective_period_end <= scoring_period_end`**, where the effective end is computed deterministically in the DERIVED layer only: annual and irregular (year-dated) YYYY → YYYY-12-31; quarterly YYYY-Qn → the quarter's last day (Q1 → 03-31, Q2 → 06-30, Q3 → 09-30, Q4 → 12-31). An annual 2020 observation is therefore NOT eligible at the 2020-Q1/Q2/Q3 snapshots even though its period_start precedes them, and first becomes eligible at 2020-Q4. `effective_period_end` travels as `AlignedValue` provenance.

### Reason

The Sprint 5.6 rule admitted period-INCOMPLETE observations: an annual 2020 observation at the 2020-Q2 snapshot (as-of 2020-06-30) represents a period that has not yet ended — period-completeness leakage. Momentum (Sprint 5.7) computes change between two aligned values, so it must not be built on an alignment layer with a known leakage. The fix is derived-layer only: raw observations are never modified and no synthetic period-end dates are persisted.

### Impact

Implemented in `app/services/alignment_service.py` (index-based eligibility expression, identical on SQLite and PostgreSQL) + `effective_period_end` in `AlignedValue`. Alignment semantics changed → model version bumped `normalization-v0.1` → `normalization-v0.2` (method `part0-period-complete-alignment-r1`). Live-DB verification: CHE RULE_OF_LAW_WGI_SCORE at 2024-Q2 now aligns to 2023 (was the incomplete-year 2024 value); first 2024-eligible at 2024-Q4; BIS CREDIT_TO_GDP_GAP aligns to exactly its own completed quarter. This fixes period-completeness leakage ONLY — it provides NO historical release-date safety; every signal keeps `backtest_safe = False` until Milestone 9. Tests: 225 passing (5 new regressions; the former leak expectation inverted). The momentum definition decision, when implemented, becomes DEC-016.

## DEC-016 — WGI momentum: signed raw provider-point change, OWN_HISTORY

Date: 2026-09-09
Status: Accepted (Sprint 5.7, DEC-014 direction)

### Decision

For the WGI ×3 (RULE_OF_LAW_WGI_SCORE, CONTROL_OF_CORRUPTION_WGI_SCORE, POLITICAL_STABILITY_WGI_SCORE), momentum is the **signed change in the provider's own 0–100 points** between the current aligned raw value and the anchor aligned raw value: `momentum_w = current_aligned_raw − anchor_aligned_raw`, for the registry windows **3y (diagnostic) and 5y (primary)**. The headline `NormalizedSignal.momentum` is the **5-year change ONLY** — no averaging of windows, no silent fallback to 3y when 5y is unavailable. The anchor is `align_observation_as_of` at the same quarter w years earlier (`shift_scoring_period_years`), so it inherits country isolation, latest-vintage selection, **DEC-015 period-complete eligibility**, and no-future-leakage; the actual aligned anchor (which may be an earlier year than requested) is carried in per-window provenance (`MomentumWindowResult`: requested_anchor_period, anchor_source_period, change). **Anchor tolerance = 1 annual period** (versioned MODEL PARAMETER in ModelVersionConfig): the aligned anchor may be at most one source year older than the requested anchor year — this accepts the known WGI biennial gaps (1997/1999/2001 → prior-year anchors) and rejects older anchors with `change = None`, never zero, never a stretched window. Sign: higher WGI = stronger governance → rising = positive momentum, no inversion. Momentum is computed from ALIGNED RAW values, never from level_score. The historical anchor is intentionally NOT freshness-decayed and momentum is never multiplied by the freshness factor (freshness gates the CURRENT observation only).

### Reason

Momentum must be change through time only (DEC-012), and the provider's 0–100 scale makes the signed difference fully explainable ("WGI improved by 4.2 provider points over 5 years") with the −100…+100 momentum range holding by construction — no invented scale constants, no z-scores. Anchoring through the existing alignment service means one proven, period-complete, country-scoped query path instead of parallel momentum-specific observation logic.

### Impact

Implemented in `app/cycle/normalizer.py` + `MomentumWindowResult`/`NormalizedSignal.momentum_windows`/`momentum_window_years` in `normalization_definitions.py`; momentum execution is gated on level_family DIRECT_0_100 AND momentum_family OWN_HISTORY (resolves to exactly the WGI ×3 — other indicators' registry OWN_HISTORY entries do NOT make their momentum approved). Model version **normalization-v0.3** (method `sprint-5.7-wgi-momentum-r1`) versioning the windows, primary=5y, tolerance=1, WGI-positive sign convention, and the existing exponential freshness policy. **WGI momentum is currently WGI-scale-specific: it is NOT calibrated for direct aggregation with momentum from DSR, credit gap, productivity, Gini, GDP growth, ULC, or CPI** — no averaging of raw momentum across unlike scales in any future force layer until a separate momentum-calibration methodology is approved. Anchors use DEC-015 period-complete alignment (unmodified). `backtest_safe` remains False; nothing persisted, no public API, no force scores/weights/phases. Sign conventions for all other indicators remain unresolved (NORMALIZATION.md §17 item 5 stays open beyond the WGI ×3).

## DEC-017 — WGI relative scores within tracked_8: mid-rank plotting position, complete-universe rule

Date: 2026-09-09
Status: Accepted (Sprint 5.8)

### Decision

For the WGI ×3 (RULE_OF_LAW_WGI_SCORE, CONTROL_OF_CORRUPTION_WGI_SCORE, POLITICAL_STABILITY_WGI_SCORE), `relative_score` is the country's **relative position within the fixed, versioned tracked_8 comparison universe at the SAME scoring snapshot** — USA, CHN, CHE, DEU, FRA, GBR, JPN, IND, exactly 8 members, frozen as a `ReferenceUniverseSpec` (membership is NEVER derived from the DB — not the Country table, not who currently has data; a changed universe gets a new id + new model version, never an in-place edit). It is **NOT a global/world percentile, NOT a level, NOT a phase**; `level_score` keeps its own meaning untouched.

**Formula (versioned model choice)**: mid-rank plotting position — `relative_score = 100 * (average_rank − 0.5) / n`, rank 1 = weakest, rank n = strongest, **ties use the AVERAGE rank** (deterministic and order-independent; never broken by ISO code, row id, or query order). Higher WGI = stronger (no inversion). For n=8 the possible scores are 6.25–93.75 in steps of 12.5 — the top member of only 8 countries is not mislabeled 100 and the bottom is not mislabeled 0.

**Complete-universe rule**: tracked_8 requires ALL 8 members usable. 7/8 → `relative_score`/`relative_rank` = None for EVERYONE (never a seven-country score still called tracked_8), with `reference_universe_id` / `reference_universe_expected_n` / `reference_universe_usable_n` carried as provenance; missing members never become zero. Every member is aligned with `align_observation_as_of` at the same (indicator, scoring period, model version, freshness policy) — country scoping (ISSUE-004), latest vintage, DEC-015 period-complete eligibility, and no-future-leakage inherited; never "latest overall". Freshness gates member USABILITY only (stale-but-usable members participate; unusable members do not) and **never scales relative_score**; confidence stays None. Every participating value is validated 0..100 — out-of-range raises `NormalizationDataError` (never clamps, never treats as missing, never ranks).

**Execution gate**: relative scoring runs only when relative_family = CROSS_SECTIONAL_RELATIVE AND the executable level family is DIRECT_0_100 → exactly the WGI ×3. GDP_GROWTH, GROSS_CAPITAL_FORMATION_GDP, GINI_INDEX, and LABOUR_PRODUCTIVITY_PER_HOUR also say CROSS_SECTIONAL_RELATIVE in the registry, but their level semantics are not approved — they keep raising NormalizationNotImplementedError (no generic fallback). Relative remains independent from momentum: either dimension may exist when the other is None.

### Reason

Big Cycle power requires both domestic condition and relative standing, but n=8 is a weak statistical reference distribution: a mid-rank plotting position is rank-based (resistant to outlier magnitudes), deterministic, avoids min-max distortion, and honestly bounds the top/bottom members short of 100/0. The complete-universe rule keeps the comparison universe identical across periods — otherwise the universe silently changes whenever one country's data is late, breaking comparability. This resolves NORMALIZATION.md §16 (robust statistics) for the WGI ×3 only.

### Impact

Implemented in `app/cycle/relative.py` (mid-rank engine + `build_relative_cross_section`) + `normalizer.py` integration + `ReferenceUniverseSpec` / signal provenance fields in `normalization_definitions.py`. Model version **normalization-v0.4** (method `sprint-5.8-wgi-tracked8-relative-r1`) versioning universe id + frozen membership, the complete-universe requirement, the mid-rank formula, tie method, WGI direction, the v0.3 momentum config, and the exponential freshness policy. The formula does NOT auto-approve other indicators' relative scoring; `backtest_safe` stays False; nothing persisted, no public API, no confidence, no force scores/weights/phases. Tests: 278 offline (35 new). Live read-only smoke: CHE RULE_OF_LAW @2025-Q2 → relative 93.75 (rank 8/8, universe 8/8); CHN → 6.25 (rank 1/8); USA CONTROL_OF_CORRUPTION → 31.25 (rank 3/8).

## DEC-018 — Non-WGI level methodology audit: four reclassifications to CONTEXTUAL_DEFERRED, Gini direction without curve, DSR selected as next implementation target

Date: 2026-09-09
Status: Accepted (Sprint 5.9)

### Decision

Sprint 5.9 critically audited the eight proposed non-WGI level methodologies (NORMALIZATION.md "Non-WGI Level Parameter Decision Audit — Sprint 5.9") before any numeric thresholds were implemented. NO numeric curve thresholds were approved. Outcomes:

- **RECLASSIFIED to CONTEXTUAL_DEFERRED (level)**: GDP_GROWTH (was TARGET_BAND — potential growth differs by development stage; a universal band would punish catch-up growth and/or reward stagnation), GROSS_CAPITAL_FORMATION_GDP (was MONOTONIC_SATURATING — very high GCF can be credit-driven overinvestment; no defensible universal healthy level), INFLATION_CPI (was TARGET_BAND — inflation objectives differ across countries/regimes; a universal raw-CPI band would encode "2% ideal for every country"), UNIT_LABOUR_COST_GROWTH (was TARGET_BAND — raw domestic ULC growth is not by itself a relative-competitiveness measure; no FX/partner-ULC context imported). These were Sprint 5.5 PROPOSED entries, not accepted decisions — reclassifying an unresolved proposal to DEFERRED is an explicit methodology outcome, not a regression. All four keep raising NormalizationNotImplementedError.
- **GINI_INDEX**: MONOTONIC_NEGATIVE direction CONFIRMED (higher Gini = more income inequality), but NO numeric level curve approved — "100 − Gini" is NOT an approved mapping; the calibration universe (global empirical history vs tracked_8) and survey-base comparability remain open.
- **CREDIT_TO_GDP_GAP**: asymmetric TARGET_BAND family CONFIRMED (large positive gap = vulnerability, near trend = lower stress, very negative = deleveraging/weak credit — lower is NOT always better; separate positive/negative slopes expected). Thresholds remain UNRESOLVED — the research question (what values the BIS early-warning literature justifies, and how the calibration must be as-of-safe) is recorded in NORMALIZATION.md; no values invented.
- **DEBT_SERVICE_RATIO**: OWN_HISTORY family CONFIRMED and DSR is SELECTED AS THE NEXT IMPLEMENTATION TARGET — READY_FOR_IMPLEMENTATION_DESIGN. The candidate design (the country's DSR position versus its OWN prior historical distribution; higher historical stress position → weaker level_score) is self-contained: no external calibration data needed, 104 quarters per country exist. Open design questions to resolve in the implementation sprint: minimum historical sample, trailing vs expanding as-of calibration window (no future leakage), empirical percentile vs robust z/MAD transform, stress-percentile → Atlas 0–100 strength mapping, insufficient early history → None never zero.
- **LABOUR_PRODUCTIVITY_PER_HOUR**: MONOTONIC_POSITIVE direction approved, but the ABSOLUTE 0–100 level curve is DEFERRED — tracked_8 min-max is explicitly rejected; an expanded calibration universe decision (e.g. OECD-wide distribution) is required first. Level and growth stay separable dimensions.

### Reason

The Sprint 5.5 families were proposals; the audit tested each against economic defensibility rather than assuming it. Universal bands fail where the "healthy" value is development-stage-, model-, or regime-dependent (empirically: tracked_8 GDP-growth medians 2015–2025 span 0.8–7.2; GCF medians span 18.5–42.4; CPI medians span 0.29–6.35). Deferring is a valid outcome: inventing thresholds to show progress would bake arbitrary norms into a versioned model. DSR's own-history family is the safest next executable path because it needs no external calibration universe — the same reason BIS discourages cross-country raw DSR comparison.

### Impact

Implemented in `app/cycle/normalization_definitions.py` registry (level families + notes for GDP_GROWTH, GCF, INFLATION_CPI, UNIT_LABOUR_COST_GROWTH, GINI_INDEX, CREDIT_TO_GDP_GAP, DEBT_SERVICE_RATIO, LABOUR_PRODUCTIVITY_PER_HOUR) + the Sprint 5.9 audit section in NORMALIZATION.md. No numeric thresholds approved; no new scores published; every non-WGI indicator still raises NormalizationNotImplementedError; `backtest_safe` stays False; no force aggregation, no weights, no persistence, no public API, no frontend change. NO model-version bump: WGI ×3 outputs (level + momentum + relative) are unchanged, and non-WGI indicators were unimplemented before and after. Read-only research support: `apps/api/scripts/normalization_profile.py` (descriptive statistics only — no scores, no writes, not proof that an empirical percentile is economic truth). Recommended Sprint 5.10: DSR OWN_HISTORY level design + implementation.

## DEC-019 — DSR OWN_HISTORY level: expanding own-history calibration, empirical mid-rank stress percentile, minimum 20 observations

Date: 2026-09-09
Status: Accepted (Sprint 5.10)

### Decision

For EXACTLY DEBT_SERVICE_RATIO, the level signal answers: **"where is the country's current DSR relative to ITS OWN historical DSR distribution available as of this scoring snapshot?"** — NOT a cross-country comparison (cross-country raw-DSR ranking remains PROHIBITED per the BIS caution), NOT a tracked_8 percentile, NOT a global/world percentile, NOT a probability, NOT a force score, NOT a phase.

- **Calibration window — LOCKED**: the country's **EXPANDING OWN HISTORY** of DSR observations from the first eligible observation through the current aligned observation, **inclusive of the current observation**. Never post-snapshot/future data (as-of discipline: DEC-015 period-complete eligibility, latest-vintage selection, country isolation — ISSUE-004 — all inherited through the alignment layer). Never a trailing window; never external data; never post-T information.
- **Sample composition — LOCKED**: REAL observations only — one latest-vintage value per actual source period. No forward-fill, no interpolation, no duplicate-across-quarters, no synthesized values, no zero-fill (MISSING ≠ ZERO — a gap stays a gap and shrinks nothing).
- **Minimum history — LOCKED MODEL PARAMETER**: `minimum_sample_n = 20` observations (quarterly ≈ 5 years). This is an ATLAS versioned MODEL PARAMETER, NOT BIS methodology truth. Below 20: `level_score = None` (never 0, never a stretched sample); the signal is still returned with the raw value, source period, freshness provenance, and the own-history counts as provenance. No observation at all / unusably stale → no signal.
- **Formula — LOCKED**: empirical mid-rank plotting position. Sort the own-history sample ascending; rank 1 = lowest DSR = least stress; ties share the AVERAGE rank (deterministic, order-independent — never broken by period, row id, or insertion order). `stress_percentile = 100 * (average_rank − 0.5) / n`; **`level_score = 100 − stress_percentile`** (higher DSR = greater debt-service burden = weaker). No z-score, no MAD, no min-max, no winsorization, no external thresholds.
- **Endpoints**: finite-sample endpoints are NOT forced to 100/0 — n=20 lowest → 97.5, highest → 2.5; no clamping anywhere.
- **Freshness**: the existing quarterly freshness policy gates the CURRENT observation only (unusable → no signal; stale-but-usable → scored, flagged). Freshness NEVER scales the score (`level_score *= freshness_factor` is prohibited) and historical calibration points are NEVER freshness-decayed.
- **Provenance**: typed `OwnHistoryLevelResult` (sample_n, minimum_sample_n, earliest/latest_source_period, rank, stress_percentile, level_score) carried on `NormalizedSignal.own_history_level`. `relative_score = None` (prohibited); DSR momentum NOT implemented (registry 4q/8q windows stay unapproved); confidence None; `backtest_safe = False`.
- **Execution gate**: OWN_HISTORY level requires BOTH the registry level family AND an explicit `own_history_level_configs` entry in the model version — a registry OWN_HISTORY entry alone never auto-enables an indicator (validated at import). No generic fallback exists anywhere.

### Reason

DSR has no defensible universal healthy level (the DEC-018 audit reclassified the band-based competitors), but each country's own history is a well-defined, self-contained reference distribution that needs no external calibration data — the same self-containment that makes BIS caution against cross-country raw-DSR comparison moot here. The empirical mid-rank plotting position is rank-based (resistant to outlier magnitudes), deterministic, needs no distributional assumptions, and (as in DEC-017) honestly bounds a finite history short of 100/0. Expanding (not trailing) history maximizes the sample early in a country's coverage and keeps the calibration identical to the as-of discipline already proven for the WGI paths.

### Impact

Implemented in `app/cycle/normalizer.py` (`own_history_stress_position` pure mid-rank function + `_normalize_own_history_as_of` + dispatch refactor: DIRECT_0_100 → unchanged WGI path, OWN_HISTORY → DSR path, all other families raise NormalizationNotImplementedError) + `alignment_service.own_history_as_of` (as-of own-history selection mirroring `align_observation_as_of` semantics: country scoping, indicator scoping, latest vintage per period, DEC-015 period-complete, no-future, read-only) + `OwnHistoryLevelResult`/`OwnHistoryLevelConfig`/`NormalizedSignal.own_history_level`/`ModelVersionConfig.own_history_level_configs` in `normalization_definitions.py`. Model version **normalization-v0.5** (method `sprint-5.10-dsr-own-history-level-r1`) versioning the minimum 20, the expanding calibration, the mid-rank formula, the tie method, the inversion, and the freshness policy; all WGI v0.3/v0.4 config unchanged — WGI level/momentum/relative outputs are byte-equivalent (regression-tested). No migration; nothing persisted; no public API; no force scores/weights/phases. Tests: 311 offline (26 new). Live read-only smoke @2025-Q4: all tracked_8 score with n=104 histories (e.g. USA raw 14.1 → level 94.7115, rank 6/104; CHN raw 18.8 → level 2.88462, rank 101.5/104); CHE @2004-Q3 → raw 15.6 present, n=19, level None; CHE @2004-Q4 → n=20, first score (rank 1, stress 2.5, level 97.5). `backtest_safe` stays False until Milestone 9 (alignment is by observation period, not historical release date). Recommended Sprint 5.11: CREDIT_TO_GDP_GAP asymmetric TARGET_BAND threshold research (BIS early-warning literature) or confidence-dimension design.

## DEC-020 — Credit-to-GDP gap: asymmetric TARGET_BAND reclassified to ONE_SIDED_VULNERABILITY — positive-side breakpoints supported, negative-side penalty retracted

Date: 2026-09-09
Status: Accepted (Sprint 5.11)

### Decision

Sprint 5.11 conducted the DEC-018-mandated evidence audit for CREDIT_TO_GDP_GAP before any numeric implementation. Outcome — **RECLASSIFY / REFRAME**: the level family changes from asymmetric TARGET_BAND to a new family, **ONE_SIDED_VULNERABILITY** (no stress signaled at or below a neutral ceiling; stress rises monotonically above it). No score was implemented; every numeric Atlas breakpoint remains UNRESOLVED pending owner approval.

- **Positive side — SUPPORTED by official evidence** (recorded as evidence, NOT as Atlas score values): the Basel CCyB guide (BCBS 2010, bcbs187) uses L = +2pp / H = +10pp as a policy-guide reference point (linear 0→2.5%-of-RWA buffer add-on, flat zero below +2, explicitly non-mechanical); the BIS 2018 early-warning exercise (Aldasoro, Borio & Drehmann, BIS QR March 2018) finds a statistical crisis-prediction critical threshold ~9pp standalone (~80% of crises at a 25.7% noise-to-signal ratio), amber 4–9 / red ≥9 in its vulnerability tables, and ~4pp when combined with property-price gaps. These are TWO different instruments (policy guide vs statistical early warning) and are recorded separately — no fake consensus threshold.
- **Negative side — NO authoritative penalty threshold exists; none invented**: the Basel guide is flat zero below +2 (no rising penalty as the gap falls); the BIS 2014 Q&A (Drehmann & Tsatsaronis) treats the negative region as a phase of "no consequence" for the indicator's role (post-crisis, buffer-released periods); the persistent negative gap after a prolonged boom-bust is a documented MEASUREMENT ARTIFACT (boom-contaminated HP trend, understating renewed vulnerability — IMF WP 2020/006's assessment of the BIS gap); post-crisis deleveraging is essentially uncorrelated with recovery pace (Takáts & Upper, BIS WP 416). Therefore the DEC-018 wording "very negative gap = deleveraging/weak credit" is an ASSOCIATION, not threshold evidence, and the implied negative-side health penalty is RETRACTED: deleveraging/weak-credit conditions belong to OTHER signals (DSR own-history level — implemented in Sprint 5.10; credit growth; output growth), not to this indicator's level score.
- **Provider definition confirmed**: the gap is the credit-to-GDP ratio minus its long-run trend (one-sided HP filter, λ = 400,000, total credit to the private non-financial sector). Atlas consumes the provider-published BIS gap; it never recomputes the ratio, a trend, or an alternative gap.
- **Basel caution carried forward**: the gap is a "useful common reference point", not a mechanical standalone rule — authorities must exercise judgment, watch for misleading signals (GDP-denominator effects, trend turning points, structural breaks, post-bust artifacts), and use supplementary indicators. Any future Atlas implementation must carry these caveats as explicit score-interpretation limits.
- **As-of semantics**: BIS's one-sided trend does NOT solve Atlas's release-date limitation; backtest_safe stays False until Milestone 9.
- **Minimum history separated**: the BIS/Basel "at least 10 years of data" rule belongs to CONSTRUCTING a reliable HP trend, not to consuming the published series; no Atlas minimum-history parameter was decided.
- Three threshold concepts stay separated in all future work: (1) Basel CCyB guide thresholds, (2) statistical early-warning thresholds, (3) Atlas normalization curve parameters. Nothing in (1) or (2) automatically becomes (3).

### Reason

DEC-018 confirmed the asymmetric TARGET_BAND family "pending documented external evidence". The Sprint 5.11 audit of primary BIS/BCBS sources found that evidence supports the POSITIVE side but directly contradicts a negative-side penalty: the authoritative framework assigns no penalty to negative gaps, and a deeply negative gap is as likely a trend artifact as a health signal. Preserving the asymmetric family would have required inventing an unevidenced negative threshold — the exact failure mode this project's methodology forbids. A one-sided vulnerability mapping keeps the documented, dual-source positive-side evidence while encoding only what the sources support.

### Impact

Registry (`app/cycle/normalization_definitions.py`): new `NormalizationFamily.one_sided_vulnerability` (documented in the enum and §6); CREDIT_TO_GDP_GAP level family reclassified with an evidence-audit note; relative/momentum/freshness unchanged. CREDIT_TO_GDP_GAP still raises `NormalizationNotImplementedError` (regression-tested); no model-version bump (no score semantics became executable — CURRENT_MODEL_VERSION stays normalization-v0.5); no migration; nothing persisted; no public API; no force scores/weights/phases; DSR and WGI outputs unchanged (verified by the full suite). Tests: 312 offline (311 + 1 new still-unscored regression + updated exact-classification expectations). Evidence matrix, threshold-concept separation, provider definition, Basel caution, as-of semantics, construction-vs-normalization history, and the descriptive tracked_8 profile recorded in NORMALIZATION.md "Sprint 5.11" section. NO provisional numeric Atlas breakpoints are recorded here or anywhere — the neutral ceiling, positive-side curve shape, endpoint behavior, and the score interpretation of the no-excess region are owner decisions for a future implementation sprint. Recommended Sprint 5.12: owner chooses — credit-gap one-sided curve design (now evidence-backed), confidence-dimension design (WGI uncertainty import), Gini calibration-universe decision, or data-side work (education Option C / IMF WEO / WID).
