# Big Cycle Atlas — update DATA (Windows).
# Refreshes economic/market observations from source providers.
# Does NOT touch application code — use Upgrade.bat for that.
#   powershell -File scripts\ops\update.ps1 [-SkipMarkets]
param([switch]$SkipMarkets)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$py = Join-Path $repo "apps\api\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "API venv missing — run Setup.bat first" }

Push-Location (Join-Path $repo "apps\api")
Write-Host "== Macro/economic snapshot (all sources, revision-tracked) ==" -ForegroundColor Cyan
& $py scripts\collect_snapshot.py
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Snapshot collection failed ($LASTEXITCODE)" }
if (-not $SkipMarkets) {
  Write-Host "== Incremental market update (45d lookback) ==" -ForegroundColor Cyan
  & $py scripts\ingest_markets.py --start (Get-Date).AddDays(-45).ToString('yyyy-MM-dd')
  if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Market update failed ($LASTEXITCODE)" }
}
& $py scripts\print_db_counts.py
Pop-Location
Write-Host "Data update complete." -ForegroundColor Green
