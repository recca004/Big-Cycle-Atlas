import json
import ssl
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import certifi
import httpx

from app.data_sources.base import (
    BaseDataSourceAdapter,
    DataSourceHTTPError,
    DataSourceParseError,
    ObservationDTO,
    SeriesMappingError,
)
from app.data_sources.world_bank_mappings import get_world_bank_mapping_by_external_code

DEFAULT_TIMEOUT_SECONDS = 30.0


def _build_ssl_context() -> ssl.SSLContext:
    # Load CAs from memory: this machine's python.exe lacks the OPENSSL_Applink
    # export, so OpenSSL crashes on FILE*-based CA loading (load_verify_locations
    # with a file). cadata bypasses the file BIO entirely.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_default_certs()
    pem = Path(certifi.where()).read_text(encoding="utf-8")
    context.load_verify_locations(cadata=pem)
    return context


class WorldBankAdapter(BaseDataSourceAdapter):
    """Adapter for the World Bank API v2.

    Endpoint: {base_url}/country/{ISO3}/indicator/{series}?format=json&per_page=20000[&date=START:END]
    Response is a two-element JSON array: [pagination_metadata, observation_records].
    Null-valued records (and the trailing null record the API emits) are skipped —
    missing data is never coerced to zero. The API provides no release timestamp,
    so release_date stays None.

    indicator_code on emitted DTOs is the canonical Big Cycle Atlas code resolved
    from the requested external series via world_bank_mappings; the raw World Bank
    ID stays in external_series_code. Requesting an unmapped external series raises
    SeriesMappingError — unmapped series are never silently mislabeled.
    """

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

    async def __aenter__(self) -> "WorldBankAdapter":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()

    def _build_url(self, country_iso3: str, external_series_code: str) -> str:
        return f"{self.base_url}/country/{country_iso3}/indicator/{external_series_code}"

    def _build_params(
        self, start_year: Optional[int], end_year: Optional[int]
    ) -> dict:
        params = {"format": "json", "per_page": "20000"}
        if start_year is not None and end_year is not None:
            params["date"] = f"{start_year}:{end_year}"
        elif start_year is not None:
            params["date"] = f"{start_year}:{datetime.now(timezone.utc).year}"
        return params

    async def fetch_indicator(
        self,
        country_iso3: str,
        external_series_code: str,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[ObservationDTO]:
        url = self._build_url(country_iso3, external_series_code)
        try:
            response = await self._client.get(
                url, params=self._build_params(start_year, end_year)
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

        return self.parse_response(payload, country_iso3, external_series_code)

    def parse_response(
        self,
        payload: object,
        country_iso3: str,
        external_series_code: str,
    ) -> list[ObservationDTO]:
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

        mapping = get_world_bank_mapping_by_external_code(external_series_code)
        if mapping is None:
            raise SeriesMappingError(
                f"World Bank series {external_series_code!r} has no canonical "
                "Big Cycle Atlas indicator mapping"
            )

        observations: list[ObservationDTO] = []
        for record in records:
            if record is None:
                continue
            value = record.get("value")
            if value is None:
                continue  # missing data is skipped, never zero-filled
            raw_date = str(record.get("date", "")).strip()
            year = int(raw_date) if raw_date.isdigit() and len(raw_date) == 4 else None
            if year is None:
                raise DataSourceParseError(
                    f"World Bank record has unparseable date: {raw_date!r}"
                )
            observations.append(
                ObservationDTO(
                    country_iso3=country_iso3,
                    indicator_code=mapping.indicator_code,
                    external_series_code=external_series_code,
                    period=year,
                    value=float(value),
                    unit=record.get("unit") or None,
                    source_key=self.source_key,
                    observation_date=date(year, 1, 1),
                    release_date=None,
                    retrieved_at=self._retrieved_at,
                    raw_payload=record,
                )
            )
        return observations