import json
import math
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
from app.data_sources.imf_weo_mappings import (
    IMF_COUNTRY_BY_ISO3,
    ImfWeoMapping,
    get_imf_weo_mapping_by_external_code,
)

DEFAULT_TIMEOUT_SECONDS = 30.0

_FISCAL_YEAR_RE = re.compile(r"FY(\d{4})/(\d{2})")
_PLAIN_YEAR_RE = re.compile(r"^(\d{4})$")


def _build_ssl_context() -> ssl.SSLContext:
    # Load CAs from memory: this machine's python.exe lacks the OPENSSL_Applink
    # export, so OpenSSL crashes on FILE*-based CA loading (load_verify_locations
    # with a file). cadata bypasses the file BIO entirely.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_default_certs()
    pem = Path(certifi.where()).read_text(encoding="utf-8")
    context.load_verify_locations(cadata=pem)
    return context


def parse_latest_actual_year(raw: str | None) -> int:
    """Parse LATEST_ACTUAL_ANNUAL_DATA into a calendar-year boundary.

    WEO uses calendar years for most countries ("2024") but fiscal-year
    labels for some (e.g. India "FY2024/25"). The WEO year label for a
    fiscal-year country is the ending calendar year, so "FY2024/25" → 2025.
    Observations with year > boundary are forecasts and must be excluded.

    Raises DataSourceParseError on unparseable values — the boundary is
    never guessed.
    """
    if raw is None:
        raise DataSourceParseError(
            "LATEST_ACTUAL_ANNUAL_DATA is missing — cannot determine "
            "the historical/forecast boundary"
        )
    raw = raw.strip()
    m = _PLAIN_YEAR_RE.match(raw)
    if m:
        return int(m.group(1))
    m = _FISCAL_YEAR_RE.search(raw)
    if m:
        start_year = int(m.group(1))
        end_suffix = int(m.group(2))
        # The fiscal-year label uses a 2-digit suffix for the ending year.
        # FY2024/25 -> 2025, FY1999/00 -> 2000, FY2099/00 -> 2100.
        # The suffix is relative to the start year's century: if the suffix
        # is >= the last two digits of the start year, the end year is in the
        # same century; otherwise it rolled over into the next century.
        start_century = start_year // 100 * 100
        start_last_two = start_year % 100
        if end_suffix >= start_last_two:
            return start_century + end_suffix
        else:
            return start_century + 100 + end_suffix
    raise DataSourceParseError(
        f"Cannot parse LATEST_ACTUAL_ANNUAL_DATA: {raw!r}"
    )


