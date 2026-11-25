# Big Cycle Atlas — post-restore integrity check (Windows).
#   powershell -File scripts\ops\verify-restore.ps1 -TargetUrl postgresql://.../bca_restore_test
param([Parameter(Mandatory=$true)][string]$TargetUrl)

$ErrorActionPreference = "Stop"
$sql = @"
SELECT 'alembic=' || COALESCE((SELECT version_num FROM alembic_version), 'none');
SELECT 'countries=' || count(*) FROM countries;
SELECT 'indicators=' || count(*) FROM indicators;
SELECT 'observations=' || count(*) FROM observations;
SELECT 'ref_observations=' || count(*) FROM reference_observations;
SELECT 'market_instruments=' || count(*) FROM market_instruments;
SELECT 'market_observations=' || count(*) FROM market_observations;
SELECT 'ingestion_runs=' || count(*) FROM ingestion_runs;
SELECT 'paper_portfolios=' || count(*) FROM paper_portfolios;
SELECT 'paper_transactions=' || count(*) FROM paper_transactions;
SELECT 'watchlist=' || count(*) FROM watchlist_entries;
"@
$sql | psql $TargetUrl -At
