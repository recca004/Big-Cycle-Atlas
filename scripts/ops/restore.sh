#!/bin/sh
# Big Cycle Atlas — restore a backup into a TARGET database (Linux).
# Refuses the known dev DB name — restores must target an isolated DB.
#   sh scripts/ops/restore.sh <backup.dump> <target-dsn>
set -eu

FILE="${1:?usage: restore.sh <file> <target-dsn>}"
TARGET="${2:?usage: restore.sh <file> <target-dsn>}"

case "$TARGET" in
  *bigcycleatlas_dev*) echo "refusing to restore into the dev database" >&2; exit 1 ;;
esac

echo "Restoring $FILE -> $TARGET ..."
pg_restore --clean --if-exists --no-owner --no-privileges --dbname="$TARGET" "$FILE"
echo "Restore complete."
