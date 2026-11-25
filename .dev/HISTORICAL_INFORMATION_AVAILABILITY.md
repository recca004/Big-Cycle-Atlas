# Historical information availability — Mission 5 §6-§7

What evidence exists that a given value was publicly available at a given
time, which evidence each execution mode accepts, and how Atlas collects
evidence prospectively.

## Evidence types

| Evidence | What it proves | What it does NOT prove |
|----------|----------------|------------------------|
| `provider_release_date` | The provider published this value on this date — true publication evidence | That the value was not revised later |
| `atlas_first_observed` (`retrieved_at` on the stored vintage) | Atlas possessed this exact vintage by that timestamp — sound YES evidence | When the provider originally published it (always ≤ truth, strictly conservative) |
| `assumed_release_lag` | Nothing — a documented research estimate | Anything; never admitted to strict mode |

`first_observed` is strictly conservative: it can only *delay* eligibility
relative to true publication, never accelerate it. An observation first
retrieved 2026-09-09 might have been published in 2021, but strict mode
treats it as known no earlier than 2026-09-09 — the error is always in the
safe direction.

## Mode × evidence eligibility

| Mode | provider_release_date | atlas_first_observed | assumed_lag |
|------|----------------------|----------------------|-------------|
| `current_latest` | n/a (no as-of gate) | n/a | n/a |
| `retrospective_latest_vintage` | n/a | n/a | n/a |
| `strict_as_of` | eligible | eligible (OR) | **never** |
| `research_assumption` | — | — | eligibility basis |

Strict rule: `release_date ≤ cutoff OR retrieved_at ≤ cutoff`. Both give
sound "the value existed at the cutoff" evidence for that exact vintage.

## §6 — provider investigation findings

| Provider | Vintage/release evidence available publicly | Atlas status |
|----------|----------------------------------------------|--------------|
| World Bank WDI | Archived annual WDI editions exist as bulk downloads (each year's release snapshot) — genuine vintages, but per-observation release dates are not served by the API | `has_release_dates=False`; archive ingestion possible future work |
| BIS | BIS Stats API serves latest data; no per-observation release date field | `has_release_dates=False` |
| OECD (SDMX) | Latest data only; revision history not exposed per observation | `has_release_dates=False` |
| IMF WEO | **Semi-annual WEO editions (April/October) are downloadable as distinct database snapshots** — the strongest genuine-vintage source; each edition IS a dated vintage | `has_release_dates=False`; edition-archive ingestion is the best recovery path |
| WID | Bulk CSV snapshots only; no release metadata | `has_release_dates=False` |
| FRED/ALFRED (market data, §16) | **ALFRED vintage dates are first-class API output** (`realtime_start`/`realtime_end`) — genuine revision evidence | New in Mission 5 market layer |

Conclusion: for macro series, `atlas_first_observed` is the evidence that
exists today and accrues going forward; IMF WEO edition archives are the
one recoverable historical-vintage source worth a future import.

## §7 — prospective collection

- Every `Observation` row carries `retrieved_at` (first-observed for its
  vintage) — set at insert, never backdated.
- `IngestionRun.run_metadata` records `content_sha256` of the fetched DTO
  batch + dto_count — a repeat fetch that yields the same checksum proves
  "unchanged since"; a different checksum with unchanged values is
  impossible (checksum covers period/value/unit/release_date).
- Revised values never overwrite: they become a new `vintage_number` row
  with its own `retrieved_at`, linked by `supersedes_observation_id`,
  plus an `IndicatorRevision` row.
- Repeatable command (manual or any scheduler — no paid service):

  ```
  python scripts/collect_snapshot.py                  # all live providers
  python scripts/collect_snapshot.py --source world_bank
  python scripts/collect_snapshot.py --wid-zip path/to/wid.zip  # adds WID
  ```

  WID is skipped unless `--wid-zip` is passed — it is a bulk-file provider
  (~882 MB archive), not a live API; `scripts/ingest_wid.py` refreshes it.

- API: `GET /api/research/countries/{iso3}/availability` reports
  `with_release_evidence`, `with_retrieval_evidence`, `first_observed_at`,
  `strict_eligible` per indicator; `GET /api/research/execution-modes`
  documents the evidence-type matrix.
