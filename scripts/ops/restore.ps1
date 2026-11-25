# Big Cycle Atlas — restore a backup into a TARGET database (Windows).
# NEVER restores over the dev DB by default — requires -TargetUrl.
# Usage:
#   powershell -File scripts\ops\restore.ps1 -File backups\bca-*.dump -TargetUrl postgresql://.../bca_restore_test
param(
  [Parameter(Mandatory=$true)][string]$File,
  [Parameter(Mandatory=$true)][string]$TargetUrl
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $File)) { throw "Backup file not found: $File" }
if ($TargetUrl -match "bigcycleatlas_dev") {
  throw "Refusing to restore into the dev database — use an isolated target"
}

Write-Host "Restoring $File -> $TargetUrl ..."
pg_restore --clean --if-exists --no-owner --no-privileges --dbname=$TargetUrl $File
if ($LASTEXITCODE -ne 0) { throw "pg_restore failed ($LASTEXITCODE)" }
Write-Host "Restore complete. Verify with scripts/ops/verify-restore.ps1 -TargetUrl <same>"
