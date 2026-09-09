"""WID (World Inequality Database) adapter — bulk download CSV path.

Sprint 5.20 Part B. Reads country-level CSV files from the WID bulk archive
(https://wid.world/bulk_download/wid_all_data.zip). No API key required.

Data format (semicolon-delimited CSV):
    country;variable;percentile;year;value;age;pop;data_quality

The adapter takes a pre-downloaded zip path (or downloads it once per batch)
and extracts observations for the requested country + series. Missing values
are skipped — never zero-filled. data_quality is preserved in raw_payload
but NOT used for filtering (official semantics unverified — Sprint 5.20 B1).
"""
import csv
import io
import math
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from app.data_sources.base import (
    BaseDataSourceAdapter,
    DataSourceError,
    DataSourceParseError,
    ObservationDTO,
    SeriesMappingError,
)
from app.data_sources.wid_mappings import (
    WID_COUNTRY_BY_ISO3,
    WidMapping,
    get_wid_mapping_by_external_code,
)

DEFAULT_BULK_URL = "https://wid.world/bulk_download/wid_all_data.zip"


class WidAdapter(BaseDataSourceAdapter):
    """Adapter for WID bulk-download CSV files.

    Unlike HTTP-based adapters (WB/BIS/OECD/IMF), WID uses a single large
    zip archive (882 MB). The adapter accepts a local file path to the
    downloaded zip — the ingestion CLI handles download + caching. This
    keeps pytest fast (mocked zip fixture) and avoids re-downloading 882 MB
    per country.

    Country codes: WID uses ISO2 (US, CN, CH, DE, FR, GB, JP, IN). The
    adapter translates ISO3 → ISO2 via the typed WID_COUNTRY_BY_ISO3 mapping.
    Unknown countries raise DataSourceError.

    Values are fractions (0-1) as published by WID, stored unchanged.
    Finite validation rejects NaN, +inf, -inf. Sprint 6.6.2: the previous
    [0,1] range rejection is RETRACTED — [0,1] is the COMPLEMENT_0_100
    normalization domain, NOT a WID ingestion validity domain. A finite
    provider value outside [0,1] is preserved as the immutable raw
    Observation.value; whether Atlas can normalize it is a later-layer
    question (NormalizationDataError if scoring is attempted).
    """

    source_key = "wid"

    def __init__(
        self,
        zip_path: Path,
        retrieved_at: Optional[datetime] = None,
    ):
        self._zip_path = zip_path
        self._retrieved_at = retrieved_at or datetime.now(timezone.utc)

    async def aclose(self) -> None:
        pass  # no HTTP client

    async def __aenter__(self) -> "WidAdapter":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()

    def _resolve_country_code(self, country_iso3: str) -> str:
        code = WID_COUNTRY_BY_ISO3.get(country_iso3)
        if code is None:
            raise DataSourceError(
                f"Country {country_iso3!r} has no WID ISO2 mapping; "
                "WID country files use 2-letter ISO codes"
            )
        return code

    def _file_name(self, country_code: str) -> str:
        return f"WID_data_{country_code}.csv"

    async def fetch_indicator(
        self,
        country_iso3: str,
        external_series_code: str,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[ObservationDTO]:
        """Async fetch — WID reads from a local zip, no HTTP needed.

        The method is async to conform to the BaseDataSourceAdapter contract
        (the ingestion service awaits it). The actual zip read is synchronous
        (fast local I/O).
        """
        mapping = get_wid_mapping_by_external_code(external_series_code)
        if mapping is None:
            raise SeriesMappingError(
                f"WID external identity {external_series_code!r} has no "
                "canonical Big Cycle Atlas indicator mapping"
            )
        country_code = self._resolve_country_code(country_iso3)
        file_name = self._file_name(country_code)

        if not self._zip_path.exists():
            raise DataSourceError(
                f"WID bulk archive not found at {self._zip_path!s}"
            )

        try:
            with zipfile.ZipFile(self._zip_path, "r") as zf:
                try:
                    raw_bytes = zf.read(file_name)
                except KeyError:
                    raise DataSourceError(
                        f"WID archive has no file {file_name!r} for country "
                        f"{country_iso3!r}"
                    ) from None
        except zipfile.BadZipFile as exc:
            raise DataSourceError(
                f"WID archive is corrupt: {exc}"
            ) from exc

        return self.parse_response(
            raw_bytes, country_iso3, external_series_code,
            start_year=start_year, end_year=end_year,
        )

    def parse_response(
        self,
        payload: bytes,
        country_iso3: str,
        external_series_code: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[ObservationDTO]:
        if not isinstance(payload, (bytes, bytearray)):
            raise DataSourceParseError("WID response must be bytes")

        mapping = get_wid_mapping_by_external_code(external_series_code)
        if mapping is None:
            raise SeriesMappingError(
                f"WID external identity {external_series_code!r} has no "
                "canonical Big Cycle Atlas indicator mapping"
            )
        expected_country = WID_COUNTRY_BY_ISO3.get(country_iso3)
        if expected_country is None:
            raise DataSourceError(
                f"Country {country_iso3!r} has no WID ISO2 mapping"
            )

        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DataSourceParseError(
                "WID CSV is not valid UTF-8"
            ) from exc

        try:
            reader = csv.DictReader(io.StringIO(text), delimiter=";")
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise DataSourceParseError("WID CSV has no header row")
            required = {"country", "variable", "percentile", "year", "value", "age", "pop", "data_quality"}
            missing = required - set(fieldnames)
            if missing:
                raise DataSourceParseError(
                    f"WID CSV missing columns: {sorted(missing)}"
                )
            rows = list(reader)
        except csv.Error as exc:
            raise DataSourceParseError(
                "WID response is not valid semicolon-CSV"
            ) from exc

        observations: list[ObservationDTO] = []
        for row in rows:
            if row is None:
                continue

            # Validate row identity
            row_country = (row.get("country") or "").strip()
            if row_country != expected_country:
                raise DataSourceParseError(
                    f"WID row identity violation: expected country="
                    f"{expected_country!r} but got {row_country!r}"
                )

            row_variable = (row.get("variable") or "").strip()
            if row_variable != mapping.variable:
                continue  # not our series — skip silently (file has many variables)

            row_percentile = (row.get("percentile") or "").strip()
            if row_percentile != mapping.percentile:
                continue  # different percentile — skip

            row_age = (row.get("age") or "").strip()
            if row_age != mapping.age:
                continue  # different age code — skip

            row_pop = (row.get("pop") or "").strip()
            if row_pop != mapping.pop:
                continue  # different population type — skip

            # Parse value
            raw_value = (row.get("value") or "").strip()
            if raw_value == "":
                continue  # missing data — never zero-filled
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                raise DataSourceParseError(
                    f"WID value is not numeric: {raw_value!r}"
                ) from None

            if not math.isfinite(value):
                raise DataSourceParseError(
                    f"WID value is not finite: {raw_value!r}"
                )

            # Sprint 6.6.2: raw-preservation guard fix.
            # [0,1] is the COMPLEMENT_0_100 NORMALIZATION domain, NOT a
            # WID ingestion validity domain (DEC-034 Sprint 6.6.1/6.6.2).
            # The WID Codes Dictionary states a representation convention
            # ("Shares and wealth/income ratios are given as a fraction of
            # 1"), NOT a formal per-series domain guarantee. The theoretical
            # domain for a net-wealth top-10% share is NOT strictly [0,1] —
            # if the bottom 90% has collectively negative net wealth, the
            # top 10% could hold more than 100% of total net wealth.
            # Therefore a finite provider value outside [0,1] is accepted
            # and preserved as the immutable raw Observation.value. Whether
            # Atlas can normalize it is a LATER-LAYER question
            # (NormalizationDataError if scoring is attempted outside [0,1]).
            # The previous [0,1] hard rejection (Sprint 5.20) is RETRACTED as
            # an Atlas scoring assumption masquerading as a provider contract.

            # Parse year
            raw_year = (row.get("year") or "").strip()
            if not raw_year:
                continue
            try:
                year = int(raw_year)
            except ValueError:
                raise DataSourceParseError(
                    f"WID year is not an integer: {raw_year!r}"
                ) from None

            # Parse data_quality (preserved but not used for filtering).
            # Sprint 5.20.1: preserve the EXACT raw provider representation
            # (data_quality_raw) alongside the typed convenience value
            # (data_quality). The raw string is never lost — unknown codes
            # such as "A" stay "A", not None-or-zero. DEC-027: NO filtering.
            raw_dq = (row.get("data_quality") or "").strip()
            try:
                data_quality = int(raw_dq) if raw_dq else None
            except ValueError:
                data_quality = None

            if start_year is not None and year < start_year:
                continue
            if end_year is not None and year > end_year:
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
                        "provider_country": expected_country,
                        "variable": row_variable,
                        "percentile": row_percentile,
                        "age": row_age,
                        "pop": row_pop,
                        "data_quality_raw": raw_dq,
                        "data_quality": data_quality,
                        "value": raw_value,
                    },
                )
            )

        return observations
