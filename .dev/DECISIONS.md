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