class ImfWeoAdapter(BaseDataSourceAdapter):
    """Adapter for the official IMF SDMX 3.0 API (WEO dataflow).

    Endpoint:
    {base}/data/dataflow/{agency_id}/{dataflow_id}/+/{key}
        ?format=jsondata&attributes=LATEST_ACTUAL_ANNUAL_DATA
    Response is SDMX-JSON. No authentication required for WEO (verified
    2026-09-10). The dataflow version "+" requests the latest WEO vintage;
    the actual version is captured from the response structure and stored
    in raw_payload for provenance.

    Key dimension order (verified via structure metadata + live queries):
    COUNTRY, INDICATOR, FREQUENCY. {cc} resolves to the IMF COUNTRY code,
    which is ISO3 — identical to Big Cycle Atlas ISO3 codes for all 8
    tracked countries. Unknown ISO3 codes raise DataSourceError.

    Historical/forecast boundary:
    WEO mixes historical actuals and projections in one series. The
    LATEST_ACTUAL_ANNUAL_DATA dimension-group attribute marks the last
    actual year. The adapter requests this attribute alongside the data
    and EXCLUDES any observation with year > boundary. For fiscal-year
    countries (e.g. IND "FY2024/25"), the ending calendar year is parsed.
    No hard-coded "2024 is historical forever" rule — the boundary is
    always provider-driven. If the attribute is missing, the adapter
    raises DataSourceParseError rather than guessing.

    The requested external_series_code must be the country-independent
    identity "{dataflow_id}/{sdmx_key_template}" (e.g.
    "WEO/{cc}.GGXWDG_NGDP.A"). Unknown codes raise SeriesMappingError.

    Period handling: annual "2024" → observation_date 2024-01-01; `period`
    stays the year. Null/empty OBS_VALUE rows are skipped — missing data
    is never zero-filled. The API provides no reliable release timestamp,
    so release_date stays None.
    """

    source_key = "imf"
    DEFAULT_BASE_URL = "https://api.imf.org/external/sdmx/3.0"

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

    async def __aenter__(self) -> "ImfWeoAdapter":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()

    def _resolve_key(self, mapping: ImfWeoMapping, country_iso3: str) -> str:
        country_code = IMF_COUNTRY_BY_ISO3.get(country_iso3)
        if country_code is None:
            raise DataSourceError(
                f"Country {country_iso3!r} has no IMF WEO COUNTRY mapping; "
                "IMF WEO series keys require an ISO3 COUNTRY code"
            )
        return mapping.sdmx_key_template.replace("{cc}", country_code)

    def _build_url(self, mapping: ImfWeoMapping, key: str) -> str:
        # SDMX 3.0 REST path uses "/" separators (verified live 2026-09-10):
        # /data/dataflow/{agency}/{dataflow}/{version}/{key}
        # Comma-separated agency,dataflow,version returns 404.
        return (
            f"{self.base_url}/data/dataflow/{mapping.agency_id}/"
            f"{mapping.dataflow_id}/+/{key}"
        )

    def _build_params(self) -> dict:
        return {
            "format": "jsondata",
            "attributes": "LATEST_ACTUAL_ANNUAL_DATA",
        }

    async def fetch_indicator(
        self,
        country_iso3: str,
        external_series_code: str,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[ObservationDTO]:
        mapping = get_imf_weo_mapping_by_external_code(external_series_code)
        if mapping is None:
            raise SeriesMappingError(
                f"IMF WEO external identity {external_series_code!r} has no "
                "canonical Big Cycle Atlas indicator mapping"
            )
        key = self._resolve_key(mapping, country_iso3)
        url = self._build_url(mapping, key)
        try:
            response = await self._client.get(url, params=self._build_params())
        except httpx.HTTPError as exc:
            raise DataSourceHTTPError(f"Request to IMF failed: {exc}") from exc

        if response.status_code != 200:
            raise DataSourceHTTPError(
                f"IMF returned HTTP {response.status_code}",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise DataSourceParseError(
                "IMF response is not valid JSON"
            ) from exc

        observations = self.parse_response(
            payload, country_iso3, external_series_code
        )
        return [
            obs
            for obs in observations
            if (start_year is None or obs.period >= start_year)
            and (end_year is None or obs.period <= end_year)
        ]

    def parse_response(
        self,
        payload: object,
        country_iso3: str,
        external_series_code: str,
    ) -> list[ObservationDTO]:
        if not isinstance(payload, dict):
            raise DataSourceParseError("IMF response is not a JSON object")

        mapping = get_imf_weo_mapping_by_external_code(external_series_code)
        if mapping is None:
            raise SeriesMappingError(
                f"IMF WEO external identity {external_series_code!r} has no "
                "canonical Big Cycle Atlas indicator mapping"
            )
        expected_country = IMF_COUNTRY_BY_ISO3.get(country_iso3)
        if expected_country is None:
            raise DataSourceError(
                f"Country {country_iso3!r} has no IMF WEO COUNTRY mapping"
            )

        data = payload.get("data")
        if not isinstance(data, dict):
            raise DataSourceParseError("IMF response has no 'data' object")

        data_sets = data.get("dataSets")
        if not isinstance(data_sets, list) or len(data_sets) == 0:
            raise DataSourceParseError("IMF response has no dataSets")

        structures = data.get("structures")
        if not isinstance(structures, list) or len(structures) == 0:
            raise DataSourceParseError("IMF response has no structures")

        data_set = data_sets[0]
        if not isinstance(data_set, dict):
            raise DataSourceParseError("IMF dataSet is not an object")

        structure = structures[0]
        if not isinstance(structure, dict):
            raise DataSourceParseError("IMF structure is not an object")

        # --- Validate dimensions against expected identity ---
        dims = structure.get("dimensions")
        if not isinstance(dims, dict):
            raise DataSourceParseError("IMF structure has no dimensions")

        series_dims = dims.get("series")
        if not isinstance(series_dims, list) or len(series_dims) != 3:
            raise DataSourceParseError(
                "IMF structure must have exactly 3 series dimensions "
                "(COUNTRY, INDICATOR, FREQUENCY)"
            )

        country_dim = series_dims[0]
        indicator_dim = series_dims[1]
        frequency_dim = series_dims[2]

        country_values = country_dim.get("values", [])
        indicator_values = indicator_dim.get("values", [])
        frequency_values = frequency_dim.get("values", [])

        if len(country_values) != 1 or country_values[0].get("id") != expected_country:
            raise DataSourceParseError(
                f"IMF row identity violation: requested COUNTRY={expected_country!r} "
                f"but response has COUNTRY={country_values!r}"
            )
        if (
            len(indicator_values) != 1
            or indicator_values[0].get("id") != mapping.sdmx_key_template.split(".")[1]
        ):
            raise DataSourceParseError(
                f"IMF row identity violation: requested INDICATOR="
                f"{mapping.sdmx_key_template.split('.')[1]!r} but response has "
                f"INDICATOR={indicator_values!r}"
            )
        if len(frequency_values) != 1 or frequency_values[0].get("id") != "A":
            raise DataSourceParseError(
                f"IMF row identity violation: expected FREQUENCY=A but got "
                f"FREQUENCY={frequency_values!r}"
            )

        # --- Extract WEO vintage version from structure links ---
        weo_version = None
        links = structure.get("links", [])
        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict) and link.get("title") == "Dataflow":
                    urn = link.get("urn", "")
                    # urn:sdmx:org.sdmx.infomodel.datastructure.Dataflow=IMF.RES:WEO(9.0.0)
                    m = re.search(r"WEO\(([^)]+)\)", urn)
                    if m:
                        weo_version = m.group(1)
                    break

        # --- Extract TIME_PERIOD values ---
        obs_dims = dims.get("observation")
        if not isinstance(obs_dims, list) or len(obs_dims) == 0:
            raise DataSourceParseError("IMF structure has no observation dimensions")

        time_period_dim = obs_dims[0]
        time_period_values = time_period_dim.get("values", [])
        if not isinstance(time_period_values, list):
            raise DataSourceParseError("IMF TIME_PERIOD values is not a list")

        # --- Extract LATEST_ACTUAL_ANNUAL_DATA boundary ---
        # Validate the attribute identity from the SDMX structure, not just
        # "first attribute". The structure defines data attributes with ids;
        # dimensionGroupAttributes values are positional per that definition.
        # We locate LATEST_ACTUAL_ANNUAL_DATA by id and use its position.
        attrs_def = structure.get("attributes")
        if not isinstance(attrs_def, dict):
            raise DataSourceParseError(
                "IMF structure has no attributes section — cannot locate "
                "LATEST_ACTUAL_ANNUAL_DATA"
            )
        data_attrs = attrs_def.get("dataAttributes")
        if not isinstance(data_attrs, list):
            raise DataSourceParseError(
                "IMF structure has no dataAttributes list — cannot locate "
                "LATEST_ACTUAL_ANNUAL_DATA"
            )

        # Find the position of LATEST_ACTUAL_ANNUAL_DATA in the data
        # attributes list. Each data attribute has an "id" field.
        boundary_attr_idx = None
        for idx, attr in enumerate(data_attrs):
            if isinstance(attr, dict) and attr.get("id") == "LATEST_ACTUAL_ANNUAL_DATA":
                boundary_attr_idx = idx
                break
        if boundary_attr_idx is None:
            raise DataSourceParseError(
                "IMF structure does not define LATEST_ACTUAL_ANNUAL_DATA — "
                "cannot determine the historical/forecast boundary"
            )

        dim_group_attrs = data_set.get("dimensionGroupAttributes")
        if not isinstance(dim_group_attrs, dict) or len(dim_group_attrs) == 0:
            raise DataSourceParseError(
                "IMF response has no dimensionGroupAttributes — cannot "
                "determine LATEST_ACTUAL_ANNUAL_DATA boundary"
            )

        # For a single-country single-indicator request, the key is "0:0::".
        # Take the first (and only) attribute group. The value is a list
        # positional to the dataAttributes definition.
        raw_boundary = None
        for _key, attrs in dim_group_attrs.items():
            if isinstance(attrs, list) and len(attrs) > boundary_attr_idx:
                val = attrs[boundary_attr_idx]
                if isinstance(val, list) and len(val) > 0:
                    raw_boundary = val[0]
                elif isinstance(val, str):
                    raw_boundary = val
                # None is acceptable (attribute absent for this group)
                break

        boundary_year = parse_latest_actual_year(raw_boundary)

        # --- Extract observations ---
        series = data_set.get("series")
        if not isinstance(series, dict) or len(series) == 0:
            raise DataSourceParseError("IMF response has no series")

        # For a single-country single-indicator request, there is one series.
        series_key = next(iter(series))
        series_data = series[series_key]
        if not isinstance(series_data, dict):
            raise DataSourceParseError("IMF series data is not an object")

        observations_raw = series_data.get("observations")
        if not isinstance(observations_raw, dict):
            raise DataSourceParseError("IMF series has no observations")

        observations: list[ObservationDTO] = []
        for obs_key, obs_value in observations_raw.items():
            if not isinstance(obs_value, list) or len(obs_value) == 0:
                continue
            value_raw = obs_value[0]
            if value_raw is None:
                continue  # missing data is skipped, never zero-filled
            try:
                value = float(value_raw)
            except (TypeError, ValueError):
                raise DataSourceParseError(
                    f"IMF observation value is not numeric: {value_raw!r}"
                ) from None
            if not math.isfinite(value):  # rejects NaN, +inf, -inf
                raise DataSourceParseError(
                    f"IMF observation value is not finite: {value_raw!r}"
                )

            idx = int(obs_key)
            if idx >= len(time_period_values):
                raise DataSourceParseError(
                    f"IMF observation index {idx} out of range for TIME_PERIOD"
                )
            year_raw = time_period_values[idx].get("value")
            if year_raw is None:
                raise DataSourceParseError(
                    f"IMF TIME_PERIOD at index {idx} has no value"
                )
            year = int(year_raw)

            # Exclude forecast years — boundary is provider-driven.
            if year > boundary_year:
                continue

            observations.append(
                ObservationDTO(
                    country_iso3=country_iso3,
                    indicator_code=mapping.indicator_code,
                    external_series_code=mapping.external_code,
                    period=year,
                    value=value,
                    unit=mapping.external_unit,
                    source_key=self.source_key,
                    observation_date=date(year, 1, 1),
                    release_date=None,
                    retrieved_at=self._retrieved_at,
                    raw_payload={
                        "weo_version": weo_version,
                        "provider_indicator": mapping.sdmx_key_template.split(".")[1],
                        "provider_country": expected_country,
                        "frequency": "A",
                        "latest_actual_annual_data": raw_boundary,
                        "observation_status": "actual",
                        "value": value_raw,
                    },
                )
            )
        return observations
