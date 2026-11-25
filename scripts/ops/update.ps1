# Big Cycle Atlas — unified DATA update (native Windows).
# Refreshes provider observations, reference universes, markets and the
# Observatory. Application code upgrades remain in Upgrade.bat.
#
# Exit codes: 0 = complete success, 2 = partial provider/source failure,
#             1 = fatal configuration, database, lock or command failure.
[CmdletBinding(PositionalBinding = $false)]
param(
  [switch]$Full,
  [switch]$MacroOnly,
  [switch]$MarketsOnly,
  [switch]$ReferencesOnly,
  [switch]$RecalculateOnly,
  [switch]$Status,
  [switch]$DryRun,
  [switch]$Help,
  [switch]$SkipMarkets,
  [string]$Source,
  [string]$Country,
  [string]$WidZip,
  [int]$MarketLookbackDays = 45
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$apiDir = Join-Path $repo "apps\api"
$py = Join-Path $apiDir ".venv\Scripts\python.exe"
$logDir = Join-Path $repo ".run\updates"
$lockPath = Join-Path $env:TEMP "big-cycle-atlas\update.lock"
$lockToken = [guid]::NewGuid().ToString("N")
$runId = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss") + "-" + $lockToken.Substring(0, 8)
$logFile = Join-Path $logDir "update-$runId.log"
$script:HadPartialFailure = $false
$script:LockHeld = $false
$script:CompletedSteps = New-Object System.Collections.Generic.List[string]
$script:FailedSteps = New-Object System.Collections.Generic.List[string]
$script:SkippedSteps = New-Object System.Collections.Generic.List[string]

function Write-Run([string]$Message, [string]$Color = "Gray") {
  $line = "[{0}] {1}" -f (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss'Z'"), $Message
  if ($Color) { Write-Host $line -ForegroundColor $Color } else { Write-Host $line }
  if ($script:LogReady) { Add-Content -Path $logFile -Value $line -Encoding UTF8 }
}

function Show-Help {
  @'
Big Cycle Atlas data update commands

  Update.bat                    Standard daily update (macro + markets + recalculation)
  Update.bat -Full              Daily update + reference universes + optional WID archive
  Update.bat -MacroOnly         Economic providers only
  Update.bat -MarketsOnly       Financial market and currency observations only
  Update.bat -ReferencesOnly    Reference population distributions only
  Update.bat -RecalculateOnly   Observatory recalculation without provider downloads
  Update.bat -Status            Database totals, provider freshness and lock status
  Update.bat -DryRun            Print planned operations without modifying data
  Update.bat -Help              Show this help

Options
  -Source <provider>            world_bank, bis, oecd, imf_weo, or wid (with -WidZip)
  -Country <ISO3>               Limit provider collection to one tracked country
  -WidZip <path>                Use a locally downloaded WID bulk ZIP; never auto-downloads
  -MarketLookbackDays <n>       Incremental market lookback (default: 45)
  -SkipMarkets                  Existing compatibility option; skips market ingestion

Exit codes: 0 success, 2 partial provider/source failure, 1 fatal failure.
Logs are written to .run\updates (not tracked by Git).
'@ | Write-Host
}

function Get-DatabaseName {
  $envFile = Join-Path $apiDir ".env"
  $databaseUrl = $null
  if (Test-Path $envFile) {
    $line = Get-Content $envFile | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -Last 1
    if ($line) { $databaseUrl = $line.Substring($line.IndexOf('=') + 1) }
  }
  if (-not $databaseUrl) { $databaseUrl = "postgresql+psycopg://localhost:5432/bigcycleatlas" }
  $withoutQuery = ($databaseUrl -split '\?')[0]
  return ($withoutQuery.TrimEnd('/') -split '/')[-1]
}

function Get-AppVersion {
  $config = Join-Path $apiDir "app\core\config.py"
  $match = Select-String -Path $config -Pattern 'app_version:\s*str\s*=\s*"([^"]+)"' | Select-Object -First 1
  if ($match) { return $match.Matches[0].Groups[1].Value }
  return "unknown"
}

function Test-LockOwnerRunning($Payload) {
  try { $null = Get-Process -Id ([int]$Payload.pid) -ErrorAction Stop; return $true }
  catch { return $false }
}

function Enter-UpdateLock {
  New-Item -ItemType Directory -Force -Path (Split-Path $lockPath) | Out-Null
  if (Test-Path $lockPath) {
    try { $payload = Get-Content $lockPath -Raw | ConvertFrom-Json } catch { $payload = $null }
    if ($payload -and (Test-LockOwnerRunning $payload)) {
      throw "Another Big Cycle Atlas update is already running: $($payload.owner) (PID $($payload.pid), started $($payload.started_at))"
    }
    Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
  }
  $payload = [ordered]@{
    owner = "terminal-update"
    pid = $PID
    token = $lockToken
    started_at = (Get-Date).ToUniversalTime().ToString("o")
  }
  $json = $payload | ConvertTo-Json -Compress
  try {
    $fs = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $fs.Write($bytes, 0, $bytes.Length)
    $fs.Dispose()
  } catch [System.IO.IOException] {
    throw "Another Big Cycle Atlas update acquired the update lock."
  }
  $env:BCA_UPDATE_LOCK_TOKEN = $lockToken
  $env:BCA_UPDATE_LOCK_PATH = $lockPath
  $script:LockHeld = $true
}

function Exit-UpdateLock {
  if (-not $script:LockHeld) { return }
  Remove-Item $env:BCA_UPDATE_LOCK_TOKEN -ErrorAction SilentlyContinue
  Remove-Item $env:BCA_UPDATE_LOCK_PATH -ErrorAction SilentlyContinue
  Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
  $script:LockHeld = $false
}

function Invoke-Step([string]$Name, [string[]]$Arguments, [int[]]$PartialCodes = @()) {
  Write-Run "START  $Name :: python $($Arguments -join ' ')" "Cyan"
  $output = & $py @Arguments 2>&1
  $code = $LASTEXITCODE
  foreach ($line in $output) { Write-Run "  $line" }
  if ($code -eq 0) {
    $script:CompletedSteps.Add($Name) | Out-Null
    Write-Run "OK     $Name" "Green"
    return $true
  }
  if ($PartialCodes -contains $code) {
    $script:HadPartialFailure = $true
    $script:FailedSteps.Add("$Name (partial exit $code)") | Out-Null
    Write-Run "PARTIAL $Name exited $code; continuing independent sources" "Yellow"
    return $false
  }
  throw "$Name failed fatally with exit code $code"
}

function Show-Plan($Steps) {
  Write-Host "Planned operations:" -ForegroundColor Cyan
  foreach ($step in $Steps) { Write-Host "  - $step" }
  Write-Host "Dry run: no provider requests, writes, lock acquisition or recalculation performed." -ForegroundColor Yellow
}

function Show-Status {
  Push-Location $apiDir
  try {
    & $py scripts\print_db_counts.py
    $stateFile = Join-Path $repo ".run\observatory\refresh_state.json"
    if (Test-Path $stateFile) {
      Write-Host "`nObservatory refresh state:" -ForegroundColor Cyan
      Get-Content $stateFile -Raw
    } else {
      Write-Host "`nObservatory refresh state: none recorded yet" -ForegroundColor Yellow
    }
    if (Test-Path $lockPath) {
      Write-Host "`nUpdate lock:" -ForegroundColor Cyan
      Get-Content $lockPath -Raw
    } else {
      Write-Host "`nUpdate lock: free" -ForegroundColor Cyan
    }
    Write-Host "`nScheduled tasks:" -ForegroundColor Cyan
    Get-ScheduledTask -TaskName "BCA-*" -ErrorAction SilentlyContinue |
      Select-Object TaskName, State | Format-Table -AutoSize
  } finally { Pop-Location }
}

$modeCount = @($Full, $MacroOnly, $MarketsOnly, $ReferencesOnly, $RecalculateOnly, $Status, $Help).Where({ $_ }).Count
if ($modeCount -gt 1) { Write-Host "Incompatible options: choose only one update mode." -ForegroundColor Red; exit 1 }
if ($DryRun -and ($Status -or $Help)) { Write-Host "Incompatible options: -DryRun cannot be combined with -Status or -Help." -ForegroundColor Red; exit 1 }
if ($Help) { Show-Help; exit 0 }
if ($Status) { Show-Status; exit 0 }
if ($SkipMarkets -and $MarketsOnly) { Write-Host "Incompatible options: -SkipMarkets cannot be used with -MarketsOnly." -ForegroundColor Red; exit 1 }
if ($WidZip -and -not (Test-Path $WidZip)) { Write-Host "WID archive not found: $WidZip" -ForegroundColor Red; exit 1 }
if ($Source -and $Source -notin @("world_bank", "bis", "oecd", "imf_weo", "wid")) { Write-Host "Unknown provider source: $Source" -ForegroundColor Red; exit 1 }
if ($Source -eq "wid" -and -not $WidZip) { Write-Host "-Source wid requires -WidZip (WID never auto-downloads)." -ForegroundColor Red; exit 1 }
if (-not (Test-Path $py)) { Write-Host "API venv missing — run Setup.bat first" -ForegroundColor Red; exit 1 }

$mode = "daily"
if ($Full) { $mode = "full" }
if ($MacroOnly) { $mode = "macro-only" }
if ($MarketsOnly) { $mode = "markets-only" }
if ($ReferencesOnly) { $mode = "references-only" }
if ($RecalculateOnly) { $mode = "recalculate-only" }

$collectionSummaryPath = Join-Path $logDir "collection-summary-$runId.json"
$collectArgs = @("scripts\collect_snapshot.py", "--summary-json", $collectionSummaryPath)
if ($Source) { $collectArgs += @("--source", $Source) }
if ($Country) { $collectArgs += @("--country", $Country.ToUpperInvariant()) }
if ($WidZip) { $collectArgs += @("--wid-zip", (Resolve-Path $WidZip).Path) }
$marketArgs = @("scripts\ingest_markets.py", "--start", (Get-Date).AddDays(-$MarketLookbackDays).ToString("yyyy-MM-dd"))
$refreshArgs = @("scripts\refresh_observatory.py")
if ($mode -in @("daily", "full", "macro-only")) {
  $refreshArgs += @("--collection-summary", $collectionSummaryPath)
}
$referenceSteps = @(
  @{ Name = "World Bank labour participation reference"; Args = @("scripts\ingest_wb_reference.py", "wdi_lfp_v1") },
  @{ Name = "OECD labour productivity reference"; Args = @("scripts\ingest_oecd_reference.py", "--universe", "oecd_lpph_v1") }
)
$widArgs = @("scripts\ingest_wid.py", "--all-countries", "--all-mapped", "--zip-path")
if ($WidZip) { $widArgs += (Resolve-Path $WidZip).Path }

$steps = switch ($mode) {
  "daily" {
    @("Provider snapshot collection", "Incremental market update ($MarketLookbackDays days)", "Observatory recalculation and snapshot diff")
  }
  "full" {
    @("Provider snapshot collection", "Reference universes (WB + OECD)", "Incremental market update ($MarketLookbackDays days)", "WID local archive if supplied", "Observatory recalculation and snapshot diff")
  }
  "macro-only" { @("Provider snapshot collection", "Observatory recalculation and snapshot diff") }
  "markets-only" { @("Incremental market update ($MarketLookbackDays days)", "Observatory recalculation and snapshot diff") }
  "references-only" { @("Reference universes (WB + OECD)", "Observatory recalculation and snapshot diff") }
  "recalculate-only" { @("Observatory recalculation and snapshot diff") }
}
if ($SkipMarkets) { $steps = $steps | Where-Object { $_ -notmatch "market" }; $steps += "Market update skipped" }
if (-not $WidZip) { $steps += "WID skipped (local ZIP not supplied)" }

Write-Host ""
Write-Host "Big Cycle Atlas $(Get-AppVersion)" -ForegroundColor Magenta
Write-Host "Database : $(Get-DatabaseName)"
Write-Host "Mode     : $mode$(if ($DryRun) { ' (dry run)' })"
Write-Host "Started  : $((Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss''Z''')) UTC / $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) local"
Write-Host "Run ID   : $runId"
Write-Host ""
if ($DryRun) { Show-Plan $steps; exit 0 }

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$script:LogReady = $true
Write-Run "run_id=$runId mode=$mode database=$(Get-DatabaseName)"
try {
  Enter-UpdateLock
  Push-Location $apiDir
  try {
    if ($mode -in @("daily", "full", "macro-only")) {
      Invoke-Step "Provider snapshot collection" $collectArgs @(2) | Out-Null
      if (-not $WidZip -and ($mode -eq "full" -or $Source -eq "wid")) {
        $script:SkippedSteps.Add("WID (no local ZIP supplied)") | Out-Null
        Write-Run "SKIP   WID bulk provider — pass -WidZip to enable it" "Yellow"
      }
    }
    if (($mode -eq "full" -or $mode -eq "references-only") -and -not $Source -and -not $Country) {
      foreach ($ref in $referenceSteps) { Invoke-Step $ref.Name $ref.Args @(2) | Out-Null }
    }
    if (($mode -in @("daily", "full", "markets-only")) -and -not $SkipMarkets) {
      Invoke-Step "Financial market update" $marketArgs @(2) | Out-Null
    }
    if ($mode -eq "full" -and $WidZip) {
      Invoke-Step "WID local archive import" $widArgs @(2) | Out-Null
    }
    Invoke-Step "Observatory recalculation and snapshot diff" $refreshArgs @(2) | Out-Null
    Invoke-Step "Final database totals" @("scripts\print_db_counts.py") @() | Out-Null
  } finally { Pop-Location }

  $finalStatus = if ($script:HadPartialFailure) { "partial" } else { "success" }
  $summaryColor = "Green"
  if ($script:HadPartialFailure) { $summaryColor = "Yellow" }
  Write-Run "SUMMARY mode=$mode status=$finalStatus completed=$($script:CompletedSteps -join '; ')" $summaryColor
  if ($script:SkippedSteps.Count) { Write-Run "SKIPPED $($script:SkippedSteps -join '; ')" "Yellow" }
  if ($script:FailedSteps.Count) { Write-Run "PARTIAL FAILURES $($script:FailedSteps -join '; ')" "Yellow" }
  Write-Run "log=$logFile"
  if ($script:HadPartialFailure) { exit 2 }
  Write-Host "Data update complete." -ForegroundColor Green
  exit 0
} catch {
  Write-Run "FATAL $($_.Exception.Message)" "Red"
  if ($_.InvocationInfo) { Write-Run "AT line $($_.InvocationInfo.ScriptLineNumber): $($_.InvocationInfo.Line.Trim())" "Red" }
  Write-Run "log=$logFile"
  exit 1
} finally {
  Exit-UpdateLock
}
