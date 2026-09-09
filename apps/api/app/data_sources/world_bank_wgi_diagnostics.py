"""Narrow live-fetch path for the WGI uncertainty diagnostic series
(DEC-022, Sprint 5.15).

Fetches the 9 owner-approved auxiliary diagnostic series from the World
Bank API v2 through the DEDICATED WGI source (provider source id 3,
via the explicit `source` query parameter) — distinct from the WDI
source (id 2) that carries the score series GOV_WGI_{RL,CC,PV}_SC.
Verified live 2026-09-09: the response metadata exposes `sourceid`, and
each record carries `indicator.id` and `countryiso3code`, so the
returned provider identity is VALIDATED against the expected spec — a
mismatch is raised loudly (never retried, never silently adapted).

This path returns IndicatorDiagnosticDTOs ONLY: it can never produce an
observation DTO, a series row, or an observation row. Null provider
values are skipped — never zero-filled. Values are stored RAW: no
clamping, no rounding (a 9.7 source count survives until persistence
rejects it).
"""
import json
import math
from datetime import date, datetime, timezone
from typing import Optional

import httpx

from app.data_sources.base import (
    DataSourceHTTPError,
    DataSourceParseError,
    SeriesMappingError,
)
from app.data_sources.world_bank import DEFAULT_TIMEOUT_SECONDS, _build_ssl_context
from app.data_sources.wgi_diagnostic_specs import WgiDiagnosticSpec
from app.services.indicator_diagnostic_service import IndicatorDiagnosticDTO


class WorldBankWgiDiagnosticFetcher:
    """Fetches one WGI diagnostic series for one country from the
    dedicated WGI source. Transport/SSL/timeout conventions mirror
    WorldBankAdapter; DTO semantics are diagnostic-only."""

    source_key = "world_bank"
    DEFAULT_BASE_URL = "https://api.worldbank.org/v2"

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        retrieved_at: Optional[datetime] = None,
    ):
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self._retrieved_at = retrieved_at or datetime.now(timezone.utc)
        self._client = httpx.AsyncClient(
            timeout=timeout, transport=transport, verify=_build_ssl_context()
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "WorldBankWgiDiagnosticFetcher":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()

    def _build_params(
        self,
        spec: WgiDiagnosticSpec,
        start_year: Optional[int],
        end_year: Optional[int],
    ) -> dict:
        params = {
            "format": "json",
            "per_page": "20000",
            # Explicit dedicated-WGI-source resolution — never rely on the
            # API's default-source behavior for these series.
            "source": spec.provider_source_code,
        }
        if start_year is not None and end_year is not None:
            params["date"] = f"{start_year}:{end_year}"
        elif start_year is not None:
            params["date"] = f"{start_year}:{datetime.now(timezone.utc).year}"
        return params

    async def fetch_wgi_diagnostic(
        self,
        country_iso3: str,
        spec: WgiDiagnosticSpec,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[IndicatorDiagnosticDTO]:
        url = (
            f"{self.base_url}/country/{country_iso3}/indicator/"
            f"{spec.provider_series_code}"
        )
        try:
            response = await self._client.get(
                url, params=self._build_params(spec, start_year, end_year)
            )
        except httpx.HTTPError as exc:
            raise DataSourceHTTPError(f"Request to World Bank failed: {exc}") from exc

        if response.status_code != 200:
            raise DataSourceHTTPError(
                f"World Bank returned HTTP {response.status_code}",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise DataSourceParseError(
                "World Bank response is not valid JSON"
            ) from exc

        return self.parse_response(payload, country_iso3, spec)

    def parse_response(
        self,
        payload: object,
        country_iso3: str,
        spec: WgiDiagnosticSpec,
    ) -> list[IndicatorDiagnosticDTO]:
        try:
            metadata, records = payload
        except (TypeError, ValueError) as exc:
            raise DataSourceParseError(
                "World Bank response is not the expected [metadata, records] array"
            ) from exc

        if not isinstance(metadata, dict) or not isinstance(records, list):
            raise DataSourceParseError(
                "World Bank response metadata/records have unexpected types"
            )

        source_id = str(metadata.get("sourceid", "")).strip()
        if source_id != spec.provider_source_code:
            # The API response exposes the serving source id — a wrong-source
            # value must never be stored under the expected identity.
            raise SeriesMappingError(
                f"World Bank served {spec.provider_series_code!r} from source "
                f"id {source_id!r}, expected the dedicated WGI source "
                f"{spec.provider_source_code!r}"
            )

        dtos: list[IndicatorDiagnosticDTO] = []
        for record in records:
            if record is None:
                continue
            value = record.get("value")
            if value is None:
                continue  # missing data is skipped, never zero-filled

            record_series = str((record.get("indicator") or {}).get("id", "")).strip()
            if record_series != spec.provider_series_code:
                raise SeriesMappingError(
                    f"World Bank record indicator id {record_series!r} does not "
                    f"match the requested series {spec.provider_series_code!r}"
                )
            record_iso3 = str(record.get("countryiso3code", "")).strip()
            if record_iso3 != country_iso3:
                raise SeriesMappingError(
                    f"World Bank record country {record_iso3!r} does not match "
                    f"the requested country {country_iso3!r}"
                )

            raw_date = str(record.get("date", "")).strip()
            if not (raw_date.isdigit() and len(raw_date) == 4):
                raise DataSourceParseError(
                    f"World Bank record has unparseable date: {raw_date!r}"
                )
            year = int(raw_date)

            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise DataSourceParseError(
                    f"World Bank record value is not numeric: {value!r}"
                ) from exc
            if not math.isfinite(numeric):
                raise DataSourceParseError(
                    f"World Bank record value is not finite: {value!r}"
                )

            dtos.append(
                IndicatorDiagnosticDTO(
                    country_iso3=country_iso3,
                    base_indicator_code=spec.base_indicator_code,
                    source_key=spec.source_key,
                    provider_source_code=spec.provider_source_code,
                    provider_series_code=spec.provider_series_code,
                    diagnostic_kind=spec.diagnostic_kind,
                    # Annual YYYY -> Jan 1 of the score year, matching the
                    # WGI score observation_date convention. No synthetic
                    # period-end dates in raw storage.
                    period_start=date(year, 1, 1),
                    value=numeric,
                    retrieved_at=self._retrieved_at,
                    raw_payload=record,
                )
            )
        return dtos