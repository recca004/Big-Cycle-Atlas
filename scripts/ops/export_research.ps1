# Big Cycle Atlas — export research evidence for independent analysis.
[CmdletBinding()]
param(
  [int]$FromYear = 1980
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$apiDir = Join-Path $repo "apps\api"
$py = Join-Path $apiDir ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
  throw "Python virtual environment not found at $py. Run apps\api setup first."
}

Push-Location $apiDir
try {
  & $py "scripts\export_research.py" --from-year $FromYear
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & $py "scripts\generate_theory_validation_report.py"
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & $py "scripts\generate_debt_cycle_report.py"
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & $py "scripts\build_review_package.py"
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
  Pop-Location
}

Write-Host "Research export written to $repo\.dev\reports" -ForegroundColor Green
