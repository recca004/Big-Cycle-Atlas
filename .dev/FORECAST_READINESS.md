# Forecast readiness report — Mission 4 §31

**Verdict: NOT READY.** No production forecast probabilities should be
published in Mission 4 or gated into Mission 5. The evidence below shows
exactly why, and what would have to change.

## Evidence available today

| Input | Reality |
|-------|---------|
| Tracked countries | 8 |
| Annual scoring periods | ~26 (2000–2025), quarterly only for BIS series |
| Composite samples (4 models × 8 countries) | **832 valid periods** in the 2000–2025 diagnostic window |
| Observed genuine stage transitions (2000–2025) | 36–42 per model across 8 countries (~4–5 per country over 26 years; initial assignments excluded) |
| Observed genuine stage transitions (2015–2025 sub-window) | 15–19 per model — post-2015 transitions **do exist** (see correction below) |
| Score volatility | 0.6–2.1 points — composites move far less than stage thresholds |
| Strict as-of samples | **0** — no provider release evidence is ingested (§21) |

## Why this cannot support a forecast model

1. **Too few positive examples.** A stage-transition classifier or
   probability model needs transition events. The 2000–2025 retrospective
   run produces only 36–42 genuine transitions per model (~4–5 per
   country over 26 years), of which 15–19 fall post-2015 — far too few
   for trainable labels with any class balance.

   **§8 correction (Mission 5):** the earlier "zero transitions in
   2015–2025" statement was a reporting artifact, not evidence of
   stability. A 2015–2025 annual window contains only 11 scored periods,
   below the classifier's `min_observations=12` gate, so it returned
   `stage=None` for the whole window — "unclassified" was misread as
   "no transitions". The diagnostics manifest now reports
   `classifiable`/`classified_periods`/`unclassified_reason` separately,
   and a regression test locks the 11-vs-12 boundary.
2. **Sample size.** 832 valid country-periods across 4 models sounds
   adequate, but with ~40 positive labels per model and heavy
   autocorrelation (a transition "event" spans adjacent periods), the
   effective sample is far too small for out-of-sample testing,
   probability calibration, or benchmark comparison.
3. **Leakage.** Any model trained on retrospective (latest-vintage) data
   would ingest revised history — strictly prohibited by the backtest
   rules. Strict mode currently returns "unavailable" for every input, so
   a leakage-free training set does not exist yet.
4. **Event labels.** No verified recession/crisis chronology per country
   is ingested, so even an event-aligned evaluation has no ground truth.

## What Mission 5 would need first

- A longer or higher-frequency usable history, OR an expanded country set
  (8 → larger tracked universe) to multiply transition examples.
- Provider release-date ingestion (WB publication calendar, WGI release
  dates) so strict as-of produces real samples.
- A verified crisis/event chronology to define transition targets.
- Explicit benchmark models (persistence, unconditional frequency) to
  beat before any learned model is considered.
- Classifier sensitivity review: ~4–5 genuine transitions per country
  over 26 years is plausible for a long-cycle model, but the
  level-band thresholds are unvalidated assumptions — sensitivity to
  `peak_low`, `persist_periods`, and `min_stage_periods` should be
  quantified before any forecast use (recorded as a §28 finding).

## Proposed API contracts (scaffolding only)

No endpoints are shipped. When evidence exists, the intended contract is:

- `GET /api/research/forecast/{iso3}?horizon=1y|2y|5y|10y&execution_mode=strict_as_of&info_cutoff=…`
  → `{ stage_probabilities, calibration, model_id, run_manifest }` —
  every response gated on strict-mode inputs and out-of-sample
  calibration evidence.
- `GET /api/research/forecast/readiness` → per-target sample counts,
  transition counts, strict-sample availability.

## Conclusion

The correct Mission 4 output is this readiness report: the honest
finding is that current data supports **diagnostics, not forecasts** —
which is exactly the gate Mission 5 was designed to respect.

## Phase-1 H01 research update — 2026-11-25

The foundation now has an independently dated outcome registry and an
immutable prediction/outcome ledger. JST R6 supplied 2,668 covered
country-years and 88 systemic-banking-crisis onsets across 18 economies,
which permits a retrospective benchmark evaluation even though strict
provider release evidence remains absent.

H01 `H01-P1.0` was executed under `retrospective_latest_vintage`, not as
a historically pre-registered forecast. The latest registered result is
`no_evidence_of_improved_predictive_value`: test AUC 0.363 / 0.381 /
0.296 at 1/2/5 years, with top-quintile precision below the ~3.4% test
base rate. This is a genuine negative research result.

**Readiness verdict remains NOT READY.** JST improves outcome coverage
and research breadth, but it does not provide real-time macro vintages,
does not validate the Atlas stage classifier, and does not support
publishing forecast probabilities.
