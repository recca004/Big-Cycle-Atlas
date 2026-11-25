# Big Cycle Atlas v1.0.0-rc.1 — release notes

First release candidate. Native Windows is the primary supported
deployment; Linux systemd instructions provided (unverified on host);
Docker is an optional alternative only.

## What's in the release

- **Research surface**: country pages (economy/trade/debt/governance),
  17-force scores with model-version labels, country comparison, Big Cycle
  explorer, data explorer, sources/methodology/progress pages.
- **Workspace**: composable widget dashboard (charts, rankings, historical
  validation, watchlist) with drag/resize, persistence, undo.
- **Markets & strategies**: market regime explorer, strategy lab and
  simulation, forecast readiness.
- **Portfolio**: paper portfolios with transaction ledger (cash/positions/
  realised-P&L validation, FX conversion, row-locked concurrency).
- **Search**: Ctrl/Cmd+K palette over countries/indicators/instruments/forces.
- **Settings**: versioned local preferences (theme, transparency, motion,
  default country/currency) with pre-paint resolution.
- **Ingestion**: 10 data sources, revision-tracked snapshots, incremental
  market updates, WID bulk opt-in.

## Deployment

- `Start.bat` / `Start-Prod.bat` / `Stop.bat` / `Status.bat` launchers;
  `Setup.bat`/`Update.bat` lifecycle; `Backup.bat`/`Restore.bat` drills;
  `Test.bat` regression runner.
- Production = one process: `apps/api/serve.py` serves API + built frontend
  on 127.0.0.1:8000. No dev server, no Docker, no extra web server.
- Scheduled collection via Task Scheduler installer (approval-gated) or
  systemd timers on Linux.
- See `docs/DEPLOYMENT.md`, `docs/OWNER_GUIDE.md`, `docs/SECURITY.md`.

## Verification

- 798 backend + 43 vitest + 44 Playwright (incl. a11y) tests pass;
  `astro check` 0 errors; 37-page prod build.
- Backup→restore drill: all 14 table counts + representative aggregates
  identical; API verified against restored DB.
- Dep audits clean; launchers verified including stale-PID, busy-port,
  missing-config, and duplicate-instance cases.

## Known limitations

- No authentication/multi-user — loopback only or behind your own proxy.
- Linux/Proxmox instructions not run on a live host; Docker path unverified
  (engine unavailable during testing).
- Force model `normalization-v0.8`/`force-aggregation-v0.3` is a documented
  experimental methodology, not a validated forecast — labels are preserved
  in the UI.
- WID.world needs a manual bulk ZIP download.
- ~455 pre-existing ruff findings in legacy `apps/api/scripts/` diagnostics.
