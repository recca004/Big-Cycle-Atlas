# Normalization Methodology (Sprint 5.5 design — 2026-09-09)

Source of truth for the normalization/scoring layer. No force score, weight, or
confidence number is published here. The typed skeleton lives in
`apps/api/app/cycle/normalization_definitions.py`; the executable normalizer in
`apps/api/app/cycle/normalizer.py` (level + momentum + relative for the WGI ×3
— see the sprint-status sections below); the coverage-audit inputs are
in `.dev/FORCE_COVERAGE.md` ("Normalization Readiness"). Raw observations are
never modified by anything in this document.

## Sprint 5.6 implementation status (2026-09-09) — FIRST EXECUTABLE PATH

Implemented and executable (on demand, nothing persisted, no public API):

- **As-of alignment** — `apps/api/app/services/alignment_service.py`:
  `parse_scoring_period` ("YYYY-Qn"), `quarter_end_date` (2025-Q2 →
  2025-06-30; eligibility was `period_start <= as_of_date` — superseded by
  the Part 0 period-complete rule below), and
  `align_observation_as_of` → `AlignedValue` (latest vintage, latest prior
  period, country+indicator scoped at every query layer per ISSUE-004;
  `age_periods` in scoring-clock quarters; no forward-fill, no raw writes).
- **Freshness machinery** — `apps/api/app/cycle/freshness.py`:
  `FreshnessPolicy` / `FreshnessResult` / `evaluate_freshness` using the
  Section 5 MODEL PARAMETERS. Decay shape is parameterized; the CURRENT
  settled model choice is **exponential** (DEC-013, 2026-09-09 — the only
  shape that honors the half-life definition for arbitrary thresholds). The
  linear implementation remains available as an alternative for tests/future
  model versions. Too-stale → the signal is NOT
  produced, never produced-with-zero.
- **DIRECT_0_100** (this family ONLY) — `apps/api/app/cycle/normalizer.py`:
  `normalize_indicator_as_of(...)` dispatches on the registry level family;
  the three WGI governance scores map `level_score = raw_value` after
  validating 0 ≤ raw ≤ 100 (out-of-range raises `NormalizationDataError`,
  never clamps). Every other family raises
  `NormalizationNotImplementedError` — no generic fallback.
- Read-only smoke: `uv run --no-sync python scripts/normalize_smoke.py
  --country CHE --indicator RULE_OF_LAW_WGI_SCORE --period 2025-Q2`.

Still design-only (raise if requested): MONOTONIC_POSITIVE /
MONOTONIC_NEGATIVE / MONOTONIC_SATURATING / TARGET_BAND / OWN_HISTORY /
CROSS_SECTIONAL_RELATIVE / RELATIVE_SHARE / CONTEXTUAL_DEFERRED — all 16
non-WGI live indicators. *(Historical status as of Sprint 5.6 — superseded:
Sprint 5.7/DEC-016 added WGI momentum and Sprint 5.8/DEC-017 added WGI
relative scores, so `momentum` and `relative_score` are no longer None for
the WGI ×3; Sprint 5.10/DEC-019 then implemented the DEBT_SERVICE_RATIO
OWN_HISTORY level, and Sprint 5.12/DEC-021 implemented the
CREDIT_TO_GDP_GAP ONE_SIDED_VULNERABILITY level. Current truth: WGI ×3 have
executable level + momentum + relative; DEBT_SERVICE_RATIO has an executable
OWN_HISTORY level; CREDIT_TO_GDP_GAP has an executable ONE_SIDED_VULNERABILITY
level; `confidence` remains None on every signal, and every OTHER non-WGI
level indicator still raises NormalizationNotImplementedError. No force
aggregation, no weights, no Big Cycle phase, no persistence, no HTTP
endpoint. Every signal: `backtest_safe = false` (alignment is by
observation period, not release date — Milestone 9 owns that); current
model version `normalization-v0.6`.)* Tests:
`apps/api/tests/test_normalization_signals.py` (27, offline).

## Part 0 implementation status (2026-09-09) — PERIOD-COMPLETE ALIGNMENT

Owner-directed hardening applied BEFORE Sprint 5.7 momentum (DEC-015):
`period_start <= as_of_date` eligibility admitted period-INCOMPLETE
observations (annual 2020 first appears at the 2020-Q1 snapshot even though
the 2020 period has not ended). Eligibility is now
`effective_period_end <= scoring_period_end`, computed deterministically in
the DERIVED layer only — annual/irregular YYYY → YYYY-12-31, quarterly
YYYY-Qn → the quarter's end day; raw observations are never modified and no
synthetic period-end dates are persisted. `effective_period_end` travels as
`AlignedValue` provenance. Verified against the live DB: CHE
RULE_OF_LAW_WGI_SCORE at 2024-Q2 now aligns to 2023 (was the incomplete-year
2024 value — the leak), first becomes 2024-eligible at 2024-Q4; BIS
CREDIT_TO_GDP_GAP aligns to exactly its own completed quarter. Alignment
semantics changed → model version bumped to `normalization-v0.2` (method
`part0-period-complete-alignment-r1`). This fixes period-completeness
leakage ONLY — it provides NO historical release-date safety; every signal
keeps `backtest_safe = false` until Milestone 9. Tests: 32 offline
(5 new period-completeness regressions; the former leak expectation was
inverted). Momentum (Sprint 5.7) must be built ONLY on this hardened path.

## Sprint 5.7 implementation status (2026-09-09) — WGI MOMENTUM (DEC-016)

Second executable score dimension, implemented on the Part 0-hardened path
(on demand, nothing persisted, no public API):

- **Momentum gate** — `apps/api/app/cycle/normalizer.py`: momentum executes
  only when the registry has level_family DIRECT_0_100 AND momentum_family
  OWN_HISTORY — exactly the WGI ×3. Any other combination raises
  NormalizationNotImplementedError; a registry OWN_HISTORY entry alone does
  not approve an indicator's momentum.
- **Formula (DEC-016)** — signed change in the provider's own 0-100 points:
  `momentum_w = current_aligned_raw − anchor_aligned_raw`, computed from
  ALIGNED RAW values (never from level_score, which merely happens to equal
  raw for DIRECT_0_100 today). Higher WGI = positive; no inversion.
  `validate_momentum` runs on every non-None result; out-of-range raises,
  never clamps (the −100…+100 range holds by construction for 0-100 inputs).
- **Anchors** — `shift_scoring_period_years` (quarter preserved: 2025-Q2 −
  5y → 2020-Q2) + a plain `align_observation_as_of` call at the shifted
  period: country isolation, latest-vintage, DEC-015 period-complete
  eligibility, and no-future-leakage are all inherited — no separate
  momentum query logic exists.
- **Windows + primary** — registry/config windows (3, 5); the headline
  `momentum` is the **5y change ONLY** (no averaging, no fallback to 3y;
  `momentum_window_years` is 5 when the primary exists, None otherwise);
  BOTH windows' provenance travels as `MomentumWindowResult`
  (window_years, requested_anchor_period, anchor_source_period, change).
- **Anchor tolerance = 1 annual period** (versioned MODEL PARAMETER,
  `ModelVersionConfig.momentum_anchor_tolerance_periods`): the aligned
  anchor may be at most one source year older than the requested anchor
  year (WGI biennial gaps 1997/1999/2001 anchor to the prior year; anything
  older → change None — never zero, never a stretched window, the actual
  anchor stays visible in provenance). The tolerance is measured against the
  REQUESTED anchor year, so a period-complete fallback to the prior year
  (Part 0) is accepted, not punished.
- **Freshness** — the CURRENT observation keeps the existing gate and decay
  (exponential, DEC-013); the historical anchor is intentionally NOT
  freshness-decayed and momentum is never multiplied by the freshness
  factor. Freshness ≠ momentum ≠ confidence.
- **Missing history** — no alignable anchor → change None; tolerance
  violation → change None. Missing NEVER means 0. A level signal is still
  produced when momentum is unavailable.
- **Version** — `normalization-v0.3` (method `sprint-5.7-wgi-momentum-r1`)
  versioning windows/primary/tolerance/sign convention; backtest_safe False.
- Live read-only smoke (2026-09-09): CHE Rule of Law @2025-Q2 → level
  87.3184, momentum **−2.59** (5y, anchor 2019); CHN Control of Corruption
  @2025-Q2 → **+2.80**; DEU Political Stability @2025-Q2 → **−10.30**; CHE
  Rule of Law @2001-Q2 → level 91.4538 with momentum **None** (no alignable
  1996-Q2 anchor; the 3y anchor aligned 1996 is outside tolerance) — no
  fallback, no zero.
- Tests: 243 offline (18 new momentum regressions in
  `tests/test_normalization_signals.py`).

Still NOT implemented: momentum for the non-WGI indicators (their §17 sign
conventions remain open), confidence, force aggregation, weights, Big Cycle
phases, persistence, public API. WGI momentum is indicator-specific and NOT
approved for direct cross-indicator aggregation (a separate
momentum-calibration methodology is required first).

## Sprint 5.8 implementation status (2026-09-09) — WGI RELATIVE SCORES (DEC-017)

Third executable score dimension — **RESOLVED FOR THE WGI ×3 ONLY** (on
demand, nothing persisted, no public API):

- **Reference universe** — `ReferenceUniverseSpec` (id, frozen members) in
  `apps/api/app/cycle/normalization_definitions.py`; the initial universe
  `tracked_8` = USA, CHN, CHE, DEU, FRA, GBR, JPN, IND. Membership is a
  VERSIONED MODEL UNIVERSE, never derived from the DB (not the Country
  table, not who currently has data); tracked_8 is cross-checked against the
  canonical packages/shared country list in tests. Adding a country later
  does NOT silently change tracked_8 — a changed universe gets a new id and a
  new model version.
- **Semantics** — `relative_score` answers "where does this country rank on
  this indicator within tracked_8 at the same scoring snapshot?" It is the
  country's relative position within tracked_8 — **NEVER a global/world
  percentile, never a level, never a phase**. `level_score` keeps its own
  meaning (the provider's absolute 0–100 scale) and is never re-scaled.
- **Formula (DEC-017, versioned MODEL CHOICE)** — mid-rank plotting
  position: `relative_score = 100 * (average_rank − 0.5) / n`, rank 1 =
  weakest, rank n = strongest, ties = AVERAGE rank (deterministic and
  order-independent — never broken by ISO code, row id, or query order).
  For n=8 the possible scores are 6.25 / 18.75 / 31.25 / 43.75 / 56.25 /
  68.75 / 81.25 / 93.75 — the top member of only 8 countries is not
  mislabeled 100 and the bottom is not mislabeled 0. Higher WGI = stronger
  (no inversion). This resolves §16 (robust statistics) FOR THE WGI ×3
  ONLY: empirical rank / mid-rank plotting position — no min-max, no
  z-score, no winsorization needed (WGI is already bounded 0–100 and rank
  scoring is insensitive to magnitude). It does NOT auto-approve the
  formula for future CROSS_SECTIONAL_RELATIVE indicators.
- **Value being ranked** — the validated aligned WGI strength value
  (== level_score today because WGI is DIRECT_0_100). The engine
  (`apps/api/app/cycle/relative.py`, `build_relative_cross_section`) ranks
  a comparable strength value supplied by the indicator's normalization
  path — it does NOT assume future relative indicators rank raw
  observations directly.
- **Same as-of snapshot** — every member is aligned with
  `align_observation_as_of` at the SAME (indicator, scoring_period, model
  version, freshness policy): country scoping (ISSUE-004), latest vintage,
  DEC-015 period-complete eligibility, and no-future-leakage are all
  inherited. Never "latest overall".
- **Freshness** — gates member USABILITY only: stale-but-usable members
  participate; unusable members do not. Freshness NEVER scales
  relative_score (`relative_score *= freshness_factor` is forbidden —
  freshness affects trust later, not economic position). confidence stays
  None.
- **COMPLETE-UNIVERSE RULE** — tracked_8 requires ALL 8 members usable.
  7/8 → relative_score/relative_rank None for EVERYONE (never a
  seven-country score still called tracked_8), with the counts carried as
  provenance (`reference_universe_id`, `reference_universe_expected_n`,
  `reference_universe_usable_n`, `relative_rank` on NormalizedSignal).
  Missing members never become zero.
- **Range errors** — every participating member value is validated 0..100;
  out-of-range raises `NormalizationDataError` (never clamps, never treats
  as missing, never ranks).
- **Execution gate** — relative scoring runs only when
  relative_family = CROSS_SECTIONAL_RELATIVE AND the executable level family
  is DIRECT_0_100 → exactly the WGI ×3. GDP_GROWTH, GCF, Gini, and labour
  productivity also say CROSS_SECTIONAL_RELATIVE in the registry but their
  level semantics are not approved — they keep raising
  NormalizationNotImplementedError. No generic fallback.
- **Dimension independence** — relative is computed independently of
  momentum: a relative score may exist when momentum is None (complete
  same-period cross-section with insufficient own-history) and vice versa;
  neither modifies the other.
- **Version** — `normalization-v0.4` (method
  `sprint-5.8-wgi-tracked8-relative-r1`) versioning the universe id +
  frozen membership, complete-universe requirement, mid-rank formula, tie
  method, WGI direction, the v0.3 momentum config, and the exponential
  freshness policy; backtest_safe False. No migration.
- Live read-only smoke (2026-09-09, live Postgres, nothing written):
  CHE RULE_OF_LAW @2025-Q2 → level 87.3184, relative **93.75** (rank 8/8,
  universe 8/8 — CHE is the strongest tracked_8 member at the snapshot);
  CHN RULE_OF_LAW @2025-Q2 → relative **6.25** (rank 1/8); USA
  CONTROL_OF_CORRUPTION @2025-Q2 → relative **31.25** (rank 3/8). Momentum
  and level values unchanged from v0.3. All computed from the live aligned
  cross-section, nothing hardcoded.
- Tests: 278 offline (35 new relative regressions in
  `tests/test_relative_scores.py` + updated v0.4/universe-provenance
  expectations in `tests/test_normalization_signals.py`).

Still NOT implemented: relative scores for the non-WGI indicators
(their level families are not executable — enforced at the normalizer's
level gate AND, since Sprint 5.9, at the relative helper's own execution
gate), confidence, force aggregation,
weights, Big Cycle phases, persistence, public API.

## Sprint 5.9 — relative hardening + Non-WGI Level Parameter Decision Audit (2026-09-09)

A METHODOLOGY / DECISION sprint (DEC-018). Two outputs only:

1. **Relative-path hardening** — `build_relative_cross_section`
   (apps/api/app/cycle/relative.py) now enforces its OWN execution gate:
   level family DIRECT_0_100 AND relative family CROSS_SECTIONAL_RELATIVE
   (which resolves to exactly the WGI ×3 under the current registry) — a
   direct helper call for GINI_INDEX, GDP_GROWTH, GROSS_CAPITAL_FORMATION_GDP,
   LABOUR_PRODUCTIVITY_PER_HOUR, or any other non-approved indicator raises
   `NormalizationNotImplementedError`. No WGI code is hardcoded; the
   complete-universe / freshness / alignment rules are unchanged; WGI
   numerical outputs are unchanged; no model-version bump (no output
   semantics changed — only an invalid direct call that previously *could*
   rank non-approved indicators now raises).
2. **Non-WGI level parameter audit** — the eight audited non-WGI level
   methodologies below. NO numeric thresholds were invented; a valid
   outcome was DEFERRED where the methodology is not defensible yet.
   Descriptive statistics supporting the audit come from the READ-ONLY
   research script `apps/api/scripts/normalization_profile.py` (per-country
   + pooled count / earliest-latest / min / p10 / p25 / median / p75 / p90 /
   max — NO scores, NO writes, NOT proof that an empirical percentile is
   economic truth).

### Non-WGI Level Parameter Decision Audit — Sprint 5.9

| Indicator | Family at audit start | Decision (DEC-018) | Reason (short) | Parameters needed | Blocking evidence/data | Next action |
|---|---|---|---|---|---|---|
| GINI_INDEX | MONOTONIC_NEGATIVE | **APPROVE_FAMILY (direction), defer numeric curve** | Higher Gini = more inequality is clear; `100 − Gini` is NOT approved — an Atlas 50 would have no defensible meaning | A calibration mapping from raw Gini to Atlas 0–100 with a defined reference (global empirical history, not tracked_8: pooled tracked_8 range 25.5–43.7 is far narrower than the world distribution) | Global empirical Gini distribution; resolution of survey-base incomparability (income vs consumption — CHN/IND consumption-based surveys understate) | Decide calibration universe (global history vs tracked_8) before any curve; irregular freshness class stays |
| GROSS_CAPITAL_FORMATION_GDP | MONOTONIC_SATURATING | **RECLASSIFY → CONTEXTUAL_DEFERRED** | Saturating assumes more is never worse — disproved: very high GCF can reflect credit-driven overinvestment / inefficient allocation; the "healthy" level is economy-model-dependent (tracked_8 medians: CHN 42.4 vs GBR 18.5), so a universal band would also encode arbitrary norms | None invented; a future design needs a defensible own-norm or context model | GCF measures investment effort, NOT infrastructure quality; no authoritative healthy-band evidence documented locally | Future design candidate: deviation from the country's own investment norm |
| GDP_GROWTH | TARGET_BAND | **RECLASSIFY → CONTEXTUAL_DEFERRED** | One universal band is indefensible: potential growth differs by development stage (tracked_8 medians 2015–2025: IND 7.2 / CHN 6.1 vs JPN 0.8 / DEU 1.1) — a band would punish catch-up growth and/or reward stagnation | Own-history deviation + relative growth + potential-growth gap each need window/anchor design | No potential-output series imported; no per-country potential-growth reference | DEFER_LEVEL until the own-history-deviation design is approved |
| INFLATION_CPI | TARGET_BAND | **RECLASSIFY → CONTEXTUAL_DEFERRED** | A universal raw-CPI band would encode "2% ideal for every country" — objectives differ across countries/regimes (tracked_8 medians: IND 6.35 vs JPN 0.29); CPI is domestic price pressure only | Per-country/regime target metadata (none available) | No defensible per-country target reference imported; competitiveness needs FX + partner prices (not imported) | Series stays live for coverage; level waits for a defensible target/reference source |
| UNIT_LABOUR_COST_GROWTH | TARGET_BAND | **RECLASSIFY → CONTEXTUAL_DEFERRED** | Raw domestic ULC growth is not by itself a relative-competitiveness measure; an arbitrary zero-centered band is indefensible | None invented | FX, partner-country ULC, and inflation-regime context all missing; CHN/IND have no ULC at all | Series stays live for coverage; level stays deferred |
| CREDIT_TO_GDP_GAP | TARGET_BAND (asymmetric) | **APPROVE_FAMILY, parameters unresolved** | Core semantics confirmed: large positive gap = excess credit/vulnerability; near trend = lower cyclical stress; very negative = deleveraging/weak credit — lower is NOT always better | Asymmetric band: positive threshold/slope + negative threshold/slope, each versioned | RESEARCH QUESTION (recorded, unresolved): what positive/negative thresholds and slopes do authoritative external sources justify (BIS early-warning literature, e.g. credit-gap warning thresholds) — and how must the calibration be as-of-safe (expanding window only, never future data)? | Do NOT invent values; gather the external evidence first |
| DEBT_SERVICE_RATIO | OWN_HISTORY | **APPROVE_FAMILY — READY_FOR_IMPLEMENTATION_DESIGN, selected as the next implementation target** | Cross-country raw DSR levels deliberately not compared (BIS caution); own-history stress position is self-contained — no external calibration data needed; 104 quarters/country (2000Q1–2025Q4) support it | Design decisions required: minimum historical sample; trailing vs EXPANDING as-of calibration window (no future leakage); empirical percentile vs robust z/MAD transform (§16 prefers robust); stress-percentile → Atlas 0–100 strength mapping; early-history insufficient-sample → None never zero | None external — the design questions are answerable with existing data | Sprint 5.10 candidate: DSR OWN_HISTORY level design + implementation |
| LABOUR_PRODUCTIVITY_PER_HOUR | MONOTONIC_POSITIVE | **APPROVE direction, defer numeric level curve** | Higher PPP/hour = stronger structural productivity is sound, but no absolute 0–100 mapping exists without an external calibration distribution; tracked_8 min-max explicitly rejected (pooled tracked_8 range 33.5–90.5 is not a global distribution; CHN/IND not covered by OECD) | Expanded calibration universe decision (e.g. OECD-wide productivity distribution) | No external calibration distribution imported; CHN/IND coverage gap | Decide the expanded calibration universe before any curve; level vs growth stay separable |

**Audit consequences for the registry** (implemented in
`normalization_definitions.py`; PROPOSED Sprint 5.5 entries changed — no
accepted DEC was silently altered):

- GDP_GROWTH, GROSS_CAPITAL_FORMATION_GDP, INFLATION_CPI,
  UNIT_LABOUR_COST_GROWTH: level family → `CONTEXTUAL_DEFERRED` (explicitly
  deferred, not silently demoted — they still raise
  `NormalizationNotImplementedError`).
- GINI_INDEX: family stays MONOTONIC_NEGATIVE (direction), with "no numeric
  curve approved — 100 − Gini NOT an approved mapping" recorded in the note.
- CREDIT_TO_GDP_GAP: asymmetric TARGET_BAND confirmed; thresholds unresolved.
- DEBT_SERVICE_RATIO: OWN_HISTORY confirmed; READY_FOR_IMPLEMENTATION_DESIGN.
- LABOUR_PRODUCTIVITY_PER_HOUR: monotonic_positive direction confirmed;
  absolute level curve deferred pending expanded calibration.

**What this audit does NOT do**: no force weights, no numeric score outputs,
no force aggregation, no new normalized scores published, backtest_safe
remains False everywhere. Empirical percentiles from the profile script are
descriptive only — they are not economic truth and justify nothing by
themselves.

## Sprint 5.10 implementation status (2026-09-09) — DSR OWN_HISTORY LEVEL (DEC-019)

The FIRST non-WGI level signal is IMPLEMENTED — for EXACTLY
DEBT_SERVICE_RATIO. The level answers: "where is the country's current DSR
relative to ITS OWN historical DSR distribution available as of this scoring
snapshot?" (model version **normalization-v0.5**, method
`sprint-5.10-dsr-own-history-level-r1`).

