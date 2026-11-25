# Big Cycle Atlas — update: pull code, sync deps, migrate DB, rebuild frontend.
#   powershell -File scripts\ops\update.ps1
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repo
git pull --ff-only
Push-Location apps\api
uv sync --locked
uv run alembic upgrade head
Pop-Location
npm install
npm run build -w apps/web-astro
Pop-Location
Write-Host "Update complete: deps synced, DB migrated, frontend rebuilt." -ForegroundColor Green
