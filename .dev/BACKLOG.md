# Backlog

## Now

- Install Docker Desktop and verify the Postgres path end-to-end (see ISSUE-001)
- Owner approval of Milestone 1

## Next

- Milestone 2: data model + indicator system (data_sources, indicators, observations, indicator_revisions tables; ingestion run records)
- Milestone 3: World Bank connector (first real data source adapter)
- Decide on font licensing: Suisse Intl vs free alternative (Inter or similar)

## Later

- Milestone 4: BIS, OECD, FRED, Eurostat, ECB, SNB, Comtrade connectors
- Milestone 5: 17-force calculation engine
- Milestone 6: Big Cycle stage calculation
- Milestone 7: historical charts (ECharts) and /compare
- Milestone 8: forecast model (probability windows)
- Milestone 9: historical validation with release-date discipline
- Milestone 10: market regime engine
- Milestone 11: backtester
- Milestone 12: paper trading

## Ideas

- Admin data-health page driven by ingestion_runs
- Model version changelog surfaced on /methodology
- TimescaleDB hypertables for observations if query performance requires it