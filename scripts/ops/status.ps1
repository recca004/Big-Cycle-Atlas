# Big Cycle Atlas — status report (Windows).
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$runDir = Join-Path $repo ".run"
Write-Host "== Big Cycle Atlas status ==" -ForegroundColor Cyan
foreach ($name in "api","web") {
  $f = Join-Path $runDir "$name.pid"
  if ((Test-Path $f) -and (Get-Process -Id ([int](Get-Content $f)) -ErrorAction SilentlyContinue)) {
    Write-Host "${name}: RUNNING (pid $(Get-Content $f))"
  } else { Write-Host "${name}: stopped" }
}
foreach ($check in @(@("API health","http://127.0.0.1:8000/health"),@("Web dev","http://localhost:3000"))) {
  try { Invoke-WebRequest -Uri $check[1] -UseBasicParsing -TimeoutSec 3 | Out-Null; Write-Host "$($check[0]): OK ($($check[1]))" }
  catch { Write-Host "$($check[0]): unreachable ($($check[1]))" }
}
