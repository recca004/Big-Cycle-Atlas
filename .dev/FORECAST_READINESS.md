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
| Observed stage transitions (2000–2025) | 44–50 per model across 8 countries, **but ~1/5 are initial assignments** — only ~35–42 genuine transitions per model (~4–6 per country over 26 years) |
| Observed stage transitions (2015–2025 sub-window) | **0** — no movement in the most recent decade |
| Score volatility | 0.6–2.1 points — composites move far less than stage thresholds |
| Strict as-of samples | **0** — no provider release evidence is ingested (§21) |

## Why this cannot support a forecast model

1. **Too few positive examples.** A stage-transition classifier or
   probability model needs transition events. The 2000–2025 retrospective
   run produces only ~35–42 genuine transitions per model (~4–6 per
   country over 26 years), and **zero** in 2015–2025 — the experimental
   composites are too stable (or the classifier too insensitive) to
   produce trainable labels with any class balance.
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
- Classifier sensitivity review: zero transitions over a decade may
  indicate thresholds too wide rather than genuinely stable conditions
  (recorded as a §28 finding, not hidden).

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
