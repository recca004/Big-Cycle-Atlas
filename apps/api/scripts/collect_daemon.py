"""Scheduled collection daemon (Mission 6 §37).

Runs inside the collector container (or any always-on host):

- Daily at 06:00 Europe/Zurich: `collect_snapshot.py` — macro snapshot
  across all live providers.
- Daily at 06:30 Europe/Zurich: `ingest_markets.py --start <today-45d>`
  — incremental market update (45-day lookback covers late releases and
  revisions without re-pulling history).

A lockfile prevents overlapping runs. All timestamps are stored in UTC
by the underlying commands; only the schedule is zoned.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TZ = ZoneInfo(os.environ.get("BCA_SCHEDULE_TZ", "Europe/Zurich"))
HERE = Path(__file__).resolve().parent
LOCK = Path(os.environ.get("BCA_COLLECT_LOCK", "/tmp/bca-collect.lock"))

# (hour, minute, command builder, label)
def _jobs() -> list[tuple[int, int, list[str], str]]:
    start = (date.today() - timedelta(days=45)).isoformat()
    py = sys.executable
    return [
        (6, 0, [py, str(HERE / "collect_snapshot.py")], "macro snapshot"),
        (6, 30, [py, str(HERE / "ingest_markets.py"), "--start", start],
         "market update"),
    ]


def _acquire_lock() -> bool:
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        # Stale-lock recovery: ignore locks older than 6 hours.
        try:
            if time.time() - LOCK.stat().st_mtime > 6 * 3600:
                LOCK.unlink()
                return _acquire_lock()
        except OSError:
            pass
        return False


def _run_job(cmd: list[str], label: str) -> int:
    print(f"[{datetime.now(TZ):%F %T %Z}] {label}: starting", flush=True)
    rc = subprocess.call(cmd, cwd=str(HERE.parent))
    print(f"[{datetime.now(TZ):%F %T %Z}] {label}: exit {rc}", flush=True)
    return rc


def main() -> int:
    print(f"[collect-daemon] schedule zone {TZ}; jobs at 06:00/06:30", flush=True)
    last_run: dict[str, str] = {}
    while True:
        now = datetime.now(TZ)
        today = now.date().isoformat()
        for hour, minute, cmd, label in _jobs():
            due = (now.hour, now.minute) >= (hour, minute)
            if due and last_run.get(label) != today:
                if not _acquire_lock():
                    print(f"[{now:%F %T}] lock held — skipping {label}", flush=True)
                    continue
                try:
                    _run_job(cmd, label)
                    last_run[label] = today
                finally:
                    LOCK.unlink(missing_ok=True)
        time.sleep(60)


if __name__ == "__main__":
    sys.exit(main())