**DSR level — IMPLEMENTED (DEC-019)**:
- Calibration = the country's EXPANDING own history of REAL observations from
  the first eligible observation through the current aligned observation,
  INCLUSIVE — via `alignment_service.own_history_as_of` (same selection
  semantics as `align_observation_as_of`: country isolation, indicator
  scoping, latest vintage per period, DEC-015 period-complete eligibility,
  no future data; read-only). No forward-fill, no interpolation, no
  synthesized or zero-filled values.
- Method: empirical mid-rank plotting position —
  `stress_percentile = 100 * (average_rank − 0.5) / n` with rank 1 = lowest
  DSR = least stress, ties = average rank (deterministic, order-independent);
  `level_score = 100 − stress_percentile` (higher DSR = greater burden =
  weaker). Endpoints NOT forced to 100/0; no clamping.
- Minimum history: `minimum_sample_n = 20` observations (ATLAS VERSIONED MODEL
  PARAMETER — NOT BIS methodology truth). Below 20 → `level_score = None`
  (never 0, never stretched); the unscored signal still returns with raw
  value, source period, freshness provenance, and the own-history counts.
- Freshness gates the CURRENT observation only (unusable → no signal) and
  NEVER scales the score; historical calibration points are not decayed.
- Provenance: typed `OwnHistoryLevelResult` (sample_n, minimum_sample_n,
  earliest/latest_source_period, rank, stress_percentile, level_score) on
  `NormalizedSignal.own_history_level`.
- Execution gate: requires BOTH the registry OWN_HISTORY level family AND an
  explicit `own_history_level_configs` entry in the model version (v0.5
  carries exactly one: DEBT_SERVICE_RATIO, min 20). A registry entry alone
  never auto-enables; no generic fallback.

**What Sprint 5.10 does NOT implement** (do not read more into it):
- **DSR relative = None** — cross-country raw-DSR ranking is PROHIBITED (BIS
  caution), by design, not a TODO.
- **DSR momentum = not implemented** — the registry 4q/8q momentum windows
  stay unapproved.
- **Confidence = None** everywhere (§17 composition unresolved).
- **NO Indebtedness force scoring exists** — no force weights, no
  aggregation, no phases; this is an INDICATOR-level signal only.
- Nothing persisted; no public API; `backtest_safe = False` (alignment is by
  observation period, not historical release date — Milestone 9 owns that).
- WGI ×3 level + momentum + relative: UNCHANGED (regression-tested;
  dispatch refactor is behavior-equivalent for DIRECT_0_100).

Live read-only smoke (Postgres, @2025-Q4): all tracked_8 score with n=104
histories — e.g. USA raw 14.1 → level 94.7115 (rank 6/104); CHN raw 18.8 →
level 2.88462 (rank 101.5/104). Boundary: CHE @2004-Q3 → raw present, n=19,
level None; CHE @2004-Q4 → n=20, first score 97.5.

## Sprint 5.11 — Credit-to-GDP gap evidence audit (2026-09-09, DEC-020)

A METHODOLOGY / EVIDENCE sprint — NO score implemented. It answers three
questions about CREDIT_TO_GDP_GAP: (1) what the official BIS/Basel literature
actually supports on the POSITIVE side; (2) whether authoritative evidence
supports treating LARGE NEGATIVE gaps as intrinsically unhealthy IN THE SAME
indicator-level score; (3) whether the DEC-018 asymmetric TARGET_BAND
classification should remain, be reframed, or be deferred.

### 1. Indicator concept (verified — Part 2)

