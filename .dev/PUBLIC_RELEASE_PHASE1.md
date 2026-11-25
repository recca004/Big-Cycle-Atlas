# Public Release Phase 1 — Readiness Notes

Date: 2026-11-25

## Approved public framing

Big Cycle Atlas may be described as:

> An independent economic and historical research observatory inspired by
> Ray Dalio's work, using public datasets and transparent experimental
> methods.

The application must not claim that the Big Cycle theory is proven, that
leadership transitions can be dated accurately, that Atlas scores measure
total national strength, that model stages are predictions, or that Ray
Dalio endorses the project.

## Evidence status exposed publicly

`evidence_status_entries` distinguishes observed data, derived
measurements, approved methods, experimental models, retrospective
analysis, strict historically eligible analysis, prospective predictions,
independently evaluated predictions and unavailable results. The read-only
API is `/api/research-foundation/evidence-status`.

## Dataset publication rights

| Dataset | Raw redistribution | Derived publication | Notes |
|---|---:|---:|---|
| Existing Atlas provider observations | Registry-reviewed per provider | Allowed where provider terms permit | Existing export rules still apply |
| JST Macrohistory R6 | No | Yes, with attribution/share-alike/non-commercial limits | Workbook is not committed; exported aggregates/results only |
| FRED/ALFRED | Pending terms review at import time | Pending | No data imported without API key |
| IMF WP-2026-094 crisis bundle | Pending official bundle review | Pending | Not imported; official ZIP 404 during verification |

Private portfolios, credentials, admin controls and restricted raw
observations remain excluded from the research export.

## What remains unproven

- Universal Big Cycle duration
- A deterministic sequence of stages
- A reliable international-order transition forecast
- Any countdown to an order transition
- The Atlas eight stages as Dalio's original framework

## Phase-2 preparation

The UI should consume the three-timescale metadata and display coverage,
methodology status and evidence status. An unsupported long-cycle clock
must render an unclassified research state, not an invented position.
