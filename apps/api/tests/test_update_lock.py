import json

import pytest

from app.services.update_lock import (
    LOCK_ENV,
    LOCK_PATH_ENV,
    UpdateLockError,
    update_lock,
    update_lock_status,
)


@pytest.mark.asyncio
async def test_update_lock_blocks_second_process_and_releases(
    tmp_path, monkeypatch
):
    lock_path = tmp_path / "update.lock"
    monkeypatch.setenv(LOCK_PATH_ENV, str(lock_path))
    monkeypatch.delenv(LOCK_ENV, raising=False)

    async with update_lock("test-owner"):
        assert lock_path.exists()
        assert update_lock_status()["locked"] is True
        with pytest.raises(UpdateLockError):
            async with update_lock("other-owner"):
                pass

    assert not lock_path.exists()


@pytest.mark.asyncio
async def test_update_lock_is_reentrant_for_terminal_owner_token(
    tmp_path, monkeypatch
):
    lock_path = tmp_path / "update.lock"
    monkeypatch.setenv(LOCK_PATH_ENV, str(lock_path))
    monkeypatch.setenv(LOCK_ENV, "run-token")

    async with update_lock("terminal"):
        async with update_lock("refresh-script"):
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            assert payload["owner"] == "terminal"
        assert update_lock_status()["held_by_current_run"] is True
