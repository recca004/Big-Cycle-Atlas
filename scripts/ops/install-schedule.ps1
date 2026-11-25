# Big Cycle Atlas — register Windows Task Scheduler jobs (Windows).
# DRY RUN by default — prints the plan. Registration requires -Approve
# (owner approval; nothing is scheduled silently).
#   powershell -File scripts\ops\install-schedule.ps1            # preview
#   powershell -File scripts\ops\install-schedule.ps1 -Approve   # register
#   powershell -File scripts\ops\install-schedule.ps1 -Remove    # unregister
param(
  [switch]$Approve,
  [switch]$Remove
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$py = Join-Path $repo "apps\api\.venv\Scripts\python.exe"
$apiDir = Join-Path $repo "apps\api"

# Job definitions. MultipleInstances=IgnoreNew prevents overlap.
$jobs = @(
  @{ Name = "BCA-MarketUpdate";  Time = "06:30"; Desc = "Incremental market data update (45d lookback)";
     Args = "scripts\ingest_markets.py --start $((Get-Date).AddDays(-45).ToString('yyyy-MM-dd'))" },
  @{ Name = "BCA-Snapshot";     Time = "06:00"; Desc = "Macro data snapshot collector (revisions tracked)";
     Args = "scripts\collect_snapshot.py" },
  @{ Name = "BCA-Backup";       Time = "02:00"; Desc = "pg_dump -Fc backup into .\backups\";
     Script = "scripts\ops\backup.ps1" },
  @{ Name = "BCA-HealthCheck";  Time = "12:00"; Desc = "DB counts + coverage sanity log";
     Args = "scripts\print_db_counts.py" }
)

if ($Remove) {
  foreach ($j in $jobs) { Unregister-ScheduledTask -TaskName $j.Name -Confirm:$false -ErrorAction SilentlyContinue }
  Write-Host "Removed BCA scheduled tasks." -ForegroundColor Green; exit 0
}

Write-Host "== Planned BCA scheduled tasks (daily, Europe/Zurich host time) ==" -ForegroundColor Cyan
foreach ($j in $jobs) { Write-Host ("  {0,-16} {1}  {2}" -f $j.Name, $j.Time, $j.Desc) }
Write-Host "WID bulk ingest stays manual (opt-in --wid-zip); overlap prevented (IgnoreNew)."

if (-not $Approve) {
  Write-Host "`nDry run only. Re-run with -Approve to register." -ForegroundColor Yellow; exit 0
}

foreach ($j in $jobs) {
  if ($j.Script) {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
      -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$repo\$($j.Script)`""
  } else {
    $action = New-ScheduledTaskAction -Execute $py -Argument $j.Args -WorkingDirectory $apiDir
  }
  $trigger = New-ScheduledTaskTrigger -Daily -At $j.Time
  $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable
  Register-ScheduledTask -TaskName $j.Name -Action $action -Trigger $trigger `
    -Settings $settings -Description "Big Cycle Atlas — $($j.Desc)" | Out-Null
  Write-Host "registered $($j.Name)"
}
Write-Host "Done. Manage in Task Scheduler (taskschd.msc)." -ForegroundColor Green
