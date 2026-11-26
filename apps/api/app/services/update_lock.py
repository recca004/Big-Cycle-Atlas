"""Cross-process update lock for terminal, scheduler, and API refreshes.

The lock is an atomically-created JSON file outside the repository. Terminal
updates write an owner token into ``BCA_UPDATE_LOCK_TOKEN`` before invoking
Python refresh commands; that makes the file lock re-entrant for the scripts
belonging to the same terminal run while still blocking unrelated processes.
"""
from __future__ import annotations

import json
import os
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LOCK_ENV = "BCA_UPDATE_LOCK_TOKEN"
LOCK_PATH_ENV = "BCA_UPDATE_LOCK_PATH"


class UpdateLockError(RuntimeError):
    """Another Big Cycle Atlas update is already running."""


def update_lock_path() -> Path:
    override = os.environ.get(LOCK_PATH_ENV)
    if override:
        return Path(override)
    return Path(tempfile.gettempdir()) / "big-cycle-atlas" / "update.lock"


def _read_payload(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _pid_running(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _release_stale_lock(path: Path, payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    if _pid_running(payload.get("pid")):
        return False
    try:
        path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def update_lock_status() -> dict[str, Any]:
    """Return current lock state without acquiring it."""
    path = update_lock_path()
    payload = _read_payload(path) if path.exists() else None
    if payload is None:
        return {"locked": False, "path": str(path)}
    stale = _release_stale_lock(path, payload)
    if stale:
        return {"locked": False, "path": str(path), "stale_released": True}
    token = os.environ.get(LOCK_ENV)
    reentrant = bool(token and token == payload.get("token"))
    return {
        "locked": not reentrant,
        "held_by_current_run": reentrant,
        "path": str(path),
        "owner": payload.get("owner"),
        "pid": payload.get("pid"),
        "started_at": payload.get("started_at"),
    }


@asynccontextmanager
async def update_lock(owner: str) -> AsyncIterator[None]:
    """Acquire the shared update lock, or no-op inside the owning terminal run."""
    path = update_lock_path()
    token = os.environ.get(LOCK_ENV)
    if path.exists():
        payload = _read_payload(path)
        if token and payload and token == payload.get("token"):
            yield
            return
        if payload and _release_stale_lock(path, payload):
            pass
        else:
            detail = "unreadable lock"
            if payload:
                detail = (
                    f"{payload.get('owner', 'unknown owner')} "
                    f"pid={payload.get('pid')} "
                    f"started={payload.get('started_at')}"
                )
            raise UpdateLockError(f"update already in progress ({detail})")

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "owner": owner,
        "pid": os.getpid(),
        "token": token or f"python-{os.getpid()}",
        "started_at": datetime.now(UTC).isoformat(),
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(path, flags)
    except FileExistsError as exc:
        raise UpdateLockError("update already in progress") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        yield
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
