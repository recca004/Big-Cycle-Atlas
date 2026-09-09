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
    DataSourceParseError,
    ObservationDTO,
    SeriesMappingError,
)
from app.data_sources.bis_mappings import (
    BIS_ISO2_BY_ISO3,
    BisMapping,
    get_bis_mapping_by_external_code,
)

DEFAULT_TIMEOUT_SECONDS = 30.0
_TIME_PERIOD_RE = re.compile(r"^(\d{4})-Q([1-4])$")


def _build_ssl_context() -> ssl.SSLContext:
    # Load CAs from memory: this machine's python.exe lacks the OPENSSL_Applink
    # export, so OpenSSL crashes on FILE*-based CA loading (load_verify_locations
    # with a file). cadata bypasses the file BIO entirely.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_default_certs()
    pem = Path(certifi.where()).read_text(encoding="utf-8")
    context.load_verify_locations(cadata=pem)
    return context


class BISAdapter(BaseDataSourceAdapter):
    """Adapter for the official BIS Stats API v1 (SDMX REST subset).

    Endpoint: {base_url}/data/{dataflow}/{key}/all?format=csv[&startPeriod=YYYY-Q1&endPeriod=YYYY-Q4]
    Response is SDMX-CSV text. No authentication required. Series keys use ISO2
    borrower-country codes; the {cc} placeholder in the mapping's key template
    is resolved from the requested ISO3 via bis_mappings.BIS_ISO2_BY_ISO3.

    The requested external_series_code must be the full country-independent
    identity "{dataflow_id}/{sdmx_key_template}" (e.g.
    "WS_CREDIT_GAP/Q.{{cc}}.P.A.C"). Unknown codes raise SeriesMappingError and
    untracked ISO3 codes raise DataSourceError — neither is ever guessed.

    Because one dataflow carries several series families, every non-empty CSV
    row is validated against the mapping's expected dimensions (FREQ, sector,
    CG_DTYPE, ...) and the expected ISO2 borrower country. A row that violates
    the requested identity raises DataSourceParseError instead of being
    silently relabelled — this guards against data-scoping bugs like the
    cross-country leak found in Milestone 3.

    Quarterly periods map to quarter start dates (2025-Q1 → 2025-01-01,
    Q2 → 04-01, Q3 → 07-01, Q4 → 10-01); `period` stays the year, so the
    ObservationDTO schema is unchanged and persistence can keep quarterly
    identity via observation_date → period_start. Null/empty OBS_VALUE rows
    are skipped — missing data is never zero-filled. The API provides no
    release timestamp, so release_date stays None.
    """

    source_key = "bis"
    DEFAULT_BASE_URL = "https://stats.bis.org/api/v1"

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

    async def __aenter__(self) -> "BISAdapter":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()

    def _resolve_key(self, mapping: BisMapping, country_iso3: str) -> str:
        iso2 = BIS_ISO2_BY_ISO3.get(country_iso3)
        if iso2 is None:
            raise DataSourceError(
                f"Country {country_iso3!r} has no BIS ISO2 mapping; "
                "BIS series keys require ISO2 codes"
            )
        return mapping.sdmx_key_template.replace("{cc}", iso2)

    def _build_url(self, dataflow_id: str, key: str) -> str:
        return f"{self.base_url}/data/{dataflow_id}/{key}/all"

    def _build_params(self, start_year: Optional[int], end_year: Optional[int]) -> dict:
        params = {"format": "csv"}
        if start_year is not None:
            params["startPeriod"] = f"{start_year}-Q1"
        if end_year is not None:
            params["endPeriod"] = f"{end_year}-Q4"
        return params

    async def fetch_indicator(
        self,
        country_iso3: str,
        external_series_code: str,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[ObservationDTO]:
        mapping = get_bis_mapping_by_external_code(external_series_code)
        if mapping is None:
            raise SeriesMappingError(
                f"BIS external identity {external_series_code!r} has no canonical "
                "Big Cycle Atlas indicator mapping"
            )
        key = self._resolve_key(mapping, country_iso3)
        url = self._build_url(mapping.dataflow_id, key)
        try:
            response = await self._client.get(
                url, params=self._build_params(start_year, end_year)
            )
        except httpx.HTTPError as exc:
            raise DataSourceHTTPError(f"Request to BIS failed: {exc}") from exc

        if response.status_code != 200:
            raise DataSourceHTTPError(
                f"BIS returned HTTP {response.status_code}",
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
        self, row: dict, expected_iso2: str, mapping: BisMapping
    ) -> None:
        borrowers_cty = (row.get("BORROWERS_CTY") or "").strip()
        if borrowers_cty != expected_iso2:
            raise DataSourceParseError(
                f"BIS row identity violation: requested {expected_iso2!r} "
                f"but row has BORROWERS_CTY={borrowers_cty!r} "
                f"({mapping.external_code})"
            )
        for column, expected in mapping.expected_dims:
            if column not in row:
                continue
            actual = (row.get(column) or "").strip()
            if actual != expected:
                raise DataSourceParseError(
                    f"BIS row identity violation: expected {column}={expected!r} "
                    f"but got {column}={actual!r} ({mapping.external_code})"
                )

    def parse_response(
        self,
        payload: object,
        country_iso3: str,
        external_series_code: str,
    ) -> list[ObservationDTO]:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        if not isinstance(payload, str):
            raise DataSourceParseError(
                "BIS response is not CSV text"
            )

        mapping = get_bis_mapping_by_external_code(external_series_code)
        if mapping is None:
            raise SeriesMappingError(
                f"BIS external identity {external_series_code!r} has no canonical "
                "Big Cycle Atlas indicator mapping"
            )
        expected_iso2 = BIS_ISO2_BY_ISO3.get(country_iso3)
        if expected_iso2 is None:
            raise DataSourceError(
                f"Country {country_iso3!r} has no BIS ISO2 mapping"
            )

        try:
            reader = csv.DictReader(io.StringIO(payload))
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise DataSourceParseError("BIS CSV response has no header row")
            if "TIME_PERIOD" not in fieldnames or "OBS_VALUE" not in fieldnames:
                raise DataSourceParseError(
                    "BIS CSV response is missing TIME_PERIOD/OBS_VALUE columns"
                )
            rows = list(reader)
        except csv.Error as exc:
            raise DataSourceParseError(
                "BIS response is not valid SDMX-CSV"
            ) from exc

        observations: list[ObservationDTO] = []
        for row in rows:
            if row is None:
                continue
            raw_value = (row.get("OBS_VALUE") or "").strip()
            if raw_value == "":
                continue  # missing data is skipped, never zero-filled
            raw_period = (row.get("TIME_PERIOD") or "").strip()
            match = _TIME_PERIOD_RE.match(raw_period)
            if match is None:
                raise DataSourceParseError(
                    f"BIS record has unparseable TIME_PERIOD: {raw_period!r}"
                )
            year, quarter = int(match.group(1)), int(match.group(2))
            self._validate_row_identity(row, expected_iso2, mapping)
            observations.append(
                ObservationDTO(
                    country_iso3=country_iso3,
                    indicator_code=mapping.indicator_code,
                    external_series_code=mapping.external_code,
                    period=year,
                    value=float(raw_value),
                    unit=mapping.external_unit,
                    source_key=self.source_key,
                    # Quarter start date: Q1→01, Q2→04, Q3→07, Q4→10.
                    observation_date=date(year, 1 + (quarter - 1) * 3, 1),
                    release_date=None,
                    retrieved_at=self._retrieved_at,
                    raw_payload=dict(row),
                )
            )
        return observations