# Data collection

## Sources

10 adapters: World Bank, IMF WEO, BIS, OECD (incl. education), FRED,
WGI-derived, WID.world (bulk ZIP), market feeds, reference universes.

## Manual runs (from `apps/api`)

```powershell
uv run python scripts/collect_snapshot.py     # all live sources, revision-tracked
uv run python scripts/ingest_markets.py       # market data (add --start for incremental)
uv run python scripts/ingest_world_bank.py    # single source
uv run python scripts/print_db_counts.py      # sanity counts
```

`collect_snapshot.py` stores vintage metadata: NEW vs REVISED observations
are tracked in `indicator_revisions`/`ingestion_runs`. WID needs the ~880MB
bulk ZIP and is opt-in: `collect_snapshot.py --wid-zip <path>`.

## Scheduled collection (opt-in)

- Windows: `scripts/ops/install-schedule.ps1 -Approve` — Task Scheduler,
  daily 06:00 snapshot / 06:30 markets / 02:00 backup / 12:00 health,
  `IgnoreNew` overlap guard.
- Linux: systemd timers `bca-snapshot`, `bca-market-update`, `bca-backup`
  (Type=oneshot; disabled until enabled).
- Docker alternative: `docker compose --profile scheduled up -d` runs
  `scripts/collect_daemon.py` with a lockfile guard.

No schedule activates without explicit approval.

## Freshness & availability

Force scores expose "as-of" availability metadata (`first_observed_at`,
`with_retrieval_evidence`) — the historical-validation widget shows what
was knowable at each point in time. See `.dev/` mission reports for the
evidence gates.