CREDIT_TO_GDP_GAP is the credit-to-GDP ratio minus its long-run trend,
using the BIS published methodology: total credit to the private
non-financial sector (end-of-quarter outstanding debt, all domestic and
foreign sources) over the sum of the last four quarters of nominal GDP;
the trend is a ONE-SIDED (backward-looking) Hodrick-Prescott filter with
smoothing parameter λ = 400,000 (Borio & Lowe 2002; Drehmann et al. 2011 —
credit cycles are roughly 4x longer than business cycles). It is an
indicator of excessive credit build-up and financial vulnerability, adopted
under Basel III as the common reference point for countercyclical capital
buffer (CCyB) decisions. Atlas CONSUMES the provider-published BIS gap
(`WS_CREDIT_GAP`, dataflow via the BIS Stats API) — Atlas never recomputes
the ratio, an HP trend, or an alternative gap; raw observations are
untouched. Sources: [BIS Data Portal — Credit-to-GDP gaps overview](https://data.bis.org/topics/CREDIT_GAPS);
[Drehmann (2013), Total credit as an early warning indicator, BIS Quarterly Review June 2013](https://www.bis.org/publ/qtrpdf/r_qt1306f.pdf);
[BIS Statistical Bulletin Table J](https://www.bis.org/statistics/tables_j.pdf).

### 2. Three threshold concepts — never mixed (Part 3)

1. **BASEL CCyB GUIDE THRESHOLDS** — L = +2pp / H = +10pp (2010 BCBS
   guidance): a policy-communication device mapping the gap to a capital
   add-on, explicitly NOT a mechanical rule.
2. **EARLY-WARNING / CRISIS-PREDICTION THRESHOLDS** — statistical signal
   extraction (noise-to-signal minimization, ROC): the BIS 2018 exercise
   puts the credit-gap critical threshold at ~9pp (alone) and ~4pp (when
   combined with property-price gaps). These predict CRISES, not health.
3. **ATLAS NORMALIZATION CURVE PARAMETERS** — the breakpoints of a future
   Atlas 0–100 level mapping. NOTHING from (1) or (2) automatically becomes
   an Atlas score breakpoint; this sprint approves NONE.

### 3. Positive-side evidence (Part 4)

- **Basel CCyB guide (BCBS, Guidance for national authorities operating the
  countercyclical capital buffer, December 2010, bcbs187)**: the guide
  add-on is 0 below L = +2pp, rises LINEARLY to the 2.5%-of-RWA maximum at
  H = +10pp. The calibration criteria: L low enough that capital builds
  2–3 years before a crisis, high enough that no capital is required in
  normal times; H low enough that the buffer reaches its maximum BEFORE
  major historical crises (US 2007, Japan 1990s). A "more formal statistical
  exercise" found L=2/H=10 a robust type-1/type-2 error trade-off.
  Sources: [bcbs187 (December 2010)](https://www.bis.org/publ/bcbs187.pdf);
  [BCBS consultative document July 2010, bcbs172](https://www.bis.org/publ/bcbs172.pdf);
  [Drehmann, Borio & Tsatsaronis (2011), Anchoring countercyclical capital
  buffers, BIS WP 355](https://www.bis.org/publications/working-paper-355-anchoring-countercyclical-capital-buffers-role-credit-aggregates.pdf).
- **BIS 2018 early-warning exercise (Aldasoro, Borio & Drehmann, "Early
  warning indicators of banking crises: expanding the family", BIS
  Quarterly Review March 2018)**: at a 12-quarter horizon the credit-to-GDP
  gap's critical threshold is ~9pp (predicting 80% of crises at a 25.7%
  noise-to-signal ratio — the best standalone single indicator); in the
  vulnerability heat tables the AMBER zone runs ~4 to below 9 and RED is
  ≥9; combining the gap with property prices lowers the critical threshold
  to ~4pp. Earlier evidence around +10: Borio & Lowe (2002) and the BCBS
  2010 calibration (H set so the buffer maxes out ahead of major crises).
  Sources: [BIS QR March 2018 special feature](https://www.bis.org/publ/qtrpdf/r_qt1803e.htm);
  [Box A: Evaluating EWIs](https://www.bis.org/publ/qtrpdf/r_qt1803v.htm);
  [Online Appendix](https://www.bis.org/publ/qtrpdf/r_qt1803e_appendix.pdf);
  [Borio & Lowe (2002), BIS QR December 2002](https://www.bis.org/publications/qr/r-qt0212e.pdf).

Positive-side conclusion: TWO independent official lines (a policy guide
and a statistical early-warning exercise) support positive-side
vulnerability breakpoints in the +2 to +10 region. This is evidence about
EXCESS-CREDIT VULNERABILITY, NOT about any specific Atlas score value.

### 4. Negative-side evidence (Part 5) — the critical question

Searched for authoritative support for: "very negative credit-to-GDP gaps
are themselves an unhealthy debt condition that should reduce the level
score." FINDING: **no authoritative negative threshold exists, and the
BIS/Basel material treats the negative region as a phase observation, not a
health signal**:

- The Basel guide is FLAT ZERO below +2 — it assigns no rising penalty as
  the gap goes more negative; the guide simply does not trigger.
  ([bcbs187](https://www.bis.org/publ/bcbs187.pdf))
- The BIS 2014 Q&A (Drehmann & Tsatsaronis, "The credit-to-GDP gap and
  countercyclical capital buffers: questions and answers", BIS Quarterly
  Review March 2014) never analyzes negative-gap thresholds: the negative
  gap–GDP-growth correlation is "driven primarily by periods when the
  information from the indicator is of no consequence" — low-gap periods
  and POST-CRISIS periods when the buffer "would have been released".
  Release is judgmental, never gap-triggered.
  ([BIS QR March 2014](https://www.bis.org/publ/qtrpdf/r_qt1403g.htm))
- The known negative-gap MEASUREMENT problem cuts the other way: after a
  prolonged boom-bust, the HP trend is contaminated by the boom, so the
  gap "remains large and negative for an extended period after the bust" —
  the IMF's assessment of the BIS gap is that the persistent negative gap
  can UNDERSTATE renewed vulnerability and delay CCyB activation
  (several European authorities set positive CCyB rates despite negative
  Basel gaps). I.e. a deeply negative gap can be a statistical artifact,
  not an unhealthy-debt signal.
  ([IMF WP 2020/006, How Should Credit Gaps Be Measured?](https://www.elibrary.imf.org/view/journals/001/2020/006/article-A001-en.xml))
- Post-crisis deleveraging is real (association, "A" in the brief's
  distinction), but it is NOT evidence that a specific negative threshold
  predicts weakness ("B"): BIS research finds post-crisis credit
  contraction essentially uncorrelated with the pace of recovery
  ([Takáts & Upper (2013), BIS WP 416](https://www.bis.org/publications/working-paper-416-credit-and-growth-after-financial-crises.pdf)),
  and the ECB characterizes a negative gap as borrowing below what current
  macro conditions imply — weak credit, with cyclical AND structural
  drivers ([ECB blog, Mind the gap, 2026](https://www.ecb.europa.eu/press/blog/date/2026/html/ecb.blog20260126~5d9addcc3f.hr.html)).

**Conclusion: no negative-side penalty threshold is supported. None is
invented.** The deleveraging / weak-credit dimension exists but belongs to
OTHER signals (DSR own-history level — already implemented; credit growth;
output growth), not to a credit-gap penalty curve.

### 5. Basel caution — the indicator is a reference point, not a rule (Part 7)

The current Basel framework text ([CAD 20, countercyclical capital
buffers](https://www.bis.org/committees/bcbs/basel-consolidated-guidelines/module/cad/20))
says the gap "is a useful common reference point" and authorities are
expected to apply judgment rather than rely mechanistically on it; it "does
not need to play a dominant role"; assessments "should be mindful of
misleading signals" (GDP-denominator-driven increases, non-fundamental
spread moves); supplementary indicators include asset prices, funding
spreads, real GDP growth, and DEBT SERVICE CAPACITY. The 2014 Q&A adds the
mechanical-anchor answer is "no" — no single indicator is infallible and
combinations outperform singles. Documented misleading-signal modes: GDP
collapse inflating the ratio in early recessions; the trend absorbing
protracted booms (Dutch 1998–2004 example); structural breaks taking ~20
years to wash out; the endpoint problem (one-sided trends revise as data
arrive); BIS-published gaps may differ from national-authority gaps.
Implication for Atlas: a deterministic curve must not pretend the source
indicator is more definitive than its provider says it is — any future
implementation must carry these caveats as explicit score-interpretation
limits.

### 6. As-of / real-time semantics (Part 8)

The BIS published gap itself uses a one-sided, backward-looking trend (no
look-ahead in the provider's construction). Atlas's SEPARATE limitation
stands: we do NOT reliably know the historical RELEASE DATE of each
observation, so period-complete as-of scoring is NOT point-in-time
backtest safety. **BIS's one-sided HP filter does NOT solve Atlas's
release-date problem; backtest_safe stays False until Milestone 9.**

### 7. Minimum history: construction vs normalization (Part 9)

The BIS/Basel "at least 10 years of data" rule of thumb (Borio & Lowe
2002, adopted in BCBS 2010; validated in the 2014 Q&A via start-date
simulation: start-point differences in CCB levels are 0 in most cases after
10 years) belongs to CONSTRUCTING a reliable HP trend for the gap itself.
Atlas consumes the ALREADY-PUBLISHED BIS gap, whose trend BIS computed on
decades of data — so the construction-history requirement does NOT
automatically become an Atlas scoring minimum. Whether Atlas still wants
its own minimum-history parameter (e.g. for trend-revision/endpoint
stability at the scoring edge, or vintage confidence) is a SEPARATE
design question for the implementation sprint; no such minimum was
decided here.

### 8. Live tracked_8 profile (Part 10 — descriptive ONLY)

Read-only profile of the live BIS CREDIT_TO_GDP_GAP series (104 quarters
per country, 2000-Q1..2025-Q4, 832 observations):

| Country | min | p10 | p25 | median | p75 | p90 | max |
|---|---|---|---|---|---|---|---|
| CHE | −19.2 | −14.0 | −8.5 | 3.8 | 10.8 | 13.9 | 29.4 |
| CHN | −14.7 | −9.1 | −5.7 | 2.3 | 12.0 | 18.4 | 25.5 |
| DEU | −13.8 | −11.0 | −8.5 | −3.9 | 4.4 | 10.2 | 15.7 |
| FRA | −16.4 | −7.4 | 0.8 | 3.6 | 6.0 | 9.2 | 23.8 |
| GBR | −28.0 | −22.2 | −17.8 | −11.5 | 6.1 | 8.7 | 15.0 |
| IND | −23.2 | −15.0 | −11.6 | 0.3 | 8.0 | 17.1 | 22.7 |
| JPN | −29.7 | −26.9 | −17.7 | 0.6 | 6.8 | 17.4 | 27.3 |
| USA | −16.9 | −15.0 | −11.2 | −4.7 | 6.7 | 8.8 | 11.6 |
| POOLED | −29.7 | −16.2 | −9.9 | 0.4 | 7.7 | 12.4 | 29.4 |

Bucket counts (pooled): < 0: 403 · 0–2: 53 · 2–4: 48 · 4–9: 158 · 9–10:
29 · > 10: 141. These counts show the tracked_8 histories spend a large
fraction of time below trend (notably GBR/USA/DEU/JPN post-2008 — the
documented post-boom artifact) and substantial time in the Basel-guide
build-up region. **They are DESCRIPTIVE ONLY — they are NOT evidence that
any threshold is economically correct and justify no breakpoint.**

### 9. Evidence matrix (Part 11)

| Evidence / value | Source | Purpose in source | Supports for Atlas | Does NOT support |
|---|---|---|---|---|
| Gap = credit/GDP − one-sided HP trend (λ=400k) | BIS Data Portal; Drehmann 2013; BIS Bulletin Table J | Provider methodology | Consuming the published gap as an excess-credit vulnerability indicator | Recomputing or re-trending inside Atlas; any Atlas threshold |
| L = +2pp, H = +10pp, linear 0→2.5% RWA | BCBS 2010 guidance (bcbs187/bcbs172) | Policy-guide buffer add-on communication | Positive-side breakpoints in the +2..+10 region EXIST in official material; a neutral region near trend is consistent with the guide's zero zone | Atlas score VALUES at +2/+10; mechanical use; any negative-side penalty (the guide is flat zero below +2) |
| Critical threshold ~9pp (80% crises, N/S 25.7%); amber 4–9; red ≥9 | Aldasoro, Borio & Drehmann, BIS QR March 2018 | Statistical crisis prediction (noise-to-signal) | The positive side has statistical early-warning support around +4/+9 | Health scoring; per-country thresholds; that +9 should map to a specific Atlas score |
| ~4pp gap threshold (with asset prices) | Borio & Lowe 2002 | Composite early-warning calibration | Combining indicators improves signals — consistent with Atlas's multi-indicator force design | Standalone use of +4; Atlas score values |
| H set so the buffer maxes before US 2007 / Japan 1990s | BCBS 2010 calibration criteria | Policy calibration | Historical plausibility of a high positive danger region | A specific Atlas danger score |
| Flat zero below +2; post-crisis periods "of no consequence" | bcbs187; Drehmann & Tsatsaronis 2014 Q&A | CCyB design | NO negative-side penalty exists in the authoritative framework | Inventing a negative penalty curve; reading a negative gap as an unhealthy-debt level signal |
| Persistent negative gap after boom-bust = measurement artifact (understates renewed vulnerability) | IMF WP 2020/006 (assessment of the BIS gap) | Measurement critique | Treating deeply negative values as a health penalty would encode the artifact as signal | Any negative threshold; that negative gap = healthy either |
| Deleveraging uncorrelated with recovery pace | Takáts & Upper, BIS WP 416 | Post-crisis research | Negative gap as phase observation only | A negative-gap weakness threshold |
| "Common reference point", judgment, misleading signals (GDP denominator, trend turning points, breaks) | Basel framework CAD 20; 2014 Q&A | Regulatory guidance | A future curve must carry score-interpretation limits and must not be treated as definitive | A mechanical standalone Atlas rule; pretending more precision than the provider claims |
| One-sided trend avoids look-ahead | BIS methodology | Provider construction | Real-time as-of plausibility of the series | Atlas release-date safety — backtest_safe stays False |
| "≥10 years of data" rule of thumb | Borio & Lowe 2002; BCBS 2010; 2014 Q&A | Reliable HP-trend CONSTRUCTION | Nothing for Atlas directly (Atlas consumes the published gap) | A blind 10-year Atlas scoring minimum; that requirement belongs to constructing the trend |

No fake consensus: the policy-guide (+2/+10) and the statistical exercise
(~9, or ~4 with property prices) are DIFFERENT instruments with different
roles and are recorded separately.

### 10. Methodology verdict (Part 12)

**RECLASSIFY / REFRAME — CREDIT_TO_GDP_GAP level family: asymmetric
TARGET_BAND → ONE_SIDED_VULNERABILITY (DEC-020).**

Why: authoritative evidence supports positive-side excess-credit
vulnerability breakpoints (Basel CCyB guide +2/+10; BIS 2018 EWI red ~9,
amber 4–9) but does NOT support a mechanical negative-side penalty — the
Basel guide is flat zero below +2, the 2014 Q&A treats the negative region
as a no-consequence/post-release phase, and the persistent negative gap is
a documented boom-contaminated-trend artifact. The DEC-018 assumption that
"very negative = deleveraging/weak credit" justifies an indicator-level
health penalty is RETRACTED: deleveraging/weak-credit conditions are real
but belong to OTHER signals (DSR own-history level — implemented in 5.10;
credit growth; output growth), not to this indicator.

Conceptual replacement (NOT implemented this sprint): a one-sided mapping
where at-or-below-trend values carry NO excess-vulnerability penalty (the
indicator is silent about health there, consistent with the guide's zero
zone) and the level score weakens monotonically as the gap rises above a
neutral ceiling. Before ANY implementation the owner must approve: the
neutral ceiling, the positive-side curve shape, endpoint behavior, the
score interpretation of the no-excess region (is flat-max "strong" or
"no-signal"?), and how the documented caveats (GDP-denominator distortions,
trend turning points, post-bust artifacts) constrain the curve. The
provider's caution that the gap is a common reference point, not a
mechanical rule, must be carried as an explicit score-interpretation limit.
DEFER was rejected because the positive side IS defensibly supported —
deferring would discard documented, dual-source official evidence; KEEP
was rejected because the negative-side penalty has no evidence at all.

## Sprint 5.12 implementation status (2026-09-09) — CREDIT-GAP ONE_SIDED_VULNERABILITY LEVEL (DEC-021)

The owner approved the numeric Atlas curve (DEC-021), implementing the Sprint
5.11 verdict. Enabled for EXACTLY CREDIT_TO_GDP_GAP, via an explicit
`one_sided_vulnerability_configs` entry in the model version (the same
execution-gate pattern as DSR: a registry family alone never auto-enables —
a model version without the entry raises). Model version bumped
`normalization-v0.5` → `normalization-v0.6` (method
`sprint-5.12-credit-gap-one-sided-level-r1`). All v0.5 WGI + DSR
configuration is unchanged.

The owner-approved curve (Atlas MODEL PARAMETERS, versioned):

| Credit-to-GDP gap (pp) | level_score |
|---|---|
| ≤ +2 (including ALL negative gaps) | 50.00 |
| +2 < gap < +10 | linear: 50 at +2 falling to 0 at +10 (−6.25 per pp) |
| ≥ +10 | 0.00 |

Verbatim owner table: −20 → 50.00, 0 → 50.00, +2 → 50.00, +4 → 37.50,
+6 → 25.00, +9 → 6.25, +10 → 0.00, +20 → 0.00.

Design decisions locked by the approval:

- **Neutral ceiling = +2pp, saturation = +10pp.** The breakpoints COINCIDE
  with the Basel CCyB guide's L/H reference points (bcbs187) — but the
  guide's role is a policy add-on communication reference, and the SCORE
  mapping (50/0) is an Atlas choice, not Basel methodology truth. The three
  threshold concepts separated in Sprint 5.11 §2 stay separated.
- **No-excess region = 50, deliberately NOT 100.** Absence of excess credit
  is not evidence of strength — the indicator is SILENT about health at or
  below +2. This answers the Sprint 5.11 open question (flat-max "strong"
  vs "no-signal"): the region reads as NEUTRAL, per §1's 50 = neutral
  middle reference.
- **Negative gaps carry NO penalty** (DEC-020 retraction preserved): deep
  negatives score the same neutral 50 as +2.
- **Endpoint clamps:** flat 50 at/below +2 (no floor), flat 0 at/above +10
  (no cap); strictly linear in between.
- **No minimum-history gate:** the curve is parametric (unlike the DSR
  own-history calibration) — any single eligible observation scores.
- **Freshness gates the current observation only and NEVER scales the
  score** (quarterly class); too stale → no signal, never zero.
- **Unchanged dimensions:** relative stays CONTEXTUAL_DEFERRED (None),
  registry momentum windows (4q/8q) stay UNAPPROVED (momentum None),
  confidence None, backtest_safe False.

Score-interpretation limits carried from the Sprint 5.11 Basel caution: the
gap is a common reference point, NOT a mechanical standalone rule —
GDP-denominator distortions, trend turning points, structural breaks,
endpoint revisions, and post-bust artifacts limit what this score can
claim about underlying debt health.

Live smoke (tracked_8 @2025-Q4, read-only, model normalization-v0.6): USA
−11.54 → 50, CHN −7.69 → 50, CHE −17.04 → 50, DEU −3.96 → 50, FRA −15.11
→ 50, GBR −17.82 → 50, JPN +6.78 → 20.10, IND +1.74 → 50. Seven of eight
sit in the neutral region at this snapshot; JPN is the only one in the
declining region (descriptive — NOT evidence the breakpoints are
economically correct; the Sprint 5.11 evidence matrix is the justification).

Tests: 318 offline (312 + 6 net new: the owner-table regression through the
full align → freshness → curve path, the pure-curve clamps/continuity/
config-validation, the no-auto-enable execution gate, no-observation →
None, too-stale → None, freshness-decays-but-never-scales,
other-dimensions-stay-None; the Sprint 5.11 "still unscored" regression was
replaced by these).

## Sprint 5.13 methodology status (2026-09-09) — CONFIDENCE LAYERING + WGI UNCERTAINTY AUDIT (DEC-022)

Architecture sprint: NO scores changed, NO confidence numbers invented, NO
code change required. Every Sprint 5.12 numerical output is unchanged; the
model version stays `normalization-v0.6` (a documentation/design sprint never
bumps the version — a future FIRST EXECUTABLE confidence formula does).

Outcomes:

1. **Confidence layering resolved (§10 rewritten).** INDICATOR confidence
   (trust in one indicator's signal) and FORCE confidence (completeness of a
   force's input coverage) are now separate sections with an explicit rule:
   coverage completeness and proxy ceilings are FORCE-LAYER concepts and are
   never folded into an individual NormalizedSignal. A high-quality fresh
   POLITICAL_STABILITY_WGI_SCORE signal is not lowered because the Internal
   conflict force it feeds is PARTIAL/ceiling-capped.
2. **Confidence ≠ strength, permanently.** `level_score = 90, confidence =
   0.4` means "strong measured condition, weak trust in the estimate" — it
   must never become 36. Economic scores are never multiplied by confidence;
   `relative_score *= confidence` and `momentum *= confidence` are
   prohibited. Confidence travels ALONGSIDE the economic dimensions.
3. **Confidence ≠ freshness.** `freshness_factor` (DEC-013 exponential
   policy) is the one source of freshness truth; a future confidence may
   CONSUME it but never recomputes age with another formula, and confidence
   is never simply set equal to freshness_factor.
4. **WGI uncertainty series audited live (read-only probe, 2026-09-09).**
   Verified against WB API v2: score series `GOV_WGI_{RL,CC,PV}_SC` (WDI,
   source 2) plus dedicated-source (source id 3) uncertainty series
   `GOV_WGI_{dim}.SC_LB` / `.SC_UB` (90% CI bounds FOR THE GOVERNANCE SCORE),
   `.SE` (standard error OF THE ESTIMATE), `.SR` (number of underlying
   sources). All 8 tracked countries have all 4 uncertainty series for all
   26 score years (1996–2024 minus the 1997/1999/2001 biennial gaps; no 2025
   values yet); one-to-one year alignment with the score series is PERFECT
   for every country/dimension (208 obs per series = 8 × 26). Scale facts:
   LB ≤ score ≤ UB for all 624 points (bounds bracket the score on the SAME
   0–100 score scale; UB clamps at 100, e.g. CHE CC 2020); the CI is
   symmetric around the score; SE is on the UNDERLYING ESTIMATE scale
   (values ~0.15–0.25), and empirically width ≈ 56.5 × SE — NOT the 65.8 × SE
   a naive 90%-normal multiplier (20 × 2 × 1.645) would give — so SE does NOT
   reconstruct the published bounds. SR is integer-valued count data
   (observed range 4–16). Sample 2024 values (score / LB / UB / width / SE /
   SR): CHE RL 87.32 / 82.04 / 92.60 / 10.56 / 0.1871 / 10; USA RL 73.52 /
   69.25 / 77.78 / 8.53 / 0.1511 / 13.
5. **Initial WGI uncertainty input set selected: LB + UB + SR (Option B of
   A/B/C).** CI width = UB − LB is the primary measurement-uncertainty
   diagnostic — directly on the imported score scale, intuitive measurement
   meaning, no scale mixing. SR (source count) is a second, distinct
   data-richness diagnostic. SE is DEFERRED: it is on the estimate scale,
   cannot reconstruct the published CI (the 56.5 vs 65.8 finding), and adds
   no score-scale information the bounds do not already carry. SE can be
   added later through the same mechanism if an approved methodology ever
   needs estimate-scale precision. NO CI-width or source-count → confidence
   curve is designed or approved here — the inputs are identified, their
   numeric composition deliberately deferred.
6. **Storage architecture audited; representation chosen (DEC-022).** The
   WGI uncertainty data must NOT become ordinary canonical indicators or
   observations (the full decision matrix is in this section below). Chosen:
   dedicated auxiliary-diagnostics storage associated with the BASE
   indicator. It requires a migration → NOT implemented this sprint; the
   minimal design is specified for Sprint 5.14.
7. **As-of semantics for uncertainty locked.** Any future WGI confidence
   uses uncertainty associated with the SAME eligible WGI source period —
   same country, same dimension, same source period as the aligned score
   observation, latest appropriate vintage. Never a later year's bounds,
   never today's source count, never another country's uncertainty. No
   future uncertainty metadata; backtest_safe stays False (release dates
   remain unavailable).
8. **Missing-uncertainty rule locked.** Score present but measurement
   uncertainty missing → do NOT assume perfect confidence, do NOT set any
   factor to 1, do NOT set confidence to 0. The score itself stays usable;
   the measurement-uncertainty component is UNKNOWN (None) until an approved
   methodology says how partial confidence components aggregate. Missing
   confidence metadata ≠ missing economic observation.
9. **No arbitrary provider-quality constants.** No World Bank = 0.95 /
   BIS = 0.97 style numbers exist or are approved. Qualitative provenance
   categories may be TYPED later (official_primary, official_republished,
   proxy_measure, perception_composite); any numeric mapping is a future,
   calibrated, versioned decision. SIPRI-spending-as-input belongs to FORCE
   proxy completeness, not a fake low source-quality score.

### Sprint 5.13 storage-architecture decision matrix (WGI uncertainty)

Option A — auxiliary canonical indicators (e.g.
`RULE_OF_LAW_WGI_LOWER_BOUND` as Indicator + SourceSeries + Observation
rows): **REJECTED.** Would appear in `/api/indicators` as economic
indicators, inflate the per-country `indicator_count` (it counts distinct
sourced indicators), add rows to the catalog the force-coverage aggregate
reads, create "25 → 34 indicators" semantic confusion, and let uncertainty
metadata masquerade as a force input. The immutable-raw and
provenance requirements do not need this pollution.

Option B — multiple SourceSeries under the EXISTING WGI canonical
indicator (score + LB + UB + SR all pointing at e.g.
`RULE_OF_LAW_WGI_SCORE`): **INVALID.** `align_observation_as_of` and
`own_history_as_of` select by indicator, and the latest-vintage subquery
groups by (source series, period) — with two active series carrying the
same period, alignment could return an LB instead of the score
(nondeterministic tie-break by row id). Exactly the forbidden
interchangeable-resolution design. Also, the WB adapter resolves external
series to a canonical indicator, so persisting LB through the normal path
would store bound values as score observations.

Option C — dedicated auxiliary/diagnostics storage associated with the
base indicator: **CHOSEN.** A separate table (working name
`indicator_diagnostics`): rows keyed to the BASE canonical indicator
(RULE_OF_LAW_WGI_SCORE etc.) + country + diagnostic kind
(ci_lower_bound / ci_upper_bound / source_count) + provider series code +
period + value + retrieved-at + vintage semantics. Keeps the canonical
catalog, indicator counts, force coverage, normalization registry, and
alignment ALL untouched; provider values stay raw with revision/vintage
handling (WGI's 2025 revision DID revise historical values); extensible
beyond WGI (any provider can add diagnostic kinds); uncertainty can never
enter force coverage or score alignment. Deliberately does NOT create
SourceSeries rows for the uncertainty series — a SourceSeries pointing at
the base indicator is one careless ingest away from Option B's failure;
the diagnostics ingestion path is structurally separate from
`persist_observations`. **Requires an Alembic migration → STOPPED before
implementation; Sprint 5.14 spec below.**

Option D — provider metadata stored in per-observation raw_payload:
**FACTUALLY UNAVAILABLE.** The WB API v2 record for the score series
carries only indicator/country/date/value/unit/obs_status/decimal — no
uncertainty fields. The uncertainty series are separate source-3 series;
the provider does not transmit them alongside the score. (raw_payload
remains good provenance hygiene for whatever the provider DOES carry.)

Evaluation axes (all options): immutable raw-data rule, revision/vintage
preservation, source provenance, country isolation, period alignment,
API/catalog pollution, force-coverage pollution, normalization ambiguity,
future extensibility beyond WGI, migration complexity. C wins on every
axis except migration complexity — and forcing the data through A/B/D to
avoid a migration is the exact failure this audit exists to prevent.

### Sprint 5.14 spec (minimal, if the owner accepts the recommendation)

1. Alembic migration: `indicator_diagnostics` table (country_id FK,
   indicator_id FK = base canonical indicator, data_source_id FK,
   diagnostic_kind, external_series_code, period_start, value,
   observation_date, retrieved_at, vintage_number,
   supersedes-diagnostic-id optional; unique identity
   (country, indicator, kind, period, vintage)). No SourceSeries rows.
2. Ingestion: a WB fetch path for GOV_WGI_{dim}.SC_LB/.SC_UB/.SR reusing
   the adapter's SSL/date conventions but persisting ONLY into the
   diagnostics table (never `persist_observations`); idempotent,
   revision-aware like the observation path; recorded as IngestionRun.
3. Derived-layer lookup helper: diagnostics for (country, base indicator,
   kinds) at the ALIGNED source period, latest vintage — the same-period
   rule above; missing → None.
4. Nothing else: no confidence formula, no NormalizedSignal change, no
   model-version bump, no public API.

## Sprint 5.14 implementation status (2026-09-09) — DIAGNOSTICS STORAGE / PERSISTENCE / LOOKUP FOUNDATION

The owner accepted the DEC-022 recommendation. Items 1 and 3 of the spec
above are implemented, plus the typed representations item 2 needs (the
LIVE WB FETCH for `GOV_WGI_{dim}.SC_LB/.SC_UB/.SR` is deliberately NOT —
that is Sprint 5.15). Model version stays **normalization-v0.6**; this
sprint changed raw auxiliary-data capability only.

Implemented (offline-verified, 340 tests):

1. **`indicator_diagnostics` table** (Alembic `e3a7c94b1d51`, applied to
   the dev DB; observations/indicators/source_series counts verified
   unchanged): rows keyed to the BASE canonical indicator + country +
   DataSource + `diagnostic_kind` (exactly `ci_lower_bound` /
   `ci_upper_bound` / `source_count` — no SE) + `provider_source_code`
   (WB dedicated WGI source id "3", distinct from the WDI source id 2 of
   the score series) + exact `provider_series_code` (e.g.
   `GOV_WGI_RL.SC_LB`) + `period_start` + raw `value` + `retrieved_at` +
   `vintage_number` + `raw_payload`. Deliberately NO `source_series_id`
   and no SourceSeries rows; DB-unique identity
   `uq_indicator_diagnostics_identity` (country, indicator, source,
   provider source, provider series, kind, period, vintage) + lookup
   index (country, indicator, kind, period).
2. **Immutable persistence** (`persist_indicator_diagnostics` +
   `IndicatorDiagnosticDTO`, structurally separate from
   `persist_observations`): insert vintage 1 → skip identical → new
   vintage N+1 on changed value; old vintages retained, never
   overwritten; no IndicatorRevision rows (the vintages are the
   history); caller owns the transaction. Unknown identities (unknown
   country/indicator, or a DTO whose provider identity does not match
   the expected spec) are rejected, not stored free-form; `source_count`
   must be a non-negative integer-valued float (9.7 is rejected, never
   rounded); all values must be finite.
3. **WGI diagnostic spec registry** (9 specs = 3 indicators × 3 kinds,
   series codes verified Sprint 5.13; provider-diagnostic metadata
   only — seeds nothing): persistence and lookup both tie to the
   EXPECTED provider-series identity.
4. **Exact-period lookup** (`get_indicator_diagnostics_for_period`):
   latest-vintage values by kind at the ALIGNED source period, country-
   scoped (ISSUE-004 class), exact period match — no prior-year
   fallback, no future-year borrowing, no today's-latest; missing →
   None (missing ≠ perfect ≠ zero; the base Observation stays usable);
   if multiple provider identities claim one logical diagnostic the
   lookup RAISES, never resolves by row order.
5. **Catalog/coverage isolation verified**: diagnostics never create
   Observation/SourceSeries/Indicator rows; `/api/indicators`,
   per-country `indicator_count` (still 25 canonical indicators), force
   coverage, WGI/DSR/credit-gap normalization outputs and
   `confidence = None` are all regression-tested unchanged.

### CI-width boundary caution (methodology note, storage is raw either way)

Future WGI confidence work must NOT assume raw `SC_UB − SC_LB` is an
unbiased precision measure everywhere: published WGI score bounds clip
at the 0/100 score boundaries (e.g. UB clamps at 100 — CHE CC 2020),
so boundary clipping can compress observed CI width near the scale
ends. CI width and source count may also carry overlapping information
— future confidence composition must test for double-counting. This
sprint only stores the RAW provider values; no correction or
transformation is applied or implied.

## Sprint 5.15 implementation status (2026-09-09) — WGI DIAGNOSTIC LIVE INGESTION

Item 2 of the spec above is implemented and executed against the live
API: the 9 owner-approved diagnostic series are now IMPORTED into
`indicator_diagnostics`. Model version stays **normalization-v0.6**;
`confidence` stays None everywhere; backtest_safe stays False (provider
RELEASE DATES are still not stored — do not overclaim historical
knowledge safety).

Implemented and live-verified:

1. **Dedicated source-3 fetch path**
   (`app/data_sources/world_bank_wgi_diagnostics.py`): requests each
   diagnostic series with the EXPLICIT `source=3` parameter (dedicated
   WGI source, distinct from the WDI source 2 of the score series) and
   VALIDATES the response provider identity — metadata `sourceid`,
   each record's `indicator.id`, and `countryiso3code` must match the
   expected spec or the fetch raises (never retried, never silently
   adapted). Returns `IndicatorDiagnosticDTO`s only — never an
   observation DTO; nulls skipped; values RAW (no clamping, no
   rounding); annual `YYYY` → `period_start = YYYY-01-01` matching the
   WGI score convention.
2. **Diagnostic ingestion + IngestionRun**
   (`app/services/wgi_diagnostic_ingestion.py`): one run per
   country × diagnostic series with `run_metadata.data_kind =
   "indicator_diagnostic"` + base_indicator_code + diagnostic_kind +
   provider_series_code + provider_source_code; persists ONLY via
   `persist_indicator_diagnostics`; caller owns the transaction; fetch
   failures recorded as failed runs, per-series failure isolation.
3. **Separate batch CLI** (`scripts/ingest_wgi_diagnostics.py`):
   --country/--all-countries, --indicator/--all-indicators,
   --kind/--all-kinds, --start/--end; transient-only retry (network/5xx
   up to 3 attempts; 4xx/parse/spec-identity never); deliberately NOT
   part of `ingest_world_bank.py --all-mapped`.
4. **Live import verified (read-only post-validation)**: 1872 rows =
   exactly the expected 8 × 3 × 3 × 26 (624 per kind, 624 per WGI
   indicator, 234 per country; 1996–2024 with the biennial gaps only),
   all vintage 1, 0 duplicate identity groups; **LB ≤ score ≤ UB for
   all 624/624 latest-vintage score points**; SR all finite/integer/
   non-negative (observed range 4–16, descriptive); perfect one-to-one
   score-year alignment; canonical isolation — Indicator 25 /
   SourceSeries 19 / Observation 5647 unchanged. Idempotent re-run:
   CHE RL all kinds → 0 inserted / 78 skipped / 0 revised. Exact-period
   lookup smoke: CHE Rule of Law @2025-Q2 → aligned 2024 score 87.32
   with 2024 LB 82.04 / UB 92.60 / SR 10 (CI width 10.56 displayed for
   inspection ONLY — not attached to any signal); a 2025 lookup returns
   None (no future/latest-available fallback).

NOT done (deliberately): no confidence formula, no CI-width or SR curve,
no NormalizedSignal diagnostics field, no force confidence, no public
diagnostics API, no frontend. The imported data is confidence INPUT
DATA only; the Sprint 5.14 boundary caution above applies to every
future use.

## Sprint 5.16 methodology status (2026-09-09) — WGI CONFIDENCE CALIBRATION AUDIT + DIAGNOSTIC HARDENING

A METHODOLOGY / EMPIRICAL RESEARCH sprint. NO numeric confidence was
implemented; NO NormalizedSignal output changed; the model version stays
**normalization-v0.6**; `confidence` stays None everywhere; `backtest_safe`
stays False. The profile is DESCRIPTIVE / READ-ONLY — it is not proof that
any empirical distribution is economic truth.

Two outputs:

1. **Transaction hardening** — `wgi_diagnostic_ingestion.py` now
   distinguishes recoverable `DBAPIError` (savepoint rolled back, FAILED
   `IngestionRun` retained, non-raising outcome) from
   `DBAPIError.connection_invalidated = True` (the DB connection is dead;
   the outer transaction CANNOT persist a FAILED audit row — the error
   PROPAGATES so the caller can rollback/close/retry; no false audit-record
   promise is made). Focused regression coverage for both cases.
2. **WGI confidence calibration audit** — a read-only empirical profile
   (`apps/api/scripts/wgi_confidence_profile.py`) of the 624 aligned
   score/diagnostic rows, plus this decision matrix and verdict.

### Empirical profile (624 rows = 8 countries x 3 WGI dimensions x 26 score years)

Dataset integrity (Part 2): exactly 624 rows; 208 per dimension; 78 per
country; 24 per year (8 x 3); 0 missing LB/UB/SR; 0 duplicate identities;
0 LB>score violations; 0 score>UB violations. The dataset is clean and
exactly the expected size.

CI width (Part 3): pooled median 11.54 (min 7.65, max 17.04). By
dimension: RL median 9.23 (narrowest), CC median 11.54, PV median 13.88
(widest). By country: CHE median 13.10 (widest), IND median 10.58
(narrowest). The CI is symmetric around the score for unclipped rows
(median margin asymmetry ~0).

Boundary clipping (Part 4): 9/624 (1.4%) upper-clipped (UB >= 100); 0
lower-clipped. All 9 are CHE (7 CC + 2 PV). Clipping is rare and
concentrated in one country. The margin asymmetry for upper-clipped rows
is small (median 0.70) — the CI is nearly symmetric even when clipped.
Raw CI width is NOT an unbiased precision measure at the upper boundary,
but the distortion is small and localized.

Score vs width (Part 5): pooled Pearson 0.080, Spearman 0.052 —
essentially no correlation between score level and CI width. A
width-based confidence would NOT systematically penalize high or low
governance scores. Per-dimension correlations are weak (0.21-0.39).
Unclipped rows: 0.07/0.04 — no correlation. CI width is NOT a proxy for
score level.

Source count (Part 6): pooled median 9 (min 4, max 16). By dimension: RL
median 12 (most sources), CC median 10, PV median 8.5 (fewest). By
country: IND median 11.5 (most), CHE median 8 (fewest). Temporal trend:
Pearson 0.543, Spearman 0.554 — SR increases over time (median 6 in 1996
to 10.5 in 2024). SR is NOT stationary; a confidence based on SR would
partly encode "newer = more sources" rather than purely measurement
quality.

CI width vs SR overlap (Part 7): pooled Pearson -0.829, Spearman -0.797
— STRONG negative correlation. More sources -> narrower CI. Per
dimension: RL -0.85/-0.87, CC -0.87/-0.92, PV -0.96/-0.97. The median CI
width by integer SR is monotonically decreasing (SR=4 -> 17.04, SR=16 ->
7.79). **SR and CI width are highly informationally redundant — they
carry largely the same measurement-uncertainty signal. Combining both
in a confidence formula would double-count the same information.**

Dimension differences (Part 8): RL has the narrowest CI (median 9.23) and
most sources (median 12); PV has the widest CI (median 13.88) and fewest
sources (median 8.5); CC is in between. The dimensions differ
systematically. A single pooled calibration would systematically assign
PV lower confidence than RL — whether this is correct depends on whether
the dimension differences reflect genuine measurement quality
differences or the inherent difficulty of measuring political stability
vs rule of law. The profile cannot distinguish these.

Country differences (Part 9): CHE stands out (widest CI median 13.10,
fewest sources median 8, all 9 clipped rows). IND has the most sources
(median 11.5). Country differences exist but are less pronounced than
dimension differences. A pooled calibration would give CHE
systematically lower confidence — whether this reflects CHE's genuinely
wider measurement uncertainty or a country-specific measurement-system
artifact cannot be determined from the data alone.

Time trends (Part 10): SR increases over time (Pearson 0.543 vs year);
CI width decreases over time (implied by the strong SR-width negative
correlation). Any empirical calibration (percentile-based) faces a
leakage / drift tradeoff: full-history calibration leaks future
distribution information; expanding-window calibration is as-of safe but
makes confidence drift over time as measurement systems improve. A fixed
mapping avoids leakage but is arbitrary without an external calibration
basis.

### Calibration option matrix (Part 10)

| Option | Meaning | As-of safe? | Leakage | Arbitrary? | Defensible now? |
|---|---|---|---|---|---|
| A. Fixed provider-scale mapping | A fixed function from raw CI width (or SR) to a confidence component | Yes (same for all snapshots) | None | Yes — no empirical grounding for the mapping shape | NO — arbitrary without external calibration |
| B. Expanding own-history percentile | Country's own expanding CI-width history -> percentile | Yes (expanding only) | None | Moderate — early years tiny n; drifts as measurement improves | PARTIALLY — as-of safe but unstable early + drifts |
| C. Expanding cross-country percentile | All countries' expanding CI-width history for one dimension -> percentile | Yes (expanding only) | None | Moderate — pools countries with different measurement systems | PARTIALLY — as-of safe but encodes development status |
| D. Full-history percentile | Percentile using ALL history (including future) | NO | YES — future data | Low | NO — leaks future data |
| E. tracked_8 cross-sectional percentile | Current CI width ranked within tracked_8 at the same snapshot | Yes (same snapshot) | None | High — n=8 is a weak distribution; not global measurement quality | NO — tracked_8 is not a measurement-quality reference |
| F. Diagnostics-only / no scalar | Keep LB/UB/SR as diagnostic provenance; do not collapse to a scalar | N/A | None | None | YES — preserves all information; defers the arbitrary choice |

### Freshness composition (Part 11)

The composition with freshness (multiplication, weighted arithmetic mean,
weighted geometric mean, minimum/bottleneck, or separate diagnostics
without scalar composition) is UNRESOLVED. Each option has distinct
semantics:

- Multiplication: a single bad component tanks the whole (semantically
  correct for "AND" trust but harsh).
- Weighted arithmetic mean: a bad component only partially reduces
  confidence (may overstate trust).
- Weighted geometric mean: balances (a zero in one component zeroes the
  product; less harsh than pure multiplication on partial degradation).
- Minimum/bottleneck: the weakest link dominates (conservative; may be
  too harsh).
- Separate diagnostics without scalar composition: preserves all
  information; defers the aggregation decision.

No composition rule has an evidence basis. The permanent rules
(confidence != freshness, confidence != strength, missing != perfect !=
zero) constrain the choice but do not resolve it.

### Source quality (Part 12)

WGI is a perception_composite (aggregated expert assessments + survey
data), NOT an official_primary source. Source quality should remain
PROVENANCE ONLY for now — typed as an ordinal enum later
(official_primary / official_republished / proxy_measure /
perception_composite), NOT a numeric constant. No "World Bank = 0.95" or
"WGI = 0.85" is approved or defensible.

### Method sufficiency / scalar vs dimension-specific (Part 13)

A single scalar confidence for the entire NormalizedSignal would HIDE
the distinction between "level is well measured but momentum is
unavailable" and "level is poorly measured." The recommendation is that
confidence should eventually be PER-DIMENSION (level_confidence,
relative_confidence, momentum_confidence), not one scalar. This is a
methodology recommendation only — no schema change is implemented this
sprint.

### Verdict: DEFER_NUMERIC_CONFIDENCE

**Atlas cannot yet define a defensible numeric indicator confidence for
the WGI x3.** The deferral is a durable methodology decision, not a
postponement of an obvious answer. The reasons:

1. **CI width and SR are highly redundant** (Pearson -0.83). Combining
   both double-counts the same measurement-uncertainty signal; using
   only one discards the other. No evidence basis exists to choose one
   as the sole input or to weight them in a joint formula.
2. **Dimension differences are substantial and unexplained.** RL, CC,
   and PV have systematically different CI widths and SR distributions.
   A pooled calibration would systematically favor RL over PV; a
   per-dimension calibration would need a per-dimension evidence basis
   that does not exist. The profile cannot distinguish genuine
   measurement-quality differences from inherent concept difficulty.
3. **Temporal trends make empirical calibration leaky or drifting.**
   Full-history calibration leaks future distribution information;
   expanding-window calibration is as-of safe but makes confidence drift
   as measurement systems improve. A fixed mapping avoids leakage but
   is arbitrary without an external calibration basis.
4. **No external calibration basis exists** for mapping raw CI width
   (or SR) to a 0-1 confidence value. Any mapping (linear, percentile,
   rank) would be an arbitrary choice without evidence — the exact
   failure mode this project's methodology forbids.
5. **Freshness composition is unresolved.** No composition rule
   (multiplication, weighted mean, geometric mean, minimum, separate
   diagnostics) has an evidence basis.
6. **A single scalar confidence would hide dimension-specific trust.**
   The eventual confidence architecture should be per-dimension, not
   one scalar — but that schema decision is not this sprint's work.

**What additional evidence / data / methodology is required before
numeric confidence can be defensibly implemented:**

- An external calibration basis for mapping raw CI width (or SR) to a
  0-1 confidence value (e.g. WB/WGI methodology documentation on the
  relationship between CI width and estimate reliability; or a
  peer-reviewed calibration study).
- A decision on whether confidence is pooled across WGI dimensions or
  per-dimension — and if per-dimension, a per-dimension evidence basis.
- A decision on the calibration window (fixed mapping vs expanding
  own-history vs expanding cross-country) — and if empirical, an
  as-of-safe expanding-window design that does not drift.
- A decision on the freshness composition rule (multiplication, weighted
  mean, geometric mean, minimum, or separate diagnostics) with an
  evidence basis.
- A decision on whether confidence is one scalar or per-dimension
  (level_confidence / relative_confidence / momentum_confidence).
- Resolution of the CI-width / SR redundancy: which is the primary
  measurement-uncertainty input, and how (if at all) the other
  contributes without double-counting.

Until these are resolved, the diagnostics remain INPUT DATA only; the
Sprint 5.14 boundary caution (raw CI width is not unbiased at the 0/100
boundaries) and the Sprint 5.13 permanent rules (confidence != strength,
confidence != freshness, missing != perfect != zero, no arbitrary
provider-quality constants) apply to every future use.

## Sprint 5.17 methodology status (2026-09-09) — GINI CALIBRATION UNIVERSE + COMPARABILITY AUDIT

A METHODOLOGY / EMPIRICAL RESEARCH sprint. NO Gini level_score was
implemented; NO NormalizedSignal output changed; the model version stays
**normalization-v0.6**; `confidence` stays None everywhere; `backtest_safe`
stays False; the Wealth / opportunity / values gaps force stays PARTIAL
(DEC-009). The profile is DESCRIPTIVE / READ-ONLY — it is not proof that any
empirical distribution is economic truth.

Two outputs:

1. **Provider semantics + comparability audit** — verified what
   `SI.POV.GINI` represents (World Bank Poverty and Inequality Platform;
   0–100 scale; higher = more inequality; mixes income-based and
   consumption-based surveys; the WB API does NOT expose a per-observation
   welfare-concept tag).
2. **Calibration universe audit** — a read-only empirical profile
   (`apps/api/scripts/gini_calibration_profile.py`) of both the tracked_8
   imported data (187 obs) and the broader WB global Gini universe (2430
   country-year observations, 171 countries, 1963–2025), plus this decision
   matrix and verdict.

### Part 1 — Provider semantics (verified)

`SI.POV.GINI` (World Bank, Poverty and Inequality Platform / PIP):
- Scale: 0–100, where 0 = perfect equality, 100 = perfect inequality.
- Higher = more inequality. Direction CONFIRMED (DEC-018: MONOTONIC_NEGATIVE).
- Welfare concept: **mixes income-based and consumption-based surveys**.
  High-income economies (USA, CHE, DEU, FRA, GBR, JPN) use income-based
  surveys (LIS Database / EU-SILC; after-tax income). Most low- and
  middle-income countries (including CHN, IND) use consumption-based
  surveys.
- **The WB API does NOT expose a per-observation welfare-concept tag.**
  The PIP methodology handbook documents that comparability breaks exist
  (questionnaire changes, welfare-aggregate changes) and provides a binary
  within-country comparability indicator — but NOT a cross-country
  welfare-concept classification exposed via the WDI API.
- PIP explicitly cautions: "Changes in questionnaire design imply that
  poverty estimates within countries become incomparable." OWID states:
  "consumption tends to be more evenly distributed than income" — so a
  consumption-based Gini is systematically LOWER than an income-based Gini
  for the same true inequality.
- Survey definitions can vary through time; national vs harmonized
  definitions exist (PIP harmonizes where possible but country-specific
  decisions remain).

### Part 2 — Tracked_8 Gini coverage (live DB, latest vintage)

| Country | n | first | latest | min | median | max | latest val | welfare concept (hint) |
|---|---|---|---|---|---|---|---|---|
| USA | 35 | 1990 | 2024 | 38.0 | 40.8 | 41.9 | 41.8 | income (LIS) |
| CHE | 21 | 1992 | 2022 | 31.6 | 33.0 | 34.3 | 33.8 | income (LIS) |
| CHN | 20 | 1990 | 2022 | 32.2 | 38.65 | 43.7 | 36.0 | consumption (grouped data) |
| DEU | 32 | 1991 | 2022 | 28.1 | 30.4 | 33.7 | 33.7 | income (LIS) |
| FRA | 29 | 1990 | 2023 | 29.7 | 32.0 | 33.7 | 31.8 | income (EU-SILC/LIS) |
| GBR | 32 | 1990 | 2021 | 32.4 | 35.0 | 38.9 | 32.4 | income (LIS) |
| JPN | 13 | 2008 | 2020 | 30.7 | 32.3 | 34.6 | 32.3 | income (LIS) |
| IND | 5 | 1993 | 2022 | 25.5 | 27.7 | 28.8 | 25.5 | consumption (South Asia) |

Pooled tracked_8: n=187, min=25.5, p10=29.9, p25=31.65, median=33.1,
p75=38.35, p90=41.1, max=43.7.

**Welfare-concept hint is from official PIP documentation, NOT from the
WB API.** The WB API does not expose a per-observation welfare-concept
field. The hint is a methodology-level classification, not a per-row
metadata column that could drive a defensible automated adjustment.

The income-vs-consumption difference is visible in the data: IND
(consumption) median 27.7 is the lowest; USA (income) median 40.8 is the
highest. A single global curve would systematically score consumption-based
countries as "more equal" than they really are — conflating a
measurement-concept difference with a true inequality difference.

### Part 3 — Why `100 - Gini` is not approved

`level_score = 100 - Gini` would imply that a raw Gini of 40 has an
Atlas-defined absolute economic meaning (level 60). No such meaning has
been approved. The 0–100 Gini scale is a Lorenz-curve area, not an Atlas
strength scale. A raw-Gini-to-level mapping requires a calibration
reference (global empirical distribution, normative threshold, or
external justification) — none exists. `100 - Gini` is NOT an approved
mapping (DEC-018) and remains NOT approved.

### Part 4 — Calibration universe options

| Option | Economic meaning | Sample size | Global representativeness | Cross-country comparability | As-of safe? | Future leakage | Sensitivity to coverage | Sensitivity to survey-concept mix | Versioning | Complexity | Defensible now? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A. tracked_8 pooled history | Low — 8 countries are not a global inequality distribution | 187 obs | NONE — range 25.5–43.7 vs world 20.2–71.1 | Weak (income + consumption mixed) | No (full history) | Yes (encodes future) | High (8 only) | High (CHN/IND consumption) | v0.7 bump | Low | NO — tracked_8 is not a global inequality distribution |
| B. tracked_8 same-year cross section | Low — n=8 is a weak distribution | 8 per year | NONE | Weak | Yes (same snapshot) | None | Very high (n=8) | High | v0.7 bump | Low | NO — n=8 is too sparse and not global |
| C. Full WB global history | Moderate — 171 countries is broad | 2430 obs | High | Weak (income + consumption mixed, no per-obs tag) | NO (full history) | YES — leaks future distribution + composition | Moderate | High (unavoidable) | v0.7 bump | Moderate | NO — leaks future data |
| D. WB global same-year cross section | Moderate | 57–86 per representative year | Moderate (sparse some years) | Weak | Yes (same snapshot) | None | High (sparse years: 2025 n=4) | High | v0.7 bump | Moderate | PARTIALLY — as-of safe but sparse + concept-mixed |
| E. Expanding global history (as-of) | Moderate | Grows over time | Moderate → High | Weak | Yes (expanding only) | None (if strictly expanding) | Moderate | High | v0.7 bump | High (window logic) | PARTIALLY — as-of safe but drifts as coverage/concept mix changes |
| F. Welfare-concept-specific global calibration | High — separates income vs consumption | Requires per-obs metadata | High within each group | Strong within group | Depends on window | Depends | Moderate | Resolved by construction | v0.7 bump | Very High | NO — WB API does NOT expose per-observation welfare concept |
| G. Fixed externally-justified raw-Gini thresholds | Requires external authority | N/A | N/A if authority is global | Depends on authority | Yes | None | None | Depends | v0.7 bump | Low | NO — no authoritative source for specific thresholds |
| H. CONTEXTUAL_DEFERRED / no scalar | N/A | N/A | N/A | N/A | N/A | None | None | None | None | None | YES — preserves all information; defers the arbitrary choice |

### Part 5 — Global WB Gini universe (read-only live query)

Read-only WB API v2 query (no DB writes, no new connector):
- 2430 valid country-year observations, 171 countries, 1963–2025.
- Global pooled: min=20.2, p10=27.5, p25=30.8, median=35.3, p75=42.6,
  p90=50.8, max=71.1.
- tracked_8 (25.5–43.7) is a NARROW subset of the world (20.2–71.1).
  tracked_8 is NOT representative of the global Gini distribution.

Same-year cross-sections (representative years):
- 2000: n=57, median 36.4 (p10=28.88, p90=53.72)
- 2010: n=86, median 33.7 (p10=27.75, p90=47.85)
- 2020: n=70, median 34.35 (p10=26, p90=44.61)
- 2025: n=4 (too sparse)

### Part 6 — Distribution stability

Median Gini by decade: 1960s 36.7, 1970s 34.0, 1980s 35.4, 1990s 39.0,
2000s 35.6, 2010s 34.8, 2020s 34.35. The 1990s median (39.0) is notably
higher than the 2020s (34.35) — but this is largely composition-driven.

Country count by decade: 1960s 2, 1970s 10, 1980s 64, 1990s 120, 2000s 152,
2010s 160, 2020s 115. **The country composition changes materially by
decade.** A fixed full-history pooled percentile would encode both future
information and future composition changes. The distribution is NOT stable
enough for one fixed curve without an as-of-safe expanding-window design
that handles composition drift.

### Part 7 — Survey-concept comparability (MAIN METHODOLOGICAL RISK)

The income-vs-consumption difference is the primary blocker:

- High-income economies (USA/CHE/DEU/FRA/GBR/JPN): income-based (LIS /
  EU-SILC; after-tax income).
- CHN, IND: consumption-based (PIP groups China under grouped data; India
  under South Asia consumption surveys).
- OWID: "consumption tends to be more evenly distributed than income" —
  consumption Gini is systematically LOWER than income Gini for the same
  true inequality.
- This is visible in the tracked_8 data: IND (consumption) median 27.7 vs
  USA (income) median 40.8.
- **The WB API does NOT expose a per-observation welfare-concept tag.**
  No defensible automated adjustment is possible from the data alone.
- PIP has a within-country comparability database (binary), NOT a
  cross-country welfare-concept classification exposed via WDI.

Possible outcomes:
- Provider harmonization is sufficient for one curve: NO — income vs
  consumption is a systematic level difference, not a noise term.
- Separate calibration groups are required: MAYBE — but the WB API does
  not expose the grouping metadata per observation.
- Metadata is insufficient for defensible adjustment: YES — this is the
  current state.
- Global percentile should remain descriptive only: YES — for now.

No fixed adjustment (e.g. "consumption Gini + 5 points") is invented. No
authoritative source directly supports a specific numeric transformation.

### Part 8 — Level vs relative (kept separate)

A Gini LEVEL score would answer: "How unequal is this country's measured
distribution on an interpretable absolute/global calibration?" A future
relative_score could answer: "Where does it rank within a named universe?"
tracked_8 relative rank is NOT used as the level_score. relative_score is
NOT implemented this sprint.

### Part 9 — Irregular freshness (preserved)

Gini publication is irregular (IND 5 obs over 29 years; JPN 13 obs over
12 years; latest year varies 2020–2024 by country). The existing freshness
policy (DEC-013, exponential decay, irregular class: 2y/4y/8y thresholds)
remains the one source of truth. A country may have an old but still usable
Gini observation with freshness_factor < 1. The economic level must NOT
be multiplied by freshness. Freshness later affects trust/confidence.
No freshness parameters were modified.

### Part 10 — As-of calibration / future leakage

- FULL-HISTORY pooled percentile: NOT as-of-safe — leaks future
  distribution and composition.
- EXPANDING global distribution (all eligible observations known by the
  snapshot): potentially as-of-safe by observation period, but composition
  drifts as coverage changes.
- SAME-YEAR global cross section: as-of-safe but sensitive to sparse
  reporting (2025 n=4).
- TRAILING global window: requires a window decision (unresolved).
- Release dates remain unavailable → backtest_safe stays False even for a
  period-safe calibration.

### Part 11 — Candidate transformation families

| Family | Required parameters | What Atlas 50 means | Endpoint meaning | Sensitivity to tails | Comparability assumptions | Interpretability | Defensible now? |
|---|---|---|---|---|---|---|---|
| 1. Empirical percentile inversion | A calibration distribution | Median of calibration distribution | 0=worst, 100=best in distribution | High (driven by extremes) | Distribution is comparable across countries | Moderate | NO — no defensible calibration distribution |
| 2. Monotonic piecewise-linear raw-Gini | Thresholds + segment slopes | A raw-Gini normative threshold | Thresholds define endpoints | Moderate | Raw Gini is comparable across countries | High | NO — no authoritative thresholds |
| 3. Monotonic saturating | Saturation point + slope | Inflection point | Asymptote | Low | Raw Gini is comparable | Moderate | NO — no defensible saturation point |
| 4. Robust z / MAD | Center + scale | Center + 0 MADs | z-score-based | Low (robust) | Distribution is stable + comparable | Low | NO — distribution not stable |
| 5. Logistic mapping | Midpoint + slope | Midpoint | Asymptotes | Low | Midpoint is meaningful | Moderate | NO — no defensible midpoint |
| 6. CONTEXTUAL_DEFERRED | None | N/A | N/A | N/A | N/A | N/A | YES — defers the arbitrary choice |

### Part 12 — Midpoint semantics

What does level_score = 50 mean?
- Median of a global calibration distribution: the distribution shifts over
  time (decade medians 34–39) and is composition-dependent — not stable.
- A raw-Gini normative threshold: no authoritative source for a specific
  threshold value.
- Historical median: leaks future information.
- No approved interpretation: **this is the current state.**

No defensible 50 interpretation exists. Without a defensible midpoint, no
monotonic curve (logistic, piecewise-linear, saturating) can be calibrated.

### Part 13 — Wealth-gap force ceiling (locked)

The Wealth / opportunity / values gaps force stays PARTIAL (DEC-009) even
if GINI_INDEX eventually gets a numeric indicator level. Gini measures
income inequality only; wealth inequality, opportunity gaps, and
values/polarization remain incomplete. The ceiling acts at the force layer
only — an indicator level_score never lifts the force ceiling. No
FORCE_COVERAGE status change.

### Decision matrix — Gini Calibration Audit (Sprint 5.17)

| Issue | Evidence | Risk | Decision | Implementation implication |
|---|---|---|---|---|
| Provider definition | SI.POV.GINI = 0–100 Lorenz area; higher = more inequality; PIP mixes income + consumption surveys | Systematic level difference between income-based and consumption-based Gini | Direction confirmed (DEC-018); numeric curve deferred | No level_score until calibration universe is resolved |
| Income vs consumption comparability | WB API does NOT expose per-observation welfare-concept tag; PIP documents comparability breaks; OWID: consumption more evenly distributed than income | A single global curve conflates measurement-concept difference with true inequality difference | Metadata insufficient for defensible adjustment | Need a welfare-concept metadata source OR a separate-calibration methodology OR an external adjustment authority |
| Global distribution | 2430 obs, 171 countries, 20.2–71.1; decade medians 34–39; tracked_8 25.5–43.7 is a narrow subset | tracked_8 is NOT representative; global distribution shifts by decade | tracked_8 calibration rejected; global calibration needs as-of-safe window | Expanding-global or same-year design required; full-history rejected |
| Temporal stability | Country count shifts 2→160→115 by decade; decade medians vary 34–39 | A fixed full-history percentile encodes future info + composition changes | Full-history pooled percentile NOT as-of-safe | Expanding-window design that handles composition drift (unresolved) |
| tracked_8 suitability | 8 countries, 25.5–43.7, income + consumption mixed | Not a global inequality distribution; n=8 cross-section too sparse | tracked_8 calibration permanently rejected as calibration universe | No tracked_8-based level_score |
| Expanding-global option | As-of-safe by observation period; composition drifts | Drift as coverage/concept mix changes | Partially defensible but requires window + drift handling | Needs a window decision + drift-mitigation design |
| Same-year option | As-of-safe; 57–86 countries per representative year; 2025 n=4 | Sparse years; concept mix unchanged | Partially defensible but sensitive to sparse reporting | Needs a sparse-year fallback rule |
| Midpoint semantics | No defensible level_score=50 interpretation exists | Any monotonic curve requires a midpoint | No curve can be calibrated without a midpoint | Need an external calibration basis OR a normative threshold authority |
| Irregular freshness | IND 5 obs/29y; JPN 13 obs/12y; latest varies 2020–2024 | Old-but-usable observations must not be zeroed | Freshness policy (DEC-013) preserved; level NOT multiplied by freshness | No freshness parameter changes |
| As-of leakage | Release dates unavailable; full-history leaks future | backtest_safe stays False | Any calibration is period-safe at best, not release-safe | backtest_safe stays False |
| Force proxy ceiling | Gini = income inequality only; wealth/opportunity/values missing | Indicator level must not lift force ceiling | Wealth-gap force stays PARTIAL (DEC-009) | No FORCE_COVERAGE change |

### Verdict: DEFER_GINI_LEVEL

**Atlas cannot yet defensibly map World Bank GINI_INDEX into an Atlas
0–100 INDICATOR strength level.** The deferral is a durable methodology
decision, not a postponement of an obvious answer. The reasons:

1. **Survey-concept comparability is insufficient.** Income-based and
   consumption-based Gini are systematically different (consumption is more
   evenly distributed). The WB API does NOT expose a per-observation
   welfare-concept tag, so no defensible automated adjustment is possible.
   A single global curve would conflate a measurement-concept difference
   with a true inequality difference — exactly the failure mode this
   project's methodology forbids.
2. **tracked_8 is NOT a defensible calibration universe.** The tracked_8
   range (25.5–43.7) is a narrow subset of the world distribution
   (20.2–71.1). tracked_8 is 8 countries, not a global inequality
   distribution. tracked_8 calibration is permanently rejected.
3. **The global distribution is not stable enough for one fixed curve.**
   Country composition shifts materially by decade (2→160→115 countries).
   Decade medians vary (34–39). A fixed full-history pooled percentile
   would encode future information and composition changes.
4. **No defensible midpoint semantics exists.** level_score=50 has no
   approved interpretation (global median shifts; no authoritative
   raw-Gini threshold; historical median leaks future). Without a
   defensible midpoint, no monotonic curve can be calibrated.
5. **No external calibration basis exists** for fixed raw-Gini thresholds.
   Any threshold (e.g. "Gini 40 = level 50") would be an arbitrary choice
   without evidence — the failure mode DEC-018 explicitly rejected.
6. **As-of safety requires an expanding-window design that doesn't drift
   — unresolved.** Full-history leaks future; same-year is sparse;
   expanding drifts as coverage/concept mix changes.

**What additional evidence / data / methodology is required before a Gini
level can be defensibly implemented:**

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

Until these are resolved, GINI_INDEX stays MONOTONIC_NEGATIVE (direction
confirmed by DEC-018) with NO numeric curve; `100 - Gini` remains NOT
approved; the Wealth / opportunity / values gaps force stays PARTIAL
(DEC-009); the Sprint 5.13 permanent rules apply to every future use.

## Sprint 5.17.1 methodology status (2026-09-09) — GINI GLOBAL-UNIVERSE FILTER HARDENING

A METHODOLOGY / EMPIRICAL-RESEARCH BUG-FIX sprint. NO Gini level_score was
implemented; NO NormalizedSignal output changed; the model version stays
**normalization-v0.6**; `confidence` stays None everywhere; `backtest_safe`
stays False; the Wealth / opportunity / values gaps force stays PARTIAL
(DEC-009). No DEC change — DEC-024 verdict UNCHANGED.

### Root cause

The Sprint 5.17 read-only profile
(`apps/api/scripts/gini_calibration_profile.py`) filtered the global WB
SI.POV.GINI universe using a hand-written `aggregate_codes` blacklist that
wrongly listed real economies ZAF (South Africa) and PSE (West Bank and Gaza)
as aggregates. Two compounding defects: (1) the blacklist was methodologically
wrong (ZAF/PSE are real economies with real WB region assignments); (2) the
filter matched the GINI record's 2-letter `country.id` against the 3-letter
blacklist codes, so the blacklist was in fact INEFFECTIVE — no code ever
matched. The reported 2430/171 counts happened to be correct by accident,
but the filter was not trustworthy.

### Authoritative economy-filter design

The official WB `/v2/country` metadata endpoint returns every country and
aggregate record. Each record carries a nested `region` object:
- Real economies: `region.id` is a real region code (NAC, SSF, MEA, EAS,
  SAS, ...), `region.value` is a region name.
- Aggregates: `region.id == "NA"`, `region.value == "Aggregates"`.

A pure helper `build_valid_economy_codes(country_records: list[dict]) ->
set[str]` builds the set of real-economy ISO3 codes from the metadata
records (region.id NOT in {"NA", "", None}). The GINI record's
`countryiso3code` (3-letter, e.g. USA/ZAF/PSE) is matched against this set.
No inference from code length, capitalization, or a manual blacklist. The
helper has no I/O — it is unit-tested offline with mocked provider
metadata (no external HTTP in pytest).

Notable subtlety: SSF appears BOTH as a real-economy region id (on ZAF's
record, region.id="SSF") AND as an aggregate code (the SSF aggregate's
own record has region.id="NA"). The filter keys on the record's OWN region
field, never on the code itself, so the two senses never collide: ZAF is
retained, the SSF aggregate is excluded.

### Fail loudly

If the country metadata cannot be retrieved or parsed reliably (HTTP
error, non-200, JSON decode failure, unexpected response shape, no
records), the GLOBAL live profile STOPS. It does NOT silently fall back
to the old blacklist. The tracked_8 DB profile (Part 2, which reads the
live dev DB) may still run. Research output states that global profiling
was unavailable.

### Corrected global counts/statistics (read-only live WB API v2, 2026-09-09)

- Authoritative economy filter: **217 real economies** identified
  (region.id != "NA").
- **ZAF: RETAINED** — 7 observations (min=54.1, median=59.6, max=65).
- **PSE: RETAINED** — 9 observations (min=33.7, median=34.5, max=36.4).
- Total valid country-year observations: **2430**.
- Distinct countries/economies: **171**.
- Year span: **1963–2025**.
- Pooled: min=20.2, p10=27.5, p25=30.8, median=35.3, p75=42.6, p90=50.8,
  max=71.1.
- Cross-sections: 2000 n=57 median 36.4; 2010 n=86 median 33.7; 2020 n=70
  median 34.35; 2025 n=4 (too sparse).
- Latest sufficiently populated year (n>=30): **2023 (n=57, median 33.9)**.
- Country count by decade: 1960s 2, 1970s 10, 1980s 64, 1990s 120, 2000s
  152, 2010s 160, 2020s 115.
- Decade medians: 1960s 36.7, 1970s 34.0, 1980s 35.4, 1990s 39.0, 2000s
  35.6, 2010s 34.8, 2020s 34.35.

The counts (2430/171) match the Sprint 5.17 reported values — the old
blacklist was ineffective (2-letter vs 3-letter mismatch), so the bug was
methodological, not numerical. The corrected filter is authoritative and
defensible.

### Impact on DEC-024

**Verdict UNCHANGED (option B — wording/statistics basis strengthened but
the durable methodology conclusion does not change).** The filtering bug
did not materially alter the Sprint 5.17 methodology verdict. The six
DEFER_GINI_LEVEL reasons stand: (1) survey-concept comparability
insufficient (income vs consumption; no per-observation tag); (2) tracked_8
not a defensible calibration universe; (3) global distribution not stable
enough for one fixed curve; (4) no defensible midpoint semantics; (5) no
external calibration basis; (6) as-of-safe expanding-window design
unresolved. The welfare-concept problem and the missing per-observation
welfare tag remain SEPARATE from this filtering bug. DEC-024 is not
rewritten — the durable methodology conclusion is unchanged; only the
filtering mechanism and the ZAF/PSE retention are corrected.

### Welfare-concept wording

Refined to "provider-methodology / country-level welfare-concept
classification" rather than "every CHN observation is definitively tagged
consumption by the API". The API does NOT expose a per-observation
welfare-concept tag; the classification is a methodology-level hint from
official PIP documentation, not a per-row metadata column. No invented
adjustments are applied.

### Tests

6 new offline regressions in `apps/api/tests/test_gini_economy_filter.py`
(mocked WB country metadata — no external HTTP):
- ZAF retained as a real economy.
- PSE retained as a real economy.
- Known aggregates (WLD, EAP, HIC, SSF, INX) excluded.
- Real-economies set exactly {USA, ZAF, PSE, CHN, IND} for the mock.
- SSF region-id collision handled (ZAF retained, SSF aggregate excluded).
- Malformed records (non-dict, missing id, missing region) skipped
  defensively.

pytest **379 passed** (373 baseline + 6 new), all offline. Model version
stays **normalization-v0.6**; confidence stays None; no migration; no
model-version bump; no force scores/weights/phases; no public API; no
frontend change; no FORCE_COVERAGE change (Wealth-gap stays PARTIAL).

## 1. Score semantics — four separable dimensions

A score is never a single number. Every derived signal keeps these dimensions
independent; they may be *combined later* by an explicit, versioned force
aggregation — never collapsed at normalization time.

| Dimension | Range | Meaning |
|---|---|---|
| `level_score` | 0–100 | Domestic/absolute condition for the force concept. 0 = extremely weak/unhealthy, 50 = neutral middle reference, 100 = extremely strong/healthy. NOT a provider percentile by definition, NOT a country ranking, NOT a probability, NOT a cycle phase. |
| `relative_score` | 0–100 or null | Position versus the comparison universe (Section 14). ~90 = stronger than most of the universe on this dimension. Big Cycle power requires BOTH domestic condition and relative global strength, so this stays separate from level. null when no defensible comparison exists. |
| `momentum` | −100…+100 | Direction of change through time. Negative = deteriorating, 0 = broadly stable, positive = improving. Always computed from change between periods — never inferred from level. null when insufficient history. |
| `confidence` | 0–1 | Trust in the derived signal, from source quality, freshness, coverage, known uncertainty, proxy completeness, missing inputs. Confidence is NOT economic strength. |

Ranges are declared as module constants in the skeleton
(`LEVEL_SCORE_RANGE`, `RELATIVE_SCORE_RANGE`, `MOMENTUM_RANGE`,
`CONFIDENCE_RANGE`) with trivial validation helpers — no computation.

## 2. Quarterly scoring clock

The derived layer scores on a **quarterly** clock: snapshots `YYYY-Q1` …
`YYYY-Q4`.

Why quarterly, not daily/monthly:

- BIS credit gap and DSR are quarterly; OECD ULC growth is quarterly.
- Big Cycle forces change slowly; annual resolution is too coarse for
  momentum on quarterly series, sub-quarterly resolution adds noise and
  nothing else.
- Annual and irregular indicators contribute to quarterly snapshots via
  as-of alignment (Section 3) — their observation dates are untouched.

Raw observation dates are NEVER altered. The clock exists only in the derived
layer (`ScoringPeriod` in the skeleton).

## 3. As-of alignment

For each (country, indicator, scoring period) the derived layer selects the
**latest known usable observation whose OWN economic period has fully ENDED
by the scoring snapshot**, and carries its provenance forward:

```
AlignedValue:
    indicator_code, country_iso3, scoring_period
    source_period          # raw observation's own period
    raw_value              # untouched raw value
    age_periods            # scoring_period − source_period, in periods
    effective_period_end   # DERIVED last day of the observation's own period
    freshness_factor       # 0..1, per Section 5 (not computed yet)
    is_stale               # per staleness thresholds (Section 5)
    vintage_number          # raw provenance preserved
```

Rules:

- Latest-vintage reads only (consistent with the rest of the platform).
- **Period-complete eligibility (Part 0, DEC-015)**: an observation is
  eligible only when `effective_period_end <= scoring_period_end`, where
  the effective end is derived deterministically in this layer — annual and
  irregular (year-dated) periods YYYY end YYYY-12-31; quarterly YYYY-Qn ends
  on the quarter's last day. An annual 2020 observation is therefore NOT
  eligible at the 2020-Q1/Q2/Q3 snapshots and first becomes eligible at
  2020-Q4. The derived end date is provenance only: raw observations are
  never modified and no synthetic period-end dates are persisted.
- Period-completeness is NOT release-date safety (Section 4): a completed
  period may still have been released long after it ended, so every signal
  keeps `backtest_safe = false` until Milestone 9.
- The aligned record always retains source period, age, and vintage — a
  2020 observation used for a 2025-Q4 snapshot is visibly 20 periods old,
  never silently "current".
- No forward-fill, no interpolation in this layer. Interpolation (if ever
  adopted) would be a separate, explicitly versioned scoring-phase decision.
- `AlignedValue` is a typed structure only — not persisted.

## 4. Historical backtest safety — explicit limitation

Most current WB/BIS/OECD observations do **not** carry reliable historical
release dates (the `release_date` column exists but is unpopulated; full
vintages exist only from the current import onward). Therefore:

- Normalization produced today on historical periods is **CURRENT/RESEARCH
  scoring**: it knows what we know now, not what was known then.
- It must never be claimed or marketed as "what the model knew in 2018".
- Point-in-time/backtest scoring is owned by **Milestone 9** (release-date
  discipline).
- Every derived signal carries `backtest_safe: bool = False` until Milestone 9
  changes it. Current-research vs point-in-time is a first-class distinction,
  not a footnote.

## 5. Freshness policy

Frequency-aware freshness. **Missing is never zero-filled; stale is never
silently current.** Principle: recent observation → confidence ~1; older →
confidence decays gradually; too stale → the indicator is unavailable for that
snapshot (the signal is not produced, not produced-with-zero).

Proposed **initial model parameters** (MODEL PARAMETERS — versioned, initial
choices, NOT provider truth; see Section 13):

| Freshness class | Full confidence within | Decays with half-life | Unusable after |
|---|---|---|---|
| quarterly | 2 quarters | 8 quarters | 12 quarters |
| annual | 1 year | 3 years | 5 years |
| irregular (Gini) | 2 years | 4 years | 8 years |

Decay SHAPE — **RESOLVED (DEC-013, 2026-09-09)**: exponential is the settled
model choice (`0.5 ** ((age − full) / (half_life − full))` — passes through
exactly 0.5 at the half-life for any thresholds). The linear implementation
remains in the code as an available alternative for tests and possible future
model versions, but it is NOT current methodology. A 2020 Gini and a 2025 CPI
observation are never treated equivalently — the aligned record's
`age_periods`/`is_stale` make the difference explicit.

## 6. Normalization families

There is no universal z-score. Every indicator is assigned one family per
dimension (level / relative / momentum), or is explicitly DEFERRED. Families
(the enum lives in the skeleton):

| Family | Meaning |
|---|---|
| `DIRECT_0_100` | Provider already publishes a defensible fixed 0–100 scale (WGI 2025 revision). Level signal = provider value; never re-ranked into a percentile that destroys the absolute scale. |
| `MONOTONIC_POSITIVE` | More is better across the plausible range; direction is unambiguous. |
| `MONOTONIC_NEGATIVE` | Less is better (Gini). |
| `MONOTONIC_SATURATING` | More is better with diminishing returns; twice the input is never twice the health (gross capital formation). |
| `TARGET_BAND` | Healthiest inside a band / near a target; both tails can be unhealthy, possibly asymmetrically. Band thresholds are versioned model parameters, never invented silently. (Sprint 5.11/DEC-020: the credit gap LEFT this family — see ONE_SIDED_VULNERABILITY below.) |
| `ONE_SIDED_VULNERABILITY` | No stress is signaled at or below a neutral ceiling; stress rises monotonically ABOVE it (added by Sprint 5.11/DEC-020 for the credit-to-GDP gap: authoritative evidence supports positive-side excess-credit breakpoints but NO negative-side penalty — the below-ceiling region carries no health signal from this indicator). Breakpoints are versioned model parameters, never invented silently. **IMPLEMENTED (Sprint 5.12/DEC-021)** for CREDIT_TO_GDP_GAP with the owner-approved curve: 50 at/below +2pp, linear to 0 at +10pp, clamped above. |
| `OWN_HISTORY` | Level meaning comes from the country's own historical distribution — cross-country levels are not comparable (BIS DSR caution). |
| `CROSS_SECTIONAL_RELATIVE` | Position within the comparison universe for the relative dimension. Robust statistics required (Section 15); never treated as global truth with n=8 (Section 14). |
| `RELATIVE_SHARE` | Country's share of a universe total (future: military expenditure share of tracked/global spending). |
| `CONTEXTUAL_DEFERRED` | Deliberately unresolved: no defensible curve exists yet with current inputs. The indicator still counts for coverage/eligibility, but no level curve is invented this sprint. |

## 7. Indicator-by-indicator classification (all 19 live series)

Registry source: `apps/api/app/cycle/normalization_definitions.py`
(`NORMALIZATION_REGISTRY`). Force inputs cross-check against
`force_definitions.py` — the registry fails loudly if a live force input has no
entry. Deliberately-unassigned indicators have explicit DEFERRED entries so
they cannot be accidentally promoted into force scoring.

| Indicator | Level family | Relative family | Momentum family (windows) | Freshness class | Notes |
|---|---|---|---|---|---|
| GDP_GROWTH | CONTEXTUAL_DEFERRED (reclassified by DEC-018 — Sprint 5.9 audit; superseded the Sprint 5.5 TARGET_BAND proposal) | CROSS_SECTIONAL_RELATIVE | OWN_HISTORY (3y, 5y annual) | annual | Output growth ≠ productivity. A universal band would punish catch-up growth / reward stagnation (tracked_8 growth medians span 0.8–7.2). Future design candidate: own-history deviation + potential-growth gap. |
| GDP_CURRENT_USD | CONTEXTUAL_DEFERRED | CONTEXTUAL_DEFERRED | — | annual | Deliberately unassigned (economic scale/context). Nominal USD; any future role (relative power) needs PPP/deflation — a separate justified decision. |
| GDP_PER_CAPITA | CONTEXTUAL_DEFERRED | CONTEXTUAL_DEFERRED | — | annual | Deliberately unassigned. Nominal; needs PPP + likely log before any use. |
| EXPORTS_GDP | CONTEXTUAL_DEFERRED | CONTEXTUAL_DEFERRED | OWN_HISTORY (3y, 5y) | annual | High exports = integration/demand, not automatically "good". Trade force is a multi-indicator contextual case (Section 7.1). |
| IMPORTS_GDP | CONTEXTUAL_DEFERRED | CONTEXTUAL_DEFERRED | OWN_HISTORY (3y, 5y) | annual | Imports are NOT negative: strong demand, capital goods, supply-chain integration. Never monotonic-negative. |
| TRADE_BALANCE | CONTEXTUAL_DEFERRED | CONTEXTUAL_DEFERRED | — | annual | Sign/magnitude both ambiguous (surplus = competitiveness or weak demand; deficit = investment or imbalance). Deferred rather than invented. |
| CURRENT_ACCOUNT_GDP | CONTEXTUAL_DEFERRED | CONTEXTUAL_DEFERRED | — | annual | Large surpluses and deficits both carry meanings; banding deferred. |
| GROSS_CAPITAL_FORMATION_GDP | CONTEXTUAL_DEFERRED (reclassified by DEC-018 — Sprint 5.9 audit; superseded the Sprint 5.5 MONOTONIC_SATURATING proposal) | CROSS_SECTIONAL_RELATIVE | OWN_HISTORY (3y, 5y) | annual | Investment effort, not infrastructure quality. MONOTONIC_SATURATING disproved: very high GCF can be credit-driven overinvestment; the healthy level is economy-model-dependent. Future design candidate: deviation from the country's own investment norm. |
| GINI_INDEX | MONOTONIC_NEGATIVE, numeric curve DEFERRED (DEC-024, Sprint 5.17: survey-concept comparability insufficient; tracked_8 rejected; global distribution not stable; no defensible midpoint) | CROSS_SECTIONAL_RELATIVE (weak: survey-base differences) | OWN_HISTORY (irregular — only when enough observations) | irregular | Higher = more income inequality. "100 - Gini" is NOT an approved mapping; the calibration universe (global vs tracked_8) and survey-base comparability remain open. Sprint 5.17 (DEC-024): verdict DEFER_GINI_LEVEL — WB API does NOT expose per-observation welfare-concept tag; tracked_8 (25.5-43.7) is a narrow subset of world (20.2-71.1); global distribution shifts by decade (composition 2->160->115 countries); no defensible level_score=50 interpretation. Never forward-filled; freshness decay applies to stale values. Force capped PARTIAL (income != wealth/opportunity/values). |
| INFLATION_CPI | CONTEXTUAL_DEFERRED (reclassified by DEC-018 — Sprint 5.9 audit; superseded the Sprint 5.5 TARGET_BAND proposal) | CONTEXTUAL_DEFERRED | OWN_HISTORY (3y, 5y) | annual | Domestic price pressure; a universal raw-CPI band would encode "2% ideal for every country" (objectives differ across regimes). Level waits for a defensible per-country target/reference. |
| MILITARY_EXPENDITURE_USD | CONTEXTUAL_DEFERRED | RELATIVE_SHARE (future; share of tracked/global spending, or PPP-adjusted resources) | — | annual | Nominal, scale-dependent; spending ≠ capability (DEC-011). No more-spending-is-stronger curve. |
| MILITARY_EXPENDITURE_GDP | CONTEXTUAL_DEFERRED | CONTEXTUAL_DEFERRED | — | annual | Effort/burden, not capability. |
| RULE_OF_LAW_WGI_SCORE | DIRECT_0_100 | CROSS_SECTIONAL_RELATIVE (optional, later) | OWN_HISTORY (3y, 5y) | annual | Provider's fixed 0–100 absolute scale preserved — never percentile-ranked. Perception uncertainty documented (CI/SE series not imported). |
| CONTROL_OF_CORRUPTION_WGI_SCORE | DIRECT_0_100 | CROSS_SECTIONAL_RELATIVE (optional, later) | OWN_HISTORY (3y, 5y) | annual | Higher = stronger control; raw value never reversed. Perception uncertainty. |
| POLITICAL_STABILITY_WGI_SCORE | DIRECT_0_100 | CROSS_SECTIONAL_RELATIVE (optional, later) | OWN_HISTORY (3y, 5y) | annual | Feeds the ceiling-capped internal-conflict force; the indicator spec itself is a normal DIRECT_0_100 entry (ceilings act at the force layer only). |
| CREDIT_TO_GDP_GAP | ONE_SIDED_VULNERABILITY (reclassified from asymmetric TARGET_BAND by Sprint 5.11 evidence audit, DEC-020; **IMPLEMENTED Sprint 5.12/DEC-021** with the owner-approved curve: 50 at/below +2pp, linear to 0 at +10pp, clamped 0 above — breakpoints coincide with the Basel CCyB guide L/H; the 50/0 mapping is an Atlas MODEL PARAMETER and the no-excess region is deliberately NEUTRAL 50, not 100) | CONTEXTUAL_DEFERRED | OWN_HISTORY (4q, 8q — UNAPPROVED, momentum stays None) | quarterly | The indicator measures EXCESS-CREDIT vulnerability on the positive side: authoritative evidence supports positive breakpoints (Basel CCyB guide +2/+10; BIS 2018 EWI red ~9 / amber 4–9) but NO negative-side penalty — the guide is flat zero below +2 and a persistent negative gap is a post-boom measurement artifact, not an unhealthy-debt signal. Deleveraging/weak-credit conditions belong to other signals (DSR level, credit growth, output). Score-interpretation limits from the Basel caution are carried (Sprint 5.12 section). |
| DEBT_SERVICE_RATIO | OWN_HISTORY (confirmed by DEC-018; selected as the next implementation target) | none (explicitly discouraged) | OWN_HISTORY (4q, 8q) | quarterly | Never cross-sectionally rank raw DSR (income definitions differ). Level = own-history stress-position percentile (Sprint 5.10). |
| LABOUR_PRODUCTIVITY_PER_HOUR | MONOTONIC_POSITIVE, numeric level curve deferred (direction confirmed by DEC-018) | CROSS_SECTIONAL_RELATIVE | OWN_HISTORY (3y, 5y) | annual | Level AND growth stay distinguishable: high level + weak growth ≠ low level + fast improvement. Absolute 0–100 mapping deferred pending an expanded calibration universe decision (tracked_8 min-max explicitly rejected). |
| UNIT_LABOUR_COST_GROWTH | CONTEXTUAL_DEFERRED (reclassified by DEC-018 — Sprint 5.9 audit; superseded the Sprint 5.5 TARGET_BAND proposal) | CONTEXTUAL_DEFERRED | OWN_HISTORY (4q, 8q) | quarterly | Raw domestic ULC growth is not by itself a relative-competitiveness measure — needs FX + partner-country ULC + inflation-regime context (none imported). Series stays live for coverage. |

### 7.1 Multi-indicator contextual forces

Trade and capital flows (EXPORTS_GDP, IMPORTS_GDP, TRADE_BALANCE,
CURRENT_ACCOUNT_GDP) and Military strength (both spending series) are
**multi-indicator contextual cases**: the force-level meaning emerges from the
combination (e.g. openness + balance composition), not from any single
indicator curve. Sprint 5.5 deliberately defers their level curves rather than
inventing them. If a defensible combination is not found, those inputs stay
DEFERRED and the force remains unscored (Section 11).

## 8. Absolute vs relative design

Designed independently, at indicator level:

- Level answers: "how strong/healthy is the domestic condition on its own
  terms?" (WGI absolute score; PPP productivity level; own-history DSR
  position).
- Relative answers: "where does the country stand versus the comparison
  universe?" (robust percentile within tracked_8; future expenditure share).

Rules:

- A relative percentile never masquerades as absolute health: if only a
  relative score is defensible, `level_score` stays null.
- Absolute-vs-relative applies per dimension: labour productivity has BOTH
  (level PPP + relative percentile); military spending has NEITHER yet
  (nominal confound) — only a future relative-share concept.
- The UI must eventually show both separately (docs/data-model.md already
  requires absolute/relative separation).

## 9. Momentum design

Separate from level, always from change through time:

| Series type | Candidate windows (model parameters) |
|---|---|
| Quarterly | 4-quarter and/or 8-quarter change |
| Annual | 3-year and/or 5-year trend |
| Irregular (Gini) | only when enough observations exist; no fixed window |

- Windows are per-indicator (registry `momentum_windows`), versioned, and
  never one-size-fits-all.
- Momentum direction must respect indicator semantics: Rule of Law rising →
  positive; Gini rising → negative; credit gap rising toward positive →
  deteriorating (sign conventions resolved at implementation, documented).
- **Sprint 5.7 (DEC-016) — RESOLVED FOR THE WGI ×3 ONLY**: momentum =
  signed change in the provider's own 0-100 points, `current_aligned_raw −
  anchor_aligned_raw`; windows 3y (diagnostic) + 5y (primary, the headline
  `momentum`); anchor = period-complete as-of alignment (DEC-015) at the
  same quarter w years earlier, tolerance 1 annual period (the 1997/1999/
  2001 biennial gaps anchor to the prior year; older anchors → change None);
  higher WGI = positive, no inversion. Per-window provenance
  (requested + actual anchor, change) travels on the signal; no averaging,
  no shorter-window fallback; the anchor is never freshness-decayed. WGI
  momentum is WGI-scale-specific — NOT approved for direct cross-indicator
  aggregation. Sign conventions for every other indicator remain open.

## 10. Confidence architecture — two separate layers (rewritten Sprint 5.13, DEC-022)

Confidence is TRUST in a signal, never economic strength, and it lives at
two DISTINCT layers. The old single-factor table mixed them; they are now
separated permanently.

### 10.1 Permanent rules (apply to both layers)

- **Confidence is independent from strength.** `level_score = 90,
  confidence = 0.4` means "strong measured condition, weak trust in that
  estimate" — it must NEVER be collapsed to 36. Economic scores are never
  multiplied by confidence; `relative_score *= confidence` and
  `momentum *= confidence` are prohibited. Confidence travels ALONGSIDE the
  economic dimensions.
- **Confidence is not freshness.** `freshness_factor` (Section 5, DEC-013
  exponential policy) is the one source of freshness truth. A future
  confidence may CONSUME freshness_factor as an input; it must never
  recompute age with another formula, and `confidence = freshness_factor`
  is not a confidence methodology.
- **Missing ≠ perfect ≠ zero.** Missing confidence metadata never implies
  perfect confidence (no default factor 1) and never zeroes anything.
  Unknown components stay UNKNOWN (None) until an approved methodology
  defines how partial components aggregate. Missing confidence metadata is
  not a missing economic observation — the score itself stays usable.
- **No arbitrary numeric provider-quality constants.** No "World Bank =
  0.95" style numbers — there is no defensible calibrated scale. Qualitative
  provenance categories may be TYPED later (official_primary,
  official_republished, proxy_measure, perception_composite); any numeric
  mapping is a future, calibrated, versioned decision.
- The exact numeric composition (product vs weighted mean, component
  weights, floors) remains an UNRESOLVED question (Section 17 item 6);
  whatever is chosen is a versioned model parameter — no fake `0.873`
  precision from arbitrary constants. The first executable confidence
  formula bumps the model version; a design/documentation change never does.

### 10.2 INDICATOR confidence (per NormalizedSignal — trust in ONE indicator's signal)

Eventual diagnostic inputs (typed metadata first; NO numeric conversion
approved yet):

| Component | Captures | Examples |
|---|---|---|
| `source_quality` | Provider/methodology quality — QUALITATIVE/typed metadata only | WGI perception-composite methodology; BIS DSR income-definition caveats; Basel/BIS credit-gap interpretation caveats |
| `freshness_factor` | Existing numeric provenance (Section 5) — reused, never recomputed | current: the DEC-013 exponential decay factor |
| `measurement_uncertainty` | Optional provider-specific diagnostics | WGI: 90% CI bounds on the governance score (width = UB − LB), number of underlying sources (audited Sprint 5.13; storage/persistence/lookup foundation implemented Sprint 5.14; LIVE INGESTION complete Sprint 5.15 — 1872 rows in `indicator_diagnostics`; still no confidence formula — the field remains a design placeholder, §17 item 6 open) |
| `method_sufficiency` | Optional method-specific diagnostics | DSR: own-history sample_n / minimum_sample_n / calibration span (OwnHistoryLevelResult provenance already carries these); credit gap: parametric curve needs no Atlas history sample; WGI: CI width + source count |

Method-diagnostics note: these describe how WELL-DETERMINED the method's
output is, not how to invent cross-indicator equivalences. No
"20 DSR observations = confidence 0.6" style conversions are approved; any
such mapping needs its own evidence/calibration basis and a model-version
bump. Future shape (NOT implemented): an `IndicatorConfidenceDiagnostics`
provenance object on NormalizedSignal (`confidence` itself stays None until
an executable formula exists and is versioned).

WGI measurement-uncertainty alignment rule (Sprint 5.13): any future WGI
confidence uses uncertainty associated with the SAME eligible source period
— same country, same dimension, same source period as the aligned score,
latest appropriate vintage. Never a later year's bounds, never today's
source count, never another country's uncertainty, no future metadata.

### 10.3 FORCE confidence (per force, at the aggregation layer — NOT on individual signals)

Force-layer concepts ONLY — they must never be folded into an individual
NormalizedSignal merely because that indicator feeds a partial/proxy force:

| Component | Captures |
|---|---|
| usable-input confidence | Combination of the confidence of the force's usable indicator inputs |
| coverage/completeness | Fraction of the force's inputs usable for this snapshot (CHN productivity: GDP growth only → lower FORCE confidence; never zero-fill the missing OECD series) |
| missing required inputs | Missing inputs reduce force confidence/coverage; they never enter as zero |
| proxy completeness / DEC-009 ceilings | Ceiling-capped forces (wealth gaps / internal conflict / military strength) are explicit proxies — the ceiling reduces FORCE confidence and score eligibility, never the indicator values |

**The layering rule (locked):** a high-quality, fresh
POLITICAL_STABILITY_WGI_SCORE signal is NOT lowered because the Internal
conflict force is PARTIAL/ceiling-capped — the raw indicator signal stays
what it is, and the force layer reports the reduced completeness. Likewise
SIPRI spending being an input proxy belongs to Military-strength FORCE
completeness, not to a fake low indicator source-quality number. Force
confidence (a future `ForceConfidence` combining the four rows above) is
NOT designed or implemented here; it arrives only with the versioned force
aggregation sprint. Sections 11 and 12 continue to govern missing-data and
ceiling behavior unchanged.

## 11. Missing-data rules

- **MISSING ≠ ZERO.** No observation is ever substituted with 0 (a missing
  ULC is not 0% ULC growth; a missing 2025 export value is not 0% of GDP).
- When combining indicators in a future force aggregation: re-normalize
  weights across usable inputs only if minimum coverage is met; otherwise
  return **unscored**.
- Unscored ≠ score 0. Coverage is exposed alongside every result.
- Force weights are NOT designed in this sprint.

## 12. Proxy / coverage-ceiling behavior

DEC-009 ceilings (wealth gaps, internal conflict, military strength) act at
the **force layer only**:

- The indicator-level normalization entries for GINI_INDEX,
  POLITICAL_STABILITY_WGI_SCORE, and the military series are ordinary specs —
  ceilings never clamp or modify indicator values.
- At the force layer, a ceiling-capped force may produce at most a
  **PROVISIONAL / PROXY** score with reduced confidence, visibly retaining
  its PARTIAL/proxy status in every API response and UI surface.
- Proposed minimum force-score eligibility:

| Force coverage | Score eligibility |
|---|---|
| available | score eligible |
| partial | score may be produced as PROVISIONAL/PROXY with reduced confidence |
| defined_not_sourced | no force score |
| missing | no force score |

Unscored forces are never scored 0.

## 13. Versioning

Every future derived result must be reproducible. A model version bundles:

```
ModelVersionConfig:
    version_id                 # e.g. "normalization-v0.1"
    normalization_method       # family registry revision
    normalization_parameters   # thresholds, curves, decay shapes
    reference_universe_id      # Section 14
    calibration_window         # Section 15
    momentum_windows           # Section 9
    freshness_policy           # Section 5
    backtest_safe              # Section 4 — False until Milestone 9
```

**Sprint 6.4.1 note:** `force_mapping_version` was removed from
`ModelVersionConfig`. It had no runtime consumer — the indicator→force
mapping is owned by `force-aggregation-v0.2` (a separately versioned layer
since DEC-029/Sprint 5.21). Normalization owns indicator normalization
only; force aggregation owns force roles/aggregation semantics.

No `model_versions` DB table exists yet (planned in docs/data-model.md). Sprint
5.5 adds configuration-first typed structures only — no migration unless a
persisted scoring layer genuinely requires it.

## 14. Reference universe

Current tracked universe: USA, CHN, CHE, DEU, FRA, GBR, JPN, IND
(`tracked_8`). Eight countries are enough for UI comparisons but a **weak
statistical reference distribution** — n=8 positions are never calibrated as
world truth. Design:

- `reference_universe_id` is a model-version parameter; initial value
  `tracked_8`; the architecture supports `expanded_global` later.
- **Sprint 5.8 (DEC-017) — IMPLEMENTED as `ReferenceUniverseSpec`**: tracked_8
  is a typed FROZEN membership (never derived from the DB); relative scores
  carry the universe id plus expected/usable member counts as provenance; a
  future universe change is a new id + new model version, not an in-place
  recalibration. tracked_8 requires ALL 8 members usable (complete-universe
  rule) — otherwise no relative score is produced. Positions within
  tracked_8 are "tracked_8 relative scores", NEVER global percentiles.

## 15. Calibration vs as-of windows (no future-data leakage)

Two separate concepts:

- **CALIBRATION WINDOW** — the data a normalization's parameters (bands,
  robust statistics, own-history distributions) are estimated from; must end
  at or before the model version's cut-off. Never uses future observations.
- **AS-OF WINDOW** — the data actually eligible at a scoring date
  (latest-known-usable per Section 3).

Exact calibration dates are model-version parameters. Rolling normalization
must never see the future.

## 16. Robust statistics

For empirical transformations (percentiles, own-history positioning, relative
scores) prefer:

- median, MAD, winsorization, percentiles / empirical CDF

over raw min-max — a single extreme observation must not destroy a
normalization. Where robust statistics apply is documented per family
(`CROSS_SECTIONAL_RELATIVE` and `OWN_HISTORY` especially). No universal method
is implemented this sprint.

**RESOLVED FOR THE WGI ×3 ONLY (Sprint 5.8, DEC-017)**: WGI relative scores
use the empirical rank / mid-rank plotting position (`100 * (average_rank −
0.5) / n`, ties = average rank) — rank-based, deterministic, no min-max
distortion, no z-score, no winsorization needed (WGI is already bounded
0–100 and rank scoring is insensitive to magnitude). This choice is for WGI
relative scoring only and does not auto-approve the formula for other
CROSS_SECTIONAL_RELATIVE indicators.

## 17. Unresolved methodological questions (deliberately open)

1. Exact freshness decay shape (linear vs exponential) and parameter values.
   Sprint 5.6 note: the machinery now EXECUTES with the Section 5 threshold
   values and an exponential default (honors the half-life definition for any
   thresholds) — an initial model choice, versioned with the model config.
   **RESOLVED 2026-09-09 (DEC-013):** the owner confirmed the exponential shape
   as the settled model choice. Parameter-value tuning and any future shape
   change remain model-version changes.
2. TARGET_BAND thresholds/curves. **UPDATED Sprint 5.9 (DEC-018)**: GDP
   growth, CPI, and ULC growth were RECLASSIFIED to CONTEXTUAL_DEFERRED —
   their universal-band proposals were disproved (see the Sprint 5.9 audit).
   **UPDATED Sprint 5.11 (DEC-020)**: the credit gap ALSO left TARGET_BAND —
   the Sprint 5.11 evidence audit reclassified it to ONE_SIDED_VULNERABILITY
   (positive-side breakpoints supported by Basel/BIS evidence; negative-side
   penalty NOT supported). **RESOLVED 2026-09-09 (DEC-021)**: the owner
   approved the credit-gap numeric curve — neutral ceiling +2pp, linear to
   0 at +10pp, no-excess region = 50 — implemented in Sprint 5.12 (model
   version normalization-v0.6). No other TARGET_BAND indicator remains.
3. MONOTONIC_SATURATING curve for gross capital formation. **RESOLVED
   Sprint 5.9 (DEC-018)**: the proposal was DISPROVED (very high GCF can be
   credit-driven overinvestment; no defensible universal healthy level) —
   GCF is reclassified to CONTEXTUAL_DEFERRED.
4. Trade-force multi-indicator composition (whether any defensible level
   exists, or the force stays momentum/context-only).
5. Momentum sign conventions and window values (3y/5y, 4q/8q are
   candidates, not decisions). **RESOLVED 2026-09-09 (DEC-016) FOR THE WGI
   ×3 ONLY**: higher WGI = positive (windows 3y/5y, primary 5y, tolerance
   1 annual period). Every other indicator's sign convention and window
   values remain open until its momentum is implemented.
6. Confidence composition (product vs weighted factors) and factor weights.
   **Sprint 5.13 (DEC-022)**: the LAYERING is resolved — indicator
   confidence (§10.2) is separated from force confidence (§10.3), the
   permanent rules (confidence != strength, confidence != freshness, missing
   != perfect != zero, no arbitrary provider-quality constants) are locked,
   and the WGI uncertainty inputs are identified (LB + UB + SR). **Sprint
   5.16**: the empirical profile (624 rows, `scripts/wgi_confidence_profile.py`)
   found CI width and SR are HIGHLY REDUNDANT (Pearson -0.83), dimension
   differences are substantial and unexplained, temporal trends make
   empirical calibration leaky or drifting, and no external calibration basis
   exists for a numeric mapping. Verdict: **DEFER_NUMERIC_CONFIDENCE** — a
   durable methodology decision (see the Sprint 5.16 section above for the
   full decision matrix and the evidence/data/methodology required before
   numeric confidence can be defensibly implemented). The NUMERIC composition
   and weights remain open.
7. Labour productivity: levels (favor advanced economies) vs growth rates for
   fairness — final choice deferred to scoring sprint. **UPDATED Sprint 5.9
   (DEC-018)**: the MONOTONIC_POSITIVE direction is approved, but the
   ABSOLUTE level curve is DEFERRED — no tracked_8 min-max; an expanded
   calibration universe decision (e.g. OECD-wide distribution) is required
   first. Level and growth stay separable dimensions.
8. Military relative-share concept (tracked-8 share vs global share vs
   PPP-adjusted resources).
9. Whether/when to import WGI uncertainty series (SE/CI/number of sources)
   for measurement_confidence. **RESOLVED 2026-09-09 (Sprint 5.13, DEC-022)**:
   audited live and verified — LB/UB are 90% CI bounds on the SAME 0–100
   governance-score scale as the imported score, SE is on the underlying
   estimate scale (and cannot reconstruct the published bounds), SR is an
   integer source count, all 8 tracked countries have all four series for
   every score year 1996–2024. Selected initial input set: LB + UB + SR
   (CI width as the primary measurement diagnostic; SE deferred).
   Representation: dedicated auxiliary-diagnostics storage (the Sprint
   5.13 decision matrix rejected auxiliary canonical indicators, multiple
   SourceSeries per indicator, and raw_payload metadata). **UPDATED Sprint
   5.14:** the storage/persistence/lookup foundation is implemented
   (`indicator_diagnostics` migration applied; exact-period lookup;
   nothing ingested). **RESOLVED 2026-09-09 (Sprint 5.15):** LIVE
   INGESTION complete — the 9 LB/UB/SR series are imported into
   `indicator_diagnostics` (1872 rows = 8 countries × 3 indicators ×
   3 kinds × 26 score years; LB ≤ score ≤ UB verified 624/624; SR
   integer 4–16; one-to-one score-year alignment; idempotent re-import;
   no canonical/SourceSeries/Observation pollution). The input DATA now
   exists; using it for confidence is still §17 item 6's open numeric
   composition.
10. WGI biennial-gap handling in scoring snapshots (missing 1997/1999/2001).
    **RESOLVED FOR THE CURRENT WGI PATH ONLY (2026-09-09)**: level and
    relative snapshots handle the gaps via DEC-015 as-of alignment (a
    snapshot aligns to the latest period-complete observation, so a missing
    year is never forward-filled), and WGI momentum handles them via the
    DEC-016 1-year anchor tolerance (a biennial gap resolves to the prior
    year; older → change = None). This is alignment mechanics ONLY — it does
    NOT imply release-date safety (backtest_safe stays False until
    Milestone 9).
11. Force weights — out of scope entirely until the scoring sprint.

## What this sprint explicitly does NOT do

*(Sprint 5.5 closing scope — superseded by the sprint-status sections above:
`level_score` (Sprint 5.6), `momentum` (Sprint 5.7/DEC-016), and
`relative_score` (Sprint 5.8/DEC-017) are now executable for the WGI ×3,
`level_score` is now executable for DEBT_SERVICE_RATIO via OWN_HISTORY
(Sprint 5.10/DEC-019), and for CREDIT_TO_GDP_GAP via ONE_SIDED_VULNERABILITY
(Sprint 5.12/DEC-021). The points below remain true for everything else —
the 14 remaining non-WGI indicators still raise
`NormalizationNotImplementedError`.)*

- No force scores, no force weights, no Big Cycle phase.
- No confidence numbers anywhere (`confidence` remains None on every
  signal — composition unresolved, §17).
- No normalizer computation for the remaining non-WGI indicators (they
  raise `NormalizationNotImplementedError`).
- No API connection, no frontend change, no new data, no raw-layer change.
- No persistence of derived signals (computed on demand only).
- `level_score`, `relative_score`, `momentum`, `confidence` remain
  `Optional`/`None` in the typed structures until each dimension's
  methodology is implemented and versioned.

## Sprint 6.2 methodology status (2026-09-10) — GOVERNMENT-DEBT NORMALIZATION AUDIT (DEC-031)

A METHODOLOGY / RESEARCH sprint. NO `GOVERNMENT_DEBT_GDP` level_score was
implemented; NO NormalizedSignal output changed; NO force code changed;
the model version stays `normalization-v0.6` and the force aggregation
version stays `force-aggregation-v0.1`. `GOVERNMENT_DEBT_GDP` stays
`CONTEXTUAL_DEFERRED` in the registry. Indebtedness stays `DEFERRED_MULTI`
with `level_score = None`. No DB writes, no migrations, no commit/push.

### Verdict: DEFER_GOVERNMENT_DEBT_LEVEL

No defensible semantic target exists for a government-debt/GDP LEVEL
signal that is (a) cross-country comparable, (b) composable with DSR
(OWN_HISTORY flow-stress) and credit gap (ONE_SIDED_VULNERABILITY excess-
credit), and (c) implementable from data currently in the Atlas.

### Official-source evidence (primary)

- **IMF (2011, "Modernizing the Framework for Fiscal Policy and Public
  Debt Sustainability Analysis")**: "no sound basis for integrating
  specific sustainability thresholds into the DSA framework"; a 60%
  reference point may be used FLEXIBLY to trigger deeper analysis, and
  other vulnerabilities can require deeper analysis even below 60%.
- **IMF (2013, "Staff Guidance Note for Public Debt Sustainability
  Analysis in Market-Access Countries")**: differentiated triggers
  (60% for advanced economies, 50% for emerging markets) — these are
  TRIGGERS, not thresholds, and they differ by WEO classification.
- **IMF (2022, SRDSF)**: replaces the MAC DSA with a multivariate logit
  model, debt fanchart, and rollover-risk modules. Risk is divided into
  low/moderate/high zones calibrated by false-alarm and missed-crisis
  probabilities (10% each), NOT by a universal debt/GDP threshold. "The
  framework does not in fact use binary decision rules."
- **EU Maastricht Treaty (Protocol on the Excessive Deficit
  Procedure)**: 60% debt/GDP reference value for EU member states with a
  shared monetary/institutional framework. The treaty allows the ratio
  to exceed 60% if "sufficiently diminishing and approaching the
  reference value at a satisfactory pace" — a convergence/fiscal-rule
  criterion, not a universal strength boundary.
- **World Bank (2010, Caner et al., WPS5391)**: growth-effect threshold
  of 77% (full sample) / 64% (developing economies). The threshold
  "differs substantially for developing and developed economies" — NOT
  universal.
- **World Bank (2018, "Debt Intolerance")**: thresholds depend on debt
  COMPOSITION (foreign private holdings share) — conditional, not
  universal.
- **Reinhart & Rogoff (2010) — 90% threshold**: debunked by Herndon,
  Ash & Pollin (2013) — coding errors, selective exclusion,
  unconventional weighting. Corrected mean growth above 90% is +2.2%,
  not -0.1%.
- **IMF (2014, "No Magic Threshold", Finance & Development)**: "little
  evidence that there is any particular debt ratio above which growth
  falls sharply."

**Synthesis:** No official source supports a universal debt/GDP
threshold for cross-country strength comparison. The IMF explicitly
states "no sound basis for specific sustainability thresholds." The 60%
Maastricht reference is a fiscal-rule convergence criterion for EU
member states. The 90% Reinhart-Rogoff threshold was debunked. The IMF
SRDSF uses multivariate risk bands, not a single debt/GDP threshold.

### Candidate families audited

| Family | Semantic | Cross-country comparable | Composable with DSR + CG | Defensible midpoint | Implementable now | Verdict |
|---|---|---|---|---|---|---|
| A. OWN_HISTORY_STRESS (DEC-019 analog) | trend / regime-position | NO | NO (third semantic) | NO (median-of-own-history is a trend signal) | yes | NOT a LEVEL — could be a MOMENTUM candidate |
| B. ABSOLUTE_FISCAL_BURDEN (monotonic) | higher debt = weaker | NO (JPN 214% sustained; IND 84% different constraints) | NO | NO (no official threshold) | yes | NOT defensible — encodes arbitrary norms |
| C. CROSS_SECTIONAL_LEVEL (rank within universe) | relative position | mechanically yes, but RELATIVE not LEVEL | NO (third semantic) | NO (tracked_8 prohibited as calibration universe) | yes | NOT a LEVEL — a future relative dimension needs its own DEC + universe |
| D. STRUCTURAL_BREAK_AWARE | position within current regime | NO | NO | NO | NO (no break-detection method) | NOT defensible as LEVEL in this sprint |
| E. SUSTAINABILITY/CAPACITY-ADJUSTED (multivariate) | debt/GDP adjusted for rates/growth/monetary-sovereignty/currency/maturity/fiscal-capacity | YES (the adjustment makes it comparable) | YES (would be a LEVEL signal) | YES (calibrated) | NO (data not in the Atlas) | The CORRECT long-term approach — requires additional data ingestion + multivariate model |
| F. CONTEXTUAL_DEFERRED (no curve) | none | n/a | n/a | n/a | yes | ACCEPTED — the only defensible current state |

### Empirical tracked_8 profile (read-only, 297 obs)

Per-country government-debt/GDP (latest vintage, IMF WEO
GGXWDG_NGDP): debt/GDP spans 20.4%–228.8%; JPN sustained debt/GDP >200%
for an extended period, demonstrating that debt/GDP alone does not
mechanically imply a universal distress threshold (the debt profile
itself contains no sovereign-distress outcome data; no causal claim is
made); CHE remains low (39.4%) but its DSR stress is high (level 16.7)
— rate-driven, not stock-driven. This confirms DSR (flow) and government
debt (stock) are not substitutes. The tracked_8 cross-sectional median
rose from 66.5% (2005) to 96.4% (2025) — a tracked_8 cross-sectional
trend (tracked_8 is not a global universe); any absolute threshold
would shift meaning over time.

### Own-history counterfactual (RESEARCH ONLY, not a published signal)

DEC-019-style mid-rank stress position applied to government debt:

| Country | current | own-history rank | hypothetical level |
|---|---:|---:|---:|
| JPN | 214.5 | 41/45 | 10.0 |
| CHE | 39.4 | 8/36 | 79.2 |
| USA | 123.9 | 23/25 | 10.0 |
| CHN | 90.4 | 30/30 | 1.7 |
| FRA | 113.2 | 44/45 | 3.3 |

This confirms candidate A is a TREND signal, not a LEVEL: JPN and USA
both get level 10 despite very different absolute burdens (214% vs
124%); CHN gets the worst score (1.7) because 90.4% is its all-time
high, even though 90.4% is below JPN's 1990 starting point. If JPN's
debt fell to 130% (below its median), it would get a strong own-history
score despite 130% debt/GDP — one of the highest in the world.

### Relation to DSR + credit gap composability

DSR (CORE_CONDITION, OWN_HISTORY): current debt-service FLOW burden
relative to own history. Credit gap (VULNERABILITY_PENALTY,
ONE_SIDED_VULNERABILITY): excess-credit vulnerability; neutral 50 = no
excess (NOT strength). Government debt (SUPPORTING_CONTEXT, currently
CONTEXTUAL_DEFERRED): stock of sovereign debt as % of GDP.

For government debt to be composable, it would need a LEVEL semantic
that is cross-country comparable, shares the "higher = weaker"
orientation, and has a defensible midpoint. None of the candidate
families satisfy all three. Even if a level curve were approved, a
separate composition DEC would still be required (DEC-030 Blocker 2
remains).

### Missingness and coverage boundary

This sprint does NOT generalize DEC-030's "all three required"
composition rule. Coverage boundary (preserved from DEC-029 §1.2 and
the Sprint 6.2 correction to DEC-030): coverage_status = data
availability. If DSR + credit-gap + government-debt observations are all
available, coverage MAY be AVAILABLE even while level_score = None. No
coverage ceiling is added to Indebtedness.

### Impact

NO production code changed. NO force code changes. NO normalization
code changes. NO phase, cycle composite, force confidence, relative
aggregation, momentum aggregation, persistence, API, or frontend.
Model versions unchanged: `normalization-v0.6`, `force-aggregation-v0.1`.
`GOVERNMENT_DEBT_GDP` stays `CONTEXTUAL_DEFERRED`. Indebtedness stays
`DEFERRED_MULTI` with `level_score = None`. confidence = None.
backtest_safe = False. Read-only profile script
(`scripts/gov_debt_profile.py`) retained as a research artifact (no
scores, no writes).

### Recommended Sprint 6.3

**Sprint 6.3 — Government-debt momentum candidate audit.** Since a
LEVEL curve is deferred but government debt is live, audit whether a
MOMENTUM signal (debt/GDP change relative to own history, DEC-016 analog)
is defensible. Momentum is a trend signal, which is what own-history
actually measures (candidate A reclassified from level to momentum).
This would NOT enable Indebtedness composition (still DEFERRED_MULTI),
but it would make government debt useful as a non-level signal and
inform future composition. If momentum is also not defensible, the next
option is to ingest additional data (interest rates, growth, monetary
sovereignty) for a future sustainability-adjusted level (candidate E).

## Sprint 6.3 methodology status (2026-09-10) — EDUCATION LEVEL CALIBRATION + PROXY-FORCE ELIGIBILITY AUDIT (DEC-032)

A METHODOLOGY / RESEARCH sprint. NO `TERTIARY_ATTAINMENT_25_34`
level_score was implemented; NO NormalizedSignal output changed; NO
force code changed; the model version stays `normalization-v0.6` and
the force aggregation version stays `force-aggregation-v0.1`.
`TERTIARY_ATTAINMENT_25_34` stays in the registry with
`level_family=monotonic_positive` (NOT yet `direct_0_100` — that
reclassification is a Sprint 6.4 implementation step). Education force
stays `SUPPORTING_CONTEXT` / `DEFERRED_MULTI` with `level_score = None`.
No DB writes, no migrations, no commit/push.

### Verdict: READY_FOR_EDUCATION_LEVEL_DESIGN

A defensible LEVEL semantic exists for
`TERTIARY_ATTAINMENT_25_34`: DIRECT_0_100 (raw percentage identity).
Sprint 6.4 MAY implement it subject to the conditions in DEC-032.

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
alone does NOT justify `level_score = raw percentage`. DIRECT_0_100 is
defensible here because the semantic meaning of the raw value IS the
level signal:

1. **The raw percentage has an absolute, cross-country comparable
   meaning.** 50% tertiary attainment means 50% of the 25-34
   population has completed ISCED 5-8 — this statement is true in the
   USA, in IND, in JPN, and in any OECD dataflow country, using the
   same ISCED 2011 classification and the same denominator definition.
   The OECD itself uses this indicator for cross-country level
   comparison (Education at a Glance Chapter A1, "To what level have
   adults studied?"; the OECD data dashboard "Population with tertiary
   education").

2. **Higher = stronger is defensible.** More tertiary attainment means
   a more educated young-adult cohort. The OECD frames rising tertiary
   attainment as a positive trend. The Atlas direction
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
   NOT endorse 50% as a policy target, but 50 has a clear semantic
   meaning as a population share.

5. **This is NOT the government-debt case.** DEC-031 deferred
   government-debt because no official source supports a universal
   debt/GDP threshold and the raw ratio does not have a defensible
   cross-country level meaning. Tertiary attainment is different: the
   OECD itself uses the raw percentage for cross-country level
   comparison, the scale is bounded 0-100 by construction, and higher
   unambiguously means more educated.

### No official benchmark / target percentage

The OECD does NOT publish a target or benchmark percentage for
tertiary attainment. The OECD reports the OECD average (48% of 25-34
year-olds in 2024) as a descriptive statistic, NOT as a normative
target. Therefore DIRECT_0_100 does NOT encode an OECD-endorsed target
— it preserves the raw population share as the level signal. A future
FIXED_MONOTONIC_CURVE with externally-justified thresholds would
require an official benchmark that does not exist today.

### Comparability limits (documented, not blocking)

The OECD itself notes comparability caveats: ISCED mapping differences
across countries; ISCED-97 → ISCED-2011 break (trend data before 2013
on ISCED 5+ no longer reliable for some countries); country-specific
methodology differences (e.g., UK GCSE equivalencies mapped to ISCED
3 completion). These are documented by the OECD and do not invalidate
the cross-country level comparison. The Atlas carries the same
comparability caveat as the OECD.

### Empirical tracked_8 profile (read-only, 200 obs)

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

Sparsity: CHN n=1 (2010 only — extremely sparse; freshness will gate
post-2010 snapshots); IND n=8 (sparse — momentum not viable); 6/8
countries have 29-35 annual observations (adequate for level/momentum
candidates). Sparsity affects level eligibility ONLY through freshness
(a stale observation is gated, not zeroed). It does NOT block the
DIRECT_0_100 family itself.

### Broader OECD dataflow universe (read-only external SDMX fetch)

The OECD dataflow contains 51 economies (not just OECD member states),
year span 1981-2025. Latest cross-section (2025): n=40, min 7.0%,
median 45.0%, max 71.1%. This is the OECD/dataflow universe — NOT
tracked_8, and NOT world/global. A CROSS_SECTIONAL_RELATIVE score
within this universe is a RELATIVE dimension, not a LEVEL. DIRECT_0_100
answers the level question directly.

### Candidate normalization methods audited

| Family | Semantic | Cross-country comparable | Defensible midpoint | CHN/IND sparsity | Result type | Verdict |
|---|---|---|---|---|---|---|
| A. RAW_PERCENT_IDENTITY (DIRECT_0_100) | share of 25-34 pop with ISCED 5-8 | YES (OECD-designed) | YES (50 = half the cohort) | level OK; momentum gated by freshness | LEVEL | **DEFENSIBLE — selected** |
| B. FIXED_MONOTONIC_CURVE | externally-justified thresholds | would be | would need benchmark | same | LEVEL | NOT defensible — no official benchmark |
| C. SAME-YEAR OECD/DATAFLOW CROSS-SECTION | relative position | mechanically | median of dataflow | same | RELATIVE | NOT a LEVEL — belongs in relative_score |
| D. EXPANDING BROADER-UNIVERSE CALIBRATION | percentile in expanding universe | mechanically | n/a | same | RELATIVE | NOT a LEVEL — relative dimension |
| E. OWN_HISTORY | progress vs own past | NO | NO | CHN n=1 impossible | MOMENTUM | NOT a LEVEL — momentum candidate |
| F. CONTEXTUAL_DEFERRED | none | n/a | n/a | n/a | none | Rejected — a defensible LEVEL exists (A) |

### Absolute vs relative

DIRECT_0_100 is a LEVEL signal, not a RELATIVE signal: it answers
"what share of the 25-34 population has tertiary attainment" — an
absolute, interpretable statement. It does NOT answer "where does this
country rank" (relative) or "is this country improving" (momentum).
The OECD itself uses the raw percentage for cross-country level
comparison.

### Proxy force eligibility

If DEC-032 is accepted (it is), Sprint 6.4 MAY implement:
1. Indicator level: `TERTIARY_ATTAINMENT_25_34` DIRECT_0_100 (reclassify
   registry `level_family` from `monotonic_positive` to `direct_0_100`;
   bump `normalization-v0.6` → `normalization-v0.7`).
2. Force aggregation: Education `SUPPORTING_CONTEXT` →
   `PROXY_CONDITION`; `DEFERRED_MULTI` → `IDENTITY_SINGLE`; bump
   `force-aggregation-v0.1` → `force-aggregation-v0.2`.
3. Coverage ceiling stays PARTIAL (DEC-009, DEC-026). No numeric
   modification of level_score by coverage.
4. Force notes must explicitly state this is a tertiary-attainment
   proxy.

### Relative / momentum / confidence boundaries

A level READY verdict does NOT automatically approve other dimensions:
- **Relative**: NOT approved. No reference-universe methodology
  approved. The OECD dataflow universe (51 economies) is a candidate
  but is NOT tracked_8 and is NOT global. Relative stays None.
- **Momentum**: NOT approved. CHN (n=1) cannot support momentum.
  Momentum stays None.
- **Confidence**: stays None (DEC-023).

### Impact

NO production code changed. NO force code changes. NO normalization
code changes. NO phase, cycle composite, force confidence, relative
aggregation, momentum aggregation, persistence, API, or frontend.
Model versions unchanged: `normalization-v0.6`, `force-aggregation-v0.1`.
`TERTIARY_ATTAINMENT_25_34` stays `monotonic_positive` in the registry.
Education stays `SUPPORTING_CONTEXT` / `DEFERRED_MULTI` with
`level_score = None`. confidence = None. backtest_safe = False.
Read-only research artifact `scripts/education_profile.py` retained
(no scores, no writes).

### Recommended Sprint 6.4

**Sprint 6.4 — Education level + proxy-force implementation.**
Implement DIRECT_0_100 for TERTIARY_ATTAINMENT_25_34 and promote
Education to the 4th executable force via PROXY_CONDITION +
IDENTITY_SINGLE. Specific steps: (1) reclassify registry
`level_family` to `direct_0_100`, bump normalization-v0.7; (2) promote
Education to PROXY_CONDITION + IDENTITY_SINGLE, bump
force-aggregation-v0.2; (3) force notes state this is a tertiary-
attainment proxy, coverage stays PARTIAL; (4) relative/momentum/
confidence stay None; (5) tests for DIRECT_0_100 level, IDENTITY_SINGLE
force, PARTIAL coverage, CHN/IND sparsity/freshness, no regression on
existing 3 forces.

Deliberately NOT queued in 6.4: relative score for education (needs
its own reference-universe DEC); momentum for education (CHN n=1
blocks; needs its own DEC); confidence (DEC-023); force persistence;
public force API; frontend force scores; cycle composite; phase/stage;
backtesting; trading; any other indicator's normalization curve.

## Sprint 6.4 implementation status (2026-09-10) — EDUCATION DIRECT_0_100 + EXPLICIT DIMENSION APPROVAL GATES (DEC-032)

### What changed

`TERTIARY_ATTAINMENT_25_34` reclassified from `MONOTONIC_POSITIVE` to
`DIRECT_0_100`. The level_score IS the aligned raw OECD percentage (ISCED
5-8, % of same-age population) preserved unchanged — no rescale, percentile,
z-score, invert, or winsorize. OECD publishes tertiary attainment as a
bounded absolute percentage and uses it for cross-country attainment
comparison; Atlas independently preserves that percentage as the
indicator-level level proxy.

### Critical hazard fixed: explicit dimension approval gates

The Sprint 5.7/5.8 family-combination gates (DIRECT_0_100 + OWN_HISTORY
for momentum; DIRECT_0_100 + CROSS_SECTIONAL_RELATIVE for relative)
resolved to the WGI x3 only because no other DIRECT_0_100 indicator
existed. Education's registry candidate families (OWN_HISTORY momentum,
CROSS_SECTIONAL_RELATIVE relative) would have SILENTLY passed those gates
once the level family changed.

v0.7 adds EXPLICIT approved indicator sets to `ModelVersionConfig`:
- `direct_momentum_approved_indicators` = WGI x3 exactly
- `direct_relative_approved_indicators` = WGI x3 exactly

A registry family declaration alone NEVER enables a dimension. The
direct relative helper (`build_relative_cross_section`) now also checks
the approved set. Education is deliberately NOT in either set — its
relative and momentum stay None (dimension separation: unapproved = None,
not error).

### Dimensions

- **Level**: DIRECT_0_100 identity (aligned raw percentage, validated
  [0, 100], no clamp, out-of-range raises `NormalizationDataError`).
- **Relative**: None (DEC-032: not approved; not in
  `direct_relative_approved_indicators`).
- **Momentum**: None (DEC-032: not approved; not in
  `direct_momentum_approved_indicators`).
- **Confidence**: None (DEC-023).

### Freshness / period-complete

Unchanged: annual freshness class, period-complete eligibility (annual
first eligible at its own Q4), no-future-leakage, latest-vintage. CHN
(1 obs, 2010) is stale at 2025-Q4 → None. IND (sparse) is usable when
fresh. Freshness gates usability but NEVER scales the direct raw score.

### Model versions

- `normalization-v0.6` → `normalization-v0.7`
  (method: `sprint-6.4-education-direct-0-100-explicit-dimension-gates`)
- `force-aggregation-v0.1` → `force-aggregation-v0.2`

### Tests

32 new tests in `tests/test_sprint_6_4_education.py` covering the A-G
matrix (level, missing/stale, out-of-range, dimension separation,
execution-gate regression, WGI regression, force behavior, 17-force
orchestration, no-writes, version propagation). 528 existing tests
updated for new versions and Education's new role. 560 total pass.

### Live smoke (tracked_8 @2025-Q4, read-only)

USA 52.77, CHE 50.60, DEU 40.88, FRA 53.35, GBR 61.19, JPN 67.53,
IND 23.10, CHN None (stale 2010). Education relative/momentum/confidence
None everywhere. Other 3 forces unaffected. DB counts unchanged
(6814/27/22/10/1872). No writes.

### What did NOT change

All v0.6 WGI + DSR + credit-gap configuration unchanged. WGI x3 level,
momentum, and relative outputs are byte-equivalent. DSR own-history level
unchanged. Credit-gap one-sided-vulnerability level unchanged. No force
persistence. No public force API. No frontend force scores. No cycle
composite. No phase/stage. No backtesting. No commit/push.