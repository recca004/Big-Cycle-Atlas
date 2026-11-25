"""FRED market data adapter (Mission 5 §16).

Uses the public fredgraph.csv endpoint — NO API KEY REQUIRED. The FRED
API itself needs a key; the graph CSV export used by the public site
does not, and serves the same published series values. Verified live
against yields, FX, equity price indices, policy rates and commodity
indices (2026-11).

Terms: FRED data is public domain or provider-licensed; Atlas stores
values with source provenance, no redistribution.

    rows = await adapter.fetch_series("DGS10", start=date(2020, 1, 1))
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timezone
from typing import Optional

import httpx
from pydantic import BaseModel

from app.data_sources.base import (
    DataSourceHTTPError,
    DataSourceNoDataError,
    DataSourceParseError,
)

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


class MarketPriceDTO(BaseModel):
    """One market observation from a provider — never persisted directly."""
    external_code: str
    obs_date: date
    value: float
    retrieved_at: datetime
    raw_payload: dict


class FredAdapter:
    """Fetches a FRED series as dated values via fredgraph.csv."""

    source_key = "fred"
    timeout = 30.0

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "FredAdapter":
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client is not None:
            await self._client.aclose()
        self._client = None

    async def fetch_series(
        self,
        external_code: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> list[MarketPriceDTO]:
        params = {"id": external_code}
        if start:
            params["cosd"] = start.isoformat()
        if end:
            params["coed"] = end.isoformat()

        client = self._client or httpx.AsyncClient(timeout=self.timeout)
        try:
            resp = await client.get(FRED_CSV_URL, params=params)
        except httpx.HTTPError as exc:
            raise DataSourceHTTPError(f"FRED fetch failed: {exc}") from exc
        finally:
            if self._client is None:
                await client.aclose()

        if resp.status_code != 200:
            raise DataSourceHTTPError(
                f"FRED {external_code}: HTTP {resp.status_code}",
                status_code=resp.status_code,
            )
        body = resp.text
        if "<html" in body[:200].lower():
            # FRED serves an HTML error page for unknown series codes.
            raise DataSourceNoDataError(
                f"FRED series {external_code!r} not found (HTML response)"
            )

        retrieved = datetime.now(timezone.utc)
        rows = list(csv.reader(io.StringIO(body)))
        if not rows or rows[0][0].strip().lower() != "observation_date":
            raise DataSourceParseError(
                f"FRED {external_code}: unexpected header {rows[:1]}"
            )

        out: list[MarketPriceDTO] = []
        for line_no, row in enumerate(rows[1:], start=2):
            if len(row) < 2 or row[1] in ("", "."):
                continue  # FRED uses '.' for missing values
            try:
                d = date.fromisoformat(row[0].strip())
                v = float(row[1])
            except ValueError as exc:
                raise DataSourceParseError(
                    f"FRED {external_code} line {line_no}: {row}"
                ) from exc
            out.append(MarketPriceDTO(
                external_code=external_code,
                obs_date=d,
                value=v,
                retrieved_at=retrieved,
                raw_payload={"source": "fredgraph.csv"},
            ))
        return out
