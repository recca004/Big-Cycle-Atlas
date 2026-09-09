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

## DEC-021 — Credit-to-GDP gap: owner-approved ONE_SIDED_VULNERABILITY level curve (neutral ceiling +2pp, linear to 0 at +10pp, no-excess region = 50)

Date: 2026-09-09
Status: Accepted (Sprint 5.12)

### Decision

The owner approved the numeric Atlas level curve for CREDIT_TO_GDP_GAP, implementing the Sprint 5.11/DEC-020 verdict. The curve (verbatim owner table: −20 → 50.00, 0 → 50.00, +2 → 50.00, +4 → 37.50, +6 → 25.00, +9 → 6.25, +10 → 0.00, +20 → 0.00):

- **Neutral ceiling = +2pp**: level_score = 50 for every gap at or below +2pp, including ALL negative gaps (no floor, no penalty — DEC-020's retraction preserved).
- **Positive side = strictly linear** from (+2, 50) to (+10, 0) — slope −6.25 per pp.
- **Endpoint clamp**: level_score = 0 for every gap at or above +10pp (no cap beyond).
- **No-excess region = 50, deliberately NOT 100**: absence of excess credit is not evidence of strength — the indicator is silent about health at or below +2; the region reads as NEUTRAL (§1's 50 = neutral middle reference). This resolves the DEC-020 open question "is the flat region 'strong' or 'no-signal'?" in favor of no-signal/neutral.

All four parameters (neutral_ceiling 2.0, saturation_value 10.0, no_excess_score 50.0, saturated_score 0.0) are Atlas MODEL PARAMETERS, versioned in `ModelVersionConfig.one_sided_vulnerability_configs` (normalization-v0.6). The +2/+10 breakpoints COINCIDE with the Basel CCyB guide's L/H reference points (bcbs187); the 50/0 score mapping is an Atlas choice, not Basel methodology truth — the three threshold concepts separated in DEC-020 stay separated. No minimum-history gate: the curve is parametric (any single eligible observation scores), unlike the DSR own-history calibration. Freshness gates the current observation only and never scales the score. Unchanged: relative stays CONTEXTUAL_DEFERRED (None), registry momentum windows (4q/8q) stay UNAPPROVED (momentum None), confidence None, backtest_safe False. The DEC-020 Basel-caution score-interpretation limits (GDP-denominator distortions, trend turning points, structural breaks, endpoint revisions, post-bust artifacts) carry to every published use of this score.

### Reason

DEC-020 left the numeric breakpoints as owner decisions. The owner supplied the exact curve table above; every mid-table point (+4 → 37.50, +6 → 25.00, +9 → 6.25) sits exactly on the linear segment from (+2, 50) to (+10, 0), so the table is fully consistent with flat-50-below-+2, linear-between, clamped-0-above — recorded here as the settled semantics.

### Impact

`app/cycle/normalizer.py`: new `one_sided_vulnerability_level` pure function + `_normalize_one_sided_vulnerability_as_of` path (align → freshness gate → curve), dispatched on the registry family with the same execution-gate pattern as DSR (registry family alone never auto-enables — an explicit model-version config entry is required). `app/cycle/normalization_definitions.py`: new `OneSidedVulnerabilityConfig` / `OneSidedVulnerabilityResult` (provenance travels with each signal), registry validation gate, CREDIT_TO_GDP_GAP notes updated to implemented. Model version bumped normalization-v0.5 → **normalization-v0.6** (method `sprint-5.12-credit-gap-one-sided-level-r1`); all v0.5 WGI + DSR configuration unchanged (DSR live values verified unchanged). `scripts/normalize_smoke.py` prints the new method with the curve parameters and the Basel-caution note. Tests: 318 offline (312 + 6 net new: owner-table exact regression through the full path, pure-curve clamps/continuity/config validation, no-auto-enable gate, no-observation → None, too-stale → None, freshness-decays-but-never-scales, other-dimensions-stay-None; the Sprint 5.11 still-unscored regression was replaced). Live read-only smoke (tracked_8 @2025-Q4): USA −11.54 → 50, CHN −7.69 → 50, CHE −17.04 → 50, DEU −3.96 → 50, FRA −15.11 → 50, GBR −17.82 → 50, JPN +6.78 → 20.10, IND +1.74 → 50. No migration; nothing persisted; no public API; no force scores/weights/phases; backtest_safe stays False. Indebtedness force layer: the credit-gap level now pairs with the DSR level as the force's second indicator-level input — but force aggregation/weights remain unapproved. Recommended Sprint 5.13: owner chooses — confidence-dimension design (WGI uncertainty import), Gini calibration-universe decision, productivity expanded calibration universe, or data-side work (education Option C / IMF WEO / WID).

## DEC-022 — Confidence layering: indicator trust separated from force completeness; WGI uncertainty representation chosen (not yet ingested)

Date: 2026-09-09
Status: Accepted (Sprint 5.13 — architecture/methodology sprint, no code change)

### Decision

Sprint 5.13 resolved the confidence architecture BEFORE any confidence implementation. Durable decisions:

**Layering (NORMALIZATION.md §10 rewritten — the old factor table mixed layers):**

1. **Confidence is independent from strength.** A signal with `level_score = 90, confidence = 0.4` means "strong measured condition, weak trust in the estimate" — economic scores are NEVER multiplied by confidence (`level_score *= confidence`, `relative_score *= confidence`, `momentum *= confidence` are all prohibited); confidence travels alongside the economic dimensions.
2. **Confidence is not freshness.** `freshness_factor` (DEC-013 exponential policy) is the single source of freshness truth: a future confidence may CONSUME it as an input but never recomputes age with another formula; `confidence = freshness_factor` is not a methodology.
3. **INDICATOR confidence (per NormalizedSignal)** contains indicator-level trust diagnostics only: source_quality (QUALITATIVE/typed only), freshness_factor (reused), measurement_uncertainty (optional provider diagnostics), method_sufficiency (optional method diagnostics, e.g. the DSR own-history sample_n/minimum_sample_n already carried in OwnHistoryLevelResult).
4. **FORCE confidence (aggregation layer only)** owns coverage/completeness, missing required inputs, and proxy completeness / DEC-009 coverage ceilings. **Locked rule:** coverage completeness and proxy ceilings are FORCE-layer concepts — they are NEVER folded into an individual NormalizedSignal merely because that indicator feeds a partial/proxy force. A high-quality fresh POLITICAL_STABILITY_WGI_SCORE signal is not lowered because Internal conflict is PARTIAL-ceiling-capped; SIPRI-spending-as-input belongs to Military-strength force completeness, not a fake low indicator source-quality number.
5. **Missing uncertainty ≠ perfect confidence ≠ zero.** If a score exists but measurement uncertainty is missing, the measurement-uncertainty component is UNKNOWN (None) — never a default factor of 1, never a confidence of 0; the score itself stays usable. Missing confidence metadata ≠ missing economic observation.
6. **No arbitrary numeric provider-quality constants** (no "World Bank = 0.95"). Qualitative provenance categories (official_primary, official_republished, proxy_measure, perception_composite) may be TYPED later; any numeric mapping needs a calibrated, versioned basis. No method-sufficiency numeric conversions (no "20 DSR observations = confidence 0.6") are approved.
7. **Numeric composition stays deferred** (§17 item 6 remains open for the formula/weights only). Model version stays **normalization-v0.6** — no executable NormalizedSignal output changed, and a design/documentation sprint never bumps the version; the future first executable confidence formula does.

**WGI uncertainty audit (live read-only probe, 2026-09-09 — verified, not assumed):**

- Exact series confirmed against WB API v2 metadata: score `GOV_WGI_{RL,CC,PV}_SC` (WDI, source 2) plus dedicated WGI source (id 3) series `GOV_WGI_{dim}.SC_LB` / `.SC_UB` ("Lower/Upper bound of the 90% confidence interval for the governance score"), `.SE` ("Standard error of the governance estimate"), `.SR` ("Number of sources").
- All 8 tracked countries have all 4 uncertainty series for every score year 1996–2024 (208 obs per series = 8 × 26; biennial gaps 1997/1999/2001 only; no 2025 values yet); one-to-one year alignment with the score series is PERFECT for every country/dimension.
- Scale verified: LB ≤ score ≤ UB for all 624 points — the CI bounds are on the SAME 0–100 governance-score scale as the imported score (symmetric; UB clamps at 100). SE is on the UNDERLYING ESTIMATE scale (~0.15–0.25), and empirically width ≈ 56.5 × SE (NOT 65.8 × SE = 20 × 2 × 1.645) — SE does not reconstruct the published bounds. SR is integer-valued count data (observed range 4–16).

**Selected initial WGI uncertainty input set: LB + UB + SR** (CI width = UB − LB as the primary score-scale measurement diagnostic; SR as a distinct data-richness diagnostic; SE DEFERRED — estimate-scale, non-reconstructive, adds no score-scale information). No CI-width or source-count → confidence curve is designed or approved anywhere here.

**Storage representation (decision matrix in NORMALIZATION.md "Sprint 5.13"):** dedicated auxiliary-diagnostics storage associated with the BASE canonical indicator (working name `indicator_diagnostics` — country, base indicator, diagnostic kind ci_lower_bound/ci_upper_bound/source_count, provider series code, period, value, retrieved-at, vintage semantics; NO SourceSeries rows). REJECTED: auxiliary canonical indicators (catalog/API/indicator_count/force-coverage pollution — uncertainty would masquerade as economic indicators and force inputs); multiple SourceSeries under the existing WGI indicator (INVALID — `align_observation_as_of`/`own_history_as_of` select by indicator and could return a bound instead of the score, nondeterministically); raw_payload provider metadata (FACTUALLY UNAVAILABLE — the WB score-series records carry no uncertainty fields; they are separate source-3 series).

**As-of semantics for uncertainty:** same country, same dimension, SAME eligible source period as the aligned score observation, latest appropriate vintage — never a later year's bounds, never today's source count, never another country's uncertainty, no future metadata. backtest_safe stays False (release dates remain unavailable).

### Reason

The Sprint 5.5 §10 factor table mixed indicator trust with force completeness, which would have pressured the first confidence implementation into lowering good indicator signals for proxy forces. The audit verified (rather than assumed) the WGI uncertainty series: the CI bounds are directly score-scale, which makes CI width the defensible primary diagnostic; SE's estimate scale plus the empirical 56.5 (not 65.8) width/SE ratio means SE cannot serve as a score-scale proxy. The storage audit found that every no-migration option corrupts a semantic boundary (catalog, alignment ambiguity, or nonexistent provider fields); accepting a small migration is the correct trade.

### Impact

NO production code changed; NO migration executed; NOTHING ingested; no confidence number exists; confidence stays None on every signal; no force scores/weights/phases; no public API change; model version stays normalization-v0.6 (all Sprint 5.12 numerical outputs unchanged — pytest 318 green). NORMALIZATION.md §10 rewritten (10.1 permanent rules / 10.2 indicator confidence / 10.3 force confidence), §17 items 6 and 9 updated, Sprint 5.13 status section + storage decision matrix + Sprint 5.14 spec added; DATA_SOURCES.md WGI uncertainty line updated with the verified facts. **Sprint 5.14 spec (pending owner acceptance):** (1) Alembic migration for `indicator_diagnostics` (no SourceSeries rows); (2) a WB fetch path for `GOV_WGI_{dim}.SC_LB/.SC_UB/.SR` persisting ONLY into the diagnostics table (never `persist_observations`), idempotent + revision-aware, recorded as IngestionRun; (3) a derived-layer lookup helper (diagnostics at the ALIGNED source period, latest vintage; missing → None); (4) nothing else — no confidence formula, no NormalizedSignal change, no model-version bump, no public API.

## DEC-023 — WGI numeric indicator confidence: DEFERRED (no defensible calibration basis exists yet)

Date: 2026-09-09
Status: Accepted (Sprint 5.16 — methodology / empirical research sprint)

### Decision

Sprint 5.16 conducted the empirical confidence calibration audit for the
WGI x3 (RULE_OF_LAW / CONTROL_OF_CORRUPTION / POLITICAL_STABILITY_WGI_SCORE)
using the 624 aligned score/diagnostic rows imported in Sprint 5.15. The
verdict is **DEFER_NUMERIC_CONFIDENCE** — a durable methodology decision,
not a postponement of an obvious answer. Atlas cannot yet define a
defensible numeric indicator confidence for the WGI x3.

The deferral is based on six empirical findings from the read-only profile
(`apps/api/scripts/wgi_confidence_profile.py`):

1. **CI width and SR are highly informationally redundant** (pooled
   Pearson -0.829, Spearman -0.797; per-dimension -0.85 to -0.97). More
   sources -> narrower CI, monotonically. Combining both in a confidence
   formula would double-count the same measurement-uncertainty signal;
   using only one discards the other. No evidence basis exists to choose
   one as the sole input or to weight them in a joint formula without
   double-counting.
2. **Dimension differences are substantial and unexplained.** RL has the
   narrowest CI (median 9.23) and most sources (median 12); PV has the
   widest CI (median 13.88) and fewest sources (median 8.5); CC is in
   between. A pooled calibration would systematically assign PV lower
   confidence than RL; a per-dimension calibration would need a
   per-dimension evidence basis that does not exist. The profile cannot
   distinguish genuine measurement-quality differences from inherent
   concept difficulty.
3. **Temporal trends make empirical calibration leaky or drifting.** SR
   increases over time (Pearson 0.543 vs year; median 6 in 1996 to 10.5 in
   2024); CI width decreases over time (implied by the strong SR-width
   negative correlation). Full-history calibration leaks future
   distribution information; expanding-window calibration is as-of safe
   but makes confidence drift as measurement systems improve. A fixed
   mapping avoids leakage but is arbitrary without an external
   calibration basis.
4. **No external calibration basis exists** for mapping raw CI width (or
   SR) to a 0-1 confidence value. Any mapping (linear, percentile, rank)
   would be an arbitrary choice without evidence — the exact failure mode
   this project's methodology forbids (DEC-022: "no arbitrary numeric
   provider-quality constants").
5. **Freshness composition is unresolved.** No composition rule
   (multiplication, weighted arithmetic mean, weighted geometric mean,
   minimum/bottleneck, or separate diagnostics without scalar
   composition) has an evidence basis. The permanent rules (confidence !=
   freshness, confidence != strength, missing != perfect != zero)
   constrain the choice but do not resolve it.
6. **A single scalar confidence would hide dimension-specific trust.**
   The eventual confidence architecture should be per-dimension
   (level_confidence / relative_confidence / momentum_confidence), not
   one scalar — but that schema decision is not this sprint's work.

Boundary clipping (Part 4): 9/624 (1.4%) upper-clipped (UB >= 100); 0
lower-clipped; all 9 are CHE. Clipping is rare and concentrated; the
distortion is small but must be documented as a known limitation of raw
CI width. Score vs width (Part 5): pooled Pearson 0.080 — essentially no
correlation; a width-based confidence would NOT systematically penalize
high or low governance scores.

### What is NOT deferred

- The Sprint 5.13/DEC-022 permanent rules remain locked (confidence !=
  strength, confidence != freshness, missing != perfect != zero, no
  arbitrary provider-quality constants).
- The Sprint 5.14/5.15 diagnostics storage and ingestion remain
  implemented and live (1872 rows in `indicator_diagnostics`).
- The Sprint 5.16 transaction hardening (connection_invalidated
  propagation) is implemented and regression-tested.
- The diagnostics remain INPUT DATA for a future confidence formula;
  they are not deleted or deprecated.

### What additional evidence / data / methodology is required

Before numeric confidence can be defensibly implemented, the following
must be resolved:

- An external calibration basis for mapping raw CI width (or SR) to a
  0-1 confidence value (e.g. WB/WGI methodology documentation on the
  relationship between CI width and estimate reliability; or a
  peer-reviewed calibration study).
- A decision on whether confidence is pooled across WGI dimensions or
  per-dimension — and if per-dimension, a per-dimension evidence basis.
- A decision on the calibration window (fixed mapping vs expanding
  own-history vs expanding cross-country) — and if empirical, an
  as-of-safe expanding-window design that does not drift.
- A decision on the freshness composition rule with an evidence basis.
- A decision on whether confidence is one scalar or per-dimension.
- Resolution of the CI-width / SR redundancy: which is the primary
  measurement-uncertainty input, and how (if at all) the other
  contributes without double-counting.

### Reason

The Sprint 5.16 empirical profile found that the two available
measurement-uncertainty diagnostics (CI width and SR) are highly
redundant, that dimension and temporal differences are substantial and
unexplained, and that no external calibration basis exists for a numeric
mapping. Inventing a numeric formula now would be fake precision —
exactly the failure mode this project's methodology forbids (DEC-018,
DEC-020, DEC-022). Deferral is the honest outcome; it preserves the
diagnostics as input data and the permanent rules as constraints without
publishing an undefensible number.

### Impact

NO numeric confidence was implemented; NO NormalizedSignal output
changed; the model version stays **normalization-v0.6**; `confidence`
stays None everywhere; `backtest_safe` stays False. The read-only profile
script `apps/api/scripts/wgi_confidence_profile.py` is added (descriptive
statistics only — no scores, no writes, not proof of economic truth).
The transaction hardening in `wgi_diagnostic_ingestion.py`
(connection_invalidated propagation) is implemented with focused
regression coverage. NORMALIZATION.md Sprint 5.16 section + decision
matrix + verdict added; §17 item 6 updated; this DEC-023 added. No
migration; nothing persisted; no public API; no force scores/weights/
phases; no frontend change. The diagnostics remain confidence INPUT
DATA only; the Sprint 5.14 boundary caution and the Sprint 5.13
permanent rules apply to every future use.

## DEC-024 — Gini numeric level: DEFERRED (no defensible calibration universe or comparability basis exists yet)

Date: 2026-09-09
Status: Accepted (Sprint 5.17 — methodology / empirical research sprint)

### Decision

Sprint 5.17 conducted the Gini calibration universe + comparability audit
for GINI_INDEX (World Bank SI.POV.GINI). The verdict is **DEFER_GINI_LEVEL**
— a durable methodology decision, not a postponement of an obvious answer.
Atlas cannot yet defensibly map World Bank GINI_INDEX into an Atlas 0–100
INDICATOR strength level.

The deferral is based on six findings from the read-only profile
(`apps/api/scripts/gini_calibration_profile.py`) and the WB/PIP methodology
documentation:

1. **Survey-concept comparability is insufficient.** SI.POV.GINI mixes
   income-based surveys (high-income economies: USA/CHE/DEU/FRA/GBR/JPN,
   via LIS/EU-SILC, after-tax income) and consumption-based surveys
   (CHN/IND and most low- and middle-income countries). OWID states:
   "consumption tends to be more evenly distributed than income" — so
   consumption Gini is systematically LOWER than income Gini for the same
   true inequality. This is visible in the tracked_8 data: IND
   (consumption) median 27.7 vs USA (income) median 40.8. **The WB API
   does NOT expose a per-observation welfare-concept tag**, so no
   defensible automated adjustment is possible. A single global curve
   would conflate a measurement-concept difference with a true inequality
   difference.
2. **tracked_8 is NOT a defensible calibration universe.** The tracked_8
   range (25.5–43.7) is a narrow subset of the world distribution
   (20.2–71.1, 171 countries, 2430 country-year observations). tracked_8
   is 8 countries, not a global inequality distribution. tracked_8
   calibration is permanently rejected.
3. **The global distribution is not stable enough for one fixed curve.**
   Country composition shifts materially by decade (2 -> 160 -> 115
   countries). Decade medians vary (34–39). A fixed full-history pooled
   percentile would encode future information and composition changes.
4. **No defensible midpoint semantics exists.** level_score=50 has no
   approved interpretation: global median shifts over time; no
   authoritative raw-Gini threshold exists; historical median leaks future.
   Without a defensible midpoint, no monotonic curve (logistic,
   piecewise-linear, saturating) can be calibrated.
5. **No external calibration basis exists** for fixed raw-Gini thresholds.
   Any threshold (e.g. "Gini 40 = level 50") would be an arbitrary choice
   without evidence — the failure mode DEC-018 explicitly rejected.
6. **As-of safety requires an expanding-window design that doesn't drift
   — unresolved.** Full-history leaks future; same-year is sparse
   (2025 n=4); expanding drifts as coverage/concept mix changes. Release
   dates remain unavailable, so backtest_safe stays False even for a
   period-safe calibration.

### What is NOT deferred

- The DEC-018 direction confirmation (MONOTONIC_NEGATIVE) remains.
- `100 - Gini` remains NOT approved.
- tracked_8 min/max calibration remains explicitly rejected.
- The freshness policy (DEC-013, irregular class) remains the one source
  of truth; no parameter changes.
- The Wealth / opportunity / values gaps force stays PARTIAL (DEC-009).
- GINI_INDEX raw data stays live and imported (187 obs, tracked_8).

### What additional evidence / data / methodology is required

Before a Gini level can be defensibly implemented, the following must be
resolved:

- A welfare-concept metadata source (per-observation income vs
  consumption tag) OR an authoritative welfare-concept adjustment
  methodology OR a decision to calibrate income-based and consumption-based
  Gini separately.
- A decision on the calibration universe (expanding global vs same-year vs
  a fixed externally-justified reference distribution) — tracked_8 is
  permanently rejected.
- A defensible midpoint semantics (what does level_score=50 mean?) —
  requiring an external calibration basis or a normative threshold
  authority.
- An as-of-safe expanding-window design that handles composition drift
  (if expanding global is chosen).
- A sparse-year fallback rule (if same-year is chosen).
- Resolution of whether income-based and consumption-based Gini need
  separate calibration curves.

### Reason

The Sprint 5.17 audit found that the WB Gini series mixes two
systematically different survey concepts (income vs consumption) without
exposing the per-observation metadata needed to adjust for it; tracked_8
is a narrow, non-representative subset; the global distribution shifts
with country composition; and no defensible midpoint or external
calibration basis exists. Inventing a numeric curve now would be fake
precision — exactly the failure mode this project's methodology forbids
(DEC-018, DEC-020, DEC-022, DEC-023). Deferral is the honest outcome; it
preserves the direction confirmation and the raw data without publishing
an undefensible number.

### Impact

NO Gini level_score was implemented; NO NormalizedSignal output changed;
the model version stays **normalization-v0.6**; `confidence` stays None
everywhere; `backtest_safe` stays False. The read-only profile script
`apps/api/scripts/gini_calibration_profile.py` is added (descriptive
statistics only — no scores, no writes, no new connector). NORMALIZATION.md
Sprint 5.17 section + decision matrix + verdict added; §7 GINI_INDEX row
updated; this DEC-024 added. No migration; nothing persisted; no public
API; no force scores/weights/phases; no frontend change; no FORCE_COVERAGE
change (Wealth-gap stays PARTIAL). GINI_INDEX stays
MONOTONIC_NEGATIVE (direction confirmed) with NO numeric curve; the
Sprint 5.13 permanent rules apply to every future use.

### Sprint 5.17.1 impact note (2026-09-09) — verdict UNCHANGED

Sprint 5.17.1 corrected an empirical-research bug in the read-only profile's
global-universe filter: the hand-written `aggregate_codes` blacklist wrongly
listed real economies ZAF (South Africa) and PSE (West Bank and Gaza) as
aggregates. The filter now uses the AUTHORITATIVE WB country-metadata endpoint
(`/v2/country`, `region.id != "NA"` => real economy). Corrected global counts
(read-only live WB API v2, 2026-09-09): 217 real economies identified; 2430
valid country-year observations, 171 countries, 1963–2025 (same counts as
Sprint 5.17 — the old blacklist was ineffective due to a 2-letter vs 3-letter
code mismatch, so the bug was methodological, not numerical); ZAF RETAINED
(7 obs, 54.1–65), PSE RETAINED (9 obs, 33.7–36.4); pooled 20.2–71.1 median
35.3; latest sufficiently populated year 2023 n=57.

**DEC-024 verdict UNCHANGED (option B — wording/statistics basis strengthened
but the durable methodology conclusion does not change).** The filtering bug
did not materially alter the Sprint 5.17 methodology verdict. The six
DEFER_GINI_LEVEL reasons stand unchanged. The welfare-concept problem and the
missing per-observation welfare tag remain SEPARATE from this filtering bug.
DEC-024 is not rewritten — the durable methodology conclusion is unchanged;
only the filtering mechanism and the ZAF/PSE retention are corrected. See
NORMALIZATION.md "Sprint 5.17.1 methodology status" for the full record.

## DEC-025 — Milestone-5 high-value gap source contracts: WEO debt + Education Option C + WID wealth

Date: 2026-09-10
Status: Accepted (Sprint 5.18 — read-only research / documentation sprint)

### Decision

Sprint 5.18 conducted read-only, official-source-only research on three
high-value data-gap tracks. No ingestion, persistence, normalization, scoring,
or code changes resulted. This decision records the verified provider
contracts and the distinct readiness verdict for each track.

### Track A — IMF WEO general-government gross debt: READY for implementation

- **Indicator code verified**: `GGXWDG_NGDP` — "General government gross
  debt", unit "Percent of GDP", source "World Economic Outlook (April 2026)",
  dataset WEO. Confirmed live via the IMF DataMapper API
  (`https://www.imf.org/external/datamapper/api/v1/indicators`) and the
  DataMapper series endpoint
  (`/api/v1/GGXWDG_NGDP/{ISO3...}`). The code matches DEC-008's requirement
  (general government, gross, % of GDP) — NOT the rejected World Bank
  central-government series `GC.DOD.TOTL.GD.ZS`.
- **API mechanisms**: Two official access paths exist:
  1. **IMF DataMapper API** (public, no auth): JSON response, simple
     `/{indicator}/{country1}/{country2}/...` path; returns all years
     (historical + forecast) in one flat object. No vintage/release metadata.
  2. **IMF SDMX 3.0 API** (`https://api.imf.org/external/sdmx/3.0`): the
     system-of-record API; exposes `LATEST_ACTUAL_ANNUAL_DATA` attribute to
     distinguish historical from forecast values; dataflow versions
     correspond to WEO vintages (April/October). Requires an
     `Ocp-Apim-Subscription-Key` header (free registration).
- **Tracked_8 coverage**: ALL 8 countries covered (USA, CHN, CHE, DEU, FRA,
  GBR, JPN, IND), verified live. Historical coverage: USA 2001–2024, CHN
  1995–2024, CHE 1990–2024, DEU 1991–2024, FRA 1980–2024, GBR 1980–2024,
  JPN 1980–2024, IND 1991–2024. Forecast horizon extends to 2031.
- **Vintage/forecast risk**: The DataMapper API returns historical and
  projected values in one flat series with NO flag distinguishing them. The
  SDMX 3.0 API exposes `LATEST_ACTUAL_ANNUAL_DATA` to mark the boundary.
  **Implementation must NOT silently treat projected values as historical
  observations.** The existing `ObservationDTO` schema (with `raw_payload`)
  is sufficient IF the adapter stores only historical values OR records the
  estimate/projection status in `raw_payload`. A schema change is NOT
  required for historical-only ingestion. If estimates/projections are to
  be retained, a `raw_payload` flag or a future `observation_status` column
  would be needed — deferred to the implementation sprint.
- **Verdict**: READY. The contract is verified, coverage is complete, and
  the existing architecture can ingest historical-only values. The
  implementation sprint (5.19) must choose: (a) historical-only ingestion
  via the DataMapper API (simplest, safest), or (b) SDMX 3.0 with
  `LATEST_ACTUAL_ANNUAL_DATA` filtering (more robust, requires API key).

### Track B — Education Option C: PARTIAL — WB SE.SEC.NENR stale, OECD attainment triennial

- **WB SE.SEC.NENR** (secondary net enrollment): Official WB metadata
  confirms: "School enrollment, secondary (% net)", annual, source UNESCO
  UIS via WDI. Net enrollment rate = children of official school age
  enrolled / population of corresponding official school age. **Coverage
  problem verified live**: USA last data 2017 (2018–2025 all null); CHE last
  2017; DEU last 2017; GBR last 2017; CHN has NO data at all (all years
  null); JPN last data 2016. The WB metadata itself states "Reference
  period: 1970–2019" — the series is effectively discontinued for most
  tracked_8 countries. This is a stale-source problem, not a mapping
  problem.
- **OECD tertiary attainment** (`DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA_MIGR`,
  agency `OECD.EDU.IMEP`, v1.0): "Adults' educational attainment
  distribution, by country of birth, age group and gender". Measure:
  `PT_POP_SEX_AGE` (percentage of population in the same sex and age).
  Attainment level `ISCED11A_5T8` = tertiary education. Age group `Y25T34`
  = 25–34 years. **Frequency: A3 (triennial)**, NOT annual. Values are
  fractions (0–1), e.g. USA 2023 = 0.372 (37.2%). **Tracked_8 coverage:
  5 of 8** — USA, CHE, DEU, FRA, GBR have data; JPN, CHN, IND are NOT in
  the dataset (OECD non-member / non-coverage). Data years: 2017, 2020,
  2023 (triennial cycle).
- **Verdict**: PARTIAL. WB SE.SEC.NENR is too stale for a live force input
  (last data ~2017, CHN has none). OECD tertiary attainment is a valid
  attainment measure (not enrollment) but is triennial and covers only 5/8
  tracked_8. Neither indicator alone can make the Education force
  AVAILABLE. Recommendation: promote OECD tertiary attainment as a partial
  proxy (5/8 coverage, triennial); DO NOT promote WB SE.SEC.NENR without a
  fresher source or an explicit stale-data acceptance decision. The
  Education force stays at its current status (defined_not_sourced for
  most, partial for OECD-5 if promoted).

### Track C — WID wealth: access verified, ceiling NOT lifted

- **Official access mechanism**: WID provides four documented access paths:
  (1) website graphing tools, (2) specific-series download from the DATA
  section, (3) bulk download (full dataset from `https://wid.world/data/`),
  (4) R/Stata packages using a webservice at
  `https://rfap9nitz6.execute-api.eu-west-1.amazonaws.com/prod/`. The
  webservice requires an `x-api-key` header (base64-encoded API key bundled
  in the R package's `sysdata.rda`). Bulk download does NOT require an API
  key. No scraping of unofficial interfaces is needed.
- **Wealth indicator**: `shweal` (share of net personal wealth, `hweal` =
  net personal wealth, `s` = share). Percentile `p90p100` = top 10% wealth
  share, `p99p100` = top 1% wealth share. Values are fractions (0–1).
  Annual frequency. Country codes are 2-letter ISO (US, CN, CH, DE, FR,
  GB, JP, IN). Age code `992` = adults (20+). Population type `i` =
  individuals.
- **Tracked_8 coverage**: WID covers 100+ countries; all 8 tracked_8
  countries are listed in the WID country index (USA, China, Switzerland,
  Germany, France, UK, Japan, India). Actual wealth-share data coverage
  varies by country and year (WID data is research-grade, with
  interpolations/extrapolations — the R package exposes
  `include_extrapolations = FALSE` to exclude fragile estimates).
- **Ceiling recommendation**: Adding one wealth-share series does NOT
  automatically lift the DEC-009 `PARTIAL` ceiling on the Wealth /
  opportunity / values gaps force. The force covers wealth inequality,
  equality of opportunity, AND values/social gaps. A wealth share
  (top-10%) addresses wealth inequality only. The ceiling stays PARTIAL
  until opportunity and values/social-gap measures are also addressed.
  WID wealth shares would strengthen the force (add a wealth-distribution
  input alongside the income-inequality Gini) but the force remains a
  multi-concept proxy.
- **Verdict**: READY for implementation as a partial proxy. The access
  mechanism is stable (bulk download or R-package webservice). The
  indicator (`shweal`, `p90p100` or `p99p100`) is well-defined. The
  implementation sprint must: (a) choose bulk-download vs webservice, (b)
  decide whether to exclude extrapolations (`include_extrapolations =
  FALSE` is recommended for Atlas), (c) accept that the force stays
  PARTIAL.

### Reason

The three tracks were audited to close the highest-value remaining data
gaps before Milestone 5 closeout. Each track has a distinct readiness
verdict: WEO debt is fully ready, education is partially ready with
significant staleness/coverage caveats, and WID wealth is ready as a
partial proxy that does NOT lift the conceptual ceiling. Recording these
contracts now prevents re-research and ensures implementation sprints
have verified provider identities, codes, and coverage matrices.

### Impact

NO code changed; NO ingestion performed; NO persistence; NO
normalization; NO scoring; NO migration; NO model-version bump; NO
frontend change. The existing `ObservationDTO` schema is sufficient for
WEO historical-only and WID wealth-share ingestion (with `raw_payload`
preserving provider dimensions). WEO forecast/estimate retention would
require a future schema discussion. DEC-007 (education Option C) and
DEC-008 (general-government debt) are HONORED — this sprint verified
their contracts without overriding their conceptual decisions. DEC-009
(wealth ceiling) is HONORED — WID wealth does NOT lift the PARTIAL
ceiling. The recommended sprint sequence is 5.19 (WEO debt), 5.20
(OECD attainment), 5.21 (WID wealth), 5.22 (Force Layer + Milestone 5
Closeout).

### Sprint 5.19 verification corrections (2026-09-10)

Sprint 5.19 implemented Track A (IMF WEO) and completed final
verification of Tracks B and C. The following corrections to the
Sprint 5.18 research above are recorded:

**Track A — IMF SDMX 3.0 works WITHOUT subscription key.** DEC-025
stated the SDMX 3.0 API "Requires an `Ocp-Apim-Subscription-Key` header
(free registration)." This is INCORRECT. The official endpoint
`https://api.imf.org/external/sdmx/3.0` is publicly accessible without
authentication. Sprint 5.19 successfully imported all 8 tracked
countries (297 observations, historical-only) via SDMX 3.0 with
`LATEST_ACTUAL_ANNUAL_DATA` filtering. No DataMapper fallback was
needed. The adapter, mappings, CLI, and seed are implemented and tested
(21 offline tests pass). Idempotent re-import verified (0 inserted /
297 skipped / 0 revised on second run). The revision/vintage path is
covered by the shared `persist_observations` infrastructure
(`test_observation_revisions.py`).

**Track B — OECD dataflow and dimensions corrected.** DEC-025
referenced `DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA_MIGR` with age
`Y25T34` (25–34), triennial frequency (A3), 5/8 coverage, and fraction
values (0–1). Sprint 5.19 verification found:
- Correct dataflow: `DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA` (NOT `_MIGR`)
  — "Adults' educational attainment distribution, by age group and
  gender" (national-level, not migration-specific).
- Age group: `Y25T64` (25–64 years), NOT `Y25T34` (25–34). No `_T`
  (all-ages total) exists in this dataflow.
- Frequency: `A` (annual), NOT `A3` (triennial). Data is available
  annually, though some countries have sparse coverage.
- Coverage: 8/8 countries have data, NOT 5/8. However, CHN (2 data
  points: 2010, 2020) and IND (6 data points: 2011, 2012, 2018–2021)
  are extremely sparse. USA, CHE, DEU, FRA, GBR, JPN have good annual
  coverage (1981–2025 / 1989–2025 / 1989–2025 / 1981–2024 / 1997–2025 /
  1997–2025 respectively).
- Values: percentages (`PT_POP_SEX_AGE`), NOT fractions (0–1). E.g.
  USA 2023 = 50.71% (not 0.5071).
- Attainment level: `ISCED11A_5T8` = "Tertiary education" (ISCED
  levels 5–8), confirmed correct.
- SEX = `_T` (total, both sexes), confirmed.
- Canonical recommendation: `EDUCATION_IMPLEMENTABLE_PARTIAL` — the
  series is implementable for 6/8 countries with good coverage; CHN
  and IND are too sparse for reliable time-series use. The age
  constraint (25–64, not all-ages) is the standard OECD/EAG convention
  for adult educational attainment.

**Track C — WID canonical series and extrapolation counts verified.**
DEC-025 stated pop=`i` (individuals). Sprint 5.19 bulk-download
verification found:
- Canonical series for all 8 countries: `shwealj992` (age=992 adults,
  pop=`j` = equal-split adults), NOT pop=`i` (individuals). Pop=`i`
  exists only for USA and GBR; pop=`j` is the only series available
  for all 8 tracked countries.
- Coverage (shwealj992, p90p100 + p99p100): all 8 countries have data
  from at least 1980 to 2024. Modern-era coverage is good; pre-1900
  gaps are expected for WID's long-run series.
- Extrapolation counts (data_quality=2): USA 0, CHN 0, CHE 0, DEU 24,
  FRA 80, GBR 93, JPN 0, IND 0. Three countries (DEU, FRA, GBR) have
  significant extrapolation. Interpolation counts (data_quality=1):
  DEU 1, IND 4; all others 0.
- Recommendation: `WID_IMPLEMENTABLE` — exclude data_quality=2
  (extrapolated) values during ingestion. After exclusion, coverage
  remains sufficient for all 8 countries. The `include_extrapolations
  = FALSE` recommendation from Sprint 5.18 is honored via the
  data_quality filter. The force stays PARTIAL (DEC-009 ceiling
  honored).

### Sprint 5.20 implementation notes (2026-09-10)

Sprint 5.20 implemented Tracks B and C and hardened Track A. The
following implementation corrections to the Sprint 5.19 verification
above are recorded:

**Track A — IMF WEO adapter hardened.** The NaN-only check (`not (value
== value)`) was replaced with `math.isfinite(value)` — now rejects NaN,
+inf, and -inf. The fiscal-year century rollover was fixed: `FY1999/00`
correctly maps to 2000 (was 1900), `FY2099/00` to 2100 (was 2000). The
`LATEST_ACTUAL_ANNUAL_DATA` boundary is now extracted by attribute ID
from the SDMX structure's `dataAttributes` list, not by array position
— fail-closed if the attribute is absent or ambiguous.

**Track B — OECD education: Y25T34 selected, exact no-wildcard identity.**
Sprint 5.19 recommended Y25T64. Sprint 5.20 compared Y25T34 and Y25T64
live for all 8 tracked countries and found coverage is NOT materially
different (both 8/8, similar counts). Y25T34 was selected because 25-34
represents recent cohorts and is more responsive to the current education
system. The production identity uses ALL 17 dimensions fixed (NO wildcards):
`{cc}._T.Y25T34.ISCED11A_5T8._T.POP._Z._T._Z.ED_NED.POP._Z.PT_POP_SEX_AGE.OBS._Z.NEAC.A`.
STATISTICAL_OPERATION=OBS excludes SE (standard error) rows. 200 observations
imported across 8 countries (CHN: 1 obs, IND: 8 obs — sparse). Education
promoted to PARTIAL (DEC-009 ceiling — one tertiary series cannot make
Education AVAILABLE).

**Track C — WID wealth: data_quality DEFER filtering, not exclude.**
Sprint 5.19 recommended excluding data_quality=2 (extrapolated) values.
Sprint 5.20 found that WID does NOT provide an official, authoritative
code dictionary for the data_quality column. The values 0, 1, 2 were
observed but their exact meaning (observed/interpolated/extrapolated) is
NOT officially documented. Policy: DEFER filtering — import ALL rows,
preserve data_quality in raw_payload, do NOT delete provider data using
an inferred code meaning. 670 observations imported across 8 countries.
The force stays PARTIAL (DEC-009 ceiling honored).

## DEC-026 — Education attainment age 25-34 and PARTIAL ceiling

Date: 2026-09-10
Status: Accepted (Sprint 5.20)

### Decision

OECD tertiary educational attainment for age 25-34 (`Y25T34`) is the
canonical education indicator. Y25T64 was rejected because 25-34
represents recent cohorts and is more responsive to the current education
system. Coverage is NOT materially different between the two age groups
(verified live: both 8/8, similar counts). The Education force is capped
at PARTIAL (DEC-009) — one tertiary attainment series cannot make
Education AVAILABLE. Attainment != enrollment (DEC-007 honored).

### Sprint 5.20.1 implementation clarification (2026-09-10)

The Sprint 5.20 implementation recorded the education external identity
as `EAG_LSO_NEAC/{cc}._T.Y25T34...` — a synthetic abbreviation forced by
the `SourceSeries.external_code` varchar(100) column limit. The exact
identity (agency `OECD.EDU.IMEP` + dataflow
`DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA` + version `1.0` + 17-dimension
SDMX key) is 140 chars and did not fit. Sprint 5.20.1 widened the column
to varchar(255) (Alembic `a8f3c2d1e5b7`) and replaced the abbreviation
with the exact serialized identity:
`OECD.EDU.IMEP,DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA,1.0/{cc}._T.Y25T34.ISCED11A_5T8._T.POP._Z._T._Z.ED_NED.POP._Z.PT_POP_SEX_AGE.OBS._Z.NEAC.A`
(140 chars). The delimiter choice (comma-separated agency/dataflow/version,
slash-separated key) mirrors the OECD SDMX REST URL path component
`{agency_id},{dataflow_id},{version}/{key}`. The existing SourceSeries
row was updated in place by seed — no duplicate created, no observation
FK changed. The retired `EAG_LSO_NEAC/...` abbreviation is gone.

## DEC-027 — WID data_quality filtering: DEFERRED (official semantics unverified)

Date: 2026-09-10
Status: Accepted (Sprint 5.20)

### Decision

WID's `data_quality` column is preserved in `raw_payload` but NOT used
for filtering. WID does NOT provide an official, authoritative code
dictionary for the data_quality values (0, 1, 2 observed). The Sprint
5.19 recommendation to exclude data_quality=2 (extrapolated) values is
RETRACTED — no inferred row deletion is allowed without official
documentation. If official semantics are found later, a future sprint
may add filtering.

### Sprint 5.20.1 implementation clarification (2026-09-10)

The provider `data_quality` representation is preserved for traceability.
`raw_payload` now carries both `data_quality_raw` (the raw provider CSV
field, stripped of surrounding whitespace — the adapter's normalized
representation) and `data_quality` (the typed convenience value: int for
"0"/"1"/"2", None for empty or non-integer codes). The provider code is
never lost — unknown future provider codes such as "A" are PRESERVED as
"A" (not None-or-zero, not filtered, not disappeared). Empty string
stays "". No meanings such as 0=observed, 1=interpolated, 2=extrapolated
are assigned unless official WID documentation is later found.

## DEC-028 — WID top-10 wealth share: PARTIAL ceiling confirmed

Date: 2026-09-10
Status: Accepted (Sprint 5.20)

### Decision

WID top-10% net personal wealth share (`shwealj992`, `p90p100`, pop=`j`
equal-split adults) is the canonical wealth concentration indicator. Raw
provider fraction (0-1) preserved unchanged. The Wealth / opportunity /
values gaps force stays PARTIAL (DEC-009) — a wealth share addresses
wealth inequality only, not opportunity gaps or values/social
polarization. No numeric normalization curve is approved —
MONOTONIC_NEGATIVE direction confirmed, but "100 - share*100" is NOT an
approved mapping.

## DEC-029 — Initial force aggregation methodology

Date: 2026-09-10
Status: Accepted (Sprint 5.21)

### Decision

Sprint 5.21 defines when Atlas is allowed to turn normalized indicator
signals into force-level signals. This is methodology + typed
configuration only — no force calculation, no force persistence, no force
API.

**Permanent invariants:**

1. **Dimensions remain separate.** Force output preserves level_score,
   relative_score, momentum, and confidence as independent dimensions.
   No single "force score" that secretly mixes them. No `score *=
   confidence`, no `level *= coverage`.

2. **Coverage != strength.** Coverage status (AVAILABLE / PARTIAL /
   DEFINED_NOT_SOURCED / MISSING) does NOT numerically alter level_score.
   A force may have level_score = 82 with coverage = PARTIAL. Proxy
   ceilings remain completeness semantics, not numeric penalties.

3. **Missing != zero.** Missing or unapproved force dimensions are None,
   never 0. The credit-gap indicator's approved 50 (DEC-021) is an
   indicator-level meaning, not a generalizable missing-data rule.

4. **Only executable normalized signals may enter numeric aggregation.**
   Required layering: Observation → AlignedValue → NormalizedSignal →
   ForceSignal. Never Observation → ForceSignal. CONTEXTUAL_DEFERRED
   indicators contribute no numeric value.

**Indicator role taxonomy:**

- CORE_CONDITION — normalized 0-100 condition, higher = stronger, eligible
  for level aggregation under an approved rule.
- PROXY_CONDITION — same orientation but narrower proxy; requires PARTIAL
  ceiling semantics.
- VULNERABILITY_PENALTY — asymmetric vulnerability/risk; must NOT be naively
  averaged with CORE_CONDITION; requires a force-specific composition
  formula.
- SUPPORTING_CONTEXT — relevant context with no approved numeric
  contribution.

**Aggregation modes:**

- IDENTITY_SINGLE — the ONLY approved numeric aggregation. force.level_score
  = indicator.level_score for exactly one eligible component (CORE_CONDITION
  or PROXY_CONDITION). No rescaling, no weighting, no averaging. Transparent
  identity mapping.
- DEFERRED_MULTI — used whenever 2+ numeric components require composition,
  a vulnerability penalty must interact with a condition score, or weights
  are unresolved. Result: force dimension = None. No equal-weight fallback.

**Initial approved-force matrix (3 of 17):**

- Rule of law — IDENTITY_SINGLE, level + relative + momentum approved
  (CORE_CONDITION: RULE_OF_LAW_WGI_SCORE).
- Corruption — IDENTITY_SINGLE, level + relative + momentum approved
  (CORE_CONDITION: CONTROL_OF_CORRUPTION_WGI_SCORE).
- Internal conflict — IDENTITY_SINGLE, level + relative + momentum approved
  (PROXY_CONDITION: POLITICAL_STABILITY_WGI_SCORE). Coverage stays PARTIAL.

**Indebtedness deferral:** DEFERRED_MULTI. DSR (CORE_CONDITION) + credit gap
(VULNERABILITY_PENALTY) + government debt (SUPPORTING_CONTEXT) cannot be
naively averaged. No composition formula approved. No equal weights.

**Relative policy:** identity copy only, on approved single-WGI forces.
Copy entire provenance (reference_universe_id, expected/usable n, rank).
Never recompute ranks at force layer. Never average relative scores. Never
label tracked_8 as global.

**Momentum policy:** identity copy only, on approved single-WGI forces.
DEC-016: WGI momentum is WGI-scale-specific, not approved for cross-indicator
aggregation. Indebtedness momentum = None.

**Confidence policy:** None everywhere. DEC-023 deferred numeric WGI
confidence. No force-confidence numeric composition. Do not use
freshness_factor, coverage percentage, proxy ceiling, source quality
constants, or indicator counts as force confidence.

**Backtest safety:** False everywhere. Underlying indicator signals remain
CURRENT/RESEARCH, not release-date-safe. Force backtest_safe may only be
True if every contributing component is backtest-safe AND force methodology
is historically version-safe.

**Versioning:** two separate layers:
- Indicator normalization version: normalization-v0.6 (unchanged).
- Force aggregation version: force-aggregation-v0.1.

Not all 17 forces are scoreable. 3 of 17 approved for IDENTITY_SINGLE;
14 deferred.

### Sprint 5.22 implementation note (2026-09-10)

Sprint 5.22 implemented the first executable ForceSignal layer using ONLY
this methodology. No DEC-030 is created — the implementation faithfully
executes the already-approved v0.1 methodology, so force-aggregation-v0.1
remains the version (no bump).

- ForceSignal type: `app/cycle/force_signal.py` (non-persisted dataclass).
- Pure aggregator: `aggregate_force_from_signals` (IDENTITY_SINGLE copies
  level/relative/momentum exactly; DEFERRED_MULTI returns None with
  component provenance; SUPPORTING_CONTEXT never contributes numerically).
- Service: `build_force_signals_as_of` in
  `app/services/force_signal_service.py` (returns exactly 17 forces,
  calls normalize_indicator_as_of, coverage from existing service).
- Config hardening: live-input completeness guard, duplicate force-config
  detection, proxy-condition ceiling guard, dimension approval guard
  (relative/momentum identity_copy only on WGI x3).
- 3/17 forces executable (Rule of law, Corruption, Internal conflict proxy);
  14/17 intentionally None.
- No force persistence, no public force API.
- pytest 520 passed (476 baseline + 44 new).
- Live read-only smoke (2025-Q2, CHE/USA/CHN/IND): all 17 forces returned,
  3 identity forces have scores, Indebtedness coverage=available + level=None,
  internal_conflict stays PARTIAL, no writes.
- Milestone 5 COMPLETE: indicator normalization + first defensible executable
  force layer.

## DEC-030 — Indebtedness composition: DEFER_INDEBTEDNESS_COMPOSITION (government-debt normalization required first; no defensible penalty shape)

Date: 2026-09-10
Status: Accepted (Sprint 6.1 — methodology / empirical research sprint, NO implementation)

### Decision

Sprint 6.1 audited whether Atlas can defensibly produce an Indebtedness
`level_score` from the three live inputs (DSR CORE_CONDITION, credit-gap
VULNERABILITY_PENALTY, government-debt SUPPORTING_CONTEXT). The verdict is
**DEFER_INDEBTEDNESS_COMPOSITION** — a durable methodology decision, not a
postponement of an obvious answer. Atlas cannot yet defensibly compose an
Indebtedness force level_score.

The deferral rests on two blockers, both empirical (not assumed):

**Blocker 1 — Government-debt normalization is required first.** Government
debt/GDP is currently `CONTEXTUAL_DEFERRED`: no Atlas curve maps raw % GDP to
a 0-100 strength. The empirical profile (Sprint 6.1, read-only) shows
government-debt levels span 20% (CHN min) to 229% (JPN max) across tracked_8,
with latest values from 39% (CHE) to 214% (JPN). Any composition that
numerically ignores government debt while claiming to measure "Indebtedness"
would publish a force score that is silent about the single most
consequential stock measure of sovereign indebtedness — a country at 214%
debt/GDP (JPN) and a country at 39% (CHE) would receive Indebtedness scores
driven only by DSR flow-stress and credit-cycle vulnerability, with the
stock burden invisible. That is false precision: the score would look
complete but omit the dominant conceptual input.

  The counter-argument ("DSR already encodes debt-service burden, so
  government debt is redundant") fails empirically: JPN has the highest
  debt/GDP (214%) but a mid-range DSR level (41 — debt service is affordable
  at near-zero rates); CHE has low debt (39%) but high DSR stress (level 17
  — rate-driven, not stock-driven). DSR is a flow measure (interest +
  principal / income); government debt is a stock measure. They are not
  substitutes — they measure different temporal aspects of indebtedness.

**Blocker 2 — No defensible penalty-shape interaction between DSR (base
condition) and credit-gap (vulnerability penalty) is approved.** The five
candidate structures were evaluated (see Sprint 6.1 report §5); each either
introduces arbitrary parameters, mishandles the credit-gap neutral-50
semantics, or improperly ignores government debt. Specifically:

  - **A. Base-condition + capped vulnerability deduction**: requires an
    arbitrary cap parameter (e.g. "deduct at most 20 points") with no
    economic basis. The cap is a convenience constant, not a calibrated
    parameter.
  - **B. Multiplicative vulnerability dampener**: `level = DSR * (CG/50)`
    breaks when CG=50 (neutral): it leaves DSR unchanged, which is correct
    for the no-excess case, but when CG=0 (saturated excess) it zeroes the
    DSR score entirely — a country with low DSR stress but high credit-gap
    excess would get level=0, conflating "vulnerable" with "indebted."
    The 50-as-neutral semantics of DEC-021 are indicator-level, not a
    multiplicative base.
  - **C. Gate / regime rule**: "if CG < 50, force = DSR; else force = None"
    requires an arbitrary threshold and discards the credit-gap signal
    magnitude. A gate is a binary regime classification, not a level score.
  - **D. Worst-component / minimum rule**: `level = min(DSR, CG)` treats
    credit-gap 50 (neutral no-excess) as a strength of 50, which would cap
    every no-excess country at 50 — false precision (neutral is not
    mid-strength).
  - **E. DEFER_COMPOSITION** (this verdict): honest. Force level stays
    None. Component signals remain as provenance. No arbitrary parameters.
    No false precision.

No equal weighting is considered (DEC-029 prohibition). No constants are
chosen for convenience.

### Missingness policy (would apply IF a composition were approved)

For the record, the missingness policy analysis (Sprint 6.1 §6) concludes
that any future composition must preserve:
- **missing != zero**: DSR missing → no base condition → force level None
  (not a credit-gap-only score). Credit-gap missing → no vulnerability
  penalty → force level None (DSR alone is a flow measure, not the force).
  Government-debt missing → no stock context → force level None (the
  dominant stock input is invisible). A composition requires ALL THREE
  present; any missing component makes the force unscored, not partially
  scored.
- **coverage != strength** (permanent invariant, DEC-029 §1.2): coverage
  status measures DATA AVAILABILITY only and does NOT numerically alter
  level_score. If DSR + credit-gap + government-debt observations are ALL
  available, coverage_status MAY remain AVAILABLE even while
  force.level_score = None — because force aggregation / government-debt
  normalization is unresolved. Coverage != normalization readiness. No
  coverage ceiling is added to Indebtedness. This is a wording/methodology
  correction only; force_coverage_service behavior is unchanged.
- **confidence separate**: force confidence stays None (DEC-023).
- **momentum separate**: Indebtedness momentum stays None (DEC-029).

### Empirical tracked_8 findings (read-only, 2025-Q2)

| Country | DSR level | CG level | GovDebt% | DSR<50 | CG<50 |
|---|---|---|---|---|---|
| USA | 94.1 | 50.0 | 123.9 | no | no |
| CHN | 1.0 | 50.0 | 90.4 | YES | no |
| CHE | 16.7 | 50.0 | 39.4 | YES | no |
| DEU | 78.9 | 50.0 | 62.9 | no | no |
| FRA | 6.4 | 50.0 | 113.2 | YES | no |
| GBR | 99.5 | 50.0 | 102.3 | no | no |
| JPN | 41.2 | 35.9 | 214.5 | YES | YES |
| IND | 49.0 | 50.0 | 84.1 | YES | no |

Key observations:
- Credit-gap excess (CG<50) is RARE in the current snapshot: only JPN
  (level 35.9). 7 of 8 countries are at neutral 50. A composition that
  weights credit gap heavily would be near-identity to DSR for 7/8
  countries today — the credit-gap signal rarely activates.
- DSR stress (level<50) and credit-gap excess (level<50) rarely co-occur
  in the historical sample: only JPN shows both simultaneously (2022-Q1,
  2024-Q1, 2025-Q2). CHE and FRA show DSR stress + credit-gap excess in
  2020-Q1 / 2022-Q1 but not recently. The two signals are largely
  orthogonal in practice — which means a composition formula would need
  to define behavior for the common case (one signal active, one neutral),
  not just the rare co-occurrence.
- Government debt spans 20%–229% — a 10x range. JPN (214%) and CHE (39%)
  have similar DSR stress levels (41 vs 17) but wildly different debt
  stocks. Any composition ignoring government debt is dominated by the
  flow measure and silent on the stock.

### Government-debt-normalization dependency

**Government-debt normalization is a hard prerequisite, not optional.**
The empirical profile shows government debt is the dominant
differentiator when DSR is similar. Without an Atlas curve mapping
raw % GDP to a 0-100 strength, any Indebtedness composition would be a
two-input (DSR + credit gap) formula masquerading as a three-input force.

The government-debt normalization itself faces the same DEC-018 audit
hurdle that reclassified GDP_GROWTH, GCF, INFLATION_CPI, and
UNIT_LABOUR_COST_GROWTH to CONTEXTUAL_DEFERRED: there is no universal
"healthy" debt/GDP level. Japan functions at 214%; the EU Maastricht
reference is 60%; emerging markets face different constraints than
advanced economies. A universal band would encode arbitrary norms. A
country-specific own-history approach (like DSR's DEC-019) is a
candidate but requires its own DEC and owner approval — it is NOT
inferred from the DSR methodology.

### Reason

DEC-029 deferred Indebtedness because "DSR + credit gap + government debt
cannot be naively averaged." Sprint 6.1 tested whether a NON-naive
composition could be defensible. The audit found that every candidate
structure either (a) requires arbitrary parameters with no economic
basis, (b) mishandles the credit-gap neutral-50 semantics, or (c)
improperly ignores government debt — the dominant stock measure. The
deferral is therefore not "we have not tried" but "we tried, and the
honest answer is that government-debt normalization must be solved
first, and even then the DSR × credit-gap interaction shape needs an
explicit owner-approved formula, not a convenient default."

### Impact

NO production code changed. NO force code changes. NO phase, cycle
composite, force confidence, relative aggregation, momentum aggregation,
persistence, API, or frontend. Model versions unchanged:
`normalization-v0.6`, `force-aggregation-v0.1`. Indebtedness stays
`DEFERRED_MULTI` with `level_score = None`. Provenance layering preserved
(required: Observation → AlignedValue → NormalizedSignal → ForceSignal —
never Observation → ForceSignal): the DSR NormalizedSignal is preserved;
the credit-gap NormalizedSignal is preserved; GOVERNMENT_DEBT_GDP is
recorded as a deferred/supporting component (its raw value was used only
in Sprint-6.1 read-only research, never carried as a raw Observation into
ForceSignal). Read-only empirical profile script
(`scripts/sprint_6_1_indebtedness_profile.py`) was used during the sprint
and removed after — no persistent artifact.

### Recommended Sprint 6.2

**Sprint 6.2 — Government-debt normalization methodology audit.** Decide
whether GOVERNMENT_DEBT_GDP can receive a defensible Atlas level curve.
Candidates to evaluate: (a) own-history approach (DEC-019 analog — a
country's debt/GDP relative to its own history, no universal band); (b)
structural-break-aware level (debt/GDP regimes differ across eras); (c)
defer (no curve — CONTEXTUAL_DEFERRED stays). If (a) or (b) is approved,
Sprint 6.3 would then revisit the DSR × credit-gap × government-debt
composition with all three inputs normalized. If (c), Indebtedness
remains DEFERRED_MULTI indefinitely unless a non-debt-based composition
is proposed.

Deliberately NOT queued in 6.2: DSR × credit-gap composition without
government debt (would publish a two-input score masquerading as the
force), equal weights, arbitrary caps, multiplicative dampeners,
gate/regime rules, worst-component rules.

### Sprint 6.2 wording corrections (2026-09-10)

Sprint 6.2 corrected two wording errors in the original DEC-030 text
above (methodology/wording only — no score or coverage semantics in code
changed, no force_coverage_service behavior modified, no coverage ceiling
added to Indebtedness):

1. **Coverage semantics corrected.** The original "Missingness policy"
   section said a force with all three components present but
   government-debt normalization unapproved is "conceptually PARTIAL."
   This was WRONG. The permanent invariant (DEC-029 §1.2: coverage !=
   strength, coverage != normalization readiness) means: if DSR +
   credit-gap + government-debt observations are all available,
   coverage_status MAY remain AVAILABLE even while force.level_score =
   None. Coverage measures data availability; it does not measure
   normalization readiness or force-score eligibility. No coverage
   ceiling is added to Indebtedness.

2. **Provenance wording corrected.** The original "Impact" section said
   "government debt raw" remains in ForceSignal provenance. The current
   production architecture does NOT carry a raw Observation directly into
   ForceSignal. Corrected: the DSR NormalizedSignal is preserved; the
   credit-gap NormalizedSignal is preserved; GOVERNMENT_DEBT_GDP is
   recorded as a deferred/supporting component; its raw value was used
   only in Sprint-6.1 read-only research. The required layering
   (Observation → AlignedValue → NormalizedSignal → ForceSignal) is never
   violated.

## DEC-031 — Government-debt normalization: DEFER_GOVERNMENT_DEBT_LEVEL (no defensible level curve from debt/GDP alone)

Date: 2026-09-10
Status: Accepted (Sprint 6.2 — methodology / research only, NO implementation)

### Decision

Sprint 6.2 audited whether `GOVERNMENT_DEBT_GDP` (IMF WEO
`GGXWDG_NGDP`, general-government gross debt as % of GDP) can receive a
defensible Atlas 0-100 level_score. The verdict is
**DEFER_GOVERNMENT_DEBT_LEVEL** — a durable methodology decision, not a
postponement of an obvious answer.

`GOVERNMENT_DEBT_GDP` stays `CONTEXTUAL_DEFERRED` (level_family in the
registry unchanged). No level curve is approved. No `own_history_level_configs`
or `one_sided_vulnerability_configs` entry is added. Model versions
unchanged: `normalization-v0.6`, `force-aggregation-v0.1`. Indebtedness
stays `DEFERRED_MULTI` with `level_score = None`. No production score
code changed. No DB writes. No migrations.

### The durable blocker

**No defensible semantic target exists for a government-debt/GDP LEVEL
signal that is (a) cross-country comparable, (b) composable with DSR
(OWN_HISTORY flow-stress) and credit gap (ONE_SIDED_VULNERABILITY excess-
credit), and (c) implementable from data currently in the Atlas.**

The blocker is durable because it is structural, not a matter of tuning
parameters. Each candidate semantic family was audited against the
official-source evidence and the empirical tracked_8 profile; none
satisfies all three requirements simultaneously.

### Official-source evidence (primary)

1. **IMF (2011, "Modernizing the Framework for Fiscal Policy and Public
   Debt Sustainability Analysis")** — "The paper does not find a sound
   basis for integrating specific sustainability thresholds into the DSA
   framework. However, based on recent empirical evidence, it suggests
   that a reference point for public debt of 60 percent of GDP be used
   flexibly to trigger deeper analysis for market-access countries: the
   presence of other vulnerabilities would call for in-depth analysis
   even for countries where debt is below the reference point." The 60%
   figure is a TRIGGER for deeper analysis, NOT a universal strength
   boundary.

2. **IMF (2013, "Staff Guidance Note for Public Debt Sustainability
   Analysis in Market-Access Countries")** — Triggers for deeper
   analysis: 60% debt/GDP for advanced economies, 50% for emerging
   markets (reduced ~15% from the early-warning model estimates "to be
   conservative"). These are TRIGGERS, not thresholds. They differ by
   WEO classification (AE vs EM).

3. **IMF (2022, SRDSF — Sovereign Risk and Debt Sustainability
   Framework for Market Access Countries)** — Replaces the MAC DSA. Uses
   a multivariate logit model predicting sovereign stress over 1-2
   years, a debt fanchart, rollover-risk modules, and triggered stress-
   tests. Risk is divided into low/moderate/high zones calibrated by
   false-alarm and missed-crisis probabilities (10% each), NOT by a
   universal debt/GDP threshold. The framework is explicitly
   multivariate: debt level, gross financing needs, debt profile
   (maturity, currency, investor base), and country-specific risks all
   enter. "The framework does not in fact use binary decision rules."

4. **EU Maastricht Treaty (Protocol on the Excessive Deficit
   Procedure)** — 60% debt/GDP reference value. Applies to EU member
   states with a shared monetary/institutional framework. The treaty
   language explicitly allows the ratio to exceed 60% if "the ratio is
   sufficiently diminishing and approaching the reference value at a
   satisfactory pace" — i.e., it is a convergence/fiscal-rule criterion,
   not a universal strength boundary. "Debt" = total gross debt at
   nominal value, consolidated within general government.

5. **World Bank (2010, Caner et al., WPS5391)** — Found a growth-
   threshold of 77% (full sample) / 64% (developing economies). The
   threshold "differs substantially for developing and developed
   economies" — i.e., NOT universal. This is a growth-effect finding,
   not a sustainability threshold.

6. **World Bank (2018, "Debt Intolerance")** — Thresholds depend on
   debt COMPOSITION (foreign private holdings share): the marginal
   impact of debt on interest rates rises non-linearly once foreign
   private holdings exceed ~20% of local-currency debt AND debt/GDP
   exceeds ~60%. The threshold is conditional, not universal.

7. **Reinhart & Rogoff (2010) — 90% threshold** — Debunked by Herndon,
   Ash & Pollin (2013): coding errors, selective exclusion,
   unconventional weighting. Corrected mean growth above 90% is +2.2%,
   not -0.1%. "The relationship between public debt and GDP growth
   varies significantly by period and country."

8. **IMF (2014, "No Magic Threshold", Finance & Development)** — "We
   found little evidence that there is any particular debt ratio above
   which growth falls sharply."

**Synthesis:** No official source supports a universal debt/GDP
threshold for cross-country strength comparison. The IMF explicitly
states "no sound basis for specific sustainability thresholds." The
60% Maastricht reference is a fiscal-rule convergence criterion for EU
member states. The 90% Reinhart-Rogoff threshold was debunked. The IMF
SRDSF uses multivariate risk bands, not a single debt/GDP threshold.
Debt sustainability depends on interest rates, growth, monetary
sovereignty, currency composition, maturity, investor base, and fiscal
capacity — none of which is captured by debt/GDP alone.

### Candidate semantic families audited

**A. OWN_HISTORY_STRESS (DEC-019 analog) — NOT a defensible LEVEL.**
- Semantic: "Where does the country's current debt/GDP sit relative to
  its own historical distribution?"
- This is a TREND/REGIME-POSITION signal, not an absolute stock-burden
  level. It measures deterioration relative to own past, not the stock
  burden itself.
- Empirical counterfactual (Sprint 6.2, read-only): JPN at 214.5% gets
  hypothetical own-history level 10 (near its own max). But if JPN's
  debt dropped to 130% (below its median of 134.6), it would get a
  STRONG own-history score despite 130% debt/GDP — one of the highest
  in the world. The score would say "improving" while the level remains
  extreme.
- Semantically DIFFERENT from DSR's own-history: DSR is a FLOW (annual
  service cost), so the own-history position IS the burden. Government
  debt is a STOCK; the own-history position measures trajectory, not
  burden.
- Cross-country comparability: NONE. A score of 80 for JPN (if it
  dropped below its median) and 80 for CHE (at 39%) would mean
  completely different things.
- Composability with DSR + credit gap: INCOMPATIBLE. Would introduce a
  third semantic (own-history trajectory of a stock) alongside DSR
  (own-history position of a flow) and credit gap (excess-credit
  vulnerability).
- Midpoint 50: no defensible meaning (median position in own history
  is a trend signal, not a level).
- Verdict: Could be a MOMENTUM candidate (debt rising relative to own
  history), but NOT a LEVEL.

**B. ABSOLUTE_FISCAL_BURDEN (monotonic: higher debt = weaker) — NOT
defensible.**
- Semantic: "Higher government debt/GDP = greater absolute fiscal
  burden = weaker."
- No official source supports a universal monotonic curve. IMF: "no
  sound basis for specific sustainability thresholds." JPN has
  sustained 214% for decades without crisis; IND at 84% faces
  different constraints.
- Structural-regime sensitivity: EXTREME. Monetary sovereignty,
  currency composition, maturity, investor base, growth, interest
  rates all alter debt tolerance.
- Midpoint 50: no defensible meaning.
- Verdict: Would encode arbitrary norms.

**C. CROSS_SECTIONAL_LEVEL (rank within tracked_8 or broader) — NOT a
LEVEL signal.**
- Semantic: "Where does the country's debt/GDP rank relative to peers?"
- This is a RELATIVE dimension, not a LEVEL. The registry already has
  relative_family = CONTEXTUAL_DEFERRED for government debt.
- tracked_8 is explicitly prohibited as a global calibration universe
  (DEC-018). A broader universe would require a new ReferenceUniverse
  and its own DEC.
- Composability: would introduce a relative-position semantic
  incompatible with DSR (own-history) and credit gap (vulnerability).
- Verdict: NOT a LEVEL. A future relative dimension would need its
  own DEC and universe.

**D. STRUCTURAL_BREAK_AWARE (regime-segmented level) — NOT
implementable in this sprint.**
- Semantic: "Debt/GDP level interpreted within the country's current
  regime segment."
- Requires a structural-break detection method (e.g., Bai-Perron) or
  external regime classification — neither is available.
- Still measures "position within current regime," not "absolute
  stock burden." Cross-country comparability: NONE.
- Verdict: NOT defensible as a LEVEL signal without additional
  methodology not available.

**E. SUSTAINABILITY/CAPACITY-ADJUSTED (multivariate) — the CORRECT
approach, NOT implementable in this sprint.**
- Semantic: "Debt/GDP adjusted for interest rates, growth, monetary
  sovereignty, currency composition, maturity, fiscal capacity."
- This is the IMF SRDSF approach: multivariate risk assessment.
- Required data NOT all available: no interest rates, no currency
  composition, no maturity profile, no fiscal capacity, no monetary-
  sovereignty classification in the current Atlas.
- Cross-country comparability: YES (the adjustment makes it
  comparable). Composability: would be a LEVEL signal, potentially
  composable.
- Verdict: The correct long-term approach. Requires additional data
  ingestion and a multivariate model beyond Sprint 6.2's scope.

**F. CONTEXTUAL_DEFERRED (no curve) — the only defensible current
state.**
- No level_score. No false precision. Government debt remains a
  deferred/supporting component.
- Verdict: ACCEPTED.

### Empirical tracked_8 profile (Sprint 6.2, read-only)

Per-country government-debt/GDP (latest vintage, IMF WEO
GGXWDG_NGDP):

| Country | n | earliest | latest | min | median | max | current |
|---|---:|---|---|---:|---:|---:|---:|
| USA | 25 | 2001 | 2025 | 53.5 | 104.9 | 132.6 | 123.9 |
| CHN | 30 | 1995 | 2024 | 20.4 | 33.3 | 90.4 | 90.4 |
| CHE | 36 | 1990 | 2025 | 32.8 | 42.1 | 57.1 | 39.4 |
| DEU | 35 | 1991 | 2025 | 39.0 | 63.3 | 81.0 | 62.9 |
| FRA | 45 | 1980 | 2024 | 21.3 | 62.1 | 114.9 | 113.2 |
| GBR | 46 | 1980 | 2025 | 28.4 | 43.0 | 104.8 | 102.3 |
| JPN | 45 | 1980 | 2024 | 41.4 | 134.6 | 228.8 | 214.5 |
| IND | 35 | 1991 | 2025 | 67.1 | 74.9 | 90.6 | 84.1 |

Pooled (297 obs): min 20.4, p25 41.9, median 64.2, p75 85.6, max 228.8.

Historical snapshot cross-sections (as-of, no future leakage):

| Year | min | median | max |
|---|---:|---:|---:|
| 2005 | 25.9 | 66.5 | 153.4 |
| 2010 | 33.3 | 78.3 | 178.6 |
| 2015 | 40.8 | 79.3 | 200.1 |
| 2020 | 42.4 | 97.7 | 228.8 |
| 2025 | 39.4 | 96.4 | 214.5 |

Key observations:
- Government debt spans 20%–229% across tracked_8 — a 10x range.
- JPN sustained debt/GDP >200% for an extended period, demonstrating
  that debt/GDP alone does not mechanically imply a universal distress
  threshold (the debt profile itself contains no sovereign-distress
  outcome data; no causal claim is made).
- CHN rose from 20.4% (1995) to 90.4% (2024) — a 4.4x increase, but
  still below JPN's 1990 starting point.
- CHE remains low (39.4%) but its DSR stress is high (level 16.7) —
  rate-driven, not stock-driven. This confirms DSR (flow) and
  government debt (stock) are not substitutes.
- The tracked_8 cross-sectional median rose from 66.5% (2005) to
  96.4% (2025) — a tracked_8 cross-sectional trend. Any absolute
  threshold would shift meaning over time. (tracked_8 is not a global
  universe; this is a tracked_8 cross-sectional observation, not a
  world trend.)

### Own-history counterfactual (RESEARCH ONLY, not a published signal)

DEC-019-style mid-rank stress position applied to government debt
(higher debt = more stress = weaker, same inversion as DSR):

| Country | n | current | own-history rank | stress_pct | hypothetical level |
|---|---:|---:|---:|---:|---:|
| JPN | 45 | 214.5 | 41/45 | 90.0 | 10.0 |
| CHE | 36 | 39.4 | 8/36 | 20.8 | 79.2 |
| USA | 25 | 123.9 | 23/25 | 90.0 | 10.0 |
| CHN | 30 | 90.4 | 30/30 | 98.3 | 1.7 |
| FRA | 45 | 113.2 | 44/45 | 96.7 | 3.3 |

The counterfactual illustrates why own-history is NOT a level:
- JPN and USA both get level 10 — but JPN is at 214% and USA at 124%.
  The score conflates two very different absolute burdens.
- CHN gets level 1.7 (worst) because 90.4% is its all-time high. But
  90.4% is below JPN's 1990 starting point (50.8%... actually JPN's
  1980 value was 41.4%). The score says "CHN is the most stressed"
  because it measures trajectory, not burden.
- If JPN's debt fell to 130% (below its median), it would get a strong
  own-history score despite 130% debt/GDP — one of the highest in the
  world. The score would say "improving" while the level remains
  extreme.

This confirms candidate A is a trend signal, not a level signal.

### Relation to DSR + credit gap composability

DSR (CORE_CONDITION, OWN_HISTORY): current debt-service FLOW burden
relative to own history. Higher DSR = weaker. Level = 100 - stress
percentile.

Credit gap (VULNERABILITY_PENALTY, ONE_SIDED_VULNERABILITY): excess-
credit vulnerability. Positive gap above +2pp = vulnerability. Neutral
50 = no excess (NOT strength).

Government debt (SUPPORTING_CONTEXT, currently CONTEXTUAL_DEFERRED):
stock of sovereign debt as % of GDP.

For government debt to be composable with DSR + credit gap, it would
need a LEVEL semantic that:
1. Is cross-country comparable (so the same score means the same
   burden).
2. Shares the "higher = weaker" orientation (or is explicitly a
   vulnerability penalty with its own composition formula).
3. Has a defensible midpoint (50 = ?).

None of the candidate families satisfy all three:
- A (own-history): not cross-country comparable; 50 = median-of-own-
  history (trend, not level).
- B (absolute): no defensible curve; 50 = ? (no official threshold).
- C (cross-sectional): relative, not level; 50 = median of a
  prohibited universe.
- D (structural-break): not cross-country comparable.
- E (sustainability-adjusted): would satisfy all three, but requires
  data not in the Atlas.

Therefore, even if a government-debt level curve were approved, it
would NOT be automatically composable with DSR + credit gap. A
separate composition DEC would still be required (DEC-030 Blocker 2
remains).

### Missingness and coverage boundary

This sprint does NOT generalize DEC-030's "all three required"
composition rule. Missingness policy for a FUTURE composition is a
force-methodology decision, not a coverage decision.

Coverage boundary (preserved from DEC-029 §1.2 and the Sprint 6.2
correction to DEC-030):
- coverage_status = data availability. If DSR + credit-gap + government-
  debt observations are all available, coverage MAY be AVAILABLE.
- level_score = None is consistent with coverage = AVAILABLE when
  normalization/aggregation is unresolved.
- A missing government-debt observation may eventually block a
  particular composition formula, but that is a force-methodology
  decision, not a coverage redefinition.
- No coverage ceiling is added to Indebtedness.

### Impact

NO production code changed. NO force code changes. NO normalization
code changes. NO phase, cycle composite, force confidence, relative
aggregation, momentum aggregation, persistence, API, or frontend.
Model versions unchanged: `normalization-v0.6`, `force-aggregation-v0.1`.
Indebtedness stays `DEFERRED_MULTI` with `level_score = None`.
`GOVERNMENT_DEBT_GDP` stays `CONTEXTUAL_DEFERRED` in the registry.
confidence = None. backtest_safe = False.

Read-only empirical profile script
(`scripts/gov_debt_profile.py`) was used during the sprint and remains
as a research artifact (it produces no scores, writes nothing, and is
clearly labeled as research support).

### Reason

DEC-030 deferred Indebtedness composition because government-debt
normalization was a hard prerequisite. Sprint 6.2 audited whether that
prerequisite can be met. The audit found that it CANNOT be met from
debt/GDP alone: no official source supports a universal threshold, and
the candidates that avoid a universal threshold (own-history,
structural-break) produce trend/regime signals, not level signals. The
correct approach (sustainability-adjusted, multivariate) requires
additional data not in the Atlas. The deferral is therefore durable
until either (a) additional data is ingested to support a
sustainability-adjusted measure, or (b) a non-level semantic (e.g.,
government-debt momentum) is proposed and approved in a future DEC.

### Recommended Sprint 6.3

**Sprint 6.3 — Government-debt momentum candidate audit (smallest
useful next sprint).** Since a LEVEL curve is deferred but government
debt is live, audit whether a MOMENTUM signal (debt/GDP change relative
to own history, DEC-016 analog) is defensible. Momentum is a trend
signal, which is what own-history actually measures (candidate A
reclassified from level to momentum). This would NOT enable
Indebtedness composition (still DEFERRED_MULTI), but it would make
government debt useful as a non-level signal and inform future
composition. If momentum is also not defensible, the next option is
to ingest additional data (interest rates, growth, monetary
sovereignty) for a future sustainability-adjusted level (candidate E).

Deliberately NOT queued in 6.3: government-debt level implementation
(blocked by DEC-031), Indebtedness composition (still deferred),
force-aggregation-v0.2, normalization-v0.7, DSR momentum, credit-gap
momentum, force confidence, phase/stage, cycle composites, API,
frontend, persistence, backtesting, trading.

## DEC-032 — Education level: READY_FOR_EDUCATION_LEVEL_DESIGN (DIRECT_0_100 identity for TERTIARY_ATTAINMENT_25_34; PROXY_CONDITION + IDENTITY_SINGLE eligible for the Education force)

Date: 2026-09-10
Status: Accepted (Sprint 6.3 — methodology / research only, NO implementation)

### Decision

Sprint 6.3 audited whether `TERTIARY_ATTAINMENT_25_34` (OECD EAG LSO
NEAC, age 25-34, ISCED 5-8, % of population in same sex and age) can
receive a defensible Atlas 0-100 level_score and, if so, whether the
Education force may become the fourth executable force through
PROXY_CONDITION + IDENTITY_SINGLE. The verdict is
**READY_FOR_EDUCATION_LEVEL_DESIGN**. A defensible LEVEL semantic
exists; Sprint 6.4 MAY implement it (subject to the conditions below).
Sprint 6.3 itself implements NOTHING and changes NO model version.

### The semantic target

`TERTIARY_ATTAINMENT_25_34` measures exactly one concept: the share of
the 25-34 year-old population that has successfully completed ISCED
2011 levels 5-8 (short-cycle tertiary, bachelor's, master's, doctoral
or equivalent). The OECD defines this precisely (Education at a Glance
2025, Sources/Methodologies/Technical Notes; OECD dataflow
`DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA` v1.0):

- **Denominator**: total population in the same sex and age group
  (`UNIT_MEASURE=PT_POP_SEX_AGE`).
- **Numerator**: individuals whose highest successfully completed
  education level is ISCED 2011 5-8.
- **Age 25-34 rationale**: the OECD explicitly uses 25-34 as the
  "younger adults" cohort because it represents recent cohorts and is
  more responsive to the current education system than 25-64 (DEC-026
  confirmed this choice).
- **Attainment, not enrollment**: a stock measure of completed
  qualifications, not a flow measure of current participation
  (DEC-007 honored).

The indicator does NOT measure: overall education quality, school-
system performance, literacy, test scores (PIAAC), secondary completion,
skills quality, older cohorts, or human-capital quality generally.
Any force use is therefore a PROXY. Education coverage MUST stay
PARTIAL (DEC-009, DEC-026).

### Why DIRECT_0_100 is defensible here (and NOT just because the range is 0-100)

The provider value is a percentage 0-100, but numeric-range matching
alone does NOT justify `level_score = raw percentage` (Sprint 6.3 Part
2). DIRECT_0_100 is defensible here because the semantic meaning of
the raw value IS the level signal:

1. **The raw percentage has an absolute, cross-country comparable
   meaning.** 50% tertiary attainment means 50% of the 25-34
   population has completed ISCED 5-8 — this statement is true in the
   USA, in IND, in JPN, and in any OECD dataflow country, using the
   same ISCED 2011 classification and the same denominator definition.
   The OECD itself uses this indicator for cross-country level
   comparison (Education at a Glance Chapter A1, "To what level have
   adults studied?"; the OECD data dashboard "Population with tertiary
   education"). The comparability is not perfect (see "Comparability
   limits" below) but it is the OECD's intended use.

2. **Higher = stronger is defensible.** More tertiary attainment means
   a more educated young-adult cohort. The OECD frames rising tertiary
   attainment as a positive trend ("educational attainment is at an
   all-time high, with 48% of young adults in OECD countries now
   completing tertiary education"). The Atlas direction
   `MONOTONIC_POSITIVE` (already in the registry) is correct.

3. **No arbitrary threshold or curve is invented.** DIRECT_0_100 means
   `level_score = raw value` — no breakpoints, no bands, no caps, no
   rescaling. This is the same family as the WGI x3 (Sprint 5.6), where
   the provider's fixed 0-100 scale IS the level signal. The OECD
   percentage IS the level signal for the same reason: the provider
   designed the scale to be the indicator.

4. **Midpoint meaning is defensible.** 50 = "half of the 25-34
   population has tertiary attainment." This is a meaningful,
   interpretable statement — unlike the government-debt case where no
   official source supports a universal 50% threshold. The OECD does
   NOT endorse 50% as a policy target (see "No official benchmark"
   below), but 50 has a clear semantic meaning as a population share.

5. **This is NOT the government-debt case.** DEC-031 deferred
   government-debt because no official source supports a universal
   debt/GDP threshold and the raw ratio does not have a defensible
   cross-country level meaning (JPN at 214% is not "weaker" than IND
   at 84% in any simple sense). Tertiary attainment is different: the
   OECD itself uses the raw percentage for cross-country level
   comparison, the scale is bounded 0-100 by construction, and higher
   unambiguously means more educated.

### No official benchmark / target percentage

The OECD does NOT publish a target or benchmark percentage for
tertiary attainment. The OECD reports the OECD average (48% of 25-34
year-olds in 2024) as a descriptive statistic, NOT as a normative
target. No Education-at-a-Glance chapter endorses a specific
percentage as "strong" or "healthy." Therefore:

- DIRECT_0_100 does NOT encode an OECD-endorsed target. It preserves
  the raw population share as the level signal.
- A future FIXED_MONOTONIC_CURVE with externally-justified thresholds
  would require an official benchmark that does not exist today.
- The absence of a benchmark does NOT block DIRECT_0_100, because
  DIRECT_0_100 does not invent one — it uses the raw value as-is.

### Comparability limits (documented, not blocking)

The OECD itself notes comparability caveats (Education at a Glance
Sources/Methodologies/Technical Notes):

- **ISCED mapping**: a formal education programme in one country
  could occasionally be classified differently in another. The OECD
  provides ISCED mapping tables per country (Table X3.A1.1) to
  minimize this.
- **ISCED-97 vs ISCED-2011 break**: trend data before 2013 on ISCED 5
  and above are no longer reliable for some countries due to the
  classification change. The Atlas ingests the current ISCED 2011
  dataflow; historical observations before the break carry the
  classification as published.
- **Country methodology differences**: some countries include people
  without formal education under ISCED 0; GCSE equivalencies in the
  UK are mapped to ISCED 3 completion. These are documented by the
  OECD and do not invalidate the cross-country level comparison.

These limits are real but do NOT rise to the level of blocking
DIRECT_0_100. The OECD itself considers the indicator cross-country
comparable enough for its flagship cross-country comparison publication.
The Atlas carries the same comparability caveat as the OECD.

### Empirical tracked_8 profile (read-only, 200 obs)

Per-country TERTIARY_ATTAINMENT_25_34 (latest vintage, OECD):

| Country | n | earliest | latest | min | median | max | current |
|---|---:|---|---|---:|---:|---:|---:|
| USA | 35 | 1990 | 2025 | 23.76 | 40.39 | 52.77 | 52.77 |
| CHN | 1 | 2010 | 2010 | 17.95 | 17.95 | 17.95 | 17.95 |
| CHE | 33 | 1991 | 2025 | 21.26 | 38.02 | 52.97 | 50.60 |
| DEU | 33 | 1991 | 2025 | 20.34 | 25.66 | 40.88 | 40.88 |
| FRA | 32 | 1991 | 2024 | 20.08 | 42.16 | 53.35 | 53.35 |
| GBR | 29 | 1997 | 2025 | 24.68 | 46.91 | 61.19 | 61.19 |
| JPN | 29 | 1997 | 2025 | 45.74 | 58.37 | 67.53 | 67.53 |
| IND | 8 | 2011 | 2023 | 9.64 | 20.31 | 23.10 | 23.10 |

Pooled (200 obs): min 9.64, p25 28.94, median 40.18, p75 50.29, max 67.53.

Key observations:
- The tracked_8 range (9.6% IND to 67.5% JPN) is wide but each value
  has the same absolute meaning (share of 25-34 population with ISCED
  5-8).
- JPN (67.5%) and GBR (61.2%) are high; IND (23.1%) and CHN (17.95%,
  single observation) are low. The raw percentages are directly
  comparable as population shares.
- The OECD dataflow average for 25-34 year-olds in 2024 is ~48%; the
  tracked_8 median (40.2%) is below the OECD average, reflecting the
  inclusion of CHN and IND (large non-OECD economies with low
  attainment).

### Sparsity and its consequences

- **CHN: n=1 (2010 only).** EXTREMELY SPARSE. A DIRECT_0_100 level
  score CAN be produced for the 2010 snapshot (the raw value 17.95%
  is a valid level signal for that year), but NO momentum is possible
  and the value is extremely stale by 2025 (15 years old). Freshness
  policy will gate the current snapshot — CHN will likely return None
  for any scoring period well after 2010. This is correct behavior:
  missing != zero, and stale != current.
- **IND: n=8 (2011-2023).** SPARSE. A DIRECT_0_100 level score CAN be
  produced for snapshots where IND has an eligible observation.
  Momentum is possible in principle but unreliable with 8 points;
  Sprint 6.3 does NOT approve momentum (see Part 9).
- **6 of 8 countries (USA, CHE, DEU, FRA, GBR, JPN)** have 29-35
  annual observations — adequate for level and momentum candidates.

Sparsity affects level eligibility ONLY through freshness (a stale
observation is gated, not zeroed). It does NOT block the DIRECT_0_100
family itself. It affects momentum eligibility separately (Part 9).
It affects force publication through the PARTIAL coverage ceiling
(DEC-009), which is a coverage/status semantic, NOT a numeric
modification of the level_score.

### Broader OECD dataflow universe (read-only external SDMX fetch)

The OECD dataflow `DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA` v1.0 contains
**51 economies** (not just OECD member states — some non-OECD
countries participate), year span 1981-2025. The latest cross-section
(2025) has n=40 economies, min 7.0%, median 45.0%, max 71.1%. The
universe composition grew from 15 economies (1980s) to 51 (2010s).

This is the **OECD/dataflow universe** — NOT tracked_8, and NOT
world/global. tracked_8 (8 countries) is a frozen subset. The dataflow
universe is broader but still not global (it excludes many
developing economies outside the OECD education dataflow).

A CROSS_SECTIONAL_RELATIVE score within the OECD dataflow universe is
a RELATIVE dimension, not a LEVEL — it would answer "where does this
country rank among dataflow participants," not "what is the absolute
attainment share." DIRECT_0_100 answers the level question directly.
A future relative dimension would need its own approved
reference-universe methodology (Part 9).

### Candidate normalization methods audited

| Family | Semantic | Cross-country comparable | Defensible midpoint | CHN/IND sparsity | Result type | Verdict |
|---|---|---|---|---|---|---|
| A. RAW_PERCENT_IDENTITY (DIRECT_0_100) | share of 25-34 pop with ISCED 5-8 | YES (OECD-designed) | YES (50 = half the cohort) | level OK; momentum gated by freshness | LEVEL | **DEFENSIBLE — selected** |
| B. FIXED_MONOTONIC_CURVE | externally-justified thresholds | would be | would need benchmark | same | LEVEL | NOT defensible — no official benchmark exists |
| C. SAME-YEAR OECD/DATAFLOW CROSS-SECTION | relative position | mechanically | median of dataflow | same | RELATIVE | NOT a LEVEL — belongs in relative_score |
| D. EXPANDING BROADER-UNIVERSE CALIBRATION | percentile in expanding universe | mechanically | n/a | same | RELATIVE | NOT a LEVEL — relative dimension |
| E. OWN_HISTORY | progress vs own past | NO (each country's own history differs) | NO | CHN n=1 impossible | MOMENTUM | NOT a LEVEL — momentum candidate |
| F. CONTEXTUAL_DEFERRED | none | n/a | n/a | n/a | none | Rejected — a defensible LEVEL exists (A) |

### Absolute vs relative (Part 7)

DIRECT_0_100 is a LEVEL signal, not a RELATIVE signal:
- It answers "what share of the 25-34 population has tertiary
  attainment" — an absolute, interpretable statement.
- It does NOT answer "where does this country rank" — that is a
  relative question for a future relative_score dimension.
- It does NOT answer "is this country improving" — that is a momentum
  question for a future momentum dimension.

The OECD itself uses the raw percentage for cross-country level
comparison (Education at a Glance Chapter A1). The Atlas DIRECT_0_100
path preserves this semantic.

### Proxy force eligibility (Part 8)

If DEC-032 is accepted (it is), Sprint 6.4 MAY implement:

1. **Indicator level**: `TERTIARY_ATTAINMENT_25_34` DIRECT_0_100 level
   via the existing `_normalize_direct_0_100_as_of` path (the same
   code path as the WGI x3). The registry already has
   `level_family=monotonic_positive` and
   `direction=positive`; the only change is that DIRECT_0_100 dispatch
   must accept `MONOTONIC_POSITIVE` (currently gated to
   `DIRECT_0_100` family only — see "Implementation note" below).
   - **Wait**: the registry currently has
     `level_family=NormalizationFamily.monotonic_positive` for
     TERTIARY_ATTAINMENT_25_34, NOT `direct_0_100`. The normalizer
     dispatches on `direct_0_100` only. Sprint 6.4 must either (a)
     reclassify the registry to `direct_0_100` (a registry change,
     which is a model-version bump), or (b) extend the normalizer to
     accept `monotonic_positive` with a DIRECT_0_100 config. Option
     (a) is cleaner and more honest: DIRECT_0_100 IS the family. The
     registry reclassification is part of the implementation, not
     this sprint.

2. **Force aggregation**: Education force role
   `SUPPORTING_CONTEXT` → `PROXY_CONDITION`; aggregation
   `DEFERRED_MULTI` → `IDENTITY_SINGLE`. This requires:
   - exactly one executable scoring component (satisfied:
     TERTIARY_ATTAINMENT_25_34 is the only live Education input);
   - indicator level orientation higher = stronger (satisfied:
     MONOTONIC_POSITIVE);
   - force semantics explicitly say this is only a tertiary-attainment
     proxy (the force notes must state this);
   - coverage ceiling remains PARTIAL (DEC-009, DEC-026 — unchanged);
   - coverage never modifies the numeric score (DEC-029 invariant —
     unchanged);
   - no claim that tertiary attainment == complete Education force
     (the PARTIAL ceiling enforces this).

3. **Model versions**: `normalization-v0.6` → `normalization-v0.7`
   (registry reclassification + new DIRECT_0_100 indicator);
   `force-aggregation-v0.1` → `force-aggregation-v0.2` (new
   IDENTITY_SINGLE force + PROXY_CONDITION role).

### Relative / momentum / confidence boundaries (Part 9)

A level READY verdict does NOT automatically approve other dimensions:

- **Relative**: NOT approved. The registry has
  `relative_family=cross_sectional_relative` for
  TERTIARY_ATTAINMENT_25_34, but no reference-universe methodology is
  approved. The OECD dataflow universe (51 economies) is a candidate,
  but it is NOT tracked_8 and is NOT global — a future relative DEC
  must define the universe and its membership policy. Relative stays
  None.
- **Momentum**: NOT approved. The registry has
  `momentum_family=own_history` with windows (3, 5), but no
  momentum methodology is approved for this indicator. CHN (n=1)
  cannot support momentum at all. Momentum stays None.
- **Confidence**: stays None (DEC-023). No numeric confidence
  composition is approved.

### Missingness and coverage

- **Missing != zero**: a missing TERTIARY_ATTAINMENT_25_34 observation
  returns None, never 0. CHN with no post-2010 observation returns
  None for any scoring period after 2010 (freshness-gated).
- **Coverage != strength**: coverage_status measures data
  availability. Education coverage stays PARTIAL (DEC-009 ceiling)
  even when TERTIARY_ATTAINMENT_25_34 has data. The PARTIAL ceiling
  does NOT modify the numeric level_score.
- **Freshness gates current observations**: a stale observation is
  gated (returns None), never scaled. CHN's 2010 observation is
  valid for 2010 snapshots but stale for 2025 snapshots.

### Impact

NO production code changed. NO force code changes. NO normalization
code changes. NO phase, cycle composite, force confidence, relative
aggregation, momentum aggregation, persistence, API, or frontend.
Model versions unchanged: `normalization-v0.6`, `force-aggregation-v0.1`.
`TERTIARY_ATTAINMENT_25_34` stays in the registry with
`level_family=monotonic_positive` (NOT yet `direct_0_100` — that
reclassification is a Sprint 6.4 implementation step). Education force
stays `SUPPORTING_CONTEXT` / `DEFERRED_MULTI` with `level_score = None`.
confidence = None. backtest_safe = False.

Read-only research artifact `scripts/education_profile.py` retained
(no scores, no writes, clearly labeled research support).

### Reason

DEC-026 implemented the live OECD tertiary attainment series but
deferred its normalization. Sprint 6.3 audited whether a defensible
level curve exists. The audit found that DIRECT_0_100 is defensible
because the OECD designed the raw percentage to BE the cross-country
level indicator (unlike government-debt/GDP, where no official source
supports a universal threshold). The OECD uses the raw percentage for
cross-country level comparison in its flagship publication. The
indicator is bounded 0-100 by construction, higher unambiguously means
more educated, and no arbitrary threshold or curve is invented. The
comparability limits are real but documented by the OECD and do not
block the level signal. Sparsity (CHN n=1, IND n=8) affects freshness
and momentum but not the DIRECT_0_100 family itself.

### Recommended Sprint 6.4

**Sprint 6.4 — Education level + proxy-force implementation.**
Implement DIRECT_0_100 for TERTIARY_ATTAINMENT_25_34 and promote
Education to the 4th executable force via PROXY_CONDITION +
IDENTITY_SINGLE. Specific implementation steps (all subject to
DEC-032 approval, which is granted):

1. Reclassify `TERTIARY_ATTAINMENT_25_34` registry `level_family`
   from `monotonic_positive` to `direct_0_100` (honest: DIRECT_0_100
   IS the family). Bump `normalization-v0.6` → `normalization-v0.7`.
2. Extend the DIRECT_0_100 dispatch gate if needed (currently the WGI
   x3 are the only DIRECT_0_100 indicators; the gate checks
   `level_family is direct_0_100` which will pass after step 1).
3. Promote Education force component role
   `SUPPORTING_CONTEXT` → `PROXY_CONDITION`; aggregation
   `DEFERRED_MULTI` → `IDENTITY_SINGLE`. Bump
   `force-aggregation-v0.1` → `force-aggregation-v0.2`.
4. Force notes must explicitly state: "Education force is a
   tertiary-attainment proxy (age 25-34, ISCED 5-8). Coverage stays
   PARTIAL — one attainment series cannot measure complete education
   strength."
5. Coverage ceiling stays PARTIAL (DEC-009, DEC-026). No numeric
   modification of level_score by coverage.
6. Relative, momentum, confidence stay None.
7. Tests: DIRECT_0_100 level for TERTIARY_ATTAINMENT_25_34;
   IDENTITY_SINGLE force aggregation for Education; coverage stays
   PARTIAL; CHN/IND sparsity/freshness behavior; no regression on
   existing 3 forces.

Deliberately NOT queued in 6.4: relative score for education (needs
its own reference-universe DEC); momentum for education (CHN n=1
blocks; needs its own DEC); confidence (DEC-023); force persistence;
public force API; frontend force scores; cycle composite; phase/stage;
backtesting; trading; any other indicator's normalization curve.

### Sprint 6.4 implementation note (2026-09-10)

DEC-032 was implemented in Sprint 6.4. All seven prescribed steps were
executed, plus a critical hardening step (step 2.5 below) that the original
decision text did not anticipate but the implementation revealed as
necessary:

1. ✅ `TERTIARY_ATTAINMENT_25_34` registry `level_family` reclassified
   `monotonic_positive` → `direct_0_100`; `normalization-v0.7`.
2. ✅ DIRECT_0_100 dispatch gate passes for Education (level family check).
2.5. ✅ **CRITICAL HAZARD FIX**: the Sprint 5.7/5.8 family-combination
   gates (DIRECT_0_100 + OWN_HISTORY for momentum; DIRECT_0_100 +
   CROSS_SECTIONAL_RELATIVE for relative) resolved to the WGI x3 only
   because no other DIRECT_0_100 indicator existed. Education's registry
   candidate families (OWN_HISTORY momentum, CROSS_SECTIONAL_RELATIVE
   relative) would have SILENTLY passed those gates once the level family
   changed. v0.7 adds EXPLICIT approved indicator sets
   (`direct_momentum_approved_indicators`,
   `direct_relative_approved_indicators`) — both exactly the WGI x3 — so
   a registry family declaration alone NEVER enables a dimension. The
   direct relative helper (`build_relative_cross_section`) now also
   checks the approved set. Education is deliberately NOT in either set.
3. ✅ Education force: `SUPPORTING_CONTEXT` → `PROXY_CONDITION`;
   `DEFERRED_MULTI` → `IDENTITY_SINGLE`; `force-aggregation-v0.2`.
4. ✅ Force notes state Education is a tertiary-attainment proxy; coverage
   stays PARTIAL.
5. ✅ Coverage ceiling stays PARTIAL; no numeric modification by coverage.
6. ✅ Education relative, momentum, confidence stay None.
7. ✅ Tests: 32 new tests in `tests/test_sprint_6_4_education.py` covering
   the A-G matrix; 528 existing tests updated for new versions and
   Education's new role; 560 total pass.

Live read-only smoke (2025-Q4): USA 52.77, CHE 50.60, DEU 40.88, FRA 53.35,
GBR 61.19, JPN 67.53, IND 23.10, CHN None (stale 2010). Education
relative/momentum/confidence None everywhere. Other 3 forces unaffected.
DB counts unchanged (6814/27/22/10/1872). No writes. No commit/push.

---

## DEC-033 — Productivity / output growth methodology: DEFER_PRODUCTIVITY_LEVEL + DEFER_GDP_GROWTH_LEVEL

Date: 2026-09-10
Status: Accepted (Sprint 6.5 — methodology / research only, NO implementation)

### Decision

Sprint 6.5 audited whether `LABOUR_PRODUCTIVITY_PER_HOUR` and/or
`GDP_GROWTH` can receive a defensible Atlas 0-100 level_score and whether
the Productivity / output growth force may become the fifth executable
force. The verdict is **DEFER_PRODUCTIVITY_LEVEL** and
**DEFER_GDP_GROWTH_LEVEL**. Neither indicator receives a defensible
LEVEL mapping under current Atlas constraints. No implementation, no
model-version bump, no force code changes.

### Part 1 — Force semantic target

The force name "Productivity / output growth" conflates two distinct
economic dimensions:

**A. Structural efficiency / productivity level** — output generated per
unit of labour input. This is a STOCK/LEVEL concept: how much real output
a country's labour can produce per hour, given its capital, technology,
organisation, and skill base. A high productivity LEVEL means the economy
is structurally efficient — it can generate more output per hour worked.

**B. Output-growth dynamics** — how rapidly real economic output is
expanding or contracting. This is a FLOW/CHANGE concept: is the economy
growing, stagnating, or contracting? A high GDP GROWTH RATE means the
economy is expanding rapidly — but that does NOT mean its structural
productivity level is high. A catch-up economy (IND at 7.2% growth) can
have high growth from a low productivity base; a mature economy (JPN at
0.8% growth) can have high productivity but slow growth.

**Answers:**
- Does a high productivity LEVEL mean the force is structurally strong?
  YES — higher output per hour = more efficient production = stronger
  structural capability. The OECD confirms this interpretation.
- Does a high GDP GROWTH RATE mean the force level is strong? NO — GDP
  growth is a cyclical/flow measure, not a structural level. DEC-018
  already rejected a universal "healthy GDP growth" level band because
  potential growth differs by development stage, demographics,
  convergence, and business-cycle position.
- Is GDP growth better interpreted as momentum/change/context? YES —
  GDP growth is inherently a rate of change. It is a MOMENTUM or
  CONTEXT signal, not a LEVEL signal. Relabelling a growth rate as a
  domestic strength level would be false precision.

The slash in the force name does NOT imply an equal-weight formula.
The two indicators measure different dimensions and must not be
numerically combined without an explicit composition DEC.

### Part 2 — OECD labour-productivity provider semantics

**Indicator**: `LABOUR_PRODUCTIVITY_PER_HOUR`
**Source**: OECD Productivity Database (`OECD.SDD.TPS/DSD_PDB@DF_PDB`
v2.0)
**Production SourceSeries**:
`DSD_PDB@DF_PDB/{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP`
**External name**: GDP per hour worked (total economy, constant prices,
USD PPP)

Official OECD metadata (OECD Productivity Statistics Database: Sources,
Coverages and Definitions; OECD Productivity Statistics Methodological
Note; OECD Data Dashboard "GDP per hour worked"):

- **Exact concept**: GDP at market prices per hour worked, total economy
  (ACTIVITY=_T). Labour productivity measured as gross domestic product
  per hour of labour input. The OECD explicitly states: "GDP per hour
  worked measures labour productivity, expressed as the amount of gross
  domestic product (GDP) generated per hour of labour."
- **Exact unit**: US dollars per hour worked, PPP converted
  (UNIT_MEASURE=USD_PPP_H, CONVERSION_TYPE=PPP).
- **PPP basis**: PPPs are the rates of currency conversion that equalise
  purchasing power across countries. The OECD uses PPPs to convert
  national-currency GDP to a comparable USD basis for cross-country
  productivity level comparison. This is the OECD's intended use: "to
  compile internationally comparable estimates of productivity."
- **Price-year / constant-price semantics**: PRICE_BASE=LR (constant
  prices / volume basis). The value is a REAL (volume) productivity level,
  not nominal. The OECD notes the exact LR label still requires
  confirmation, but the series is verified live.
- **Hours-worked denominator**: total hours worked by all individuals
  involved in production. The OECD prefers hours-worked over
  persons-employed for analytical purposes.
- **Cross-country comparability intent**: the OECD publishes and uses this series
  for cross-country productivity-level comparison. The OECD Data Dashboard presents
  GDP per hour worked as a cross-country comparable productivity level.
  The OECD Productivity Database revamp report (2025) states: "Aggregate
  labour productivity... varies widely across OECD and accession
  countries" and uses the USD PPP/hour values directly for level
  comparison.
- **Time-series comparability limits**: PPP benchmarks are revised
  periodically; constant-price base years change; the OECD rebases to
  constant 2020 prices and constant PPPs for time-series consistency.
  Historical levels may shift when the base or PPP benchmark changes.
- **Revisions / methodological breaks**: the OECD Productivity Database
  was revamped in 2025 (new dataflow v2.0). Methodological breaks exist
  at revision boundaries.
- **Geographic coverage**: 51 economies in the OECD/dataflow universe
  (OECD members + accession/partner countries). CHN and IND are NOT
  covered. The universe is advanced-economy-heavy.
- **Level vs growth**: the OECD presents GDP per hour worked as a LEVEL
  indicator (USD/hour), not a growth rate. Growth variants (GY) exist in
  the same dataflow but are NOT mapped.

### Part 3 — World Bank GDP-growth provider semantics

**Indicator**: `GDP_GROWTH`
**Source**: World Bank national accounts data files + OECD National
Accounts data
**WB code**: `NY.GDP.MKTP.KD.ZG`
**External name**: GDP growth (annual %)

Official WB metadata (DataBank glossary):

- **Exact concept**: annual percentage growth rate of GDP at market prices
  based on constant local currency. "Annual percentage growth rate of
  GDP at market prices based on constant local currency."
- **Real vs nominal**: REAL — constant prices (base year 2015 in USD
  series; constant local currency in the primary definition).
- **Annual percentage-growth definition**: percentage change over each
  previous year. This is a RATE OF CHANGE, not a level.
- **Base / chain-volume semantics**: "constant 2015 U.S. dollars" for the
  aggregate series; individual country series use constant local
  currency. The WB notes limitations: "In many industries, value added
  is extrapolated from the base year using single volume indexes...
  Particularly in the services industries... measuring the growth of
  services remains difficult."
- **Comparability limitations**: measurement methods differ across
  countries (double-deflation vs single-volume extrapolation); services
  output is imputed from labour inputs in many countries; technical
  progress quality improvements are not fully captured.
- **Level, growth, or cyclical change**: this is unambiguously a GROWTH
  RATE (flow/change), not a level. It represents cyclical + structural
  output dynamics.

**DEC-018 reconfirmation**: DEC-018 rejected a universal TARGET_BAND for
GDP_GROWTH because potential growth differs by:
- **Development stage**: catch-up economies (IND 7.2%, CHN 6.1%) have
  structurally higher potential growth than mature economies (JPN 0.8%,
  DEU 1.1%). A single band would punish convergence growth and/or reward
  stagnation.
- **Demographics**: ageing economies have lower potential growth;
  young-population economies have higher potential growth.
- **Convergence / catch-up**: the Solow model predicts convergence —
  economies far from the technology frontier grow faster. A "healthy"
  band must be stage-dependent.
- **Business-cycle position**: actual growth deviates from potential
  growth cyclically. A single band conflates cyclical position with
  structural strength.
- **Structural maturity**: mature economies at the technology frontier
  grow slower by construction.

No new evidence has emerged to overturn DEC-018. The rejection stands.

### Part 4 — Production data profile (tracked_8, read-only)

**LABOUR_PRODUCTIVITY_PER_HOUR** (USD PPP/hour, latest vintage):

| Country | n | first | latest | min | p25 | median | p75 | max | latest_val |
|---|---|---|---|---|---|---|---|---|---|
| USA | 36 | 1990 | 2025 | 47.63 | 55.41 | 66.60 | 74.46 | 85.60 | 85.60 |
| CHE | 35 | 1991 | 2025 | 59.37 | 65.74 | 74.44 | 80.50 | 90.52 | 90.52 |
| DEU | 35 | 1991 | 2025 | 57.01 | 66.66 | 74.51 | 81.10 | 84.26 | 83.36 |
| FRA | 36 | 1990 | 2025 | 58.91 | 68.93 | 77.70 | 81.56 | 83.96 | 82.76 |
| GBR | 35 | 1990 | 2024 | 44.88 | 57.53 | 69.13 | 70.52 | 82.73 | 74.03 |
| JPN | 35 | 1990 | 2024 | 33.51 | 39.21 | 45.27 | 49.68 | 52.43 | 51.75 |
| CHN | — | — | — | — | — | — | — | — | NO DATA |
| IND | — | — | — | — | — | — | — | — | NO DATA |

Pooled (6 countries, 212 obs): min 33.51, max 90.52. CHN and IND have
NO OECD productivity data — provider no-data, NOT zero.

**GDP_GROWTH** (annual %, latest vintage):

| Country | n | first | latest | min | p25 | median | p75 | max | latest_val |
|---|---|---|---|---|---|---|---|---|---|
| USA | 11 | 2015 | 2025 | -2.08 | 2.16 | 2.58 | 2.95 | 6.15 | 2.16 |
| CHE | 11 | 2015 | 2025 | -2.26 | 1.12 | 1.42 | 3.33 | 6.18 | 1.30 |
| DEU | 11 | 2015 | 2025 | -4.13 | -0.50 | 1.14 | 2.22 | 3.91 | 0.24 |
| FRA | 11 | 2015 | 2025 | -7.44 | 0.86 | 1.44 | 2.08 | 6.88 | 0.84 |
| GBR | 11 | 2015 | 2025 | -10.05 | 1.08 | 1.55 | 3.02 | 8.54 | 1.39 |
| JPN | 11 | 2015 | 2025 | -4.28 | -0.24 | 0.83 | 1.62 | 3.56 | 1.19 |
| CHN | 11 | 2015 | 2025 | 2.34 | 4.96 | 6.07 | 6.89 | 8.57 | 4.96 |
| IND | 11 | 2015 | 2025 | -5.78 | 6.45 | 7.21 | 8.00 | 9.69 | 7.57 |

Pooled (8 countries, 88 obs): min -10.05, max 9.69. The range confirms
DEC-018: tracked_8 GDP-growth medians span 0.83 (JPN) to 7.21 (IND) —
one band cannot fit all.

### Part 5 — Broader productivity universe

The OECD Productivity Database dataflow covers **51 economies** (OECD
members + accession/partner countries), year range approximately
1960–2025 (varies by country). The DBnomics portal confirms 51 reference
areas for `DSD_PDB@DF_PDB_LV` with 871 total series across all
measure/unit combinations.

This is the **OECD/dataflow universe** — NOT tracked_8, NOT global, NOT
world. The universe is advanced-economy-heavy: it includes OECD members
(38) plus accession/partner countries (13). Many developing economies
outside the OECD dataflow are excluded.

Key findings:
- The OECD/dataflow universe is NOT a global distribution. It is biased
  toward advanced economies with established statistical systems.
- Using the OECD/dataflow universe as a calibration distribution for an
  absolute 0-100 level mapping would encode an advanced-economy-centric
  norm. A country at the 50th percentile of the OECD universe is NOT at
  the 50th percentile of the world.
- The universe composition has changed over time (expanding membership),
  creating composition drift. A fixed-universe calibration would need
  to freeze the universe and version it — but the resulting "level" would
  be a relative position, not an absolute productivity level.
- The OECD itself does NOT publish an absolute productivity threshold or
  benchmark. The OECD reports cross-country comparisons and averages as
  descriptive statistics, NOT as normative targets.

### Part 6 — Productivity level candidate evaluation

| Candidate | Semantic | Cross-country comparable | Defensible midpoint | CHN/IND | Result type | Verdict |
|---|---|---|---|---|---|---|
| A. RAW_VALUE_AS_LEVEL | raw PPP USD/hour as Atlas score | NO — unbounded, units have no 0-100 Atlas-score semantics | NO — what does score 50 mean in USD/hour? | CHN/IND no data | LEVEL | **NOT defensible** — not bounded 0-100; no Atlas-score semantics |
| B. FIXED_MONOTONIC_CURVE | externally justified anchors | would be | would need official benchmark | same | LEVEL | **NOT defensible** — no official OECD benchmark exists; the OECD publishes no "strong" productivity threshold |
| C. MONOTONIC_SATURATING | diminishing returns at high productivity | would be | would need saturation parameters | same | LEVEL | **NOT defensible** — no external evidence for saturation shape or parameters; inventing them would be false precision |
| D. SAME-YEAR OECD/DATAFLOW PERCENTILE | relative position in dataflow | mechanically | median of OECD universe | same | RELATIVE | **NOT a LEVEL** — this is a relative_score dimension, not a level; the OECD universe is not global |
| E. FIXED BROADER-UNIVERSE CALIBRATION | historically estimated distribution → 0-100 | mechanically | n/a | same | RELATIVE | **NOT a LEVEL** — relative dimension; composition drift; universe bias; future leakage risk |
| F. OWN_HISTORY | productivity improvement vs own past | NO — each country's own history differs | NO | CHN/IND no data | MOMENTUM | **NOT a LEVEL** — this is a momentum/change signal |
| G. CONTEXTUAL_DEFERRED | none | n/a | n/a | n/a | none | **Selected — no defensible LEVEL mapping exists** |

**Blocker**: the OECD publishes GDP per hour worked as a cross-country
comparable LEVEL indicator (USD PPP/hour), but the raw value is unbounded
and has no 0-100 Atlas-score semantics. Unlike Education (where the raw
percentage IS the level signal because 0-100 is the bounded semantic
scale), productivity in USD/hour has no natural 0-100 mapping. No
official source provides absolute thresholds that would justify a
FIXED_MONOTONIC_CURVE. The OECD/dataflow universe is too
advanced-economy-heavy to serve as a defensible absolute calibration
distribution. tracked_8 is explicitly rejected (DEC-018). Therefore no
defensible LEVEL mapping exists under current Atlas constraints.

### Part 7 — GDP growth candidate evaluation

| Candidate | Semantic | Is this a LEVEL? | Is this MOMENTUM? | Is this RELATIVE? | Verdict |
|---|---|---|---|---|---|
| A. ABSOLUTE_LEVEL_TARGET_BAND | universal "healthy" growth band | NO — rejected by DEC-018 | NO | NO | **DEFER** — DEC-018 stands, no new evidence |
| B. OWN_HISTORY_DEVIATION | current growth vs own historical norm | NO — this is a change/deviation statistic | YES — this is momentum | NO | **MOMENTUM candidate, NOT a LEVEL** |
| C. MULTI-YEAR_TREND_GROWTH | trailing growth average | NO — a smoothed rate is still a rate | Partially — trend, not point change | NO | **MOMENTUM/CONTEXT, NOT a LEVEL** |
| D. RELATIVE_GROWTH | same-period position vs a named universe | NO — relative position | NO | YES — this is relative | **RELATIVE candidate, NOT a LEVEL** |
| E. POTENTIAL-GROWTH_GAP | actual minus potential growth | NO — a gap is a deviation | Partially | NO | **NOT a LEVEL — requires potential-output data not in the Atlas** |
| F. SUPPORTING_CONTEXT / DEFER | none | n/a | n/a | n/a | **Selected for LEVEL — GDP growth is NOT a level** |

**Conclusion**: GDP_GROWTH is inherently a rate of change. It does NOT
measure a structural level. Every candidate that produces a numeric
value from GDP growth is either a MOMENTUM statistic (own-history
deviation, trend growth), a RELATIVE statistic (cross-country growth
position), or requires data not in the Atlas (potential-growth gap).
Relabelling a change statistic as a domestic strength LEVEL would be
false precision. GDP_GROWTH stays CONTEXTUAL_DEFERRED for level.

### Part 8 — Level vs momentum architecture conclusion

The permanent DEC-012 separation (level_score, relative_score, momentum,
confidence as independent dimensions) applies cleanly here:

- **LABOUR_PRODUCTIVITY_PER_HOUR** → structural LEVEL candidate
  (conceptually correct — it IS a level), but no defensible numeric
  0-100 mapping exists under current constraints (Part 6).
- **GDP_GROWTH** → MOMENTUM / output-growth context candidate
  (conceptually correct — it IS a rate of change), NOT a level.

A future Productivity force MAY legitimately have:
- `force.level_score` from productivity level (IF a defensible level
  mapping is approved in a future DEC — requires either an official
  benchmark or a defensible calibration universe decision)
- `force.momentum` informed by output/productivity growth (IF a
  momentum methodology is approved in a future DEC — requires
  own-history or trend design)

without averaging the two. The architecture supports this split. The
blocker is the level mapping, not the architecture.

### Part 9 — Force-eligibility audit

Because LABOUR_PRODUCTIVITY_PER_HOUR does NOT receive a defensible
executable LEVEL (Part 6 verdict: DEFER), the force-eligibility audit
does not proceed to IDENTITY_SINGLE evaluation. The force stays
DEFERRED_MULTI with both indicators as SUPPORTING_CONTEXT.

However, for completeness:

1. Does labour productivity per hour adequately represent the force's
   structural LEVEL? Conceptually YES — but without a defensible numeric
   mapping, "adequately" is moot.
2. Does the presence of GDP_GROWTH as a live supporting input prevent
   IDENTITY_SINGLE? Not necessarily — a SUPPORTING_CONTEXT indicator
   does NOT automatically block IDENTITY_SINGLE if methodology explicitly
   says the force level is defined by one structural condition and the
   other input is non-scoring context. But this requires an explicit DEC
   approving the level mapping first.
3. Would the force need a PARTIAL coverage ceiling? YES — labour
   productivity per hour measures only labour productivity, NOT
   total-factor productivity, capital productivity, or innovation. A
   future PROXY_CONDITION role would require PARTIAL coverage. But this
   is moot while the level is deferred.

### Part 10 — CHN / IND policy

Current OECD labour-productivity coverage does NOT include CHN or IND.
If Productivity were to become an identity force from labour
productivity (it does NOT in this sprint):

- CHN / IND `level_score` would remain `None` — no OECD productivity
  observation exists.
- GDP_GROWTH exists for CHN/IND but must NOT be substituted for missing
  productivity. GDP growth is NOT productivity.
- No zero fill. No inference from GDP growth to productivity. No score
  reduction for missing coverage. No silent provider substitution.
- Coverage and numeric eligibility remain separate (DEC-029 invariant).

Expected behavior:
- **OECD-covered countries** (USA, CHE, DEU, FRA, GBR, JPN): would
  receive a productivity level IF a mapping were approved (it is not).
- **CHN**: `level_score = None` (no data, no substitution).
- **IND**: `level_score = None` (no data, no substitution).

### Part 11 — Verdict

**Primary verdict: DEFER_PRODUCTIVITY_LEVEL**

`LABOUR_PRODUCTIVITY_PER_HOUR` cannot receive a defensible Atlas 0-100
level_score under current constraints. The blocker is the absence of:
(a) an official OECD productivity threshold/benchmark that would
justify a FIXED_MONOTONIC_CURVE, and (b) a defensible calibration
universe that would justify a broader-universe mapping. The OECD/dataflow
universe (51 economies) is too advanced-economy-heavy to serve as an
absolute calibration distribution. tracked_8 is explicitly rejected
(DEC-018). The raw USD PPP/hour value is unbounded and has no 0-100
Atlas-score semantics (unlike Education's bounded 0-100 percentage).

**Independent verdict: DEFER_GDP_GROWTH_LEVEL**

`GDP_GROWTH` cannot receive a defensible Atlas 0-100 level_score. GDP
growth is inherently a rate of change, not a structural level. DEC-018
rejected a universal TARGET_BAND and no new evidence has emerged. Every
numeric candidate from GDP growth is a MOMENTUM or RELATIVE statistic,
not a LEVEL. GDP_GROWTH stays CONTEXTUAL_DEFERRED for level.

**Both indicators stay SUPPORTING_CONTEXT. The force stays
DEFERRED_MULTI. No model-version bump. No force promotion.**

### Future unblockers (NOT approved in this DEC)

A future DEC MAY revisit productivity level if:
1. An official OECD productivity benchmark/threshold is published
   (currently does not exist).
2. A defensible calibration universe is approved (e.g. a genuinely
   global productivity distribution from a source that includes
   developing economies — not the OECD/dataflow universe alone).
3. A different normalization family (e.g. OWN_HISTORY for productivity
   improvement) is approved as a MOMENTUM dimension (separate from level).

A future DEC MAY revisit GDP growth as:
1. A MOMENTUM dimension (own-history deviation or trend growth) for the
   Productivity force — NOT a level.
2. A RELATIVE dimension (cross-country growth position) — NOT a level.

### Impact

NO production code changed. NO force code changes. NO normalization
code changes. NO phase, cycle composite, force confidence, relative
aggregation, momentum aggregation, persistence, API, or frontend.
Model versions unchanged: `normalization-v0.7`, `force-aggregation-v0.2`.
`LABOUR_PRODUCTIVITY_PER_HOUR` stays `MONOTONIC_POSITIVE` with deferred
level curve. `GDP_GROWTH` stays `CONTEXTUAL_DEFERRED`. Productivity force
stays `SUPPORTING_CONTEXT` / `DEFERRED_MULTI` with `level_score = None`.
confidence = None. backtest_safe = False.

Read-only research artifact: `scripts/productivity_profile.py` (NEW —
descriptive statistics only, no scores, no writes, clearly labeled
research support).

pytest 571 passed (unchanged). DB unchanged (6814/27/22/10/1872). No
migration, no ingestion, no persistence. No commit/push.

### Reason

The Productivity / output growth force conflates two distinct economic
dimensions: structural productivity level (a stock) and output-growth
dynamics (a flow). The OECD publishes and uses PPP-adjusted GDP per hour
worked for cross-country productivity-level comparison, but the raw USD PPP/hour
value has no natural 0-100 Atlas-score semantics and no official
benchmark exists to justify a fixed curve. The OECD/dataflow universe
is too advanced-economy-heavy for absolute calibration. GDP growth is
inherently a rate of change, not a level — DEC-018's rejection of a
universal band stands. Deferring both is the honest outcome: inventing
thresholds or relabelling a growth rate as a level would bake arbitrary
norms into a versioned model, exactly the false precision the Atlas
architecture is designed to prevent.

### Recommended Sprint 6.6

If the owner wants to continue normalization methodology:
- **WID wealth-share normalization audit** — `WEALTH_SHARE_TOP_10` is
  live (670 obs), the Wealth-gap force is PARTIAL (DEC-009), and the WID
  raw fraction (0-1) may have defensible level semantics similar to
  Education's bounded percentage (needs its own DEC).
- **Gini / WID joint wealth-gap methodology** — Gini direction is
  confirmed (DEC-018) but no curve; WID wealth share may complement Gini
  as a second partial proxy.
- **Global openness proxy methodology** — trade-based openness ratio
  (needs owner approval before any promotion or derived ratio).

Do NOT recommend arbitrary curve implementation. Each candidate needs
its own DEC with the same audit rigor as DEC-032/DEC-033.

---

## DEC-034 — WID top-10 wealth-share level: READY_FOR_WID_WEALTH_LEVEL_DESIGN (COMPLEMENT_0_100 for WEALTH_SHARE_TOP_10; PROXY_CONDITION + IDENTITY_SINGLE eligible for the Wealth-gap force)

Date: 2026-09-10
Status: Accepted (Sprint 6.6 — methodology / research only, NO implementation)
Sprint 6.6.1 (2026-09-10): domain contract hardened — [0,1] reclassified
from "structurally guaranteed" to "empirically observed for the
complete exact-series universe"; adapter range guard identified as an
Atlas assumption (not a verified provider contract); verdict
UNCHANGED (KEEP_READY) — see Sprint 6.6.1 addendum at end.

### Decision

Sprint 6.6 audited whether `WEALTH_SHARE_TOP_10` (WID `shwealj992`,
`p90p100`, pop=`j` equal-split adults) can receive a defensible Atlas
0-100 level_score and, if so, whether the Wealth / opportunity / values
gaps force may become the fifth executable force through
PROXY_CONDITION + IDENTITY_SINGLE. The verdict is
**READY_FOR_WID_WEALTH_LEVEL_DESIGN**. A defensible LEVEL semantic
exists; Sprint 6.7 MAY implement it (subject to the conditions below).
Sprint 6.6 itself implements NOTHING and changes NO model version.

### Part 1 — Exact WID series semantics

**Indicator**: `WEALTH_SHARE_TOP_10`
**Provider**: World Inequality Database (WID)
**WID variable**: `shwealj992`
**WID percentile**: `p90p100`
**Production SourceSeries**: `WID/shwealj992/p90p100`
**External name**: Top 10% net personal wealth share (equal-split adults)
**External unit**: share (0-1)

WID code construction (official WID Codes Dictionary,
wid.world/codes-dictionary/):

- **`s`** (series type) = **share** — the share of a total held by a
  specific group. "Shares and wealth/income ratios are given as a
  fraction of 1."
- **`hweal`** (five-letter concept) = **net personal wealth** (= household
  net wealth in the WID household sector). This is NET wealth: assets
  minus liabilities. The WID code dictionary defines `hweal` as
  "(=) household net wealth" — the equal sign indicates it is the
  balance (assets minus liabilities), not a gross total.
- **`992`** (three-digit age group) = **adults** (age group code for
  adult population).
- **`j`** (one-letter population unit) = **equal-split adults** — income
  and wealth distributed to adults and distributed equally within
  couples or households. This is the WID benchmark series convention
  (DINA Guidelines 2025). Pop=`j` is the ONLY series available for all 8
  tracked countries (pop=`i`/individuals exists only for USA and GBR).
- **`p90p100`** (percentile) = **top 10%** — the group from the 90th to
  the 100th percentile of the wealth distribution.

**Exact concept**: the fraction of total net personal wealth held by the
richest 10% of the adult population, under the equal-split-adults
convention. The value is a share (fraction of 1), not a percentage.

**Wealth concept**: net personal wealth = household assets minus
liabilities. Includes financial assets, non-financial assets (housing),
and pension assets, minus debts. Does NOT include human capital or
future earnings.

**Population unit**: equal-split adults — wealth is attributed to
individual adults, split equally within couples/households. This is
the WID benchmark convention for cross-country comparability.

**Age definition**: adults (no upper age restriction; includes all
adults, not just working-age).

**Individual vs household**: equal-split adults is an individual-level
concept (wealth attributed to each adult, split equally within
couples). NOT household-level.

**Top-10 ranking basis**: ranked by net personal wealth per adult,
from poorest (p0) to richest (p100). The top 10% (p90p100) is the
richest 10% of the adult population.

**Storage**: share as fraction 0-1, stored unchanged. The adapter
validates [0,1] and rejects out-of-range values.

**Estimation / interpolation / imputation**: WID benchmark series
combine observed data (from national accounts, surveys, fiscal data)
with estimated and imputed values. The WID uses regularized regression
with constraints to estimate wealth for countries without direct
observation. The `data_quality` column (0, 1, 2) is preserved but NOT
used for filtering (DEC-027 — official semantics unverified).

**Country comparability**: the WID uses homogeneous concepts
(equal-split adults, net personal wealth, ISCO/ISCED-independent wealth
definition) for cross-country comparison. However, source data quality
varies (some countries have observed wealth surveys; others have
estimated/imputed series). The WID DINA Guidelines 2025 document
these limitations.

**Historical methodology / revision**: WID series are revised
periodically. Historical observations may shift when methodology
changes. Pre-1900 observations are long-run estimates with higher
uncertainty.

### Part 2 — Range / domain audit

**A. Mathematical / theoretical domain**: the top-10% share of TOTAL
net personal wealth is a share of a total. If total net personal wealth
is positive and the top-10% group's wealth is positive, the share is
positive. However, net wealth includes liabilities — if the bottom 90%
collectively has negative net wealth (debts exceed assets), the top 10%
could theoretically hold more than 100% of total net wealth, making
share > 1. Conversely, if the top-10% group had collectively negative
net wealth (implausible for the wealthiest decile but mathematically
possible in extreme scenarios), the share could be negative. Therefore
the THEORETICAL domain for a NET-wealth top-10% share is NOT strictly
[0, 1]; it is a ratio that can in principle fall outside [0, 1] when
subgroups have collectively negative net wealth.

**B. Official-provider contract**: the WID Codes Dictionary states
"Shares and wealth/income ratios are given as a fraction of 1." This
is a REPRESENTATION statement (values are published as fractions),
NOT an explicit mathematical guarantee that every wealth share lies
in [0, 1] for every percentile group. The WID does NOT publish an
explicit per-series domain contract stating that
`shwealj992 / p90p100` is guaranteed ∈ [0, 1]. The representation
convention (fraction of 1) is consistent with [0, 1] but does not
constitute a formal guarantee for net-wealth shares where subgroups
can have negative wealth. Therefore [0, 1] is NOT a verified
provider-guaranteed domain for this exact series; it is an empirical
property (see C and D below).

**C. Empirical domain — full exact-series universe (Sprint 6.6.1 bulk
scan)**: a read-only scan of the entire WID bulk archive
(`wid_all_data.zip`, 423 data CSV files) for the EXACT series
`shwealj992 / p90p100` found:

- Geographic entities with the exact series: **324**
- Total observations: **14,936**
- Year range: **1800 – 2024**
- Min: **0.4074**
- p01: 0.4472
- p05: 0.5590
- p25: 0.5911
- Median: 0.6382
- p75: 0.7003
- p95: 0.7911
- p99: 0.8684
- Max: **0.9882**
- Count raw < 0: **0**
- Count raw == 0: **0**
- Count raw > 1: **0**
- Count raw == 1: **0**
- Latest-year (2024) same-year cross-section: n=260, min=0.4553, max=0.8860
  (Sprint 6.6.2 corrected: the Sprint 6.6.1 scan reported n=324 by
  collecting each entity's OWN latest year; the corrected scan uses the
  GLOBAL latest year 2024 — only 260 entities have a 2024 observation)
- **NO VALUES OUTSIDE [0, 1] FOUND** across the complete exact-series
  universe.

Entity classification (approximate, using `WID_countries.csv` metadata):
sovereign economies ≈ 239, region/aggregate entities ≈ 23, unknown ≈ 62.

**D. Current Atlas adapter admissible domain**: the WID adapter
(`apps/api/app/data_sources/wid.py`, lines 226–230) enforces [0, 1]
by raising `DataSourceParseError` for any value < 0 or > 1. This is a
HARD REJECTION at ingestion time — the observation is discarded and
the ingestion for that row fails. This guard was introduced in Sprint
5.20 as an Atlas assumption (see Part 4 — Adapter Range Guard Audit
below); it is NOT derived from a verified WID provider contract.

**Conclusion (corrected)**: the domain [0, 1] is EMPIRICALLY OBSERVED
for the complete exact-series universe (14,936 observations across 324
entities, 1800–2024, zero values outside [0, 1]). It is NOT a
theoretical guarantee (net wealth can be negative; a top-10% share
could theoretically exceed 1 if the bottom 90% has collectively negative
net wealth). It is NOT a verified provider-guaranteed contract (the
WID states a representation convention, not a formal per-series domain
guarantee). The complement formula 100*(1-share) is mathematically
valid for all observed values; the adapter's [0, 1] guard ensures only
in-domain values reach the normalizer, but the guard itself is an
Atlas assumption that must be reviewed (see Part 4).

### Part 3 — Precise indicator semantic target

`WEALTH_SHARE_TOP_10` answers: "What fraction of total net personal
wealth is owned by the richest 10% of the adult population?"

**Atlas interpretation**: wealth concentration. Higher raw value =
greater top concentration = conceptually worse for wealth-distribution
equality. The confirmed direction is MONOTONIC_NEGATIVE (DEC-028).

**What it does NOT measure**:
- equality of opportunity (opportunity gaps are a separate concept)
- values gaps / social polarization (no values/social-cohesion data)
- income inequality (Gini measures income; WID measures wealth)
- poverty (wealth share says nothing about absolute poverty levels)
- absolute wealth (a share is relative to the total, not an absolute)
- middle-class wealth specifically (only the top-10% vs bottom-90% split)
- mobility (a stock measure, not a flow/transition measure)

Therefore it can at most be a PROXY for the WEALTH-CONCENTRATION
component of the broader force. Coverage ceiling MUST remain PARTIAL
(DEC-009, DEC-028).

### Part 4 — Empirical tracked_8 profile

**WEALTH_SHARE_TOP_10** (fraction 0-1, latest vintage, 670 obs):

| Country | n | first | latest | min | p25 | median | p75 | max | latest_val |
|---|---|---|---|---|---|---|---|---|---|
| USA | 117 | 1820 | 2024 | 0.6271 | 0.6824 | 0.7071 | 0.7760 | 0.8559 | 0.6954 |
| CHE | 45 | 1980 | 2024 | 0.5463 | 0.5555 | 0.5894 | 0.6089 | 0.6288 | 0.6279 |
| DEU | 76 | 1820 | 2024 | 0.4943 | 0.5712 | 0.5867 | 0.7258 | 0.8866 | 0.5852 |
| FRA | 135 | 1800 | 2024 | 0.4997 | 0.5731 | 0.7057 | 0.8030 | 0.8669 | 0.5988 |
| GBR | 125 | 1820 | 2024 | 0.5163 | 0.5684 | 0.7690 | 0.9213 | 0.9882 | 0.5714 |
| JPN | 56 | 1820 | 2024 | 0.5629 | 0.5791 | 0.5897 | 0.5912 | 0.7680 | 0.5912 |
| CHN | 58 | 1820 | 2024 | 0.4074 | 0.4081 | 0.4982 | 0.6276 | 0.6817 | 0.6805 |
| IND | 58 | 1820 | 2024 | 0.4402 | 0.4979 | 0.5625 | 0.6262 | 0.6502 | 0.6501 |

Pooled tracked_8 (all 670 local observations): min 0.4074, max 0.9882.
No observations < 0, == 0, or > 1. All 8 tracked_8 countries have data
through 2024.

Key observations:
- The tracked_8 range (0.4074 CHN to 0.9882 GBR) is wide but each value
  has the same absolute meaning (share of net personal wealth held by
  top 10%).
- GBR (0.9882 historical max, 0.5714 latest) shows large historical
  variation — the 19th-century concentration was much higher than today.
- JPN (0.5912 latest) and CHE (0.6279 latest) are relatively equal;
  USA (0.6954 latest) and CHN (0.6805 latest) are more concentrated.
- Long historical series (USA, DEU, FRA, GBR, JPN, CHN, IND all have
  pre-1900 data) provide deep time-series context.

### Part 5 — Broader WID universe profile

**Sprint 6.6.1 full bulk scan** (read-only, `scripts/wid_full_universe_scan.py`):
the WID bulk archive contains 423 data CSV files (plus metadata files).
A scan of ALL data files for the EXACT series `shwealj992 / p90p100`
found:

- Geographic entities with the exact series: **324**
- Total observations: **14,936**
- Year range: **1800 – 2024**
- Min: 0.4074, p01: 0.4472, p05: 0.5590, p25: 0.5911, median: 0.6382,
  p75: 0.7003, p95: 0.7911, p99: 0.8684, max: 0.9882
- Count raw < 0: 0; count raw == 0: 0; count raw > 1: 0; count raw == 1: 0
- Latest-year (2024) same-year cross-section: n=260, min=0.4553, max=0.8860
  (Sprint 6.6.2 corrected: the Sprint 6.6.1 scan reported n=324 by
  collecting each entity's OWN latest year; the corrected scan uses the
  GLOBAL latest year 2024 — only 260 entities have a 2024 observation)
- Entity classification (approximate, using `WID_countries.csv`):
  sovereign economies ≈ 239, region/aggregate entities ≈ 23, unknown ≈ 62

Key findings:
- The WID exact-series universe is significantly broader than tracked_8
  (324 entities / 14,936 obs vs 8 entities / 670 obs).
- The universe includes both advanced and developing economies (unlike
  the OECD productivity universe which is advanced-economy-heavy).
- However, data quality varies: some countries have observed wealth
  surveys; others have estimated/imputed series (DEC-027).
- The WID does NOT publish an absolute threshold or benchmark for
  top-10% wealth share. The WID reports cross-country comparisons as
  descriptive statistics, not normative targets.
- A CROSS_SECTIONAL_RELATIVE score within the WID universe is a
  RELATIVE dimension, not a LEVEL — it would answer "where does this
  country rank," not "what is the absolute concentration."

### Part 6 — Data-quality / estimation semantics

DEC-027 deliberately did NOT turn WID `data_quality` into an Atlas
filter. This means:

1. **Does shwealj992 combine observed, estimated, interpolated, imputed?**
   YES. WID benchmark series combine observed data (national accounts,
   surveys, fiscal data) with estimated and imputed values. The WID uses
   regularized regression with constraints for countries without direct
   observation. The `data_quality` column (0, 1, 2) may distinguish
   these, but official semantics are unverified.

2. **Does WID expose enough provenance to distinguish them reliably?**
   The `data_quality` column is preserved but its official semantics
   are unverified (DEC-027). WID does NOT provide an official code
   dictionary for data_quality values. Sprint 5.19 inferred
   0=observed, 1=interpolated, 2=extrapolated, but this was RETRACTED
   as undocumented.

3. **Are cross-country levels comparable enough for an ABSOLUTE proxy
   level?** The WID uses homogeneous concepts (equal-split adults, net
   personal wealth) for cross-country comparison. Source data quality
   varies, but the WID benchmark methodology homogenizes the series.
   The comparability is sufficient for a PROXY level (not a complete
   measure), with the PARTIAL ceiling enforcing the incompleteness.

4. **Does variation in source quality belong in confidence rather than
   the level?** YES — if a future confidence methodology is approved
   (DEC-023 deferred), data-quality variation would belong in
   confidence, not in the level score. The level score preserves the
   WID-published share; confidence (future) would modulate trust.
   Currently confidence stays None.

### Part 7 — Candidate level transforms

| Candidate | Semantic | Domain valid | Midpoint defensible | Parameters | Result type | Verdict |
|---|---|---|---|---|---|---|
| A. SIMPLE_COMPLEMENT (100*(1-share)) | bottom-90% wealth share × 100 | YES (share ∈ [0,1] → score ∈ [0,100]) | YES (50 = bottom 90% holds half of wealth) | NONE (parameter-free) | LEVEL | **DEFENSIBLE — selected** |
| B. PERCENT_COMPLEMENT (100 - raw_percent) | same as A if raw is percentage | same | same | same | LEVEL | Same as A (algebraically identical) |
| C. FIXED_MONOTONIC_CURVE | externally justified anchors | would be | would need benchmark | thresholds | LEVEL | NOT defensible — no official WID benchmark |
| D. MONOTONIC_SATURATING | diminishing returns | would be | would need parameters | saturation shape | LEVEL | NOT defensible — no external evidence for shape |
| E. SAME-YEAR WID CROSS-SECTIONAL PERCENTILE | relative position | mechanically | median of WID universe | universe | RELATIVE | NOT a LEVEL — relative dimension |
| F. FIXED WID-UNIVERSE CALIBRATION | percentile in universe | mechanically | n/a | universe, window | RELATIVE | NOT a LEVEL — relative dimension; universe drift; data-quality drift |
| G. OWN_HISTORY | change vs own past | NO | NO | window | MOMENTUM | NOT a LEVEL — momentum dimension |
| H. CONTEXTUAL_DEFERRED | none | n/a | n/a | n/a | none | Rejected — a defensible LEVEL exists (A) |

**Selected: A. SIMPLE_COMPLEMENT — score = 100 * (1 - share)**

Justification:
- **Mathematically valid**: share ∈ [0,1] (WID construction + adapter
  validation) → score ∈ [0,100]. No clamping needed. The theoretical
  edge case (share > 1 if bottom-90% has collectively negative wealth)
  is rejected by the adapter (returns None — missing ≠ zero).
- **Clear semantic meaning**: score = "share of net personal wealth
  held by the bottom 90%" × 100. This is an interpretable, absolute
  distributional fact — not a percentile or relative position.
- **No arbitrary parameters**: the complement is a parameter-free
  linear inversion. No breakpoints, no curve shape, no saturation
  parameters. This is the simplest possible inversion — analogous to
  DIRECT_0_100 in its lack of invented parameters.
- **Defensible midpoint**: 50 = "the bottom 90% holds half of net
  personal wealth." This is a meaningful, interpretable statement.
  The WID does NOT endorse 50% as a target (no official benchmark
  exists), but 50 has a clear semantic meaning as a distributional
  share.
- **Direction correct**: higher score = more equal distribution =
  directionally stronger. Aligns with MONOTONIC_NEGATIVE (DEC-028).
- **Cross-country comparable**: the WID publishes the share for
  cross-country comparison using homogeneous concepts (equal-split
  adults, net personal wealth).
- **As-of behavior**: uses current period-complete as-of alignment and
  does not select future-period observations. It is CURRENT/RESEARCH
  scoring only; historical release-date safety is not established and
  backtest_safe remains False. No calibration window needed (unlike
  percentile-based methods).
- **No information loss**: the complement is a bijection — the raw
  share can be recovered from the score. No distortion.

### Part 8 — Education analogy test

**Education (DEC-032)**:
- Raw percent of population with tertiary attainment (0-100%)
- Ordinary bounded population proportion
- Higher directly represents more attainment (MONOTONIC_POSITIVE)
- DIRECT_0_100: raw value IS the score (no transformation)
- The OECD publishes and uses the raw percentage for cross-country
  level comparison

**WID top-10 wealth share**:
- Share of NET personal wealth owned by one distributional group (0-1)
- Lower concentration is directionally better (MONOTONIC_NEGATIVE)
- Debts/negative wealth can complicate ordinary-share bounds
  (theoretically, but adapter validates [0,1] and rejects out-of-range)
- COMPLEMENT_0_100: score = 100*(1-raw) (complement transformation needed)
- The WID publishes the share for cross-country comparison

**Verdict: NO, WID needs a separate normalization family/semantics.**

The complement is NOT DIRECT_0_100 because:
1. The raw value needs inversion (complement), not identity
2. The direction is negative, not positive
3. The raw value is a fraction 0-1, not a percentage 0-100
4. The semantic meaning is different (distributional share vs population
   proportion)

The complement IS defensible as a NEW family (COMPLEMENT_0_100) with
similar simplicity and transparency to DIRECT_0_100:
- Both are parameter-free (no invented thresholds or curve shapes)
- Both map to [0,100] for all empirically observed provider values
- Both have clear, interpretable midpoints
- Both use provider-published values for cross-country comparison
- Both are proxies for a broader force (PROXY_CONDITION, PARTIAL ceiling)

### Part 9 — Relation to Gini

GINI_INDEX remains DEFERRED per DEC-024. This sprint does NOT solve
Gini.

**WEALTH_SHARE_TOP_10 = one scoring proxy condition** while
**GINI_INDEX = SUPPORTING_CONTEXT** is methodologically valid because:

- Gini measures INCOME inequality (WB SI.POV.GINI, survey-based)
- WID measures WEALTH concentration (net personal wealth distribution)
- They are related but NOT interchangeable
- Gini's level is DEFERRED (DEC-024: survey-concept incomparability,
  no defensible calibration universe, no defensible midpoint)
- WID's level is READY (this DEC: empirically observed [0,1] domain,
  parameter-free complement, clear midpoint)
- The two indicators measure different dimensions of inequality and
  must NOT be averaged or combined without an explicit composition DEC

GINI_INDEX stays SUPPORTING_CONTEXT (non-scoring). It does NOT block
IDENTITY_SINGLE for the WID component — a SUPPORTING_CONTEXT indicator
does NOT automatically block IDENTITY_SINGLE if methodology explicitly
says the force level is defined by one structural condition and the
other input is non-scoring context (DEC-029).

### Part 10 — Force eligibility

Because WEALTH_SHARE_TOP_10 receives a defensible executable LEVEL
(Part 7 verdict: READY), the force-eligibility audit proceeds:

1. **Does WID top-10 wealth share adequately represent the force's
   structural LEVEL?** It is a PROXY — one distributional measure of
   wealth concentration. It does NOT measure opportunity gaps, values
   gaps, income inequality, or social polarization. But as a PROXY for
   the wealth-concentration component, it is defensible. Coverage
   ceiling stays PARTIAL.

2. **Does the presence of GINI_INDEX as a live supporting input prevent
   IDENTITY_SINGLE?** NO — GINI_INDEX stays SUPPORTING_CONTEXT
   (non-scoring). A SUPPORTING_CONTEXT indicator does NOT block
   IDENTITY_SINGLE when methodology explicitly says the force level is
   defined by one structural condition and the other input is non-scoring
   context (DEC-029). This DEC explicitly approves that architecture.

3. **Would the force need a PARTIAL coverage ceiling?** YES — already
   capped at PARTIAL (DEC-009, DEC-028). One wealth-concentration
   measure does NOT represent complete Wealth/opportunity/values
   strength. The PARTIAL ceiling is permanent until mapping coverage
   improves (e.g. opportunity measures, social polarization indicators).

**Force promotion (approved for Sprint 6.7 implementation)**:
- `WEALTH_SHARE_TOP_10`: `SUPPORTING_CONTEXT` → `PROXY_CONDITION`
- `GINI_INDEX`: stays `SUPPORTING_CONTEXT`
- Force: `DEFERRED_MULTI` → `IDENTITY_SINGLE`
- Coverage ceiling: stays PARTIAL (DEC-009, DEC-028)
- Numeric score explicitly means wealth-concentration proxy only
- No claim of complete Wealth/opportunity/values strength
- Coverage does NOT scale score (DEC-029 invariant)
- Confidence stays None (DEC-023)

### Part 11 — Verdict

**Primary verdict: READY_FOR_WID_WEALTH_LEVEL_DESIGN**

`WEALTH_SHARE_TOP_10` can receive a defensible Atlas 0-100 level_score
via the COMPLEMENT_0_100 family: `level_score = 100 * (1 - share)`.

**Complete executable semantics**:

- **Indicator-level meaning**: bottom-90% net personal wealth share × 100
- **Normalization family**: COMPLEMENT_0_100 (NEW family — fraction 0-1,
  negative direction, score = 100*(1-raw))
- **Formula**: `level_score = 100 * (1 - raw_share)` where raw_share ∈ [0,1]
- **Provider-domain assumptions**: raw_share is EMPIRICALLY OBSERVED
  in [0,1] across the complete exact-series universe (14,936 obs, 324
  entities, 1800–2024, zero values outside [0,1]). This is NOT a
  provider-guaranteed contract (the WID states a representation
  convention, not a formal per-series domain guarantee). The adapter
  enforces [0,1] as an Atlas assumption (Sprint 5.20).
- **Valid raw range**: [0, 1] (empirically observed; enforced by adapter
  as an Atlas assumption, NOT a verified provider contract)
- **Out-of-domain behavior**: (1) no aligned observation → level may be
  None per existing alignment policy (missing ≠ zero). (2) a value
  outside [0,1] should never reach the normalizer because the adapter
  rejects it at ingestion (fail-loud `DataSourceParseError`); if the
  adapter guard is later relaxed, the normalizer must fail-loud with
  `NormalizationDataError` — never clamp, never silently return None
  for a present value that violates the normalization contract. (3) a
  present value within [0,1] that passes the adapter →
  `level_score = 100 * (1 - raw_share)`.
- **Midpoint semantics**: 50 = "bottom 90% holds half of net personal
  wealth" — meaningful, interpretable, NOT a normative target
- **Direction**: MONOTONIC_NEGATIVE (higher share = more concentration =
  weaker; higher score = more equal = stronger)
- **Missingness**: missing observation → None, never 0
- **Freshness**: FreshnessClass.annual (existing); stale → None
- **As-of behavior**: uses current period-complete as-of alignment and
  does not select future-period observations. It is CURRENT/RESEARCH
  scoring only; historical release-date safety is not established and
  backtest_safe remains False.
- **Provenance**: WID shwealj992 p90p100 pop=j equal-split adults
- **Data-quality policy**: data_quality preserved in raw_payload but NOT
  used for filtering (DEC-027 — unchanged)
- **Force-role recommendation**: PROXY_CONDITION (wealth-concentration
  proxy, not complete force)
- **IDENTITY_SINGLE eligibility**: YES — exactly one eligible numeric
  proxy (WEALTH_SHARE_TOP_10); GINI_INDEX stays non-scoring context
- **PARTIAL ceiling permanence**: YES — DEC-009, DEC-028; one
  distributional measure ≠ complete Wealth/opportunity/values strength

**Independent verdict: GINI_INDEX stays DEFERRED (DEC-024)**

GINI_INDEX level remains DEFERRED. No new evidence has emerged to
overturn DEC-024. Gini stays SUPPORTING_CONTEXT (non-scoring).

### Impact

NO production code changed. NO force code changes. NO normalization
code changes. NO phase, cycle composite, force confidence, relative
aggregation, momentum aggregation, persistence, API, or frontend.
Model versions unchanged: `normalization-v0.7`, `force-aggregation-v0.2`.
`WEALTH_SHARE_TOP_10` stays `MONOTONIC_NEGATIVE` with deferred level
curve (the COMPLEMENT_0_100 reclassification is a Sprint 6.7
implementation step). Wealth-gap force stays `SUPPORTING_CONTEXT` /
`DEFERRED_MULTI` with `level_score = None`. confidence = None.
backtest_safe = False.

Read-only research artifact: `scripts/wealth_share_profile.py` (NEW —
descriptive statistics only, no scores, no writes, clearly labeled
research support).

pytest 571 passed (unchanged — no code changes). DB unchanged
(6814/27/22/10/1872). No migration, no ingestion, no persistence.
No commit/push.

### Reason

The WID publishes the top-10% net personal wealth share as a
cross-country comparable, absolute distributional measure (fraction
0-1, equal-split adults). The complement 100*(1-share) is a
parameter-free transformation with clear semantics:
"bottom-90% wealth share × 100." No arbitrary thresholds, breakpoints,
or curve shapes are invented — it is the simplest possible inversion,
analogous to DIRECT_0_100 in its lack of invented parameters. The
midpoint (50) is meaningful: "bottom 90% holds half of net personal
wealth." The WID does NOT endorse a target share, but the complement
does NOT encode one — it preserves the distributional fact as-is. The
force is a PROXY (one distributional measure ≠ complete
wealth/opportunity/values strength), so coverage stays PARTIAL.
GINI_INDEX stays SUPPORTING_CONTEXT (income inequality ≠ wealth
concentration; not averaged, not combined). This is defensible because
the WID share is empirically observed in [0,1] across the complete
exact-series universe (14,936 obs, 324 entities, 1800–2024, zero values
outside [0,1]), the complement is parameter-free, and the semantic
meaning is clear and interpretable.

### Recommended Sprint 6.7

**Sprint 6.7 — WID wealth-share level + wealth-gap proxy implementation.**
Implement COMPLEMENT_0_100 for WEALTH_SHARE_TOP_10 and promote the
Wealth-gap force to the 5th executable force via PROXY_CONDITION +
IDENTITY_SINGLE. Specific implementation steps (all subject to
DEC-034 approval, which is granted):

1. Add `COMPLEMENT_0_100` to `NormalizationFamily` enum (NEW family —
  fraction 0-1, negative direction, score = 100*(1-raw)).
2. Reclassify `WEALTH_SHARE_TOP_10` registry `level_family` from
  `monotonic_negative` to `complement_0_100`. Bump
  `normalization-v0.7` → `normalization-v0.8`.
3. Implement `_normalize_complement_0_100_as_of` dispatch (score =
  100*(1-raw_share) for raw_share ∈ [0,1]; None for missing aligned
  observation per existing alignment policy; fail-loud
  `NormalizationDataError` for a present value outside [0,1] — never
  clamp, never silently return None for a present value).
4. Add `WEALTH_SHARE_TOP_10` to the direct dimension approval sets
  (`direct_momentum_approved_indicators`,
  `direct_relative_approved_indicators`) ONLY IF momentum/relative are
  approved — they are NOT approved in this DEC. The complement family
  is a NEW family, not DIRECT_0_100, so the existing DIRECT_0_100
  approval gates do NOT apply. New approval gates for COMPLEMENT_0_100
  must be added explicitly (level only; momentum and relative stay
  None).
5. Promote Wealth-gap force: `WEALTH_SHARE_TOP_10` role
  `SUPPORTING_CONTEXT` → `PROXY_CONDITION`; aggregation
  `DEFERRED_MULTI` → `IDENTITY_SINGLE`. Bump
  `force-aggregation-v0.2` → `force-aggregation-v0.3`.
6. `GINI_INDEX` stays `SUPPORTING_CONTEXT` (non-scoring).
7. Force notes must state: "Wealth-gap force is a wealth-concentration
  proxy (top-10% net personal wealth share, WID equal-split adults).
  Coverage stays PARTIAL — one distributional measure cannot measure
  complete wealth/opportunity/values strength."
8. Coverage ceiling stays PARTIAL (DEC-009, DEC-028). No numeric
  modification of level_score by coverage.
9. Relative, momentum, confidence stay None.
10. Tests: COMPLEMENT_0_100 level for WEALTH_SHARE_TOP_10;
  IDENTITY_SINGLE force aggregation for Wealth-gap; coverage stays
  PARTIAL; GINI_INDEX stays non-scoring; no regression on existing 4
  forces.

Deliberately NOT queued in 6.7: relative score for WID (needs its own
DEC); momentum for WID (needs its own DEC); Gini level (DEC-024
deferred); confidence (DEC-023); force persistence; public force API;
frontend force scores; cycle composite; phase/stage; backtesting;
trading; any other indicator's normalization curve.

---

### Sprint 6.6.1 addendum (2026-09-10) — WID domain contract + DEC-034 hardening

Sprint 6.6.1 hardened the WID domain contract before any Sprint 6.7
implementation. The primary DEC-034 verdict is UNCHANGED
(KEEP_READY_FOR_WID_WEALTH_LEVEL_DESIGN), but the domain wording is
corrected and the adapter range guard is identified as an Atlas
assumption requiring a correctness review before Sprint 6.7.

#### Part 4 — Adapter range guard audit

**Finding**: the WID adapter's [0,1] range guard
(`apps/api/app/data_sources/wid.py`, lines 226–230) raises
`DataSourceParseError` for any value < 0 or > 1. This guard was
introduced in Sprint 5.20 as an ATLAS ASSUMPTION — it is NOT derived
from a verified WID provider contract. The WID Codes Dictionary states
"Shares and wealth/income ratios are given as a fraction of 1" (a
representation convention), NOT a formal per-series domain guarantee.

**Is this a data correctness bug?** The theoretical domain for a
net-wealth top-10% share is NOT strictly [0, 1] — if the bottom 90%
has collectively negative net wealth (debts exceed assets), the top
10% could hold more than 100% of total net wealth, making share > 1.
Therefore a valid WID provider value > 1 is THEORETICALLY POSSIBLE,
and the adapter's hard rejection would discard it. This is a
POTENTIAL data correctness bug.

**However**: the Sprint 6.6.1 full bulk scan (Part 2C above) found
ZERO values outside [0, 1] across 14,936 observations in 324 entities
over 1800–2024. The empirical risk is very low. No valid provider
value has ever been discarded by the guard in practice.

**Action taken in 6.6.1**: NONE (the brief forbids fixing production
ingestion in this sprint). The issue is RECORDED. A correctness sprint
(Sprint 6.6.2) is recommended BEFORE Sprint 6.7 to review the adapter
range guard — either (a) confirm it as a safe Atlas policy with
documentation, or (b) relax it to a warning + None (preserve the raw
value, mark as non-scoring) if valid provider values > 1 are deemed
possible. The normalizer's fail-loud `NormalizationDataError`
semantics (Part 5 below) ensure that even if the adapter guard is
relaxed, the normalizer will never silently clamp or return None for
a present value.

#### Part 5 — Normalization error semantics (corrected)

Three distinct cases must be handled separately:

1. **No aligned observation**: signal / level is `None` per existing
   alignment policy (missing ≠ zero). This is NOT an error.
2. **Provider-valid but methodology-unrepresentable value** (e.g., a
   hypothetical share > 1 if the adapter guard is relaxed): the
   normalizer must NOT silently convert to missing. Methodology must
   explicitly DEFER or define behavior. For COMPLEMENT_0_100, a
   present value outside [0, 1] is methodology-unrepresentable (the
   complement would be negative or > 100). The normalizer must
   fail-loud with `NormalizationDataError` — never clamp, never
   silently return `None` for a present value.
3. **Present value violating a verified provider/normalization
   contract**: fail-loud with `NormalizationDataError`. Never clamp.
   Never silently return `None`.

This follows the existing normalization fail-loud discipline.

#### Part 6 — As-of wording (corrected)

Previous wording "As-of safe" and "No future leakage" is RETRACTED
as overclaiming. Corrected wording:

> Uses current period-complete as-of alignment and does not select
> future-period observations. It is CURRENT/RESEARCH scoring only;
> historical release-date safety is not established and
> `backtest_safe` remains `False`.

No release-date claims are made.

#### Part 7 — Re-evaluated verdict

**A. KEEP_READY_FOR_WID_WEALTH_LEVEL_DESIGN**

The exact provider/domain evidence supports a safe, explicit
COMPLEMENT_0_100 input contract:

- [0, 1] is **empirically observed for the complete exact-series
  universe** (14,936 observations, 324 entities, 1800–2024, zero
  values outside [0, 1]).
- [0, 1] is **NOT provider-guaranteed** (the WID states a
  representation convention, not a formal per-series domain guarantee).
- [0, 1] is **NOT a theoretical guarantee** (net wealth can be
  negative; a top-10% share could theoretically exceed 1).
- The adapter enforces [0, 1] as an Atlas assumption (Sprint 5.20).
  This is a potential data correctness issue (Part 4) that requires a
  correctness review (Sprint 6.6.2) BEFORE Sprint 6.7 implementation.
- The normalizer's fail-loud semantics (Part 5) ensure that even if
  the adapter guard is later relaxed, a present out-of-range value
  will fail-loud, not silently clamp or return None.

The verdict is KEEP_READY because the empirical domain supports the
COMPLEMENT_0_100 transform for all observed values, and the
fail-loud discipline ensures correctness for any future
out-of-range value.

#### Part 8 — Force decision (unchanged)

Because Part 7 keeps READY:

- `WEALTH_SHARE_TOP_10` → `PROXY_CONDITION` candidate (Sprint 6.7)
- `GINI_INDEX` → stays `SUPPORTING_CONTEXT`
- Wealth-gap → `IDENTITY_SINGLE` candidate (Sprint 6.7)
- Coverage ceiling → stays `PARTIAL`
- Relative → `None`
- Momentum → `None`
- Confidence → `None`

No force code change in 6.6.1.

#### Sprint 6.6.1 impact

NO production code changed. NO force code changes. NO normalization
code changes. NO adapter code changes. Model versions unchanged:
`normalization-v0.7`, `force-aggregation-v0.2`. pytest 571 passed
(unchanged). DB unchanged (6814/27/22/10/1872). No migration, no
ingestion, no persistence. No commit/push.

Read-only research artifact: `scripts/wid_full_universe_scan.py` (NEW —
full bulk scan of the WID archive for `shwealj992 / p90p100`;
descriptive statistics only, no scores, no writes).

#### Sprint 6.7 authorization

Sprint 6.7 is **NOT YET AUTHORIZED**. Before Sprint 6.7, a
correctness sprint (Sprint 6.6.2) must review the WID adapter's [0, 1]
range guard and either:
(a) confirm it as a safe Atlas policy with explicit documentation, or
(b) relax it to a warning + None (preserve the raw value, mark as
non-scoring) if valid provider values > 1 are deemed possible.

Sprint 6.7 is authorized ONLY AFTER Sprint 6.6.2 resolves the adapter
range guard issue.

---

### Sprint 6.6.2 addendum (2026-09-10) — WID raw-preservation guard fix

Sprint 6.6.2 resolved the adapter range guard identified in Sprint 6.6.1.
The permanent rule is now enforced:

    Provider data validity
        !=
    Atlas normalization representability.

If WID publishes a finite numeric observation for the exact selected
series, ingestion preserves that provider value unless WID itself
defines it as invalid. Atlas does NOT convert a real provider value to
missing merely because COMPLEMENT_0_100 cannot score it.

#### Source-layer fix

The WID adapter's [0,1] hard rejection
(`apps/api/app/data_sources/wid.py`, lines 226–230, Sprint 5.20) is
**RETRACTED**. A finite provider value outside [0,1] is now accepted and
preserved as the immutable raw `Observation.value`. The adapter still
rejects: empty required value (malformed row), non-numeric text, NaN,
+inf, -inf, wrong variable/percentile/age/pop/country identity.

Required layering:

    provider value
      -> immutable Observation
      -> AlignedValue
      -> NormalizedSignal eligibility

Never:

    provider value outside Atlas scoring domain
      -> silently dropped / None Observation

#### Domain separation

- **[0,1] is the approved COMPLEMENT_0_100 normalization domain**, NOT a
  WID ingestion validity domain.
- Raw WID ingestion preserves finite numeric provider values.
- A value outside [0,1]:
  - CAN exist in `Observation`
  - CANNOT receive COMPLEMENT_0_100 under DEC-034
  - MUST fail loudly in normalization (`NormalizationDataError`) if
    scoring is attempted
- This preserves: `missing != invalid != unscorable`

#### Normalization boundary (documented for Sprint 6.7, NOT implemented)

For COMPLEMENT_0_100:

    0 <= aligned raw <= 1
        -> level_score = 100 * (1 - raw)

    present aligned raw outside [0,1]
        -> NormalizationDataError
        -> never clamp
        -> never convert to missing
        -> raw Observation remains preserved

    no aligned observation
        -> None under normal missingness policy

No normalization-v0.8 yet. No COMPLEMENT_0_100 implementation.

#### Tests

- 7 new adapter regression tests (ordinary 0.65, boundary 0, boundary 1,
  finite >1 preserved, finite negative preserved, -inf rejected,
  non-numeric rejected). 2 old range-rejection tests replaced.
- 3 new persistence regression tests (out-of-range 1.03 persisted
  unchanged, negative -0.05 persisted unchanged, ordinary 0.72 persisted
  unchanged) via mocked in-memory SQLite.

#### Research-artifact hardening

- `scripts/wid_full_universe_scan.py`: fixed latest-year cross-section
  bug (was each entity's own latest year; now uses global latest year
  across all observations).
- `scripts/wealth_share_profile.py`: pooled SQL queries now explicitly
  constrain `Country.iso3` to TRACKED_8 (previously queried all
  observations for the indicator without country filtering).

#### Impact

NO normalization code changed. NO force code changes. NO model-version
bump (normalization-v0.7, force-aggregation-v0.2 — unchanged). This
corrects source-ingestion acceptance and research tooling. No current
economic output changes because all existing 670 observations are
already within [0,1]. No migration. No production re-ingestion required.

pytest 581 passed (571 baseline + 10 new: 7 adapter + 3 persistence).
DB unchanged (6814/27/22/10/1872). No commit/push.

#### Sprint 6.7 authorization

Sprint 6.7 is **AUTHORIZED** — all 9 gate conditions are met:

1. Finite provider values are no longer discarded solely by [0,1] ✓
2. Source identity validation remains strict ✓
3. Non-finite values still fail ✓
4. Raw provider values remain preserved ✓
5. DEC-034 clearly separates ingestion domain from normalization domain ✓
6. Full scan still finds no existing exact-series observations outside [0,1] ✓
7. Tests pass (581 > 571) ✓
8. DB unchanged ✓
9. Living docs point to Sprint 6.7 next ✓
