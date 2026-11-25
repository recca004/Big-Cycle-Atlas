# Big Cycle Atlas — PostgreSQL backup (Windows).
# Creates a timestamped pg_dump custom-format archive under .\backups\
# (outside Git). Usage:
#   powershell -File scripts\ops\backup.ps1 [-DatabaseUrl <dsn>] [-OutDir <dir>] [-Keep <n>]
#
# Retention: after a SUCCESSFUL dump, automatic backups beyond $Keep are
# pruned — oldest first. $Keep defaults to env BCA_BACKUP_KEEP, else 30.
# Files matching "bca-keep-*.dump" are pinned and NEVER pruned — rename a
# dump to preserve an important manual backup forever.
param(
  [string]$DatabaseUrl = $env:DATABASE_URL,
  [string]$OutDir = "backups",
  [int]$Keep = 30
)
if ($env:BCA_BACKUP_KEEP) { $Keep = [int]$env:BCA_BACKUP_KEEP }

$ErrorActionPreference = "Stop"
if (-not $DatabaseUrl) {
  # Fall back to the API .env
  $envFile = Join-Path $PSScriptRoot "..\..\apps\api\.env"
  if (Test-Path $envFile) {
    Get-Content $envFile | Where-Object { $_ -match "^DATABASE_URL=" } | ForEach-Object {
      $DatabaseUrl = $_.Split("=", 2)[1].Trim().Trim('"')
    }
  }
}
if (-not $DatabaseUrl) { throw "DATABASE_URL not set and apps/api/.env missing" }

# Convert SQLAlchemy DSN to libpq form for pg_dump
$dsn = $DatabaseUrl -replace "postgresql\+psycopg://", "postgresql://"

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$file = Join-Path $OutDir "bca-$ts.dump"

$pgDump = "pg_dump"
if ($env:PG_BIN) { $pgDump = Join-Path $env:PG_BIN "pg_dump.exe" }

Write-Host "Backing up to $file ..."
& $pgDump --format=custom --compress=6 --file=$file $dsn
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed ($LASTEXITCODE)" }

# Retention — runs ONLY after a successful dump. Pinned backups
# (bca-keep-*.dump) are never touched; nothing outside bca-*.dump matches.
$pinned = Get-ChildItem $OutDir -Filter "bca-keep-*.dump" -ErrorAction SilentlyContinue
$ordinary = Get-ChildItem $OutDir -Filter "bca-*.dump" |
  Where-Object { $_.Name -notlike "bca-keep-*" } |
  Sort-Object LastWriteTime -Descending
$pruned = $ordinary | Select-Object -Skip $Keep
$pruned | Remove-Item -Force
if ($pruned) { Write-Host "Retention: pruned $($pruned.Count) old backup(s), kept $Keep (+ $($pinned.Count) pinned)" }

Write-Host "Backup complete: $file ($([math]::Round((Get-Item $file).Length/1MB,1)) MB)"
