# Big Cycle Atlas — first-time environment setup + validation (Windows).
# Checks tools, installs deps, applies migrations, seeds the catalog.
#   powershell -File scripts\ops\setup.ps1
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repo

Write-Host "== Big Cycle Atlas setup ==" -ForegroundColor Cyan

# 1. Tools
$missing = @()
foreach ($tool in "uv", "node", "npm") {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { $missing += $tool }
}
if ($missing) { throw "Missing tools: $($missing -join ', ')" }
Write-Host "tools ok: uv, node, npm"

# 2. API deps + env
Push-Location apps\api
if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host "created apps/api/.env from example — review DATABASE_URL" -ForegroundColor Yellow
}
uv sync --locked
Write-Host "api deps synced"

# 3. Database: migrations + seed (idempotent)
uv run alembic upgrade head
uv run python -m app.db.seed
Write-Host "database migrated + catalog seeded"
Pop-Location

# 4. Web deps
npm ci --workspace=@big-cycle-atlas/web-astro --workspace=@big-cycle-atlas/shared
Write-Host "web deps installed"

Write-Host "`nSetup complete. Start dev: scripts\ops\dev.ps1" -ForegroundColor Green
Pop-Location
