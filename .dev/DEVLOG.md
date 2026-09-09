# Devlog

## 2026-09-09 — Sprint 5.11: Credit-to-GDP gap evidence audit (DEC-020)

### Goal

Owner-directed, timeboxed METHODOLOGY brief — evidence-first audit for CREDIT_TO_GDP_GAP, NO score implementation: (1) what official BIS/Basel literature supports on the POSITIVE side; (2) whether authoritative evidence supports treating LARGE NEGATIVE gaps as intrinsically unhealthy in the SAME indicator-level score; (3) whether the DEC-018 asymmetric TARGET_BAND classification should remain, be reframed, or be deferred. Valid outcomes: KEEP_ASYMMETRIC_TARGET_BAND / RECLASSIFY-REFRAME / DEFER_LEVEL. Primary sources only (bis.org, BCBS); no invented negative threshold; three threshold concepts kept separated (Basel CCyB guide vs statistical early-warning vs Atlas normalization parameters).

### Completed

- **Part 0 doc cleanup**: NORMALIZATION.md Sprint-5.6 closer now states current truth — model version normalization-v0.5, DSR OWN_HISTORY level implemented, "every OTHER non-WGI level indicator" still raises; the Sprint-5.5 closing-scope note updated likewise. Historical sprint descriptions untouched.
- **Provider definition verified (Part 2)**: gap = credit-to-GDP ratio − long-run trend, one-sided HP filter λ=400,000, total credit to the private non-financial sector; Atlas consumes the published BIS gap, never recomputes. Sources: BIS Data Portal credit-gaps overview; Drehmann (2013) BIS QR; BIS Bulletin Table J.
- **Positive side (Part 4) — SUPPORTED**: Basel CCyB guide (BCBS 2010, bcbs187/bcbs172) L=+2pp / H=+10pp, linear 0→2.5%-of-RWA add-on, flat zero below +2, explicitly non-mechanical; calibration criteria documented (L: capital builds 2–3y pre-crisis, none in normal times; H: buffer maxes before US 2007 / Japan 1990s; robust type-1/type-2 trade-off). BIS 2018 EWI exercise (Aldasoro, Borio & Drehmann, BIS QR March 2018): critical threshold ~9pp standalone (80% of crises, 25.7% noise-to-signal), amber 4–9 / red ≥9, ~4pp when combined with property-price gaps. Earlier ~10 evidence: Borio & Lowe (2002) + the BCBS calibration. The two lines are DIFFERENT instruments and are recorded separately.
- **Negative side (Part 5) — NOT supported; nothing invented**: Basel guide flat zero below +2 (no rising penalty); BIS 2014 Q&A (Drehmann & Tsatsaronis) treats the negative region as a "no consequence" post-crisis phase (buffer would have been released; release is judgmental); the persistent post-bust negative gap is a documented MEASUREMENT ARTIFACT — boom-contaminated HP trend understating renewed vulnerability, per IMF WP 2020/006's assessment of the BIS gap (several European authorities set positive CCyB rates despite negative Basel gaps); post-crisis deleveraging is essentially uncorrelated with recovery pace (Takáts & Upper, BIS WP 416). The DEC-018 "very negative = deleveraging/weak credit" penalty expectation is RETRACTED — association (A) does not imply threshold evidence (B); deleveraging/weak-credit belongs to other signals (DSR own-history level, credit growth, output).
- **Basel caution (Part 7)**: current framework text (CAD 20) — the gap is "a useful common reference point"; judgment required, not mechanistic; "mindful of misleading signals" (GDP-denominator-driven increases, non-fundamental spread moves); supplementary indicators include debt service capacity. 2014 Q&A misleading-signal modes documented (trend absorbing protracted booms, structural breaks ~20y washout, endpoint revisions, BIS-vs-national gaps). Any future Atlas curve must carry these as score-interpretation limits.
- **As-of semantics (Part 8)**: BIS's one-sided trend does NOT solve Atlas release-date safety — backtest_safe stays False.
- **Minimum history (Part 9)**: the "≥10 years" rule belongs to CONSTRUCTING a reliable HP trend (BIS computed it on decades of data); Atlas consumes the published series, so no blind 10-year Atlas scoring minimum was added. Any Atlas minimum (e.g. for endpoint/trend-revision stability) is a separate design question.
- **Descriptive profile (Part 10)**: read-only normalization_profile.py --indicator CREDIT_TO_GDP_GAP (832 obs; pooled min −29.7 / median 0.4 / max 29.4) + bucket counts (<0: 403, 0–2: 53, 2–4: 48, 4–9: 158, 9–10: 29, >10: 141). DESCRIPTIVE ONLY.
- **Evidence matrix + verdict (Parts 11–12)**: full matrix in NORMALIZATION.md "Sprint 5.11" (each value: source, purpose in source, supports / does NOT support). Verdict: **RECLASSIFY / REFRAME — asymmetric TARGET_BAND → ONE_SIDED_VULNERABILITY**: at-or-below-trend carries NO excess-vulnerability penalty (indicator silent about health there, consistent with the guide's zero zone), level weakens monotonically above a neutral ceiling. DEFER rejected (positive side is defensibly supported — dual-source official evidence); KEEP rejected (negative-side penalty has no evidence at all). Owner-approval list before any implementation: neutral ceiling, positive-side curve shape, endpoint behavior, score interpretation of the no-excess region, caveat-carried score-interpretation limits.
- **Registry (Part 14)**: new `NormalizationFamily.one_sided_vulnerability` (documented in the enum + §6); CREDIT_TO_GDP_GAP level_family reclassified with the full evidence note; relative/momentum/freshness unchanged; NO model-version bump (normalization-v0.5 — no score semantics became executable).
- **Tests (Part 15)**: Sprint-5.9 exact-classification table updated (CREDIT_TO_GDP_GAP → one_sided_vulnerability, DEC-020 comment) + 1 new regression (the reclassified family still raises NormalizationNotImplementedError; no numeric breakpoint exists) → **312 total**; full suite green confirms DSR v0.5 outputs, WGI outputs, and all still-unscored gates unchanged.

### Results

- pytest: **312 passed, 0 failed** (all offline; baseline 311).
- Live verification read-only (nothing written): normalization_profile.py + bucket-count query for CREDIT_TO_GDP_GAP — descriptive only.
- No frontend change → no npm build; no API route, model, migration, mapping, seed, or raw-data changes; no executable scoring change (credit gap raised NormalizationNotImplementedError before and after).

### Not done (deliberately)

- NO credit-gap level_score, NO +2/+10 or +4/+9 piecewise Atlas score, NO negative-side threshold, NO DSR momentum/relative, NO Gini/productivity/GDP-growth/CPI/ULC scoring, NO non-WGI relative, NO confidence, NO force weights/Indebtedness force score/cycle composite/phase, NO persistence, NO public scoring API, NO frontend score UI, NO new provider imports.
- No provisional numeric Atlas breakpoints recorded anywhere (DECISIONS.md included).

### Next

- Sprint 5.12 — owner to choose: credit-gap one-sided curve design + implementation (evidence-backed; owner approves the breakpoints and limits), confidence-dimension design (WGI uncertainty import first), Gini calibration universe, productivity expanded universe, or data-side work (education Option C / IMF WEO / WID).

## 2026-09-09 — Sprint 5.10: DSR OWN_HISTORY level signal (DEC-019)

### Goal

Owner-directed, timeboxed brief — the FIRST non-WGI level normalization: DEBT_SERVICE_RATIO → OWN_HISTORY `level_score`, answering "where is the country's current DSR relative to ITS OWN historical DSR distribution as of this scoring snapshot?" — NOT a cross-country comparison (cross-country raw-DSR ranking PROHIBITED per BIS caution), NOT a tracked_8/global percentile, NOT a probability/force score/phase. LOCKED: expanding own-history calibration from first eligible observation through the current aligned observation INCLUSIVE, never post-snapshot data, still backtest_safe False; real observations only (latest vintage per actual source period, no forward-fill/interpolate/duplicate-across-quarters/zero-fill); minimum_sample_n = 20 (Atlas VERSIONED MODEL PARAMETER, NOT BIS truth) — below → level None never 0, unscored signal still returns with provenance; empirical mid-rank plotting position `stress_percentile = 100 * (average_rank − 0.5) / n` (rank 1 = lowest = least stress, ties = average rank, deterministic), `level_score = 100 − stress_percentile`; endpoints NOT forced to 100/0 (n=20 → 97.5/2.5), no clamping; freshness gates the current observation only (unusable → no signal) and NEVER scales the score; historical calibration points never decayed; DSR relative/momentum/confidence stay None; execution gated by a versioned own_history_level_configs entry for EXACTLY DEBT_SERVICE_RATIO — registry alone never auto-enables; model version → normalization-v0.5, DEC-019, no persistence, no public API, no force scores.

### Completed

- **Part 0 doc cleanup**: NORMALIZATION.md §7 table rewritten to agree with DEC-018 (GDP_GROWTH / GCF / INFLATION_CPI / UNIT_LABOUR_COST_GROWTH → CONTEXTUAL_DEFERRED, explicitly marked as DEC-018 reclassifications superseding the Sprint 5.5 proposals; Gini curve-deferred; credit-gap thresholds-unresolved; DSR OWN_HISTORY; productivity curve-deferred); HANDOFF In progress / Next task updated.
- **normalization_definitions.py**: `OwnHistoryLevelResult` (sample_n, minimum_sample_n, earliest/latest_source_period, rank, stress_percentile, level_score; post-init: scored fields travel together, stress in (0,100), zero-masquerading rejected) + `OwnHistoryLevelConfig` (positive minimum_sample_n) frozen dataclasses; `NormalizedSignal.own_history_level`; `ModelVersionConfig.own_history_level_configs` (docstring: the execution gate); `CURRENT_MODEL_VERSION` → **normalization-v0.5** / `sprint-5.10-dsr-own-history-level-r1` with `own_history_level_configs={"DEBT_SERVICE_RATIO": min 20}` and a version-history comment documenting every DSR choice; all WGI v0.3/v0.4 config unchanged; `validate_normalization_registry()` cross-checks the configs against the registry (lives there because the registry is defined after CURRENT_MODEL_VERSION — avoids import-time NameError).
- **alignment_service.py**: `own_history_as_of(session, country_iso3, indicator_code, scoring_period)` — as-of own-history selection with IDENTICAL semantics to `align_observation_as_of` (country + indicator lookup, latest-vintage subquery + outer join, `period_start <= as_of`, DEC-015 period-complete condition) but returning ALL eligible rows ascending; the last element IS the current aligned observation (the DSR path needs no separate align call — eliminates a cross-path consistency hazard); read-only.
- **normalizer.py**: dispatch refactor — `normalize_indicator_as_of` routes direct_0_100 → `_normalize_direct_0_100_as_of` (the former body, behavior UNCHANGED, byte-equivalent for WGI) and own_history → `_normalize_own_history_as_of`; all other level families raise NormalizationNotImplementedError listing the executable set. `_normalize_own_history_as_of`: config gate (no own_history_level_configs entry → raises, never auto-enabled) → own_history_as_of → empty → None signal → freshness gate (unusable → None signal) → min-20 gate (below → level None, never 0, counts as provenance) → `own_history_stress_position`. New pure function `own_history_stress_position(sample, current)`: strictly-below + tied counts, average_rank = strictly_below + (tied + 1)/2, stress = 100*(rank − 0.5)/n; membership-checked (current must be in the sample — guaranteed by construction since the expanding sample includes it), order-independent, empty-sample guarded.
- **Smoke** (`scripts/normalize_smoke.py`, read-only, ASCII): `--all-tracked` mode (TRACKED_8_MEMBERS loop, `=== ISO3 ===` headers, failure counting); `_print_signal` gained the own-history block (level or not-available-with-counts, sample n + minimum, calibration span, rank + stress percentile + "level = 100 − stress percentile"), "Momentum: not calculated" when no windows, per-method freshness note (historical anchors and calibration points are never decayed), DSR BIS-caution note.
- **Tests**: `tests/test_dsr_own_history.py` (NEW, 26 tests — execution gate/no auto-enable/expanding calibration/future-observation zero effect/latest-vintage-in-sample/country isolation/gap ≠ zero-fill (exact-score proof: a phantom zero would give 2.381 instead of 2.5)/n=19 → None/n=20 → first score/pure mid-rank (ties, permutation-independence, constant → 50, guards)/endpoints 97.5 & 2.5/median tie exactly 50/exact formula/OwnHistoryLevelResult validation/unusable staleness → no signal/freshness never scales/calibration points not decayed/relative+momentum+confidence None/backtest_safe False/v0.5 + exactly-DSR config/WGI level+momentum+relative unchanged with the DSR machinery present (CHE RL revision regression intact)/no DB writes + raw values never mutated/no force-weight-phase fields on NormalizedSignal) + v0.5 assertions updated in `test_normalization_signals.py` + `test_relative_scores.py` → **311 total**.

### Results

- pytest: **311 passed, 0 failed** (all offline; baseline 285).
- Live read-only smoke (Postgres, nothing written, no hardcoded expectations): --all-tracked DSR @2025-Q4 — all 8 countries score with n=104 histories, calibration 2000-Q1..2025-Q4: USA 14.1 → **94.7115** (rank 6/104), CHN 18.8 → **2.88462** (rank 101.5/104), CHE 19.7 → 13.4615, DEU 12.2 → 88.9423, FRA 20.8 → 4.32692 (rank 100/104), GBR 13.1 → 96.1538, JPN 15.5 → 25, IND 12.2 → 43.75; boundary verified: CHE @2004-Q3 → raw 15.6 present, n=19, level None (NOT zero), CHE @2004-Q4 → n=20, first score 97.5 (rank 1, stress 2.5). All model version normalization-v0.5, backtest safe: false.
- No frontend change → no npm build; no API route, model, migration, mapping, seed, or raw-data changes.

### Not done (deliberately)

- DSR momentum (registry 4q/8q windows stay unapproved), DSR relative (cross-country raw-DSR ranking prohibited — None by design, not a TODO), credit-gap score/thresholds, Gini curve, productivity curve, GDP-growth/GCF/CPI/ULC scoring, non-WGI relative, confidence, force aggregation/weights/scores, phase, persistence, public scoring API, frontend score UI, new provider/data imports.
- Release-date discipline — still Milestone 9; every signal keeps `backtest_safe = False`.

### Next

- Sprint 5.11 — owner to choose. Candidates: credit-gap TARGET_BAND threshold research (BIS early-warning literature first), confidence-dimension design (WGI uncertainty import), Gini calibration universe, productivity expanded universe, data-side work (education Option C / IMF WEO / WID).

## 2026-09-09 — Sprint 5.9: normalization parameter decision audit + relative hardening (DEC-018)

### Goal

Owner-directed, timeboxed METHODOLOGY brief — two outputs only, no new scores: (A) harden the Sprint 5.8 relative helper (`build_relative_cross_section`) so a direct call cannot accidentally relative-rank non-approved indicators (GINI_INDEX / GDP_GROWTH / GCF / LABOUR_PRODUCTIVITY_PER_HOUR) — preferred gate = level DIRECT_0_100 AND relative CROSS_SECTIONAL_RELATIVE (exactly the WGI ×3 under the current registry, no hardcoded codes), WGI outputs unchanged, no model-version bump unless semantics change; (B) critically review the unresolved non-WGI level-normalization proposals BEFORE any numeric thresholds are implemented — DEFERRED is a valid outcome, no thresholds invented, no force weights, no new scores.

### Completed

- **Part 0 hardening (`app/cycle/relative.py`)**: `build_relative_cross_section` now enforces its own execution gate before any alignment/ranking — level family DIRECT_0_100 AND relative family CROSS_SECTIONAL_RELATIVE → exactly the WGI ×3 under the current registry; a direct helper call for any other indicator raises `NormalizationNotImplementedError`. Complete-universe / freshness / 0..100-validation rules untouched; read-only as before. NO model-version bump: WGI outputs verified unchanged (live smoke: CHE RL @2025-Q2 → 87.3184 / relative 93.75 rank 8/8 / momentum −2.58971; CHN RL → 6.25 rank 1/8).
- **Part 1 doc drift**: NORMALIZATION.md — stale Sprint-5.5/5.6 "nothing computed / all dimensions None" closers corrected (WGI ×3 now have level + momentum + relative; confidence remains None); §5 + freshness.py docstring — decay shape documented as SETTLED exponential per DEC-013 (linear implementation retained as an available alternative for tests/future versions); §17 item 10 (WGI biennial gaps) marked RESOLVED FOR THE CURRENT WGI PATH ONLY (DEC-015 alignment + DEC-016 tolerance; no release-date safety implied); "other 15/16 indicators" → "non-WGI indicators" in the living docs; HANDOFF decision-summary corrected — the uq_observations_identity fix and the no-data handling are engineering decisions with NO DECISIONS.md record (the old "DEC-005"/"DEC-006" labels were numbering mistakes; DECISIONS.md is authoritative).
- **Parts 2–10 audit (recorded as "Non-WGI Level Parameter Decision Audit — Sprint 5.9" in NORMALIZATION.md + DEC-018)**: GDP_GROWTH RECLASSIFIED target_band → CONTEXTUAL_DEFERRED (universal band indefensible — tracked_8 GDP-growth medians 2015–2025 span 0.8–7.2; future design candidate: own-history deviation + relative growth + potential-growth gap, no potential-output series imported); GROSS_CAPITAL_FORMATION_GDP RECLASSIFIED monotonic_saturating → CONTEXTUAL_DEFERRED (saturating disproved — very high GCF can be credit-driven overinvestment; healthy level economy-model-dependent: medians CHN 42.4 vs GBR 18.5); INFLATION_CPI RECLASSIFIED target_band → CONTEXTUAL_DEFERRED (objectives differ across regimes: medians IND 6.35 vs JPN 0.29 — "2% ideal for every country" forbidden; series stays live for coverage); UNIT_LABOUR_COST_GROWTH RECLASSIFIED target_band → CONTEXTUAL_DEFERRED (raw domestic ULC growth is not by itself a relative-competitiveness measure — no FX/partner-ULC context; no arbitrary zero-centered band); GINI_INDEX family CONFIRMED MONOTONIC_NEGATIVE (direction approved, numeric level curve DEFERRED — "100 − Gini" NOT approved; global-calibration question open; irregular freshness stays); CREDIT_TO_GDP_GAP asymmetric TARGET_BAND family CONFIRMED (lower is NOT always better; separate positive/negative slopes expected; thresholds UNRESOLVED — research question recorded: what values the BIS early-warning literature justifies + how the calibration must be as-of-safe); DEBT_SERVICE_RATIO OWN_HISTORY CONFIRMED — **READY_FOR_IMPLEMENTATION_DESIGN, selected as the NEXT implementation target** (self-contained own-history design needs no external calibration; 104 quarters/country; open design questions: minimum sample, expanding as-of window, robust transform (percentile vs z/MAD), stress-percentile → Atlas 0–100 mapping, insufficient early history → None); LABOUR_PRODUCTIVITY_PER_HOUR direction CONFIRMED MONOTONIC_POSITIVE but the ABSOLUTE level curve DEFERRED (tracked_8 min-max explicitly rejected — pooled range 33.5–90.5 is not a global distribution; expanded calibration universe decision required; CHN/IND not covered by OECD).
- **Part 11 research support**: `scripts/normalization_profile.py` (NEW, READ-ONLY) — per-country + pooled descriptive statistics (count, earliest/latest, min/p10/p25/median/p75/p90/max, latest-vintage dedup) for the 8 audited indicators; NO scores, NO writes, NO API; explicitly NOT proof that an empirical percentile is economic truth. Run live read-only on Postgres; results fed the audit narrative.
- **Registry (`normalization_definitions.py`)**: the 4 reclassifications implemented + audited notes on all 8 audited specs; `CURRENT_MODEL_VERSION` unchanged (normalization-v0.4); momentum config untouched; every non-WGI indicator still raises NormalizationNotImplementedError.
- **Tests**: +5 hardening regressions in `tests/test_relative_scores.py` (direct helper rejects GINI_INDEX / GDP_GROWTH / GCF / productivity + contextual_deferred-relative; WGI direct-helper mid-rank table unchanged; complete-universe rule unchanged; no DB writes) + 2 registry regressions in `tests/test_normalization_signals.py` (exact post-audit level families for all 8 audited indicators; reclassified indicators still raise) → **285 total**.

### Results

- pytest: **285 passed, 0 failed** (all offline; baseline 278).
- Live read-only smoke (Postgres, nothing written): CHE RULE_OF_LAW @2025-Q2 → level 87.3184, relative 93.75 (rank 8/8, universe 8/8), momentum −2.58971 — UNCHANGED after hardening; CHN RULE_OF_LAW @2025-Q2 → relative 6.25 (rank 1/8). `scripts/normalization_profile.py` run read-only for the audit statistics.
- No frontend change → no npm build.
- backtest_safe remains False everywhere; no new normalized scores published; no force aggregation/weights/phases; nothing persisted; no public API.

### Not done (deliberately)

- NO numeric thresholds invented for ANY audited indicator (credit-gap thresholds remain unresolved pending documented BIS early-warning evidence; DSR design questions remain open for the Sprint 5.10 design).
- No Gini curve, no GCF curve, no GDP-growth/CPI/ULC band, no DSR score, no productivity score, no non-WGI relative, no non-WGI momentum, no confidence, no force aggregation, no persistence, no public scoring API, no frontend score UI, no new data imports.
- The pre-audit Sprint 5.9 recommendation (TARGET_BAND/MONOTONIC parameter design) is now largely MOOT — those proposals were reclassified to CONTEXTUAL_DEFERRED by this audit.

### Next

- Sprint 5.10 — owner to choose. Recommended per DEC-018: DSR OWN_HISTORY level design + implementation (READY_FOR_IMPLEMENTATION_DESIGN). Alternatives: confidence-dimension design (WGI uncertainty import first) or data-side work (education Option C / IMF WEO / WID wealth shares).

## 2026-09-09 — Sprint 5.8: WGI relative scores (CROSS_SECTIONAL_RELATIVE, DEC-017)

### Goal

Owner-directed, timeboxed brief: implement the THIRD executable score dimension — `relative_score` for exactly the three WGI governance scores — as the country's relative position within the fixed, versioned `tracked_8` reference universe (USA, CHN, CHE, DEU, FRA, GBR, JPN, IND). LOCKED parameters: mid-rank plotting position `100 * (average_rank − 0.5) / n` (rank 1 = weakest, rank n = strongest; n=8 scores 6.25…93.75), ties = average rank (never broken by ISO code/row id/query order), higher WGI = stronger (no inversion), universe membership FROZEN in a typed spec (never derived from DB contents; a changed universe = new id + new model version), complete-universe rule (all 8 usable or NOBODY is scored; missing members never become zero), every member aligned at the SAME scoring snapshot via `align_observation_as_of` (DEC-015 period-complete, latest vintage, ISSUE-004 country isolation inherited), freshness gates usability only (NEVER scales relative_score), participating values validated 0..100 (out-of-range raises). NOT a global/world percentile, NOT a level, NOT a phase. NO non-WGI relative, NO expanded_global, NO confidence, NO aggregation/persistence/API/frontend.

### Completed

- **normalization_definitions.py**: `ReferenceUniverseSpec` frozen dataclass (id + unique non-empty members) with `TRACKED_8_UNIVERSE` (id `tracked_8`) + `REFERENCE_UNIVERSES` registry; `NormalizedSignal` gains `reference_universe_expected_n` / `reference_universe_usable_n` / `relative_rank` (validated: expected positive, usable in 0..expected, relative_rank requires relative_score, relative_score requires reference_universe_id); exceptions moved in as the canonical home (`NormalizationNotImplementedError`, `NormalizationDataError` — re-exported from normalizer.py); `CURRENT_MODEL_VERSION` → **`normalization-v0.4`** / `sprint-5.8-wgi-tracked8-relative-r1` (momentum config unchanged; adds `reference_universe_id="tracked_8"`).
- **relative.py** (new): `mid_rank_relative_scores` — pure, ascending by value, tie runs share the average rank, `100 * (average_rank − 0.5) / n`; `RelativeMember` / `RelativeCrossSection` provenance types; `build_relative_cross_section` — per member `align_observation_as_of` at the same snapshot, freshness-unusable members skipped, out-of-range raises `NormalizationDataError`, usable_n < expected_n → incomplete cross-section with NO members (nobody scored).
- **normalizer.py**: relative block after momentum — gate = relative CROSS_SECTIONAL_RELATIVE AND level DIRECT_0_100 (exactly the WGI ×3; GDP_GROWTH/GCF/Gini/labour-productivity CROSS_SECTIONAL_RELATIVE registry entries still raise NormalizationNotImplementedError); complete-universe rule enforced; universe id/expected/usable/rank provenance carried; relative independent from momentum; confidence stays None.
- **Smoke** (`scripts/normalize_smoke.py`, extended, read-only): Relative score / Reference universe / Relative rank X/8 / Universe usable N/8 with the "NOT a global/world percentile" caption; incomplete-universe branch prints not-available with provenance.
- **Tests**: `tests/test_relative_scores.py` (new, 35 tests — fixed membership cross-checked against the packages/shared canonical tracked-country constant; universe never derived from DB; full n=8 score table; ties pure + DB; order independence; same-snapshot + leakage + period-complete + latest-vintage + isolation; 8/8 vs 7/8; freshness gating; out-of-range raises; level/momentum unchanged; relative-without-momentum; confidence; provenance; non-WGI stays unimplemented; backtest_safe; no DB writes) + `tests/test_normalization_signals.py` updates (incomplete-universe provenance; v0.4 config shape) → **278 total**.
- **Docs**: DEC-017 in DECISIONS.md; NORMALIZATION.md Sprint 5.8 status section + §14/§16 updated ("RESOLVED FOR THE WGI ×3 ONLY"); HANDOFF/PROJECT_STATUS/BACKLOG updated.

### Results

- pytest: **278 passed, 0 failed** (243 prior + 35 new; all offline)
- Live read-only smoke (Postgres, model version normalization-v0.4): CHE RULE_OF_LAW @2025-Q2 → level 87.3184, relative **93.75** (rank 8/8, universe 8/8), momentum −2.58971 unchanged; CHN RULE_OF_LAW @2025-Q2 → relative **6.25** (rank 1/8); USA CONTROL_OF_CORRUPTION @2025-Q2 → relative **31.25** (rank 3/8). Nothing hardcoded, nothing written.
- No frontend change → no npm build; no API route, model, migration, mapping, seed, or raw-data changes

### Not done

- Relative scores for the other 16 indicators — the rank/mid-rank method is approved for the WGI ×3 ONLY (robust-statistics choice does not auto-approve other indicators); no min-max/z-score/winsorization anywhere
- `expanded_global` universe, confidence (stays None), WGI uncertainty imports — all out of scope
- Release-date discipline — still Milestone 9; every signal keeps `backtest_safe = False`
- Tracked_8 relative position is NOT approved for direct cross-indicator aggregation

### Next

Sprint 5.9 — owner to choose: TARGET_BAND/MONOTONIC parameter-design sprint (recommended — needs owner-approved curve thresholds, §17.2–17.4, unlocks the largest block of the remaining 16 indicators) vs confidence-dimension design (WGI uncertainty series documented but not imported) vs data-side work (education Option C/DEC-007, IMF WEO/DEC-008, WID wealth shares).

## 2026-09-09 — Sprint 5.7: WGI momentum (OWN_HISTORY, DEC-016)

### Goal

Owner-directed, timeboxed brief (DEC-014): implement the SECOND executable score dimension — momentum for exactly the three WGI governance scores — on top of the Part 0 period-complete alignment. LOCKED parameters: signed change in the provider's own 0–100 points (`current_aligned_raw − anchor_aligned_raw`), higher WGI = positive, windows (3, 5) both computed with the 5y as PRIMARY headline (no averaging, no silent fallback), anchor tolerance = 1 annual period (versioned model parameter), freshness gates the CURRENT observation only (anchors never decayed, momentum never scaled), missing history → None never 0. NO relative scores, no other-indicator momentum, no aggregation/persistence/API/frontend.

### Completed

- **alignment_service.py**: `shift_scoring_period_years(scoring_period, years)` — pure scoring-clock arithmetic, quarter preserved (2025-Q2 − 5y → 2020-Q2), negative years rejected. No new query logic — the anchor is a plain `align_observation_as_of` call at the shifted period, so country isolation (ISSUE-004), latest-vintage, DEC-015 period-complete eligibility, and no-future-leakage are all inherited.
- **normalization_definitions.py**: `MomentumWindowResult` frozen dataclass (window_years, requested_anchor_period, anchor_source_period, change) with validation; `NormalizedSignal` + `momentum_window_years` / `momentum_windows`; `ModelVersionConfig` + `momentum_primary_window_years` / `momentum_anchor_tolerance_periods` (consistency validated: primary ∈ windows); `CURRENT_MODEL_VERSION` → **`normalization-v0.3`** / `sprint-5.7-wgi-momentum-r1` (windows (3,5), primary 5, tolerance 1 for exactly the WGI ×3; backtest_safe stays False).
- **normalizer.py**: momentum gate = level DIRECT_0_100 AND momentum OWN_HISTORY (resolves to exactly the WGI ×3; other indicators' registry OWN_HISTORY does NOT approve momentum; non-gate raises NormalizationNotImplementedError); `_momentum_window_result` — anchor aligned at the shifted period, tolerance measured as source-years older than the requested anchor year (1 covers the WGI 1997/1999/2001 biennial gaps; beyond tolerance → change None, never zero, never stretched), out-of-range anchor raises, change computed from ALIGNED RAW values (never level_score). Headline = primary 5y change ONLY; both windows always carried as provenance.
- **Tests** (`tests/test_normalization_signals.py`, +18 → 243 total): shift semantics; v0.3 config shape + validation; exact signed change with provenance (7.32 over 2019→2024); rising positive / falling negative; zero change is a real zero; primary-None with 3y still visible; 1-year gap accepted by tolerance; beyond-tolerance rejected; period-complete anchor semantics inherited; latest-vintage/country-isolated/no-future anchors; anchor never freshness-decayed; out-of-range raises; aligned-raw basis.
- **Smoke** (`scripts/normalize_smoke.py`, extended, read-only): live Postgres — CHE RL @2025-Q2 → level 87.3184, momentum −2.58971 (5y, requested anchor 2020-Q2 → actual 2019; 3y −0.443138, anchor 2021); CHE RL @2001-Q2 → level 91.4538 with momentum None (no alignable 5y anchor; 3y anchor 1996 is 2 years older → rejected — no fallback, no zero); CHN CC @2025-Q2 → +2.79934; DEU PS @2025-Q2 → −10.2986; USA CC @2025-Q2 → −1.72217. Negative, positive, and early-period cases all verified with live DB values, nothing hardcoded.
- **Docs**: DEC-016 in DECISIONS.md; NORMALIZATION.md Sprint 5.7 status section + §9 resolved-for-WGI bullet + §17 item 5 resolved for the WGI ×3 only; HANDOFF/PROJECT_STATUS/BACKLOG updated.

### Results

- pytest: **243 passed, 0 failed** (225 prior + 18 new; all offline)
- Live read-only smoke: all required cases verified (see above); nothing written
- No frontend change → no npm build; no API route, model, migration, mapping, seed, or raw-data changes

### Not done

- Momentum for the other 15 indicators — needs per-indicator sign conventions (§17 item 5 open for them)
- WGI momentum is scale-specific — NOT approved for direct cross-indicator aggregation; a separate momentum-calibration methodology would be required first
- Relative scores, confidence, force aggregation, weights, phases — unchanged (None/absent)
- Release-date discipline — still Milestone 9; every signal keeps `backtest_safe = False`

### Next

Sprint 5.8 — owner to choose: relative scores (CROSS_SECTIONAL_RELATIVE for the WGI ×3 on tracked_8, recommended — no new data needed) vs the TARGET_BAND/MONOTONIC parameter-design sprint (§17.2–17.4) vs data-side work (education Option C, IMF WEO, WID).

## 2026-09-09 — Part 0: Period-complete alignment hardening (before Sprint 5.7 momentum)

### Goal

Owner-directed hardening before any momentum work: Sprint 5.6 eligibility (`period_start <= as_of_date`) admitted period-INCOMPLETE observations — an annual 2020 observation was eligible at the 2020-Q2 snapshot (as-of 2020-06-30) even though the 2020 period had not ended. Fix: deterministic `effective_period_end` in the DERIVED layer (annual/irregular → YYYY-12-31; quarterly → quarter end), eligibility = `effective_period_end <= scoring_period_end`. No raw observation changes; no synthetic period-end dates persisted; backtest_safe stays False (this is period-completeness only — NOT release-date safety, Milestone 9 owns that). Owner decisions recorded the same day: DEC-013 (decay shape = exponential, confirmed) and DEC-014 (Sprint 5.7 = WGI momentum).

### Completed

- **alignment_service.py**: new `effective_period_end(period_start, freshness_class)` helper + `_period_complete_condition` — an index-based SQL eligibility expression (0-based quarter indices on the scoring clock) applied to BOTH the latest-vintage subquery and the outer query, rendering identically on SQLite (tests) and PostgreSQL (live). `period_start <= as_of` kept as a cheap necessary precondition. `AlignedValue` now carries `effective_period_end` provenance.
- **normalization_definitions.py**: `AlignedValue` gains the required `effective_period_end: date` field; alignment semantics changed → `CURRENT_MODEL_VERSION` bumped `normalization-v0.1` → **`normalization-v0.2`** (method `part0-period-complete-alignment-r1`) — a semantic change gets a new version, never a silent edit.
- **Tests** (`tests/test_normalization_signals.py`, +5): annual 2020 not eligible at 2020-Q1/Q2/Q3 (align + normalize → None, never zero); annual 2020 eligible at 2020-Q4 with `effective_period_end` 2020-12-31; incomplete-year fallback (2024 obs at 2024-Q2 → aligns 2023, never 2024); quarterly Q2 not eligible at Q1 / eligible at Q2 with quarter-end provenance; alignment never mutates raw `period_start` and adds no rows. The former "no future leakage" test's expectation (2023 annual at 2023-Q2) was INVERTED — it had asserted the exact leak Part 0 fixes.
- **Docs**: NORMALIZATION.md Part 0 status section + §3 rewritten (eligibility rule, effective_period_end provenance, period-completeness ≠ release-date safety; the 5.6 status block marked superseded); DEC-013/014/015 in DECISIONS.md; HANDOFF/PROJECT_STATUS/BACKLOG updated.

### Results

- pytest: **225 passed, 0 failed** (220 prior + 5 new; all offline)
- Live read-only smoke: CHE RULE_OF_LAW_WGI_SCORE @2024-Q2 → **2023** (87.8079 — was the incomplete-year 2024 value: the leak), @2024-Q4 → 2024 (87.3184, freshness 1.0000, first eligible quarter), @2025-Q2 → 2024 unchanged (87.3184, freshness 0.9170); one-off read-only check confirmed CREDIT_TO_GDP_GAP quarterly alignment on live Postgres (2025-Q1/Q2/Q3 → own quarter, script deleted after use)
- No frontend change → no npm build; no API route, model, migration, mapping, seed, or raw-data changes

### Not done

- Momentum (Sprint 5.7, DEC-014) — the delivered brief now builds on this hardened path; model version will bump again when it lands
- Relative scores, confidence, force aggregation — unchanged (None/absent)
- Release-date discipline — still Milestone 9; every signal keeps `backtest_safe = False`

## 2026-09-09 — Sprint 5.6: First executable normalization path (as-of alignment + freshness + DIRECT_0_100)

### Goal

Implement the FIRST actual normalization computation path for the lowest-risk family only — DIRECT_0_100 for the three WGI governance scores — plus the reusable quarterly as-of alignment and frequency-aware freshness that later families will reuse. No force aggregation, no weights, no Big Cycle phase, no relative scores, no momentum, no other families, no persistence, no public API.

### Completed

- **As-of alignment** (`apps/api/app/services/alignment_service.py`): `parse_scoring_period` ("YYYY-Qn"), `quarter_end_date` (2025-Q1→03-31 … Q4→12-31; eligibility = `observation.period_start <= as_of_date`), and `align_observation_as_of` → the Sprint 5.5 `AlignedValue` (latest-vintage, latest-prior selection; `age_periods` in scoring-clock quarters; source_period labeled by freshness class). CURRENT/RESEARCH alignment by observation period — every result `backtest_safe = False` until Milestone 9. Country+indicator scoping at every query layer (ISSUE-004). Alignment SELECTS the latest prior observation; it never writes, forward-fills, or interpolates — raw observations stay sparse (verified: no synthetic rows).
- **Freshness machinery** (`apps/api/app/cycle/freshness.py`): `FreshnessPolicy` / `FreshnessResult` / `evaluate_freshness` using the Sprint 5.5 §5 MODEL PARAMETERS (no new values invented). Decay shape parameterized (exponential/linear); initial executable default = exponential (the only shape that honors the half-life definition for arbitrary thresholds) — documented as an initial model choice, §17.1 stays open, changing it is a model-version change. factor ∈ [0,1]; beyond the unusable threshold → `is_usable = False` → NO signal (never produced-with-zero). Threshold ordering validated (full < half-life < unusable).
- **Normalizer dispatch** (`apps/api/app/cycle/normalizer.py`): `normalize_indicator_as_of(session, country_iso3, indicator_code, scoring_period, model_config, freshness_policy)` reads the registry level family and implements **DIRECT_0_100 only**; every other family raises `NormalizationNotImplementedError` (no generic fallback); out-of-range provider values (−1, 101) raise `NormalizationDataError` — never clamped; a model config claiming `backtest_safe=True` is rejected (Milestone 9 owns release-date discipline). `level_score = raw_value` (no z-score/rank/percentile/rescale/invert/winsorize) — an INDICATOR-level signal, not a force score. `relative_score`/`momentum`/`confidence`/`reference_universe_id` stay None; `freshness_factor`/`is_stale` are carried as provenance (factor ≠ confidence).
- **Model version**: `CURRENT_MODEL_VERSION` → `normalization-v0.1` / method `sprint-5.6-direct-0-100-r1` (not production-validated); exposed on every signal; no DB persistence, no migration.
- **Smoke script** (`scripts/normalize_smoke.py`, read-only): verified live — CHE RULE_OF_LAW_WGI_SCORE @2025-Q2 → source 2024, 87.3184, freshness 0.9170 (stale); USA CONTROL_OF_CORRUPTION_WGI_SCORE @2024-Q4 → 69.8552, freshness 1.0000; 1990-Q1 → clean no-signal exit; GDP_GROWTH/GINI_INDEX → clear not-implemented errors.
- **Docs**: NORMALIZATION.md gained a "Sprint 5.6 implementation status" section (exactly which family is executable, which are design-only) + a §17.1 execution note; no spec rewrite.

### Results

- pytest: **220 passed, 0 failed** (193 prior + 27 new in `tests/test_normalization_signals.py`; all offline — seeded SQLite + synthetic DTOs through the real persistence layer, no external calls)
- Smoke script verified against the live DB (SELECT queries only — nothing written)
- No frontend change → no npm build run; no API route, model, migration, mapping, seed, or raw-data changes

### Not done

- All other 8 families (16 non-WGI indicators) — raise `NormalizationNotImplementedError` by design
- relative scores (reference-universe percentile machinery not model-versioned yet), momentum, confidence composition, force aggregation/weights, Big Cycle phase — all still None/absent
- Freshness decay shape remains a §17 open question (exponential is the executable initial default, not a final decision)
- No normalized_signals persistence and no public HTTP endpoint — computed deterministically on demand until multiple families are stable

### Next

Sprint 5.7 (recommended): extend the proven path — WGI momentum (OWN_HISTORY 3y/5y; §17.5 sign conventions) and/or relative scores (tracked_8 + robust statistics), or a TARGET_BAND/MONOTONIC parameter-design sprint (needs owner-approved thresholds, §17.2–17.4) to unblock the remaining 16 indicators.

## 2026-09-09 — Sprint 5.5: Normalization methodology & architecture (design only)

### Goal

Design the normalization/scoring architecture for the 17-force engine — score semantics, quarterly clock, as-of alignment, freshness policy, normalization families, and a per-indicator registry for all 19 live series — without publishing any scores, weights, momentum values, or confidence numbers. No data, no frontend, no provider additions.

### Completed

- **`.dev/NORMALIZATION.md` created** (methodology source of truth): (1) four separable dimensions — level_score 0–100 / relative_score 0–100-or-null / momentum −100…+100 (from time change only) / confidence 0–1; (2) quarterly scoring clock YYYY-Qn with annual/irregular indicators aligned as-of; (3) as-of alignment retaining source period, age, vintage (no forward-fill, no interpolation); (4) explicit not-backtest-safe limitation (release dates unpopulated → CURRENT/RESEARCH scoring only until Milestone 9; `backtest_safe = False` on every signal); (5) frequency-aware freshness thresholds (quarterly/annual/irregular) labeled as versioned MODEL PARAMETERS, not provider truth; (6) nine normalization families; (7) all 19 live indicators classified per dimension (level/relative/momentum); (8) absolute-vs-relative designed independently per indicator; (9) momentum windows per frequency type; (10) confidence as composition of source/freshness/coverage/measurement/proxy factors (no fake precision); (11) MISSING ≠ ZERO rules; (12) DEC-009 ceilings act at the force layer only — provisional proxy scores with reduced confidence, never clamped indicator values; (13) ModelVersionConfig bundling method/parameters/universe/calibration/momentum/freshness/mapping-version; plus reference universe (`tracked_8`, never world truth), calibration-vs-as-of windows (no future leakage), robust-statistics preference, force-score eligibility, and 11 deliberately unresolved questions.
- **Typed skeleton** `apps/api/app/cycle/normalization_definitions.py`: NormalizationFamily enum, NormalizationSpec / AlignedValue / NormalizedSignal / ScoringPeriod / FreshnessThresholds / ModelVersionConfig dataclasses, score-range constants + trivial validation helpers, NORMALIZATION_REGISTRY covering all 19 live indicators, and import-time validation that fails loudly (duplicate codes, live force input without a spec, non-live indicator in the registry, deliberately-unassigned indicators accidentally promoted). Score fields are Optional/None; `NormalizedSignal.unscored()` encodes MISSING ≠ ZERO in the type system. Not connected to the API.
- **Key semantic classifications:** WGI ×3 = DIRECT_0_100 (provider absolute scale preserved, never percentile-ranked); DEBT_SERVICE_RATIO = OWN_HISTORY level (BIS caution; never cross-sectionally ranked, relative family explicitly None); CREDIT_TO_GDP_GAP = asymmetric TARGET_BAND; GINI_INDEX = MONOTONIC_NEGATIVE (irregular freshness class); LABOUR_PRODUCTIVITY_PER_HOUR = MONOTONIC_POSITIVE level + OWN_HISTORY momentum (level and growth stay separable); GROSS_CAPITAL_FORMATION_GDP = MONOTONIC_SATURATING; GDP_GROWTH / INFLATION_CPI / UNIT_LABOUR_COST_GROWTH = TARGET_BAND (thresholds unresolved); military ×2, trade ×4, GDP scale ×2 = CONTEXTUAL_DEFERRED (no invented curves; trade and military are multi-indicator contextual forces).
- **DEC-012 appended** (permanent methodology decisions only: dimension separation, quarterly clock, no zero-fill, explicit families, versioned calibration/universe, not backtest-safe).

### Results

- pytest: **193 passed, 0 failed** (174 prior + 19 new in `tests/test_normalization.py`; all offline — no DB, no external calls)
- No frontend change → no npm build run (per sprint instructions)
- No raw data, ingestion, API route, or migration changes

### Not done

- Actual normalizer computation, force scores, weights, momentum/confidence values — all deferred to the scoring sprint (Sprint 5.6+)
- Freshness decay shapes, TARGET_BAND thresholds, confidence composition, productivity levels-vs-growth fairness — documented as unresolved in NORMALIZATION.md §17
- `model_versions` DB table — configuration-first; deferred until a persisted scoring layer genuinely needs it

### Next

Sprint 5.6 (recommended): implement the scoring layer for the uncontroversial families first — WGI DIRECT_0_100 level signals + as-of alignment + freshness policy (real implementation of the designed architecture), leaving TARGET_BAND/CONTEXTUAL curves for parameter-design sprints.

## 2026-09-08 — Milestone 5.4: Military expenditure proxy (SIPRI via WDI) + normalization-readiness audit

### Goal

Add a defensible initial Military strength proxy using the SIPRI-derived military-expenditure series republished through the World Bank WDI API (MS.MIL.XPND.CD / MS.MIL.XPND.GD.ZS) — no direct SIPRI adapter, no SIPRI workbook — and complete the normalization-readiness audit so Sprint 5.5 (normalization design) is easier and safer. Final data-expansion sprint before normalization. No scoring, no education, no IMF debt, no WID, no ACLED.

### Completed

- **Verification (official WB API, never trusting the prompt):** both codes exist in current WDI (source 2) — MS.MIL.XPND.CD "Military expenditure (current USD)" and MS.MIL.XPND.GD.ZS "Military expenditure (% of GDP)"; sourceOrganization for both is "SIPRI Military Expenditure Database, Stockholm International Peace Research Institute (SIPRI)" (https://www.sipri.org/databases). Annual series. Licensing: WB open data defaults to CC-BY 4.0 (https://datacatalog.worldbank.org/public-licenses); attribution documented in DATA_SOURCES.md (documentation, not legal advice). Direct SIPRI workbook NOT downloaded or rehosted; no `app/data_sources/sipri.py` created — the existing WorldBankAdapter pipeline is used (source_key `world_bank`).
- **Mappings + catalog:** MILITARY_EXPENDITURE_USD → MS.MIL.XPND.CD and MILITARY_EXPENDITURE_GDP → MS.MIL.XPND.GD.ZS; both catalog entries category Military, frequency annual, strength_direction **contextual** (more spending ≠ more capability), descriptions name SIPRI as the underlying source. WB mappings 13→15; seed idempotent: catalog 23→25, SourceSeries 17→19.
- **Import (16/16 success):** both indicators × 8 countries, request range 1990–2025; every country has complete 35-year histories, 1990–2024 (provider publishes through 2024), 560 observations inserted, IngestionRuns #241–#256, all vintage 1. Idempotent CHE re-runs: 0 inserted / 35 skipped / 0 revised for both indicators (runs #257–#258); 0 duplicate identity groups. DB total: 5647 observations.
- **Force promotion (DEC-011, via the existing DEC-009 ceiling):** Military strength live inputs = MILITARY_EXPENDITURE_USD + MILITARY_EXPENDITURE_GDP with `coverage_ceiling = partial` — SIPRI describes military expenditure as an INPUT measure (resources absorbed by the military), not capability; personnel, equipment, technology, logistics, readiness, combat experience, alliances, nuclear capability are unmeasured. Military strength: MISSING → PARTIAL for countries with data, and can never report AVAILABLE from spending alone. No spending normalization done (raw observations only).
- **Live coverage verified:** OECD-6 (USA/CHE/DEU/FRA/GBR/JPN) 7 available / 3 partial (wealth gaps, internal conflict, military strength — all ceiling) / 1 defined_not_sourced / 6 missing; CHN/IND 5 available / 5 partial (productivity, cost competitiveness, wealth gaps, internal conflict, military strength) / 1 defined_not_sourced / 6 missing. Matches the sprint's expected matrix exactly; output comes from the coverage service, nothing hardcoded.
- **UI:** compact Military section on /country/[iso3] — latest military expenditure in compact current US$ ($997.31B etc.) and % of GDP, year, "Source: World Bank · Underlying source: SIPRI", caption "Military expenditure is an input proxy for military strength; spending alone does not measure military capability." No history table, no ranking, no score. The generic /forces page shows Military strength "Partially measurable" with both inputs from the coverage service (no redesign needed).
- **Normalization-readiness audit:** new "Normalization Readiness" section in .dev/FORCE_COVERAGE.md — per-indicator matrix (direction, frequency, source, cross-country/time-series comparability, likely transformation, freshness caveat, ceiling impact) for all 19 live series, plus 7 key findings for 5.5 (frequency mixing, nominal-USD confound, irregular Gini, contextual-direction banding, perception uncertainty, ceiling-capped forces, legitimate coverage gaps). Audit only — no formulas designed.

### Results

- pytest: **174 passed, 0 failed** (163 prior + 11 new military tests in `tests/test_military.py`; baseline count assertions updated 13→15 WB mappings / 17→19 series / 23→25 catalog in 6 test files; all offline)
- `npm run build -w apps/web`: SUCCESS (2026-09-08, no dev server running)
- Playwright: 16/16 real checks passed (/country/CHE, /country/USA, /country/CHE/forces, /country/CHN/forces — Military section, SIPRI attribution, military PARTIAL, 7/3/1/6 + 5/5/1/6 summaries, no force scores)
- Live DB: 5647 observations (WB 2953 + BIS 1664 + OECD 1030), 25 indicators, 19 SourceSeries, 0 duplicate identity groups

### Not done

- Military capability data (personnel/equipment/readiness) — the only thing that could lift the Military-strength ceiling; more spending series will not
- Education (DEC-007), general-government debt (DEC-008), WID/opportunity indicators, ACLED — unchanged
- Normalization itself — deliberately deferred to Sprint 5.5

### Next

Sprint 5.5: normalization design for the force-scoring engine, using the Normalization Readiness audit as input. Alternative owner choices remain education Option C / IMF WEO debt / WID.

## 2026-09-08 — Milestone 5.3: Inequality (Gini) + CPI + coverage-semantics hardening

### Goal
Clear the stale live force-coverage route, add a minimal concept-completeness (coverage ceiling) mechanism, verify + import WB Gini (SI.POV.GINI) and WB CPI (FP.CPI.TOTL.ZG) for all 8 countries, promote them to the wealth-gap and cost-competitiveness forces defensibly, add a compact Inequality UI section, and fix stale status notes (post-5.2 npm build was SUCCESS; stale-backend blocker removed). No scoring, no education, no IMF debt, no SIPRI.

### Completed
- **Part 0 — live route verified:** the 404 was NOT a code bug: an orphaned pre-M5.0 uvicorn reload worker (spawn child of the killed reloader parent) survived and kept serving :8000 through the shared duplicated socket. Owner approved the kill; backend restarted; live `/openapi.json` contains `/api/countries/{iso3}/force-coverage` and CHE returns 17 forces. Documented as a Windows uvicorn hazard (Stop-Process on the reloader parent does not kill the spawn worker) in HANDOFF known issues.
- **Coverage ceiling (DEC-009, minimal + backwards-compatible):** `ForceDefinition.coverage_ceiling: ForceCoverageStatus | None = None` + 3-line cap in `_force_status` — a force whose mapped live inputs are an explicitly incomplete proxy reports PARTIAL even with complete data. Default None (behavior unchanged for all other forces). Applied to wealth_opportunity_values_gaps (Gini = income inequality only) and internal_conflict (WGI proxy). Internal conflict AVAILABLE → PARTIAL is a documented methodology correction, not a regression. Rule of law, corruption, productivity, indebtedness deliberately NOT capped. API schema unchanged.
- **Gini verification (official WB API, never trusting the prompt):** SI.POV.GINI "Gini index", WDI source 2, 0–100 (0 = perfect equality, 100 = perfect inequality), published irregularly. Missing years are gaps — never zeros, never forward-filled. Coverage matrix: all 8 countries YES; latest year varies 2020–2024 by country.
- **Gini mapping + catalog:** GINI_INDEX → SI.POV.GINI (raw values stored exactly as published; no 0–1 rescale); seed adds the canonical entry (category Inequality, unit "index (0-100)", frequency "irregular", strength negative). Seed idempotent: catalog 22→23, SourceSeries 15→17.
- **Gini import:** 8/8 series SUCCESS, 187 observations inserted (IngestionRuns #223–230), all vintage 1, irregular years preserved. Idempotent CHE re-run: 0 inserted / 21 skipped / 0 revised. Duplicate identity groups: **0**.
- **CPI verification + semantics:** FP.CPI.TOTL.ZG "Inflation, consumer prices (annual %)", WDI, annual — concept matches the existing canonical INFLATION_CPI cleanly (name/unit/strength kept). Frequency metadata corrected monthly → annual and documented (DEC-010, not a silent rename); `/api/indicators?frequency=monthly` now returns only UNEMPLOYMENT_RATE. No new canonical indicator created.
- **CPI import:** 8/8 series SUCCESS, 287 observations inserted (runs #231–238). Idempotent CHE re-run: 0 inserted / 36 skipped / 0 revised. Duplicate identity groups: **0**.
- **Force promotion:** wealth_opportunity_values_gaps live = GINI_INDEX with `coverage_ceiling=partial` (never AVAILABLE; coverage note names the missing wealth/opportunity/values concepts and future inputs: WID wealth/income shares, unemployment/opportunity measures, social polarization). cost_competitiveness live = UNIT_LABOUR_COST_GROWTH + INFLATION_CPI — OECD-6 AVAILABLE (ULC + CPI), CHN/IND PARTIAL (CPI only; never AVAILABLE from CPI alone — CPI is domestic price pressure, relative competitiveness needs exchange rates + partner-country comparisons).
- **Live coverage after M5.3:** CHE/USA/DEU/FRA/GBR/JPN → 7 available, 2 partial (wealth gaps + internal conflict, both by ceiling), 1 defined_not_sourced (Education), 7 missing. CHN/IND → 5 available, 4 partial (productivity, cost competitiveness CPI-only, wealth gaps, internal conflict), 1 dns, 7 missing. Matches the sprint's expected outcome exactly; nothing hardcoded.
- **UI:** compact Inequality section on `/country/[iso3]` — latest Gini (value, "Latest available: {year}" staleness label since Gini is irregular, Source: World Bank, income-inequality-only caption). /forces pages needed no changes (already generic). No histories, no freshness score, no "current" labeling of stale data.
- **Docs:** DECISIONS.md +DEC-009 +DEC-010; FORCE_COVERAGE.md (ceiling section, per-force rows 9/14/15, per-country table, post-5.3 priorities); DATA_SOURCES.md (13 WB mappings, Gini coverage matrix + CPI semantics bullets, CLI, verification paragraph); HANDOFF / PROJECT_STATUS / BACKLOG updated — stale status fixed: the post-5.2 `npm run build` was SUCCESS (run with dev stopped), stale-backend blocker removed.

### Results
- pytest: **163 passed, 0 failed** (149 prior + 14 new in tests/test_gini_cpi.py; baselines updated in 7 existing test files). All offline; `uv run --no-sync pytest`.
- `npm run build -w apps/web`: SUCCESS (with `next dev` stopped), then dev restarted.
- Playwright verification: 23 checks on /country/CHE, /country/CHE/forces, /country/CHN/forces — all real checks passed (the one "FAIL" was a false negative in my own check: the page's legitimate "no force scores are calculated yet" disclaimer matched my no-score-text grep).
- Live DB: 5087 observations (WB 2393 + BIS 1664 + OECD 1030), 23 indicators, 17 SourceSeries, 0 duplicate identity groups.

### Not done / blockers
- Wealth inequality / opportunity / values indicators and ACLED event data (would lift the two PARTIAL ceilings) — future sprints, per FORCE_COVERAGE priorities.
- Education (DEC-007) and general-government debt (DEC-008) still not persisted — owner decisions already recorded, awaiting their sprints.
- Both dev processes currently run as session background tasks — if the session ends, restart them in your own terminals (commands in HANDOFF).

### Next
- Owner choice: education Option C indicators, general-government debt source (IMF WEO), wealth-share/opportunity indicators (WID — lifts the wealth-gap ceiling), or Milestone 5 force-scoring design (7 of 17 forces fully measurable for OECD-6, 4 more partial).

## 2026-09-08 — Milestone 5.2: Runtime route diagnosis + WGI governance expansion

### Goal
Fix the live force-coverage route registration discrepancy, verify the current 2025-revision WGI metadata (not the legacy RL.EST/CC.EST/PV.EST codes), add 3 approved WGI governance indicators via the existing WB connector, import for all 8 countries (~1996–2024), promote Rule of law / Corruption / Internal conflict, surface governance in the UI, and record the education (Option C) + government-debt (keep general-government) owner decisions. No education, no government debt, no new provider, no scoring.

### Completed
- **Route diagnosis (Part 0):** NO code bug. Fresh import of `app.main` registers and serves `/api/countries/{iso3}/force-coverage` correctly — in-process openapi.json contains it and TestClient dispatch reaches the handler (unknown country returns the handler's 404 detail, not a route miss). The live :8000 process (PID 55064) predates Milestone 5.0: its live openapi.json matches the pre-M5.0 route set exactly. Side finding: FastAPI 0.141.1 registers included routers as lazy `_IncludedRouter` wrappers, so `[r.path for r in app.routes]` hides them — inspect `/openapi.json` instead. Fix is an owner restart (commands in HANDOFF); no double-include, no manual route registration, no frontend workaround.
- **WGI verification (official WB API only):** current WDI carries `GOV_WGI_{RL,CC,GE,PV,RQ,VA}_{EST,SC}`; legacy RL.EST/CC.EST/PV.EST no longer exist. The `_SC` series are the 2025-revision absolute governance scores (0–100, larger = better governance; linear transformation of the estimate using hypothetical worst/base-case countries — confirmed in official metadata: "Worldwide Governance Indicators, 2025 Revision"). Chosen per DEC-006: GOV_WGI_RL_SC, GOV_WGI_CC_SC, GOV_WGI_PV_SC. Coverage matrix (verified live, 1996–2024): all 8 countries YES for all 3 series, 26 observations each (1997/1999/2001 absent — WGI biennial years); latest year 2024.
- **Uncertainty (Part 3):** the dedicated WGI source (WB source id 3) publishes, per dimension: standard error (GOV_WGI_RL.SE), 90% CI bounds for the governance score (GOV_WGI_RL.SC_LB / SC_UB), and number of underlying sources (GOV_WGI_RL.SR). Documented in DATA_SOURCES.md + FORCE_COVERAGE.md for future force-confidence work; NOT imported (no large uncertainty schema this sprint). WGI never treated as perfectly measured.
- **Mappings + catalog:** +3 mappings in `world_bank_mappings.py` (11 WB total; transform notes record the 2025-revision 0–100 scale, the control-of-corruption direction semantics, and the source-indicator-not-force-score caveat); +3 canonical indicators in `seed.py` (RULE_OF_LAW_WGI_SCORE / CONTROL_OF_CORRUPTION_WGI_SCORE / POLITICAL_STABILITY_WGI_SCORE; Governance category, score 0-100, annual, positive; PV description names "Political Stability and Absence of Violence/Terrorism"). Seed idempotent: catalog 19→22, SourceSeries 12→15.
- **Import (existing pipeline, one `--indicator` run × `--all-countries` per WGI series, 1996–2025 request range):** 24/24 series SUCCESS, 624 observations inserted (26 × 8 countries × 3), all vintage 1. Idempotency re-run CHE × 3: 0 inserted / 26 skipped / 0 revised each. Duplicate identity groups: **0**. IngestionRuns now 200 success / 16 failed (all 27 new runs success).
- **Force promotion (config only):** rule_of_law → RULE_OF_LAW_WGI_SCORE; corruption → CONTROL_OF_CORRUPTION_WGI_SCORE (coverage note: source is Control of Corruption, HIGHER = stronger control / less corruption, raw value never reversed); internal_conflict → POLITICAL_STABILITY_WGI_SCORE (note: initial institutional/conflict-risk proxy, does NOT measure every form of domestic conflict; later ACLED/event data may strengthen). No overclaiming anywhere.
- **Live coverage after promotion (service against Postgres, nothing hardcoded):** USA/CHE/DEU/FRA/GBR/JPN → 8 available (Productivity, Cost competitiveness, Rule of law, Corruption, Trade and capital flows, Infrastructure and investment, Indebtedness, Internal conflict), 1 defined_not_sourced (Education), 8 missing; CHN/IND → 6 available + Productivity partial (GDP growth only) + 2 defined_not_sourced (Cost competitiveness, Education) + 8 missing. Matches the sprint's expected outcome exactly.
- **UI:** compact Governance section on `/country/[iso3]` — latest Rule of Law / Control of Corruption / Political Stability (XX.XX / 100, year, Source: World Bank / WGI) with the caption "WGI scores are perception-based composite governance indicators and include measurement uncertainty"; no good/bad labels, no colors, no histories; renders only when governance data exists.
- **Docs:** DECISIONS.md — DEC-001 Impact corrected to npm (was pnpm); +DEC-006 (WGI 2025-revision score series), +DEC-007 (education Option C), +DEC-008 (government debt keeps general-government). HANDOFF / PROJECT_STATUS / BACKLOG / DATA_SOURCES / FORCE_COVERAGE all updated: stale-backend blocker reframed (restart fixes it, no code bug), WGI uncertainty recorded, education/debt decisions marked resolved, old RL.EST/CC.EST/PV.EST references replaced with the verified GOV_WGI_*_SC codes.

### Results
- pytest: 149 passed, 0 failed (137 prior + 12 new tests in tests/test_wgi_governance.py; baselines updated: WB mappings 8→11, SourceSeries 12→15, catalog 19→22, military_strength replaces rule_of_law as the missing-force exemplar in test_force_coverage.py).
- Live DB: 4613 observations (WB 1919 + BIS 1664 + OECD 1030), 22 indicators, 15 SourceSeries, 0 duplicate identity groups.

### Not done / blockers
- `npm run build` not re-run: `next dev` is serving (known issue — build must run with dev stopped). Owner commands in HANDOFF "Pending owner actions".
- Browser verification of the Governance section and /forces pages against the live backend: pending the owner restarting both the :8000 backend (stale, predates the force-coverage route) and `next dev` (corrupted `.next`). After restart: /country/CHE shows Governance (RL 87.32, CC 88.48, PV 82.65, 2024), /country/CHE/forces shows 8 Data available, /country/CHN/forces shows 6 + Productivity Partially measurable.
- Education and government debt deliberately not persisted (owner decisions DEC-007/DEC-008 — better indicators / genuine general-government source come later).

### Next
- Owner restarts both dev processes + build; then choose: WB Gini (wealth gaps), WB CPI (cost-competitiveness candidate), education Option C indicators, general-government debt source, or Milestone 5 force-scoring design (8 of 17 forces measurable for OECD-6).

## 2026-09-08 — Milestone 5.1: World Bank trade & investment expansion

### Goal
Verify and connect the existing World Bank trade/investment indicators, import them for all 8 countries (2000–2025), promote defensible force mappings (Trade and capital flows, Infrastructure and investment), and audit the education / government-debt candidates WITHOUT persisting them. No force scoring, no weights, no phases, no new provider.

### Completed
- Series verification (official WB API v2 metadata, all WDI): EXPORTS_GDP→NE.EXP.GNFS.ZS, IMPORTS_GDP→NE.IMP.GNFS.ZS, CURRENT_ACCOUNT_GDP→BN.CAB.XOKA.GD.ZS, GROSS_CAPITAL_FORMATION_GDP→NE.GDI.TOTL.ZS (all clean concept matches); TRADE_BALANCE→NE.RSB.GNFS.ZS "External balance on goods and services (% of GDP)" — mapped to the **published** series (Part 2 preference), NOT derived as exports − imports; scope (goods + services) is consistent with the mapped export/import series. No candidate was rejected — all 5 passed semantic verification.
- Coverage matrix (2000–2025, verified live before import): effectively all YES for all 8 countries × 5 series; only legitimate gaps are missing 2025 values (USA/JPN exports/imports/external balance/GCF; CHN GCF).
- `world_bank_mappings.py` +5 mappings (8 total; still the single source of identity — no codes in the CLI); seed idempotent → 12 SourceSeries (8 WB + 2 BIS + 2 OECD); no new canonical indicators (the 5 catalog rows already existed).
- Import via the existing batch CLI, one `--indicator` run per new series × `--all-countries`: 40/40 series SUCCESS, 1031 observations inserted (EXPORTS 206, IMPORTS 206, TRADE_BALANCE 206, CURRENT_ACCOUNT 208, GCF 205), all vintage 1.
- Idempotency re-run (full EXPORTS batch + CHE × 4): inserted 0, skipped all, revised 0. Duplicate identity groups in DB: **0**.
- Force promotion (config only, `force_definitions.py`): trade_capital_flows live = EXPORTS_GDP + IMPORTS_GDP + TRADE_BALANCE + CURRENT_ACCOUNT_GDP; infrastructure_investment live = GROSS_CAPITAL_FORMATION_GDP — promoted only after SourceSeries + observations + verified semantics all existed. Global openness deliberately NOT promoted: note updated to record that trade data is available as a future input candidate; a narrower trade-based proxy needs owner approval (no openness ratio derived).
- Live coverage after promotion (service against Postgres): USA/CHE/DEU/FRA/GBR/JPN → 5 available (Productivity, Cost competitiveness, Trade and capital flows, Infrastructure and investment, Indebtedness), 1 defined_not_sourced (Education), 11 missing; CHN/IND → 3 available (Trade, Infrastructure, Indebtedness) + Productivity partial + 2 defined_not_sourced + 11 missing. Nothing hardcoded — all computed.
- Education audit (NOT persisted): SE.TER.ENRR / SE.SEC.ENRR are **gross** enrollment ratios (can exceed 100%); canonical wording implies age-specific (25–34 / 15–19) rates → NOT Option A. Recommendation recorded: (B) redefine canonical as gross ratios (owner approval) or (C) better indicators (OECD attainment for tertiary; SE.SEC.NENR % net for secondary).
- Government-debt audit (NOT persisted): GC.DOD.TOTL.GD.ZS is **central** government debt, narrower than the canonical general-government concept → owner decision required (rename to CENTRAL_GOVERNMENT_DEBT_GDP / other source / documented proxy) before persistence.
- Optional UI (Part 11): compact Trade & Investment section on `/country/[iso3]` — latest exports/imports/trade balance/current account/GCF (% of GDP, year + source), renders only when trade data exists.
- Docs: Part 0 status cleanup done (npm build pending notes resolved — owner ran the build after 5.0).

### Results
- pytest: 137 passed, 0 failed (125 prior + 12 new tests in tests/test_world_bank_trade.py; baseline counts updated in test_world_bank_mappings.py 3→8 and test_oecd_persistence.py 7→12).
- Live DB: 3989 observations, 12 SourceSeries, IngestionRuns 173 success / 16 failed (all 52 runs added this sprint succeeded).

### Not done / blockers
- UI live-verification incomplete: `next dev`'s `.next` is corrupted (the post-5.0 build ran while dev was serving — known HANDOFF issue; every `/_next/static` chunk 404s and pages render unstyled/stuck). Owner: stop dev, restart it, then optionally `npm run build -w apps/web` while dev is stopped. The stale :8000 backend (predates force-coverage) also still needs an owner restart. Payloads for the /forces pages were generated from the live DB (P:/tmp/force-coverage-{che,chn}-m51.json) for re-verification after restart.

### Next
- Owner decisions: education (B vs C), government debt (rename / other source / proxy); then a small persistence sprint. After that: WB WGI (RL.EST / CC.EST / PV.EST → 3 forces) or Milestone 5 force-scoring design.

## 2026-09-08 — Milestone 5.0: 17-force coverage foundation (no scores)

### Goal
Answer "for each of the 17 Big Cycle forces, what data do we have, what is defined but not sourced, and what is missing" — formal definitions, defensible indicator→force mapping, per-country availability, API exposure, UI, and a prioritized data-gap plan. No scores, no weights, no phases, no new providers.

### Completed
- `app/cycle/force_definitions.py` (NEW): the 17 forces with wording preserved from docs/data-model.md + packages/shared `FORCES` (keys identical, same order). Typed config layer — no DB tables yet (Force/ForceIndicatorMapping deferred until the conceptual mapping is validated). `ForceCoverageStatus` enum: available / partial / defined_not_sourced / missing. No weights, no score formula, no normalization parameters.
- Indicator→force mapping (defensible only): Productivity / output growth live = GDP_GROWTH (WB) + LABOUR_PRODUCTIVITY_PER_HOUR (OECD); Cost competitiveness live = UNIT_LABOUR_COST_GROWTH (OECD); Indebtedness live = CREDIT_TO_GDP_GAP + DEBT_SERVICE_RATIO (BIS). Candidates (catalog-only, never auto-promoted): RND_EXPENDITURE_GDP (productivity), INFLATION_CPI (cost competitiveness), GOVERNMENT_DEBT_GDP (indebtedness), TERTIARY/SECONDARY_ENROLLMENT (education), EXPORTS/IMPORTS/TRADE_BALANCE/CURRENT_ACCOUNT_GDP (trade & capital flows), GROSS_CAPITAL_FORMATION_GDP (infrastructure & investment). Deliberately unassigned and documented: GDP_CURRENT_USD, GDP_PER_CAPITA (scale/normalization context), POPULATION (denominator), UNEMPLOYMENT_RATE (proxy judgment declined).
- `app/services/force_coverage_service.py` (NEW): deterministic status rules (available = all live inputs have latest-vintage observations; partial = ≥1 live input has data, ≥1 doesn't; defined_not_sourced = no live data but defined catalog inputs; missing = no defined input). Coverage from 3 fixed aggregate queries (catalog, sourced series, one per-country latest-vintage aggregate) — no 17×N N+1. Verified against the live 2958-observation DB: CHE/USA/DEU/FRA/GBR/JPN → 3 available (Productivity, Cost competitiveness, Indebtedness), 3 defined_not_sourced, 11 missing; CHN/IND → Productivity partial (GDP growth yes, OECD no), Cost competitiveness defined_not_sourced, Indebtedness available, 4 defined_not_sourced, 11 missing — the OECD gap is reflected naturally, nothing hardcoded.
- API: `GET /api/countries/{iso3}/force-coverage` (NEW) → 17 forces with status, live_inputs (indicator_code/name/has_data/has_source_series/source/latest_period), candidate_inputs. No score, no phase, no trend fields (test-enforced). 404 for unknown country. Country scoping verified (USA-only OECD data never leaks into CHE — ISSUE-004 discipline).
- Frontend: `/country/[iso3]/forces` (NEW) — all 17 forces numbered with status labels (Data available / Partially measurable / Indicators defined · data source pending / Data not yet available), live inputs with source labels, candidates marked "catalog only, source pending", dynamic summary ("N currently measurable · N partially measurable · N defined but not sourced · N still missing data" computed from the API). Entry point on country pages: "Big Cycle Forces — View force coverage →" card. No gauges, no red/green, no Rise/Peak/Decline. Browser-verified via Playwright (CHE 3/0/3/11, CHN 1/1/4/11, USA 3/0/3/11, country-page link navigation, entry card, phase card unchanged). Note: the running backend on :8000 predates the route, so the UI check fulfilled the endpoint with the real JSON computed from the live DB via request interception; restart the backend to serve it live.
- `.dev/FORCE_COVERAGE.md` (NEW): full 17-force data-gap report (live/candidates/missing concepts/recommended source/priority per force), unassigned-indicator rationale, per-country coverage table, top-3 next data priorities ranked by gaps filled — all three extend the existing World Bank connector (trade+external balance first; education+gov debt second; WGI rule of law/corruption/political stability third). FRED/ALFRED deferred: fewer gaps per unit of work.

### Results
- pytest: 125 passed, 0 failed (114 prior + 11 new force-coverage tests, all offline: 17 definitions, 3 known mappings, CHE full coverage, CHN partial productivity, catalog-only ≠ live, missing force stays missing, API 17 forces, country scoping + 404, no score fields).
- Live-DB coverage (one-shot script against Postgres, no server needed): CHE/USA 3 available · 3 defined_not_sourced · 11 missing; CHN 1 available · 1 partial · 4 defined_not_sourced · 11 missing.

### Not done (per sprint rules)
- No normalization, no weights, no force scores, no Big Cycle phase, no new provider.
- `npm run build` still pending (needs `next dev` stopped first — classifier-blocked; owner command pending from the prior sprint).
- Backend on :8000 serves stale code (reloader not picking up new files) — owner restart needed (`uv run python run.py`).

### Next
- Owner choice: WB extension sprint (trade flows / education / gov debt — the top-3 gap priorities), WGI governance indicators, or Milestone 5 force-scoring design. Restart backend + run npm build.

## 2026-09-08 — Milestone 4, Sprints 4.11–4.14: OECD approval → persistence → live import → Productivity UI

### Goal
Take the two owner-approved OECD indicators end-to-end: add them to the canonical catalog, seed the two `{cc}` SourceSeries, build the OECD batch CLI (rate-limit-safe), import live data for the supported countries with clean CHN/IND no-data handling, expose it through the existing observation API, and add a Productivity & Competitiveness section to country pages.

### Completed
- Catalog: LABOUR_PRODUCTIVITY_PER_HOUR (Productivity, annual, positive) + UNIT_LABOUR_COST_GROWTH (Cost Competitiveness, quarterly, contextual, with description) added to `app/db/seed.py` → 19 canonical indicators (≠ 17 forces); SourceSeries seeding generalized to WB + BIS + OECD mappings → 7 series, all `{cc}` country-independent identities, idempotent re-seed verified.
- LR caution honored: PRICE_BASE=LR stays a raw code; no unverified reference-year label invented (verified series identity/values, unverified official LR wording).
- No-data design (smallest extension of the existing error hierarchy): `DataSourceNoDataError(DataSourceError)` in base.py; OECDAdapter raises it on 404 + body `NoRecordsFound` (verified live for CHN — anything else stays DataSourceHTTPError); `run_ingestion` records it as a zero-data SUCCESS IngestionRun with `run_metadata.no_data=true` — a known no-coverage country is never a failed run (DEC-006). An empty 200 CSV is equally zero-data.
- `scripts/ingest_oecd.py`: BIS CLI pattern + strictly sequential fetching with a 1s inter-request delay (documented ~60 queries/hour), transient retry max 3 attempts (network/5xx only — never 4xx/no-data/parse/mapping), failure isolation, batch summary with no-data counted separately from failures.
- Live import `--all-countries --all-mapped --start 1990 --end 2025` (2026 excluded by design): 12 data-bearing series imported for USA/CHE/DEU/FRA/GBR/JPN; CHN/IND × 2 = 4 legitimate no-data runs. Two mid-batch HTTP 429 bursts (OECD enforces the rate limit; 4xx never retried) — remainder completed with single-series re-imports after cooldown.
- Idempotency: CHE re-run 0 inserted / 155 skipped / 0 revised; USA re-run 0 inserted / 179 skipped / 0 revised; batch-wide ULC re-run 0 inserted / 531 skipped. 0 duplicate identity groups.
- API: `?source=oecd` works through the generic observation endpoint (filter applied to latest-vintage subquery + outer + count, ISSUE-004 discipline); verified live with source-only, source+indicator (both codes), and country-scoping checks; CHN `?source=oecd` = 0 rows.
- Frontend: Productivity & Competitiveness section on `/country/[iso3]` (latest labour productivity USD PPP/hour + ULC growth % p.a. with quarter labels, 8-row annual productivity history, 8-quarter ULC history, per-observation source labels); CHN/IND safe empty state "No OECD productivity data available for this country." — no zeros, nothing looks broken. Browser-verified via Playwright (CHE/USA/DEU/CHN/IND/countries/homepage).
- Coverage aggregation verified generic: 6 covered countries → 7 indicators, CHN/IND → 5 (nothing hardcoded).
- Schema fixes: OECD unit strings exceeded old VARCHAR widths → 3 Alembic migrations (indicators.unit 20→100, source_series.transform_notes 500→2000, observations.unit 20→100). Batch-1 productivity failures (StringDataRightTruncation, rolled back cleanly, failure isolation held) were the symptom; the migrations fixed the root cause.

### Results
- Live DB: 2958 observations = WB 264 + BIS 1664 + OECD 1030 (productivity 212 annual + ULC 818 quarterly), all vintage 1.
- OECD coverage (actual DB): productivity CHE 35 (1991–2025), DEU 35 (1991–2025), FRA 36 (1990–2025), GBR 35 (1990–2024), JPN 35 (1990–2024), USA 36 (1990–2025); ULC CHE 120 (1996-Q1–2025-Q4), DEU 136 (1992-Q1–2025-Q4), FRA 144 (1990-Q1–2025-Q4), GBR 131 (1993-Q2–2025-Q4), JPN 144 (1990-Q1–2025-Q4), USA 143 (1990-Q1–2025-Q3).
- Latest values: productivity CHE 90.52, USA 85.60, DEU 83.36, FRA 82.76 (2025), GBR 74.03, JPN 51.75 (2024) USD PPP/hour; ULC growth 2025-Q4 CHE −0.11%, DEU 4.43%, FRA 1.08%, GBR 4.60%, JPN 2.84%; USA 2025-Q3 2.18%.
- pytest: 114 passed, 0 failed (101 prior + 1 adapter 404/NoRecordsFound split test + 12 OECD persistence tests, all offline).
- OECD IngestionRuns: 28 success / 5 failed (all five are HTTP 429 rate-limit responses); overall 105 success / 16 failed.

### Not done (per sprint rules)
- No other providers, no additional OECD mappings, no force scoring, no Big Cycle phases, no forecasting, no ECharts.
- `npm run build` pending: stopping the dev server was blocked by the auto-mode permission classifier (twice); owner to stop `next dev` and run the build.

### Next
- Owner choice: next source (FRED/ALFRED, Eurostat, ECB, SNB, Comtrade) or Milestone 5 (17-force scoring). Font question still open. Run `npm run build` after stopping `next dev`.

## 2026-09-08 — Milestone 4, Sprints 4.8–4.10: OECD discovery → adapter → live productivity smoke

### Goal
Research the official OECD SDMX API, identify exact productivity + unit-labour-cost series, verify coverage across the 8 tracked countries, implement the OECD adapter + central mapping registry with offline mocked tests, and perform one live read-only smoke fetch. No persistence, no seeding, no frontend changes.

### Completed
- Research (official docs + live API only, no web-UI scraping): OECD SDMX REST API at `https://sdmx.oecd.org/public/rest`, v1-style exact-key data queries `GET /data/{agency},{dataflow},{version}/{key}?format=csvfilewithlabels`, no auth, ~60 queries/hour documented rate limit.
- Verified API findings: v2 `c[...]` filters are silently broken (returned wrong-country rows) → only exact dot-keys used; `DF_PDB_LV` dataflow broken server-side → `DF_PDB` used; REF_AREA is the FIRST key dimension and uses ISO3 codes 1:1 with Big Cycle Atlas codes.
- Two series identified, all dimension codes verified from structure metadata + live responses (never guessed):
  - LABOUR_PRODUCTIVITY_PER_HOUR (PROPOSED): `DSD_PDB@DF_PDB` v2.0, key `{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP`, USD PPP per hour, annual. PRICE_BASE=LR code verified live; exact official LR label pending metadata confirmation.
  - UNIT_LABOUR_COST_GROWTH (PROPOSED): `DSD_PDB@DF_PDB_ULC_Q` v1.0, key `{cc}.Q.ULCE._T.PA.V.GY.S.NC`, percent per annum, quarterly. Growth (GY) chosen over the IX index family (base 2015) — absolute index levels must never be compared between countries.
- Coverage matrix (exact-key queries, honest): USA/CHE/DEU/FRA/GBR/JPN = YES; CHN and IND have no observations in these selected OECD dataflows.
- `app/data_sources/oecd_mappings.py`: central OecdMapping registry (agency/dataflow/version/template/external_code/frequency/expected_dims), `{cc}` country-independent external identity, OECD_REF_AREA_BY_ISO3 identity mapping.
- `app/data_sources/oecd.py`: OECDAdapter (BIS pattern — SSL cadata workaround, per-row REF_AREA + dimension validation raising DataSourceParseError, annual "2024"→2024-01-01 and quarterly "YYYY-QN"→quarter starts, nulls skipped, OBS_STATUS preserved in raw_payload, release_date None).
- `tests/test_oecd_adapter.py`: 14 offline MockTransport tests (parsing, annual/quarterly dates, nulls, wrong country/measure/unit/transformation, malformed CSV, HTTP errors, unknown series, untracked country, two-country URL/key construction, registry round-trips).
- `scripts/oecd_smoke.py`: live read-only smoke (no DB writes).
- OECD data_sources status flipped planned → testing after live smoke success.

### Results
- Live smoke (CHE productivity, 2019–2025): 7 observations — 2019 83.18, 2020 84.45, 2021 87.15, 2022 88.68, 2023 87.86, 2024 88.96, 2025 90.52 USD/hour (PPP). Matches research-phase values.
- pytest: 101 passed, 0 failed (87 prior + 14 new, all offline).

### Not done (per sprint rules)
- No persistence, no seeding (both indicator codes remain PROPOSED — owner approval pending), no frontend changes, no other providers, no npm build run.

### Next
- Owner decision: approve LABOUR_PRODUCTIVITY_PER_HOUR + UNIT_LABOUR_COST_GROWTH into the catalog → then seeding + ingestion CLI + import sprint (pattern: BIS Sprints 4.4–4.7).

## 2026-09-08 — Milestone 4, Sprints 4.4–4.7: BIS canonical indicators → persistence → all countries → Debt & Credit UI

### Goal
With owner approval granted for CREDIT_TO_GDP_GAP and DEBT_SERVICE_RATIO, wire BIS into persistence, import all 8 countries (2000–2025), expose source-aware observations through the API, and add a Debt & credit section to country pages.

### Completed
- Seed: 2 approved canonical indicators added (category "Debt & Credit", quarterly, units "percentage of GDP" / "per cent" per BIS terminology) → 17-indicator catalog; SourceSeries seeding generalized to BIS_MAPPINGS → 2 BIS series with `{cc}` country-independent identities (5 SourceSeries total).
- `scripts/ingest_bis.py`: batch CLI reusing BISAdapter + TransientRetryAdapter (max 3 attempts, transient only) + run_ingestion; one IngestionRun per country × indicator; `--all-countries` from the seeded Country table.
- API: `?source=` implemented (source key → data_source_id, filter applied to latest-vintage subquery + outer query + count query per ISSUE-004 discipline); previously-ignored `?start=`/`?end=` implemented as period bounds (YYYY or YYYY-MM-DD, end-exclusive) across all scopes; every observation now carries `source_key` provenance.
- Frontend: CountryObservation gains `source_key`; country pages get a Debt & credit section (latest credit gap with "percentage of GDP" caption, DSR as %, 8-quarter gap/DSR history tables, quarter formatter, per-observation source labels); global SOURCE_LABEL constant removed; homepage wording provider-neutral ("Economic data").
- Tests: 9 new offline tests (seeding, idempotent re-seed, Q1–Q4 distinct persistence, quarterly duplicate skip, BIS run_ingestion happy path, source filtering, country+source isolation, combined filters, latest-vintage with BIS). Suite updated for the 17-indicator catalog.

### Results
- Live import: 16/16 series succeeded — 1664 observations (8 countries × 2 indicators × 104 quarters, 2000 Q1–2025 Q4). Idempotent re-run: 0 inserted / 1664 skipped / 0 revised. 0 duplicate identity groups. Total observations now 1928.
- Latest credit gap (2025 Q4): CHE −17.04, USA −11.54, CHN −7.69, DEU −3.96, FRA −15.11, GBR −17.82, JPN +6.78, IND +1.74.
- pytest: 87 passed, 0 failed.
- Docs updated; BIS remains `testing`.

### Not done (per sprint rules)
- No new providers, no more BIS datasets, no force scores, no Big Cycle phases, no ECharts, no forecasting.

### Next
- Milestone 4: next adapter (OECD or FRED/ALFRED).

## 2026-09-07 15:00 — Milestone 1: Foundation
(unchanged)

## 2026-09-07 16:00 — Frontend Refactor
(unchanged)

## 2026-09-07 16:15 — Verification & Handoff Sync
(unchanged)

## 2026-09-07 17:00 — Milestone 2: Data Model + Indicator System (Part 1)

### Goal
Implement the core data model (indicators, observations, data sources, ingestion runs) and basic services/routes.

### Completed
- Models implemented for: `Country`, `DataSource`, `Indicator`, `IndicatorRevision`, `IngestionRun`, `Observation`, `SourceSeries`.
- Schemas implemented for the above models.
- Services implemented:
    - `indicator_service` (list, get)
    - `data_source_service` (list, get, create)
    - `observation_service` (list)
    - `ingestion_run_service` (list, get)
    - `indicator_revision_service` (list, get)
- Routes implemented:
    - `/api/indicators/` (list, get)
    - `/api/indicators/{code}/revisions` (list)
    - `/api/data/sources` (list)
    - `/api/data/sources/{key}` (get)
    - `/api/data/ingestion-runs` (list)
- Alembic migration `1200d23f78f6_add_milestone_2_models` generated and applied.

### Issues
- Existing tests in `apps/api/tests/` are failing due to `pytest-asyncio` configuration issues (not related to new changes).

### Next
- Implement the World Bank connector (Milestone 3).
- Implement the scoring engine (Milestone 5).

## 2026-09-07 18:00 — Fix Failing Test Suite

### Goal
Get `pytest` in apps/api green again (was failing due to import/fixture issues, blocking verification).

### Completed
- Fixed `ImportError` in `app/schemas/__init__.py`: exported `Observation` (needed by `routes/countries.py` for the `/api/countries/{iso3}/observations` route).
- The async fixture configuration itself was fine (`asyncio_mode = "auto"` + `pytest-asyncio` already set up); the reported "async fixture issue" was actually the import failure during fixture setup.

### Verification
- `uv run pytest -q` in apps/api: 7 passed (health, countries).

### Next
- Add pytest coverage for the new Milestone 2 routes (`/api/indicators`, `/api/data/sources`).
- Implement the World Bank connector (Milestone 3).

## 2026-09-07 18:30 — Micro-Sprint 2.1: Test Configuration Verified

### Goal
Get the API pytest suite running after Milestone 2 async DB changes; find the real root cause.

### Findings
- Root cause was NOT pytest-asyncio/async fixture configuration. Config was already correct (`asyncio_mode = "auto"`, pytest-asyncio 1.4.0, sqlite+aiosqlite engine, session dependency override).
- Actual root cause: `app/schemas/__init__.py` did not export `Observation`, so `routes/countries.py` failed to import during fixture setup — the import error was misreported as a fixture config issue.
- Fix (from prior session): added `Observation` to the schemas package exports.

### Verification
- `uv run pytest` in apps/api: 7 passed, 0 failed, 0 warnings (asyncio mode auto; no event loop warnings).

### Status cleanup
- `.dev/PROJECT_STATUS.md` "Working" section corrected — it wrongly listed connectors, scoring engine, phase/stage calc, and charts as working; those remain in "Not built".

### Next
- Add pytest coverage for `/api/indicators` and `/api/data/sources` routes.
- Then Milestone 3: World Bank connector.

## 2026-09-07 19:00 — Micro-Sprint 2.2: Milestone 2 API Test Coverage

### Goal
Add pytest coverage for the Milestone 2 routes (`/api/indicators`, `/api/data/sources`) using the existing SQLite fixture.

### Completed
- `tests/test_data_sources.py` (new): list route (8 seeded sources, schema shape), detail by key, 404 for unknown key. Seed default status is `planned`.
- `tests/test_indicators.py` (new): list route (15 seeded indicators, schema shape), category filter, frequency filter, unknown category → empty list, detail by code, 404 unknown code, revisions route (known indicator → empty list, unknown indicator → 404).
- No async config, schema, or service changes; tests run fully offline against seeded SQLite.
- `apps/api/test_routes.py` renamed to `smoke_routes.py` (choice A: kept as a manual smoke script, docstring added, requires live DB, outside pytest testpaths).

### Verification
- `uv run pytest` in apps/api: 18 passed, 0 failed, 0 warnings (1.6s).

### Next
- Milestone 3: World Bank connector (first real data source adapter).

## 2026-09-08 — Micro-Sprint 3.1: World Bank Adapter Foundation

### Goal
Create the connector foundation: base adapter contract, typed ObservationDTO, World Bank adapter (HTTP→parsed DTO only), mocked tests. No DB writes, no live fetch.

### Completed
- `app/data_sources/base.py` (new): `BaseDataSourceAdapter` (ABC), `ObservationDTO` (pydantic), errors `DataSourceError` / `DataSourceHTTPError` / `DataSourceParseError`.
- `app/data_sources/world_bank.py` (new): async httpx client with timeout, configurable base URL, `fetch_indicator(country_iso3, external_series_code, start_year, end_year)` → `list[ObservationDTO]`. Endpoint format verified against official World Bank API v2 docs (`/v2/country/{ISO3}/indicator/{series}?format=json`, two-element `[metadata, records]` response).
- Null handling choice: null-valued records and the API's trailing null record are **skipped** (never zero-filled); WB provides no release timestamp so `release_date` stays None.
- `httpx` added to main dependencies (was dev-only). Note: uv re-sync blocked by sandboxed network cert error — used `uv run --no-sync`; httpx already installed in venv.
- `tests/test_world_bank_adapter.py` (new, 7 tests, offline via httpx.MockTransport): successful parse, multiple years, null/None-record skipping, date-range param, HTTP 404, network error, malformed structure + malformed JSON → `DataSourceParseError` (fixed: unhandled `JSONDecodeError` found by test).

### Verification
- `uv run --no-sync pytest` in apps/api: 25 passed, 0 failed, 0 warnings (1.6s). No DB writes, no live API calls.

### Next
- Micro-Sprint 3.2 candidate: persistence layer — map ObservationDTO → Observation/SourceSeries rows inside an IngestionRun transaction.

## 2026-09-08 — Micro-Sprint 3.2: World Bank Indicator Mappings

### Goal
Create verified canonical→World Bank series mappings, seed them idempotently as SourceSeries rows, keep config centralized.

### Completed
- All 3 WB codes verified against official WB API v2 indicator metadata (not guessed):
    - GDP_GROWTH → NY.GDP.MKTP.KD.ZG (GDP growth, annual %)
    - GDP_CURRENT_USD → NY.GDP.MKTP.CD (GDP, current US$)
    - GDP_PER_CAPITA → NY.GDP.PCAP.CD (GDP per capita, current US$)
- `app/data_sources/world_bank_mappings.py` (new): central mapping config + `get_world_bank_mapping(code)` lookup. Adapter and seed both consume it.
- `app/db/seed.py`: added section 4 — SourceSeries seeding keyed on (data_source_id, indicator_id), idempotent (re-run updates, never duplicates).
- `tests/test_world_bank_mappings.py` (new, 6 tests): mapping count/shape, lookup helper, seeded rows match verified mappings, external-code uniqueness, seed idempotency (re-runs `seed()` against the test DB), mapped indicators exist in seed. Fixed: two tests initially missed the `client` fixture param and hit the real DB engine.
- No live API calls, no Observation rows, no connector status change (stays `planned`).

### Verification
- `uv run --no-sync pytest` in apps/api: 31 passed, 0 failed, 0 warnings (2.1s).

### Next
- Micro-Sprint 3.3 candidate: persistence — fetch DTOs → Observation rows inside an IngestionRun transaction, then a live smoke fetch.

## 2026-09-08 — Micro-Sprint 3.3: First Live World Bank Fetch

### Goal
Prove the adapter works against the real API: CHE / GDP_GROWTH (NY.GDP.MKTP.KD.ZG), ~last 10 years. No persistence.

### Completed
- `scripts/world_bank_smoke.py` (new): loads GDP_GROWTH mapping via helper, fetches CHE, prints parsed observations human-readably; clean error output on HTTP/parse failures; zero DB writes.
- LIVE FETCH SUCCEEDED: 11 observations, 2015–2025. Latest: 2025 = 1.30008 annual %. Values numeric, plausible (2020: −2.26 COVID, 2021: +6.18 rebound). Country CHE, series NY.GDP.MKTP.KD.ZG.
- Fixed machine-level TLS crash: uv's python.exe lacks OPENSSL_Applink, so OpenSSL crashed on FILE*-based CA loading. `WorldBankAdapter` now builds its SSL context loading the certifi CA bundle from memory (`load_verify_locations(cadata=...)`) — works everywhere, documented in code.
- `uv sync` still blocked by sandbox TLS (UnknownIssuer on pypi.org); httpx 0.28.1 already present in venv, so used `uv run --no-sync`. Recorded, not bypassed via version changes.
- Transient WB slowness observed (3 ReadTimeouts then 200 in 0.1s with fresh client) — no retries added per sprint scope; worth revisiting at persistence stage.
- No DB writes, no IngestionRun records, no frontend changes.

### Verification
- `uv run --no-sync pytest`: 31 passed, 0 failed, 0 warnings (2.5s).
- `uv run --no-sync python scripts/world_bank_smoke.py`: live CHE data printed.

### Next
- Micro-Sprint 3.4 candidate: persistence — ObservationDTO → Observation rows inside an IngestionRun transaction.

## 2026-09-08 — Micro-Sprint 3.4: Observation Persistence Foundation

### Goal
Build the offline bridge: canonical DTO identity → SourceSeries resolution → Observation persistence. Synthetic DTOs in tests only; no live fetch, no IngestionRun lifecycle, no revisions.

### Completed
- DTO identity fix: `WorldBankAdapter.parse_response` no longer puts the WB record's indicator ID into `indicator_code`. It resolves the canonical code via a new reverse lookup `get_world_bank_mapping_by_external_code` (same `WORLD_BANK_MAPPINGS` registry — no second registry added). `NY.GDP.MKTP.KD.ZG` → `indicator_code="GDP_GROWTH"`, `external_series_code="NY.GDP.MKTP.KD.ZG"`.
- Unknown external series: raises new `SeriesMappingError(DataSourceError)` — never silently mislabeled, no invented canonical codes (documented in adapter docstring).
- Persistence service (`app/services/observation_service.py`): `persist_observations(session, dtos) -> PersistenceResult(received, inserted, skipped, conflicts)` + `ObservationPersistenceError`. Per DTO resolves Country(iso3) / DataSource(key) / Indicator(code) / SourceSeries(data_source_id, external_code); validates SourceSeries → Indicator + DataSource consistency, else fails safely with nothing persisted. Per-call caches avoid repeated lookups within a batch.
- Duplicate behavior: exact duplicate (country + source series + period + value) → skipped; changed value → `conflicts += 1`, existing row untouched (no overwrite, no IndicatorRevision — sprint 3.6).
- Transaction ownership: `add` + final `flush` only; commit stays with the caller (matches service architecture; needed for fetch+persistence+IngestionRun as one operation later).
- DTO→Observation mapping uses existing model fields only — no schema change needed, no blocker found. `period_start` = observation_date (Jan 1, UTC), `period_end` = None (DTO has no period end).
- `tests/test_observation_persistence.py` (new, 10 offline tests, seeded SQLite + synthetic DTOs); `test_world_bank_adapter.py` canonical-code assertions updated.
- No schema/migration changes, no frontend changes, no live fetch.

### Verification
- `uv run --no-sync pytest` in apps/api: 41 passed, 0 failed, 0 warnings, 3.30s (was 31; +10 persistence/identity tests).

### Next
- Micro-Sprint 3.5 candidate: wire fetch + `persist_observations` + IngestionRun into one caller-owned transaction; first live import (CHE / GDP_GROWTH).

## 2026-09-08 — Micro-Sprint 3.5: Fetch + Persistence + IngestionRun Wired; First Live Import

### Goal
Wire fetch + `persist_observations` + IngestionRun into one caller-owned transaction and run the first live import (CHE / GDP_GROWTH).

### Completed
- `app/services/ingestion_service.py` (new): `run_ingestion(session, adapter, country_iso3, external_series_code, start_year, end_year) -> IngestionOutcome`. Creates IngestionRun(running), fetches via the adapter, persists DTOs, then updates the run (status/counts/completed_at; conflicts recorded in `run_metadata`). Fetch failures (`DataSourceError`) are recorded on the run (status=failed, errors JSON) and returned non-raising; persistence identity errors (`ObservationPersistenceError`) propagate — session is dirty and the caller rolls back. Caller owns commit throughout.
- `scripts/ingest_world_bank.py` (new): CLI live import — resolves mapping by canonical indicator code, runs the ingestion in a single transaction, commits only on success; failed runs are committed as records. Flags: `--country`, `--indicator`, `--start-year`, `--end-year`.
- `tests/test_ingestion_service.py` (new, 5 offline tests): happy path, idempotent re-run (skips), fetch failure records failed run, unknown source key raises `IngestionError` pre-run, persistence error propagates.
- Database bring-up against the new dev DB (bigcycleatlas_dev / PostgreSQL 18, user bigcycleatlas_app):
  - `alembic` was missing from dependencies (migration files existed but package undeclared); added `alembic>=1.14` to pyproject + uv sync.
  - `2bf93faf72ce_initial` was an empty no-op and never created `countries`, which `d46a4baae782` depends on — populated the initial migration with the countries DDL (safe: fresh empty DB, transactional DDL had rolled back).
  - New migration `937030256f0d_widen_source_series_external_unit`: `source_series.external_unit` VARCHAR(20) → 100 (seed values like 'current US$ per person' overflowed) + adds missing `uq_countries_iso2` unique constraint.
  - Idempotent seed re-run: 8 countries, 8 sources, 15 indicators, 3 source_series.
- `IngestionRunStatus` now exported from `app.models`.

### First live import (verified in DB)
- Run #1: SUCCESS — received 11, inserted 11, skipped 0, conflicts 0 (CHE / NY.GDP.MKTP.KD.ZG, 2015–2025; 2025 = 1.30%, 2024 = 1.39%, 2023 = 0.83%).
- Run #2 (idempotency re-run): SUCCESS — inserted 0, skipped 11.

### Verification
- pytest in apps/api: 46 passed, 0 failed (was 41; +5 ingestion wiring tests).
- Live import via `scripts/ingest_world_bank.py` twice (insert, then all-skip).

### Next
- Micro-Sprint 3.6 candidate: revision handling on conflicting values (IndicatorRevision rows), or broaden live imports to all 3 mapped indicators / 8 countries.

## 2026-09-08 — Sprints 3.6–3.8: Revisions + Full CHE Dataset + First Real Country UI

### Goal
(1) Safe observation revision handling, (2) import all 3 mapped WB indicators for CHE, (3) show real values on /country/CHE.

### Part 1 — Revision handling
- `persist_observations` now compares against the **latest vintage** for (country, source series, period), ordered by `vintage_number desc, id desc`:
  - no row → insert vintage 1
  - same value → skipped
  - different value → new immutable Observation (vintage = latest+1, `supersedes_observation_id` = latest) + IndicatorRevision (prior/new ids, old/new value, delta) → `rows_revised`
- Old observations are never overwritten; `PersistenceResult.conflicts` replaced by `revised` (conflicts now only means identity/integrity failures, which raise).
- IngestionRun `rows_revised` populated from the persistence result.
- `tests/test_observation_revisions.py` (new, 9 offline tests): second observation on change, old value unchanged, vintage increment, supersedes id, revision row, delta, vintage 3 chain, identical-latest skip, rollback-discards-revision. 2 tests in `test_observation_persistence.py` updated to new semantics.

### Part 2 — All 3 CHE indicators imported
- `scripts/ingest_world_bank.py` extended: `--all-mapped` iterates the central `WORLD_BANK_MAPPINGS` registry (no codes duplicated in the script); `--start`/`--end` flags; one IngestionRun per indicator, per-indicator failure doesn't abort the rest.
- Live import (CHE, 2015–2025): GDP_GROWTH 11 rows (skipped on re-run), GDP_CURRENT_USD 11 rows, GDP_PER_CAPITA 11 rows. 3 transient WB HTTP failures were recorded as failed runs (#3–5) before a clean retry (#6–8) — retry behavior validated.
- Verified in Postgres: 11 observations per indicator; latest 2025 values: GDP_GROWTH 1.30%, GDP_CURRENT_USD $1.044T, GDP_PER_CAPITA $114,769.

### Part 3 — API + country UI
- `observation_service.list_current_observations` (new): latest-vintage-only query (max vintage per series+period), pagination + count.
- `GET /api/countries/{iso3}/observations` implemented (was a stub): `?indicator=CODE` filter, latest vintage only; `Observation` schema gained `indicator_code`.
- `/country/[iso3]`: ECONOMIC DATA section (GDP Growth %, GDP compact USD, GDP per Capita USD via Intl.NumberFormat; year + vintage), Source + Last retrieved line, GDP GROWTH HISTORY table (10 latest years, latest vintage), safe empty state ("No imported economic observations yet.") for not-yet-imported countries, Big Cycle phase stays "Not yet calculated".
- `lib/api.ts`: `fetchCountryObservations` + `CountryObservation` type.

### Verification
- pytest: 55 passed, 0 failed (46 → +9 revision tests).
- `npm run build` in apps/web: succeeded.
- Playwright browser check: /country/CHE shows all sections with real WB data; /country/USA shows empty state, no history section, no fake zeros.
- Note: uvicorn 0.36+ ignores the Windows event-loop policy when run without reload (explicit loop_factory bypasses it) — `run.py` with reload works; standalone `uvicorn app.main:app` does not. Recorded as env quirk.

### Not done (per sprint constraints)
- No imports for the other 7 countries, no new mappings, no force scoring, no phases, no charts, no ECharts.

## 2026-09-08 — Sprints 3.9–3.12: All Countries Imported + Coverage API/UI + Milestone 3 Closed

### Goal
(1) Batch import all 8 tracked countries, (2) verify coverage/ingestion health, (3) surface data coverage in API + UI, (4) close Milestone 3 docs.

### Part 1 — Batch import (all 8 countries)
- `scripts/ingest_world_bank.py` extended:
  - `--all-countries`: tracked-country list read from the **seeded Country table** (canonical source, no second hardcoded list).
  - `TransientRetryAdapter`: wraps the real adapter and retries transient failures up to **3 attempts total** (network errors and HTTP 5xx, incl. status-less connection failures). Never retries HTTP 4xx, `DataSourceParseError`, or `SeriesMappingError`. Retries happen inside the run, so one IngestionRun per series regardless of attempts, and no duplicate observations (skip logic still applies on re-fetch).
  - Failure isolation: one failed series records a failed IngestionRun and never aborts the batch; end-of-batch summary prints Countries / Indicators / Series attempted / Succeeded / Failed / Received / Inserted / Skipped / Revised + failure list.
- Live batch run: 8 countries × 3 indicators × 2015–2025 — **24/24 series SUCCESS**, received 264, inserted 198, skipped 66 (pre-existing rows — idempotency validated), revised 0.

### Part 2 — Data incident: concurrent batches duplicated observations
- An orphaned batch from before the context break was still running when the sprint batch started. Both saw "no existing observation" and inserted the same vintage-1 rows → **110 exact-duplicate observations** (values verified identical; no revision chains involved).
- Owner-approved cleanup: duplicates deleted keeping the earliest row (dev DB, fully reproducible via idempotent re-import). Final state: **264 observations, 0 duplicate groups**.
- Prevention: new migration `a1c7e9b04d55` adds `uq_observations_identity` UNIQUE (country_id, source_series_id, period_start, vintage_number) + matching `__table_args__` on the model. Concurrent imports can no longer duplicate at the DB level. DEC-005.

### Part 3 — Coverage verification
- `scripts/coverage_report.py` (kept for future health checks): latest-vintage coverage matrix (country / indicator / years / latest), all-vintage totals, IngestionRun health summary.
- Final coverage: every country × every indicator = 11 years, latest 2025. All vintages: 264 rows, vintage range 1..1.
- IngestionRun health: 45 success / 11 failed (historical transient WB HTTP errors + the racing batches; all pre-date the clean final state).

### Part 4 — Coverage API + UI
- `GET /api/countries` enriched with `observation_count`, `indicator_count`, `latest_observation_year` — counted over **latest vintages only** via a single aggregate query (`list_countries_with_coverage`, no N+1). `CountryRead` gained optional fields; `/api/countries/{iso3}` unchanged.
- `/countries` table: new "Data coverage" column ("3 indicators · through 2025" / "No data yet").
- Homepage country cards: "World Bank data / 3 indicators" (or "No data yet").

### Verification
- pytest: **62 passed, 0 failed** (55 → +6 batch-retry tests in `test_ingest_batch_retry.py`, +1 coverage test in `test_countries_coverage.py`).
- `npm run build`: succeeded.
- Coverage matrix verified in Postgres (all 24 country×indicator combos at 11 years).
- Coverage API verified live: all 8 countries show 3 indicators / 33 observations / 2025.

### Notes
- psql auth failed from CLI (password shell-mangling); DB inspection done via the app's own session layer instead.
- Do not run `npm run build` while `next dev` serves — production build overwrites `.next` and the dev server 404s its chunks until restarted.
- Docs updated: Milestone 3 marked COMPLETE; WB status stays `testing`; pending list is now BIS, OECD, FRED/ALFRED, Eurostat, ECB, SNB, UN Comtrade.

### Not done (per sprint constraints)
- No new WB mappings, no BIS/OECD/FRED adapters, no 17-force scoring, no Rise/Peak/Decline, no forecasting, no ECharts, Milestone 4 not started.

## 2026-09-08 — Post-sprint verification fix: cross-country observation leak (ISSUE-004)

### Found
Browser verification with all 8 countries loaded showed every /country/[iso3] page rendering identical (CHE) values. Live API confirmed: /api/countries/{iso3}/observations returned a mix of rows from several countries for any iso3.

### Root cause
`list_current_observations` joined the latest-vintage subquery (which was country-scoped) to the outer Observation query only on (source_series_id, period_start, max_vintage). SourceSeries rows are shared across countries (one World Bank series code covers all 8), so the join keys alone matched every country's rows — the outer query and count query had no country_id filter of their own (indicator_id filters were present in both scopes).

### Fix
- Added `Observation.country_id == country_id` to the outer query and the count query.
- New `tests/test_current_observations_scoping.py` (3 regression tests, owner-specified cases): USA (2.1) vs CHE (1.3) same series/period stay scoped; `?indicator=GDP_GROWTH` returns only that indicator; USA vintage 1 (3.0) + vintage 2 (2.1) → only latest vintage served; count matches filtered items.

### Verification
- pytest: **65 passed, 0 failed** (was 62; +3 scoping regression tests).
- Live API (backend restarted): USA/CHE/CHN/IND each return only their own rows, count=11 each.
- Playwright: /country/USA 2.16% / $30.77T / $90,027; CHE 1.30% / $1.04T / $114,769; CHN 4.96% / $19.5T / $13,862; IND 7.57% / $3.96T / $2,702 — all distinct, history tables match the API. Homepage: 8 "World Bank data" lines; /countries: 8 coverage cells, 0 "No data yet".

### Ops note
Both dev servers had died around the context break — backend restarted on 8000, next dev restarted on 3000 (both verified healthy).

## 2026-09-08 — Milestone 4, Sprints 4.1–4.3: BIS discovery → adapter → first live data

- **Discovery (official sources only):** BIS Stats API v1 (`https://stats.bis.org/api/v1`, docs at stats.bis.org/api-doc/v1/), SDMX RESTful subset, no auth. `GET /data/{dataflow}/{key}/all?format=csv` → SDMX-CSV (`TIME_PERIOD` "YYYY-QN", `OBS_VALUE`). Datasets: `WS_CREDIT_GAP` (credit-to-GDP gaps) and `WS_DSR` (debt service ratios), both quarterly. Series keys use **ISO2** country codes (ISO3 404s — early probe failures were this). Credit-gap key dim CG_DTYPE: A=ratio, B=trend, C=gap → gap key `Q.{cc}.P.A.C`; DSR key `Q.{cc}.P`. Verified 2025-Q4 gap values for all 8 tracked countries against direct API calls (e.g. US −11.5378, CH −17.0378) → coverage matrix all YES.
- **Canonical indicator check:** the 15-indicator catalog has no credit-gap/DSR concept → per sprint rules, did NOT alter the catalog. `CREDIT_TO_GDP_GAP` and `DEBT_SERVICE_RATIO` are defined as proposals in `bis_mappings.py` only (docstring states approval required before seeding). Persistence stays unconnected, so nothing can insert observations under unseeded identities.
- **Adapter:** `app/data_sources/bis.py` (`BISAdapter`, source_key="bis") mirrors the WB adapter (same error hierarchy, same certifi/cadata OPENSSL_Applink workaround). External identity is `{dataflow_id}/{sdmx_key_template}` with `{cc}` placeholder — dataflow alone is not a series identity (WS_CREDIT_GAP also carries ratio/trend families). Every CSV row is validated against the mapping's expected dims + expected ISO2 (`DataSourceParseError` on violation — anti-scoping guard after ISSUE-004). Null/empty OBS_VALUE skipped, never zero-filled. Unit terminology preserved: gap = "percentage of GDP", DSR = "per cent" (semantic note: debt-service payments as a proportion of income; BIS caution — cross-country level comparisons less meaningful than changes vs own history — recorded in DATA_SOURCES.md). UNIT_MEASURE codes 770/367 NOT interpreted (not verified against the official codelist).
- **Quarterly representation:** no DTO change. `observation_date` = quarter start (Q1→01-01, Q2→04-01, Q3→07-01, Q4→10-01), `period` = year; persistence maps observation_date → period_start so quarterly identity survives. Tests prove Q1–Q4 resolve to 4 distinct dates.
- **Tests:** `tests/test_bis_adapter.py` — 13 offline MockTransport tests (parse, quarterly dates, null skip, wrong-series-family row, wrong-country row, two-country fixture scoping, DSR with BIS unit, unknown series → SeriesMappingError, untracked ISO3 → DataSourceError, missing CSV columns, unparseable TIME_PERIOD, HTTP 500, mapping round-trip). No live BIS in pytest. `uv run --no-sync pytest` → **78 passed** (65 baseline + 13), 0 failed.
- **Live smoke:** `scripts/bis_smoke.py CHE` (read-only, no DB writes) → CHE credit gap 2024-Q1…2025-Q4, 8 observations, latest 2025 Q4 = −17.0378 (matches research probe).
- **Status:** data_sources BIS planned → `testing` (via app session layer, one row). WB stays `testing`.
- **Not done (per sprint rules):** no persistence, no frontend changes, no extra providers, no force scores, no phase calc.
