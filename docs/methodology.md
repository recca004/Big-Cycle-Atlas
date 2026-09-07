# Methodology

This document explains how Big Cycle Atlas calculates force scores and cycle
positions. It will grow as milestones land. **Nothing described below is
implemented yet** — scoring arrives with Milestone 5 (forces) and Milestone 6
(cycle stages).

## Model versioning

Every scoring change gets a version (e.g. `cycle-model-v0.1`), stored with each
calculated result. Changelog:

| Version | Date | Change |
|---|---|---|
| — | — | No scoring released yet. |

## Scoring philosophy

- All numeric values come from deterministic Python calculations — never an LLM.
- An LLM may later be used to *explain* calculated values in plain language.
- The model must stay transparent: the UI can explain any number from its inputs,
  weights, and transforms.
- No fake data in the core product. Mock data is allowed only in clearly-marked
  UI prototypes.

## Force scores (planned)

Each of the 17 forces is scored 0–100 where **100 = strong/healthy** and
**0 = weak/stressed**.

Per metric pipeline:

1. **Validate** — range checks, unit checks, period sanity.
2. **Normalize** — rescale to 0–100 (percentile or min-max vs. comparison set).
3. **Invert when needed** — indicators where high raw values mean weakness
   (debt ratios, corruption, conflict) are flipped so orientation stays uniform.
4. **Trend** — strongly rising / rising / stable / falling / strongly falling.
5. **Momentum** — rate and acceleration of score change over time.
6. **Freshness** — penalty for aging data, per-indicator rules.
7. **Confidence** — data availability, missing indicators, age, source quality,
   and agreement between indicators. Missing data lowers confidence; values are
   never invented.

Force score = weighted combination of its mapped indicators, using the
config-driven mappings in `force_indicator_mappings` (weights, direction,
transform, freshness rules).

## Cycle phases and stages (planned)

Public phases: RISE, PEAK, DECLINE.
Internal stages: EARLY_RISE, RISE, LATE_RISE, PEAK, LATE_PEAK, EARLY_DECLINE,
DECLINE, RESET.

Stage derivation uses at least: current power level, trend, momentum, debt
stress, internal stress, relative strength vs. other countries, and data
confidence.

| Condition | Stage |
|---|---|
| Low power + strong positive momentum | EARLY_RISE |
| Medium power + positive momentum | RISE |
| High power + positive momentum | LATE_RISE |
| Very high power + flat momentum | PEAK |
| Very high power + negative momentum | LATE_PEAK |
| High power + negative momentum | EARLY_DECLINE |
| Medium/low power + strongly negative momentum | DECLINE |
| Low power after severe stress, improving momentum | RESET |

## Relative vs. absolute (planned)

Both absolute (domestic strength) and relative (vs. tracked countries) scores are
calculated and stored, and the UI separates them clearly.

## Forecasts (planned, Milestone 8)

Forecasts are probability windows (chance of leaving the current stage within
1/2/5/10 years), never exact predicted dates. No production percentages until
the model passes historical validation (Milestone 9).

## Backtesting discipline

Historical tests must respect release dates and revisions: at test date X, the
model sees only what was public at X. Future revisions never leak into
historical tests. This discipline is a prerequisite before any market or
trading logic is trusted.