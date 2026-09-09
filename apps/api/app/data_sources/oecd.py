import csv
import io
import re
import ssl
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import certifi
import httpx

from app.data_sources.base import (
    BaseDataSourceAdapter,
    DataSourceError,
    DataSourceHTTPError,
    DataSourceNoDataError,
    DataSourceParseError,
    ObservationDTO,
    SeriesMappingError,
)
from app.data_sources.oecd_mappings import (
    OECD_REF_AREA_BY_ISO3,
    OecdMapping,
    get_oecd_mapping_by_external_code,
)

DEFAULT_TIMEOUT_SECONDS = 30.0
_ANNUAL_PERIOD_RE = re.compile(r"^(\d{4})$")
_QUARTER_PERIOD_RE = re.compile(r"^(\d{4})-Q([1-4])$")


def _build_ssl_context() -> ssl.SSLContext:
    # Load CAs from memory: this machine's python.exe lacks the OPENSSL_Applink
    # export, so OpenSSL crashes on FILE*-based CA loading (load_verify_locations
    # with a file). cadata bypasses the file BIO entirely.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_default_certs()
    pem = Path(certifi.where()).read_text(encoding="utf-8")
    context.load_verify_locations(cadata=pem)
    return context


class OECDAdapter(BaseDataSourceAdapter):
    """Adapter for the official OECD SDMX REST API (v1-style exact-key queries).

    Endpoint:
    {base}/data/{agency_id},{dataflow_id},{version}/{key}?format=csvfilewithlabels
    [&startPeriod=...&endPeriod=...]
    Response is SDMX-CSV with labels. No authentication required (documented
    rate limit ~60 queries/hour — batch code must throttle, not retry-storm).
    The v2 API's c[...] filter parameters are silently broken server-side
    (observed 2026-09-08 returning wrong-country rows), so only exact dot-keys
    are used — and every returned CSV row is still dimension-validated because
    a correct request is not proof of a correct response (ISSUE-004 lesson).

    Key dimension order (verified via structure metadata + live queries):
    REF_AREA, FREQ, MEASURE, ACTIVITY, UNIT_MEASURE, PRICE_BASE, TRANSFORMATION,
    [ASSET_CODE | ADJUSTMENT], CONVERSION_TYPE. {cc} resolves to the OECD
    REF_AREA code, which is ISO3 — identical to Big Cycle Atlas ISO3 codes for
    all 8 tracked countries, so resolution is a lookup, never an alias guess.
    Unknown ISO3 codes raise DataSourceError.

    The requested external_series_code must be the country-independent
    identity "{dataflow_id}/{sdmx_key_template}" (e.g.
    "DSD_PDB@DF_PDB/{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP"). Unknown codes
    raise SeriesMappingError — never guessed.

    Period handling: annual "2024" → observation_date 2024-01-01; quarterly
    "2025-Q1..Q4" → quarter start dates (BIS convention). `period` stays the
    year so the ObservationDTO schema is unchanged. Null/empty OBS_VALUE rows
    are skipped — missing data is never zero-filled. Source status/flag fields
    present in the row (OBS_STATUS etc.) are preserved in raw_payload. The API
    provides no release timestamp, so release_date stays None.
    """

    source_key = "oecd"
    DEFAULT_BASE_URL = "https://sdmx.oecd.org/public/rest"

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

    async def __aenter__(self) -> "OECDAdapter":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()

    def _resolve_key(self, mapping: OecdMapping, country_iso3: str) -> str:
        ref_area = OECD_REF_AREA_BY_ISO3.get(country_iso3)
        if ref_area is None:
            raise DataSourceError(
                f"Country {country_iso3!r} has no OECD REF_AREA mapping; "
                "OECD series keys require a REF_AREA code"
            )
        return mapping.sdmx_key_template.replace("{cc}", ref_area)

    def _build_url(self, mapping: OecdMapping, key: str) -> str:
        return (
            f"{self.base_url}/data/{mapping.agency_id},"
            f"{mapping.dataflow_id},{mapping.version}/{key}"
        )

    def _build_params(
        self, mapping: OecdMapping, start_year: Optional[int], end_year: Optional[int]
    ) -> dict:
        params = {"format": "csvfilewithlabels"}
        if start_year is not None:
            params["startPeriod"] = (
                f"{start_year}" if mapping.frequency == "annual" else f"{start_year}-Q1"
            )
        if end_year is not None:
            params["endPeriod"] = (
                f"{end_year}" if mapping.frequency == "annual" else f"{end_year}-Q4"
            )
        return params

    async def fetch_indicator(
        self,
        country_iso3: str,
        external_series_code: str,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[ObservationDTO]:
        mapping = get_oecd_mapping_by_external_code(external_series_code)
        if mapping is None:
            raise SeriesMappingError(
                f"OECD external identity {external_series_code!r} has no canonical "
                "Big Cycle Atlas indicator mapping"
            )
        key = self._resolve_key(mapping, country_iso3)
        url = self._build_url(mapping, key)
        try:
            response = await self._client.get(
                url, params=self._build_params(mapping, start_year, end_year)
            )
        except httpx.HTTPError as exc:
            raise DataSourceHTTPError(f"Request to OECD failed: {exc}") from exc

        if response.status_code != 200:
            # Verified live (2026-09-08): a key with no observations returns
            # HTTP 404 with body "NoRecordsFound" (e.g. CHN in DF_PDB). That
            # is a clean "this series simply has no data" answer — distinct
            # from transport/API failures — so callers can record a legitimate
            # no-data outcome instead of a failed run (CHN/IND coverage).
            if response.status_code == 404 and "NoRecordsFound" in response.text:
                raise DataSourceNoDataError(
                    f"OECD reports no observations for {country_iso3!r} "
                    f"({external_series_code})"
                )
            raise DataSourceHTTPError(
                f"OECD returned HTTP {response.status_code}",
                status_code=response.status_code,
            )

        observations = self.parse_response(
            response.text, country_iso3, external_series_code
        )
        return [
            obs
            for obs in observations
            if (start_year is None or obs.period >= start_year)
            and (end_year is None or obs.period <= end_year)
        ]

    def _validate_row_identity(
        self, row: dict, expected_ref_area: str, mapping: OecdMapping
    ) -> None:
        ref_area = (row.get("REF_AREA") or "").strip()
        if ref_area != expected_ref_area:
            raise DataSourceParseError(
                f"OECD row identity violation: requested {expected_ref_area!r} "
                f"but row has REF_AREA={ref_area!r} "
                f"({mapping.external_code})"
            )
        for column, expected in mapping.expected_dims:
            if column not in row:
                continue
            actual = (row.get(column) or "").strip()
            if actual != expected:
                raise DataSourceParseError(
                    f"OECD row identity violation: expected {column}={expected!r} "
                    f"but got {column}={actual!r} ({mapping.external_code})"
                )

    def _parse_time_period(self, raw_period: str, mapping: OecdMapping) -> date:
        if mapping.frequency == "annual":
            match = _ANNUAL_PERIOD_RE.match(raw_period)
            if match is None:
                raise DataSourceParseError(
                    f"OECD record has unparseable TIME_PERIOD: {raw_period!r}"
                )
            return date(int(match.group(1)), 1, 1)
        match = _QUARTER_PERIOD_RE.match(raw_period)
        if match is None:
            raise DataSourceParseError(
                f"OECD record has unparseable TIME_PERIOD: {raw_period!r}"
            )
        year, quarter = int(match.group(1)), int(match.group(2))
        # Quarter start date: Q1→01, Q2→04, Q3→07, Q4→10.
        return date(year, 1 + (quarter - 1) * 3, 1)

    def parse_response(
        self,
        payload: object,
        country_iso3: str,
        external_series_code: str,
    ) -> list[ObservationDTO]:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        if not isinstance(payload, str):
            raise DataSourceParseError("OECD response is not CSV text")

        mapping = get_oecd_mapping_by_external_code(external_series_code)
        if mapping is None:
            raise SeriesMappingError(
                f"OECD external identity {external_series_code!r} has no canonical "
                "Big Cycle Atlas indicator mapping"
            )
        expected_ref_area = OECD_REF_AREA_BY_ISO3.get(country_iso3)
        if expected_ref_area is None:
            raise DataSourceError(
                f"Country {country_iso3!r} has no OECD REF_AREA mapping"
            )

        try:
            reader = csv.DictReader(io.StringIO(payload))
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise DataSourceParseError("OECD CSV response has no header row")
            if "TIME_PERIOD" not in fieldnames or "OBS_VALUE" not in fieldnames:
                raise DataSourceParseError(
                    "OECD CSV response is missing TIME_PERIOD/OBS_VALUE columns"
                )
            rows = list(reader)
        except csv.Error as exc:
            raise DataSourceParseError(
                "OECD response is not valid SDMX-CSV"
            ) from exc

        observations: list[ObservationDTO] = []
        for row in rows:
            if row is None:
                continue
            raw_value = (row.get("OBS_VALUE") or "").strip()
            if raw_value == "":
                continue  # missing data is skipped, never zero-filled
            raw_period = (row.get("TIME_PERIOD") or "").strip()
            observation_date = self._parse_time_period(raw_period, mapping)
            self._validate_row_identity(row, expected_ref_area, mapping)
            observations.append(
                ObservationDTO(
                    country_iso3=country_iso3,
                    indicator_code=mapping.indicator_code,
                    external_series_code=mapping.external_code,
                    period=observation_date.year,
                    value=float(raw_value),
                    unit=mapping.external_unit,
                    source_key=self.source_key,
                    observation_date=observation_date,
                    release_date=None,
                    retrieved_at=self._retrieved_at,
                    raw_payload=dict(row),
                )
            )
        return observations