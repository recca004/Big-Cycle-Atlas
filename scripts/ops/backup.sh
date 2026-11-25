#!/bin/sh
# Big Cycle Atlas — PostgreSQL backup (Linux/macOS).
# Timestamped pg_dump custom-format archive under ./backups (outside Git).
#   sh scripts/ops/backup.sh [outdir]
set -eu

OUTDIR="${1:-backups}"
KEEP="${BCA_BACKUP_KEEP:-30}"
DSN="${DATABASE_URL:-}"

if [ -z "$DSN" ] && [ -f apps/api/.env ]; then
  DSN=$(grep '^DATABASE_URL=' apps/api/.env | cut -d= -f2- | tr -d '"')
fi
[ -n "$DSN" ] || { echo "DATABASE_URL not set and apps/api/.env missing" >&2; exit 1; }

DSN=$(printf '%s' "$DSN" | sed 's/postgresql+psycopg:\/\//postgresql:\/\//')

TS=$(date -u +%Y%m%d-%H%M%S)
mkdir -p "$OUTDIR"
FILE="$OUTDIR/bca-$TS.dump"

echo "Backing up to $FILE ..."
pg_dump --format=custom --compress=6 --file="$FILE" "$DSN"

# Retention: keep newest $KEEP (never touches non-bca files)
ls -1t "$OUTDIR"/bca-*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -f

echo "Backup complete: $FILE ($(du -m "$FILE" | cut -f1) MB)"
