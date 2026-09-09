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
OWN_HISTORY level. Current truth: WGI ×3 have executable level + momentum +
relative; DEBT_SERVICE_RATIO has an executable OWN_HISTORY level;
`confidence` remains None on every signal, and every OTHER non-WGI level
indicator still raises NormalizationNotImplementedError. No force
aggregation, no weights, no Big Cycle phase, no persistence, no HTTP
endpoint. Every signal: `backtest_safe = false` (alignment is by
observation period, not release date — Milestone 9 owns that); current
model version `normalization-v0.5`.)* Tests:
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
| `ONE_SIDED_VULNERABILITY` | No stress is signaled at or below a neutral ceiling; stress rises monotonically ABOVE it (added by Sprint 5.11/DEC-020 for the credit-to-GDP gap: authoritative evidence supports positive-side excess-credit breakpoints but NO negative-side penalty — the below-ceiling region carries no health signal from this indicator). Breakpoints are versioned model parameters, never invented silently. |
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
| GINI_INDEX | MONOTONIC_NEGATIVE, numeric curve deferred (direction confirmed by DEC-018) | CROSS_SECTIONAL_RELATIVE (weak: survey-base differences) | OWN_HISTORY (irregular — only when enough observations) | irregular | Higher = more income inequality. "100 − Gini" is NOT an approved mapping; the calibration universe (global vs tracked_8) and survey-base comparability remain open. Never forward-filled; freshness decay applies to stale values. Force capped PARTIAL (income ≠ wealth/opportunity/values). |
| INFLATION_CPI | CONTEXTUAL_DEFERRED (reclassified by DEC-018 — Sprint 5.9 audit; superseded the Sprint 5.5 TARGET_BAND proposal) | CONTEXTUAL_DEFERRED | OWN_HISTORY (3y, 5y) | annual | Domestic price pressure; a universal raw-CPI band would encode "2% ideal for every country" (objectives differ across regimes). Level waits for a defensible per-country target/reference. |
| MILITARY_EXPENDITURE_USD | CONTEXTUAL_DEFERRED | RELATIVE_SHARE (future; share of tracked/global spending, or PPP-adjusted resources) | — | annual | Nominal, scale-dependent; spending ≠ capability (DEC-011). No more-spending-is-stronger curve. |
| MILITARY_EXPENDITURE_GDP | CONTEXTUAL_DEFERRED | CONTEXTUAL_DEFERRED | — | annual | Effort/burden, not capability. |
| RULE_OF_LAW_WGI_SCORE | DIRECT_0_100 | CROSS_SECTIONAL_RELATIVE (optional, later) | OWN_HISTORY (3y, 5y) | annual | Provider's fixed 0–100 absolute scale preserved — never percentile-ranked. Perception uncertainty documented (CI/SE series not imported). |
| CONTROL_OF_CORRUPTION_WGI_SCORE | DIRECT_0_100 | CROSS_SECTIONAL_RELATIVE (optional, later) | OWN_HISTORY (3y, 5y) | annual | Higher = stronger control; raw value never reversed. Perception uncertainty. |
| POLITICAL_STABILITY_WGI_SCORE | DIRECT_0_100 | CROSS_SECTIONAL_RELATIVE (optional, later) | OWN_HISTORY (3y, 5y) | annual | Feeds the ceiling-capped internal-conflict force; the indicator spec itself is a normal DIRECT_0_100 entry (ceilings act at the force layer only). |
| CREDIT_TO_GDP_GAP | ONE_SIDED_VULNERABILITY (reclassified from asymmetric TARGET_BAND by Sprint 5.11 evidence audit, DEC-020) | CONTEXTUAL_DEFERRED | OWN_HISTORY (4q, 8q) | quarterly | The indicator measures EXCESS-CREDIT vulnerability on the positive side: authoritative evidence supports positive breakpoints (Basel CCyB guide +2/+10; BIS 2018 EWI red ~9 / amber 4–9) but NO negative-side penalty — the guide is flat zero below +2 and a persistent negative gap is a post-boom measurement artifact, not an unhealthy-debt signal. Deleveraging/weak-credit conditions belong to other signals (DSR level, credit growth, output). Numeric Atlas breakpoints unresolved pending owner approval — NOT implemented. |
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

## 10. Confidence architecture

Confidence is a composition of qualitative factors, per signal:

| Factor | Captures |
|---|---|
| `source_confidence` | Provider/methodology quality (WGI: strong coverage, perception uncertainty; SIPRI input measure). |
| `freshness_confidence` | Section 5 decay (e.g. a 2020 Gini scores low even though Gini itself is well measured). |
| `coverage_confidence` | Fraction of the force's inputs usable for this snapshot (CHN productivity: GDP growth only → lower force confidence; never zero-fill the missing OECD series). |
| `measurement_confidence` | Known uncertainty (WGI CI/SE documented, not imported). |
| `proxy_confidence` | Ceiling-capped forces (GINI / POLITICAL_STABILITY / military spending) are explicit proxies. |

Rules:

- The exact composition (product vs weighted) is an unresolved question;
  whatever is chosen is a versioned model parameter — no fake `0.873`
  precision from arbitrary constants.
- Coverage ceilings affect confidence/completeness of the FORCE, never the
  normalized indicator values themselves (Section 12).
- Missing inputs reduce confidence and coverage; they never enter as zero.

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
    force_mapping_version      # indicator→force mapping revision (M5.4 config)
    backtest_safe              # Section 4 — False until Milestone 9
```

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
   penalty NOT supported). Its numeric Atlas breakpoints remain UNRESOLVED
   pending owner approval — no values invented.
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
7. Labour productivity: levels (favor advanced economies) vs growth rates for
   fairness — final choice deferred to scoring sprint. **UPDATED Sprint 5.9
   (DEC-018)**: the MONOTONIC_POSITIVE direction is approved, but the
   ABSOLUTE level curve is DEFERRED — no tracked_8 min-max; an expanded
   calibration universe decision (e.g. OECD-wide distribution) is required
   first. Level and growth stay separable dimensions.
8. Military relative-share concept (tracked-8 share vs global share vs
   PPP-adjusted resources).
9. Whether/when to import WGI uncertainty series (SE/CI/number of sources)
   for measurement_confidence.
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
and `level_score` is now executable for DEBT_SERVICE_RATIO via OWN_HISTORY
(Sprint 5.10/DEC-019). The points below remain true for everything else —
the 15 remaining non-WGI indicators still raise
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