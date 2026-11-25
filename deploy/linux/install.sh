#!/usr/bin/env bash
# Big Cycle Atlas — native Debian/Ubuntu install (no Docker).
# Run as root on a fresh VM: bash deploy/linux/install.sh
set -euo pipefail
REPO=/opt/big-cycle-atlas

echo "== packages =="
apt-get update
apt-get install -y postgresql postgresql-client python3 python3-venv nodejs npm git curl
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo "== app user + repo =="
id bca &>/dev/null || useradd -r -s /usr/sbin/nologin -d $REPO bca
# Expect the repo to be cloned to $REPO already (git clone ... $REPO)
[ -d "$REPO/apps/api" ] || { echo "clone the repo to $REPO first"; exit 1; }

echo "== database =="
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='bca'" | grep -q 1 \
  || sudo -u postgres createuser bca
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='bigcycleatlas'" | grep -q 1 \
  || sudo -u postgres createdb -O bca bigcycleatlas
sudo -u postgres psql -c "ALTER USER bca WITH PASSWORD 'change-me'"

echo "== api =="
cd $REPO/apps/api
sudo -u bca uv sync --locked || su -s /bin/bash bca -c "cd $REPO/apps/api && uv sync --locked"
[ -f .env ] || { cp .env.example .env; echo "EDIT $REPO/apps/api/.env (DATABASE_URL password)"; }

echo "== web build =="
cd $REPO && npm ci && npm run build -w apps/web-astro
chown -R bca:bca $REPO

echo "== systemd =="
cp deploy/linux/systemd/*.service deploy/linux/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now bca-api.service
echo "App unit enabled. Timers are DISABLED by default — enable after review:"
echo "  systemctl enable --now bca-snapshot.timer bca-market-update.timer bca-backup.timer"
echo "Then: cd $REPO/apps/api && .venv/bin/alembic upgrade head && .venv/bin/python -m app.db.seed"
