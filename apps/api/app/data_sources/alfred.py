"""ALFRED/FRED vintage adapter.

The official FRED API requires a registered 32-character api_key for
`series/vintagedates` and real-time `series/observations` requests. The key is
read from BCA_FRED_API_KEY and is never logged or stored.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.data_sources.base import (
    DataSourceCredentialError, DataSourceHTTPError, DataSourceParseError,
)

FRED_API_URL = "https://api.stlouisfed.org/fred"
ALFRED_SOURCE_KEY = "alfred_fred"
API_KEY_ENV = "BCA_FRED_API_KEY"


@dataclass(frozen=True)
class AlfredVintageObservation:
    series_id: str
    observation_date: date
    realtime_start: date
    realtime_end: date
    value: float
    unit: str | None
    retrieved_at: datetime
    raw_payload: dict[str, Any]


class AlfredAdapter:
    source_key = ALFRED_SOURCE_KEY
    timeout = 60.0

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)

    async def _get(self, endpoint: str, **params) -> dict:
        if not self.api_key:
            raise DataSourceCredentialError(
                "ALFRED requires BCA_FRED_API_KEY (registered 32-character FRED API key)"
            )
        params.update({"api_key": self.api_key, "file_type": "json"})
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{FRED_API_URL}/{endpoint}", params=params)
            except httpx.HTTPError as exc:
                raise DataSourceHTTPError(f"FRED API request failed: {exc}") from exc
        if response.status_code != 200:
            raise DataSourceHTTPError(
                f"FRED API {endpoint}: HTTP {response.status_code}",
                status_code=response.status_code,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise DataSourceParseError(f"FRED API {endpoint}: invalid JSON") from exc

    async def vintage_dates(self, series_id: str) -> list[date]:
        payload = await self._get("series/vintagedates", series_id=series_id)
        try:
            return [date.fromisoformat(v) for v in payload["vintage_dates"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise DataSourceParseError(f"invalid vintagedates response for {series_id}") from exc

    async def observations(
        self, series_id: str,
        realtime_start: date | None = None,
        realtime_end: date | None = None,
        vintage_date: date | None = None,
    ) -> list[AlfredVintageObservation]:
        params: dict[str, Any] = {"series_id": series_id}
        if vintage_date:
            params["vintage_dates"] = vintage_date.isoformat()
        if realtime_start:
            params["realtime_start"] = realtime_start.isoformat()
        if realtime_end:
            params["realtime_end"] = realtime_end.isoformat()
        payload = await self._get("series/observations", **params)
        retrieved = datetime.now(timezone.utc)
        out = []
        for row in payload.get("observations", []):
            if row.get("value") in (None, ".", ""):
                continue
            try:
                out.append(AlfredVintageObservation(
                    series_id=series_id,
                    observation_date=date.fromisoformat(row["date"]),
                    realtime_start=date.fromisoformat(row["realtime_start"]),
                    realtime_end=date.fromisoformat(row["realtime_end"]),
                    value=float(row["value"]),
                    unit=None,
                    retrieved_at=retrieved,
                    raw_payload=row,
                ))
            except (KeyError, TypeError, ValueError) as exc:
                raise DataSourceParseError(
                    f"invalid ALFRED observation for {series_id}: {row}"
                ) from exc
        return out
