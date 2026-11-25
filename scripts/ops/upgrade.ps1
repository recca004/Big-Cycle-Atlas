# Big Cycle Atlas — upgrade APPLICATION CODE (Windows).
# git pull -> dep sync -> migrations (backup-gated) -> frontend rebuild.
# Does NOT touch data. Safe by design: refuses dirty trees and unsafe
# operations, and requires a fresh backup before running migrations.
#   powershell -File scripts\ops\upgrade.ps1 [-SkipBackup]
param([switch]$SkipBackup)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repo

Write-Host "== Big Cycle Atlas upgrade ==" -ForegroundColor Cyan

# 1. Branch + tree safety
$branch = git rev-parse --abbrev-ref HEAD
if ($branch -notin @("main","feature/big-cycle-atlas-astro-v2")) {
  Write-Host "WARNING: on branch '$branch' — expected main or the release branch." -ForegroundColor Yellow
}
$dirty = git status --porcelain
if ($dirty) {
  Pop-Location
  throw "Uncommitted changes present ($($dirty.Count) files). Commit or stash first — upgrade will not touch them."
}

# 2. Database protection — never drop/recreate; require fresh backup before migrations
if (-not $SkipBackup) {
  Write-Host "Taking a pre-migration backup (required) ..."
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "scripts\ops\backup.ps1")
  if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Backup failed — refusing to run migrations" }
} else {
  Write-Host "WARNING: -SkipBackup set — migrations run without a fresh backup" -ForegroundColor Yellow
}

# 3. Pull code (fast-forward only — never resets or rebases)
git pull --ff-only
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "git pull --ff-only failed (local divergence?) — resolve manually" }

# 4. Dependencies
Push-Location apps\api
uv sync --locked
if ($LASTEXITCODE -ne 0) { Pop-Location; Pop-Location; throw "uv sync failed" }
Pop-Location
npm install
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "npm install failed" }

# 5. Migrations — forward-only alembic; failure is reported, never auto-fixed
Push-Location apps\api
uv run alembic upgrade head
$migRc = $LASTEXITCODE
Pop-Location
if ($migRc -ne 0) {
  Pop-Location
  throw "alembic upgrade head FAILED ($migRc). Database left as-is — restore the backup taken above if needed (Restore.bat)."
}

# 6. Frontend rebuild
npm run build -w apps/web-astro
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "frontend build failed" }

Pop-Location
Write-Host "Upgrade complete: code updated, deps synced, migrations applied, frontend rebuilt." -ForegroundColor Green
