# Big Cycle Atlas — register Windows Task Scheduler jobs (Windows).
# DRY RUN by default — prints the plan. Registration requires -Approve
# (owner approval; nothing is scheduled silently).
#   powershell -File scripts\ops\install-schedule.ps1            # preview
#   powershell -File scripts\ops\install-schedule.ps1 -Approve   # register
#   powershell -File scripts\ops\install-schedule.ps1 -Remove    # unregister
param(
  [switch]$Approve,
  [switch]$Remove,
  [switch]$Disable,
  [switch]$Enable
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$py = Join-Path $repo "apps\api\.venv\Scripts\python.exe"
$apiDir = Join-Path $repo "apps\api"

# Scheduled data jobs reuse the same lock, logging, modes and exit codes as
# Update.bat. MultipleInstances=IgnoreNew provides a second overlap guard.
$jobs = @(
  @{ Name = "BCA-Snapshot";     Time = "06:00"; Desc = "Unified daily data update + Observatory refresh";
     Script = "scripts\ops\update.ps1" },
  @{ Name = "BCA-MarketUpdate"; Time = "18:30"; Desc = "Unified financial-market-only update";
     Script = "scripts\ops\update.ps1"; Args = "-MarketsOnly" },
  @{ Name = "BCA-Backup";       Time = "02:00"; Desc = "pg_dump -Fc backup into .\backups\";
     Script = "scripts\ops\backup.ps1" },
  @{ Name = "BCA-HealthCheck";  Time = "12:00"; Desc = "DB counts + coverage sanity log";
     Command = "scripts\print_db_counts.py" }
)

if ($Remove) {
  foreach ($j in $jobs) { Unregister-ScheduledTask -TaskName $j.Name -Confirm:$false -ErrorAction SilentlyContinue }
  Write-Host "Removed BCA scheduled tasks." -ForegroundColor Green; exit 0
}
if ($Disable) {
  foreach ($j in $jobs) { Disable-ScheduledTask -TaskName $j.Name -ErrorAction SilentlyContinue | Out-Null }
  Write-Host "Disabled BCA scheduled tasks." -ForegroundColor Green; exit 0
}
if ($Enable) {
  foreach ($j in $jobs) { Enable-ScheduledTask -TaskName $j.Name -ErrorAction SilentlyContinue | Out-Null }
  Write-Host "Enabled BCA scheduled tasks." -ForegroundColor Green; exit 0
}

Write-Host "== Planned BCA scheduled tasks (daily, Europe/Zurich host time) ==" -ForegroundColor Cyan
foreach ($j in $jobs) { Write-Host ("  {0,-16} {1}  {2}" -f $j.Name, $j.Time, $j.Desc) }
Write-Host "WID bulk ingest stays manual (Update.bat -Full -WidZip <path>)."
Write-Host "Overlaps are prevented by the shared update lock and IgnoreNew."

if (-not $Approve) {
  Write-Host "`nDry run only. Re-run with -Approve to register." -ForegroundColor Yellow; exit 0
}

foreach ($j in $jobs) {
  if ($j.Command) {
    $action = New-ScheduledTaskAction -Execute $py -Argument $j.Command -WorkingDirectory $apiDir
  } else {
    $argText = "-NoProfile -ExecutionPolicy Bypass -File `"$repo\$($j.Script)`""
    if ($j.Args) { $argText += " $($j.Args)" }
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argText
  }
  $trigger = New-ScheduledTaskTrigger -Daily -At $j.Time
  $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable
  Register-ScheduledTask -TaskName $j.Name -Action $action -Trigger $trigger `
    -Settings $settings -Description "Big Cycle Atlas — $($j.Desc)" -Force | Out-Null
  Write-Host "registered $($j.Name)"
}
Write-Host "Done. Review with Get-ScheduledTask -TaskName 'BCA-*'." -ForegroundColor Green
