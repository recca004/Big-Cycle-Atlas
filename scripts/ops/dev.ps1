# Big Cycle Atlas — start local development services (Windows).
# API on :8000 + Astro dev on :3000, each in its own window.
#   powershell -File scripts\ops\dev.ps1
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")

$api = "cd '$repo\apps\api'; uv run python run.py"
$web = "cd '$repo'; npm run dev -w apps/web-astro"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $api
Start-Process powershell -ArgumentList "-NoExit", "-Command", $web
Write-Host "Started API (:8000) and web (:3000) in separate windows."
Write-Host "App: http://localhost:3000  ·  API docs: http://localhost:8000/docs"
