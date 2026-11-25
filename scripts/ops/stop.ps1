# Big Cycle Atlas — stop only processes this app started (Windows).
# Reads .run\*.pid files; verifies each process belongs to this repo
# before terminating. Never touches unrelated python/node processes.
$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$runDir = Join-Path $repo ".run"

$stopped = 0
foreach ($pidFile in (Get-ChildItem (Join-Path $runDir "*.pid") -ErrorAction SilentlyContinue)) {
  $pid_ = [int](Get-Content $pidFile.FullName)
  $proc = Get-Process -Id $pid_ -ErrorAction SilentlyContinue
  if ($proc) {
    # Safety: verify the process command line belongs to this repo before killing.
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$pid_" -ErrorAction SilentlyContinue).CommandLine
    $isWebWrapper = $proc.ProcessName -match "cmd" -and $pidFile.BaseName -eq "web"
    if (($cmd -and $cmd -like "*$repo*") -or $isWebWrapper) {
      taskkill /PID $pid_ /T /F 2>$null | Out-Null
      Write-Host "stopped $($pidFile.BaseName) (pid $pid_)"
      $stopped++
    } else {
      Write-Host "pid $pid_ exists but is NOT a Big Cycle Atlas process — leaving it alone" -ForegroundColor Yellow
    }
  }
  Remove-Item $pidFile.FullName -Force -ErrorAction SilentlyContinue
}
if ($stopped -eq 0) { Write-Host "Nothing running (no pid files / stale entries cleaned)." }
else { Write-Host "Stopped $stopped Big Cycle Atlas process tree(s)." -ForegroundColor Green }
