"""Tests for the batch importer's transient-retry wrapper."""
import asyncio
import importlib.util
import pathlib
from datetime import date, datetime, timezone

import pytest

from app.data_sources.base import (
    DataSourceHTTPError,
    DataSourceParseError,
    ObservationDTO,
    SeriesMappingError,
)

_SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "ingest_world_bank.py"
)
_spec = importlib.util.spec_from_file_location("ingest_world_bank", _SCRIPT)
_ingest_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ingest_script)


class FlakyAdapter:
    """Scriptable adapter: each call pops the next behaviour from a list."""

    source_key = "world_bank"

    def __init__(self, behaviours):
        self.behaviours = list(behaviours)
        self.calls = 0

    async def fetch_indicator(self, country_iso3, external_series_code,
                              start_year=None, end_year=None):
        self.calls += 1
        behaviour = self.behaviours.pop(0)
        if isinstance(behaviour, Exception):
            raise behaviour
        return behaviour


def _dto() -> ObservationDTO:
    return ObservationDTO(
        country_iso3="CHE",
        indicator_code="GDP_GROWTH",
        external_series_code="NY.GDP.MKTP.KD.ZG",
        period=2024,
        value=1.3,
        source_key="world_bank",
        observation_date=date(2024, 1, 1),
        retrieved_at=datetime.now(timezone.utc),
        raw_payload={},
    )


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_5xx():
    inner = FlakyAdapter([
        DataSourceHTTPError("server error", status_code=503),
        [_dto()],
    ])
    adapter = _ingest_script.TransientRetryAdapter(inner)
    dtos = await adapter.fetch_indicator("CHE", "NY.GDP.MKTP.KD.ZG")
    assert len(dtos) == 1
    assert inner.calls == 2


@pytest.mark.asyncio
async def test_retry_on_statusless_network_error():
    inner = FlakyAdapter([
        DataSourceHTTPError("connection reset", status_code=None),
        [_dto()],
    ])
    adapter = _ingest_script.TransientRetryAdapter(inner)
    await adapter.fetch_indicator("CHE", "NY.GDP.MKTP.KD.ZG")
    assert inner.calls == 2


@pytest.mark.asyncio
async def test_no_retry_on_404():
    inner = FlakyAdapter([DataSourceHTTPError("not found", status_code=404)])
    adapter = _ingest_script.TransientRetryAdapter(inner)
    with pytest.raises(DataSourceHTTPError):
        await adapter.fetch_indicator("CHE", "NY.GDP.MKTP.KD.ZG")
    assert inner.calls == 1


@pytest.mark.asyncio
async def test_no_retry_on_parse_error():
    inner = FlakyAdapter([DataSourceParseError("bad payload")])
    adapter = _ingest_script.TransientRetryAdapter(inner)
    with pytest.raises(DataSourceParseError):
        await adapter.fetch_indicator("CHE", "NY.GDP.MKTP.KD.ZG")
    assert inner.calls == 1


@pytest.mark.asyncio
async def test_no_retry_on_mapping_error():
    inner = FlakyAdapter([SeriesMappingError("unmapped series")])
    adapter = _ingest_script.TransientRetryAdapter(inner)
    with pytest.raises(SeriesMappingError):
        await adapter.fetch_indicator("CHE", "NY.GDP.MKTP.KD.ZG")
    assert inner.calls == 1


@pytest.mark.asyncio
async def test_retry_gives_up_after_max_attempts(monkeypatch):
    async def _no_sleep(*_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    inner = FlakyAdapter([
        DataSourceHTTPError("timeout", status_code=None) for _ in range(3)
    ])
    adapter = _ingest_script.TransientRetryAdapter(inner)
    with pytest.raises(DataSourceHTTPError):
        await adapter.fetch_indicator("CHE", "NY.GDP.MKTP.KD.ZG")
    assert inner.calls == 3