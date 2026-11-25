# Big Cycle Atlas — native start (Windows).
# Dev mode:  API :8000 (reload) + Astro dev :3000.
# Prod mode: single uvicorn process on :8000 serving API + built frontend.
#   powershell -File scripts\ops\start.ps1 [-Mode dev|prod] [-NoBrowser]
param(
  [ValidateSet("dev","prod")][string]$Mode = "dev",
  [switch]$NoBrowser
)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$runDir = Join-Path $repo ".run"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

function Fail([string]$msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }
function Get-PidFile([string]$name) {
  $f = Join-Path $runDir "$name.pid"
  if (Test-Path $f) {
    $pid_ = [int](Get-Content $f)
    if (Get-Process -Id $pid_ -ErrorAction SilentlyContinue) { return $pid_ }
    Remove-Item $f -Force
  }
  return $null
}
function Test-PortBusy([int]$port) {
  return [bool](Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
}
function Wait-Http([string]$url, [int]$sec = 40) {
  $deadline = (Get-Date).AddSeconds($sec)
  while ((Get-Date) -lt $deadline) {
    try { Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 | Out-Null; return $true }
    catch { Start-Sleep -Milliseconds 700 }
  }
  return $false
}

Write-Host "== Big Cycle Atlas ($Mode mode) ==" -ForegroundColor Cyan

# --- 1. Duplicate-instance guard ---
if (Get-PidFile "api") { Fail "API already running (pid file .run\api.pid). Run Stop.bat first." }
if (Get-PidFile "web") { Fail "Web already running (pid file .run\web.pid). Run Stop.bat first." }

# --- 2. Dependency check ---
foreach ($tool in "node","npm") {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { Fail "$tool not on PATH — run Setup.bat" }
}
$py = Join-Path $repo "apps\api\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Fail "API venv missing ($py) — run Setup.bat" }

# --- 3. Configuration validation ---
$envFile = Join-Path $repo "apps\api\.env"
if (Test-Path $envFile) {
  $urls = (Get-Content $envFile | Where-Object { $_ -match "^DATABASE_URL=" })
  if ($urls.Count -gt 1) { Fail "apps/api/.env has multiple DATABASE_URL lines (last wins)" }
}

# --- 4. PostgreSQL connectivity ---
Push-Location (Join-Path $repo "apps\api")
& $py -c "import sys;sys.path.insert(0,'.');from app.core.config import get_settings;import psycopg;u=get_settings().database_url.replace('postgresql+psycopg://','postgresql://');psycopg.connect(u,connect_timeout=5).close()" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Pop-Location; Fail "Cannot connect to PostgreSQL — check DATABASE_URL in apps/api/.env and that the server is up" }
Pop-Location
Write-Host "PostgreSQL: connected"

# --- 5. Port checks ---
if (Test-PortBusy 8000) { Fail "Port 8000 already in use by another process" }
$webPort = 3000
if ($Mode -eq "dev" -and (Test-PortBusy $webPort)) { Fail "Port $webPort already in use by another process" }

# --- 6. Start API ---
$apiEntry = if ($Mode -eq "prod") { "serve.py" } else { "run.py" }
$apiProc = Start-Process -FilePath $py -ArgumentList $apiEntry `
  -WorkingDirectory (Join-Path $repo "apps\api") -PassThru -WindowStyle Hidden
"$($apiProc.Id)" | Out-File (Join-Path $runDir "api.pid") -Encoding ascii
Write-Host "API starting (pid $($apiProc.Id), $apiEntry) ..."

if (-not (Wait-Http "http://127.0.0.1:8000/health")) {
  & $PSCommandPath -ErrorAction SilentlyContinue | Out-Null
  Stop-Process -Id $apiProc.Id -Force -ErrorAction SilentlyContinue
  Remove-Item (Join-Path $runDir "api.pid") -Force -ErrorAction SilentlyContinue
  Fail "API did not become healthy within 40s — check apps/api logs"
}
Write-Host "API healthy on http://127.0.0.1:8000"

# --- 7. Start web (dev only; prod is served by the API) ---
$appUrl = "http://localhost:8000"
if ($Mode -eq "dev") {
  $webProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c","npm run dev -w apps/web-astro -- --host 127.0.0.1 --port 3000" `
    -WorkingDirectory $repo -PassThru -WindowStyle Hidden
  "$($webProc.Id)" | Out-File (Join-Path $runDir "web.pid") -Encoding ascii
  Write-Host "Web dev server starting (pid $($webProc.Id)) ..."
  if (-not (Wait-Http "http://localhost:3000")) {
    taskkill /PID $webProc.Id /T /F | Out-Null
    Stop-Process -Id $apiProc.Id -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $runDir "*.pid") -Force -ErrorAction SilentlyContinue
    Fail "Astro dev server did not start within 40s"
  }
  $appUrl = "http://localhost:3000"
  Write-Host "Web dev server on $appUrl"
} else {
  $dist = Join-Path $repo "apps\web-astro\dist"
  if (-not (Test-Path (Join-Path $dist "index.html"))) {
    Stop-Process -Id $apiProc.Id -Force; Remove-Item (Join-Path $runDir "api.pid") -Force
    Fail "Production build missing (apps/web-astro/dist) — run Update.bat or 'npm run build' first"
  }
  Write-Host "Prod build served by the API at $appUrl"
}

# --- 8. Open browser ---
if (-not $NoBrowser) { Start-Process $appUrl }
Write-Host "Big Cycle Atlas running ($Mode): $appUrl" -ForegroundColor Green
Write-Host "Stop with Stop.bat"
