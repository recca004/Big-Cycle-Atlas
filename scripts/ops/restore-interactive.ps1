# Big Cycle Atlas — interactive restore with explicit confirmation (Windows).
#   powershell -File scripts\ops\restore-interactive.ps1 [-File <dump>]
param([string]$File)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$backupDir = Join-Path $repo "backups"
if (-not $File) {
  $dumps = Get-ChildItem (Join-Path $backupDir "*.dump") -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
  if (-not $dumps) { throw "No backups found in $backupDir" }
  Write-Host "Available backups:"
  for ($i=0; $i -lt [Math]::Min($dumps.Count,10); $i++) { Write-Host "  [$i] $($dumps[$i].Name)  ($([math]::Round($dumps[$i].Length/1MB,1)) MB)" }
  $File = $dumps[[int](Read-Host "Select index")].FullName
}
$envFile = Join-Path $repo "apps\api\.env"
$dsn = $env:DATABASE_URL
if (Test-Path $envFile) {
  Get-Content $envFile | Where-Object { $_ -match "^DATABASE_URL=" } | Select-Object -First 1 | ForEach-Object {
    $dsn = $_.Split("=",2)[1].Trim().Trim('"')
  }
}
$dsn = $dsn -replace "postgresql\+psycopg://","postgresql://"
Write-Host "`nThis will OVERWRITE the database at:`n  $dsn`nwith:`n  $File`n" -ForegroundColor Yellow
$confirm = Read-Host "Type RESTORE to continue"
if ($confirm -ne "RESTORE") { Write-Host "Aborted."; exit 1 }
& (Join-Path $PSScriptRoot "restore.ps1") -File $File -TargetUrl $dsn
