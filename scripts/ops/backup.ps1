# Big Cycle Atlas — PostgreSQL backup (Windows).
# Creates a timestamped pg_dump custom-format archive under .\backups\
# (outside Git). Usage:
#   powershell -File scripts\ops\backup.ps1 [-DatabaseUrl <dsn>] [-OutDir <dir>]
param(
  [string]$DatabaseUrl = $env:DATABASE_URL,
  [string]$OutDir = "backups",
  [int]$Keep = 30
)

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

Write-Host "Backing up to $file ..."
pg_dump --format=custom --compress=6 --file=$file $dsn
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed ($LASTEXITCODE)" }

# Retention: keep newest $Keep backups (never deletes non-bca files)
Get-ChildItem $OutDir -Filter "bca-*.dump" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -Skip $Keep |
  Remove-Item -Force

Write-Host "Backup complete: $file ($([math]::Round((Get-Item $file).Length/1MB,1)) MB)"
