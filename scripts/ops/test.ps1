# Big Cycle Atlas — run all regression suites (Windows).
#   powershell -File scripts\ops\test.ps1 [-E2E]
param([switch]$E2E)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repo

Write-Host "== backend pytest ==" -ForegroundColor Cyan
Push-Location apps\api; uv run pytest tests/ -q; $rc1 = $LASTEXITCODE; Pop-Location
if ($rc1 -ne 0) { throw "backend tests failed" }

Write-Host "== astro check + vitest ==" -ForegroundColor Cyan
Push-Location apps\web-astro
npx astro check; if ($LASTEXITCODE -ne 0) { throw "astro check failed" }
npx vitest run; if ($LASTEXITCODE -ne 0) { throw "vitest failed" }
if ($E2E) { npx playwright test; if ($LASTEXITCODE -ne 0) { throw "e2e failed" } }
Pop-Location

Write-Host "All suites passed." -ForegroundColor Green
Pop-Location
