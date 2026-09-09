"""Offline tests for the IMF WEO adapter (Sprint 5.19).

All tests use httpx.MockTransport — no external HTTP in pytest. The mock
responses mirror the verified IMF SDMX 3.0 JSON structure (2026-09-10).
"""
import json
import math
from datetime import date

import httpx
import pytest

from app.data_sources.base import (
    DataSourceError,
    DataSourceHTTPError,
    DataSourceParseError,
    SeriesMappingError,
)
from app.data_sources.imf_weo import ImfWeoAdapter, parse_latest_actual_year
from app.data_sources.imf_weo_mappings import get_imf_weo_mapping_by_external_code

RETRIEVED_AT_ISO = "2026-09-10T12:00:00+00:00"
DEBT_CODE = "WEO/{cc}.GGXWDG_NGDP.A"


def _make_adapter(handler) -> ImfWeoAdapter:
    return ImfWeoAdapter(
        transport=httpx.MockTransport(handler),
        retrieved_at=RETRIEVED_AT_ISO,
    )


def _imf_response(country: str, boundary: str, observations: dict, weo_version: str = "9.0.0"):
    """Build a minimal IMF SDMX 3.0 JSON response matching the verified structure."""
    years = sorted(observations.keys())
    time_values = [{"value": str(y)} for y in years]
    obs_dict = {}
    for idx, y in enumerate(years):
        obs_dict[str(idx)] = [observations[y]]
    return {
        "meta": {},
        "data": {
            "dataSets": [
                {
                    "structure": 0,
                    "action": "Replace",
                    "series": {"0:0:0": {"observations": obs_dict}},
                    "dimensionGroupAttributes": {"0:0::": [[boundary]]},
                }
            ],
            "structures": [
                {
                    "links": [
                        {
                            "urn": f"urn:sdmx:org.sdmx.infomodel.datastructure.Dataflow=IMF.RES:WEO({weo_version})",
                            "title": "Dataflow",
                        }
                    ],
                    "dimensions": {
                        "series": [
                            {"id": "COUNTRY", "keyPosition": 0, "values": [{"id": country}]},
                            {"id": "INDICATOR", "keyPosition": 1, "values": [{"id": "GGXWDG_NGDP"}]},
                            {"id": "FREQUENCY", "keyPosition": 2, "values": [{"id": "A"}]},
                        ],
                        "observation": [
                            {"id": "TIME_PERIOD", "keyPosition": 3, "values": time_values}
                        ],
                    },
                    "attributes": {
                        "dataAttributes": [
                            {"id": "LATEST_ACTUAL_ANNUAL_DATA"},
                        ],
                    },
                }
            ],
        },
    }


@pytest.mark.asyncio
async def test_fetch_indicator_parses_historical_actuals():
    obs = {2020: "100.5", 2021: "105.2", 2022: "110.0", 2023: "115.0"}
    body = _imf_response("USA", "2023", obs)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.imf.org"
        assert "/data/dataflow/IMF.RES/WEO/+/" in str(request.url)
        assert "USA.GGXWDG_NGDP.A" in str(request.url)
        assert request.url.params["format"] == "jsondata"
        assert request.url.params["attributes"] == "LATEST_ACTUAL_ANNUAL_DATA"
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator("USA", DEBT_CODE)

    assert [o.period for o in observations] == [2020, 2021, 2022, 2023]
    assert observations[0].value == 100.5
    assert observations[0].country_iso3 == "USA"
    assert observations[0].indicator_code == "GOVERNMENT_DEBT_GDP"
    assert observations[0].external_series_code == DEBT_CODE
    assert observations[0].source_key == "imf"
    assert observations[0].unit == "percent of GDP"
    assert observations[0].release_date is None
    assert observations[0].observation_date == date(2020, 1, 1)
    assert observations[0].raw_payload["weo_version"] == "9.0.0"
    assert observations[0].raw_payload["provider_indicator"] == "GGXWDG_NGDP"
    assert observations[0].raw_payload["latest_actual_annual_data"] == "2023"
    assert observations[0].raw_payload["observation_status"] == "actual"


@pytest.mark.asyncio
async def test_forecast_years_excluded():
    obs = {2023: "115.0", 2024: "120.0", 2025: "125.0", 2026: "130.0"}
    body = _imf_response("USA", "2024", obs)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator("USA", DEBT_CODE)

    # 2025 and 2026 are forecasts (boundary = 2024) — excluded.
    assert [o.period for o in observations] == [2023, 2024]
    assert all(o.raw_payload["observation_status"] == "actual" for o in observations)


@pytest.mark.asyncio
async def test_fiscal_year_boundary_parsed():
    # IND uses "FY2024/25" → boundary year 2025
    obs = {2023: "83.0", 2024: "83.3", 2025: "82.5", 2026: "81.6"}
    body = _imf_response("IND", "FY2024/25", obs)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator("IND", DEBT_CODE)

    # boundary = 2025, so 2026 is excluded
    assert [o.period for o in observations] == [2023, 2024, 2025]


def test_parse_latest_actual_year_plain():
    assert parse_latest_actual_year("2024") == 2024
    assert parse_latest_actual_year("2025") == 2025


def test_parse_latest_actual_year_fiscal():
    assert parse_latest_actual_year("FY2024/25") == 2025
    assert parse_latest_actual_year("FY2023/24") == 2024


def test_parse_latest_actual_year_missing_raises():
    with pytest.raises(DataSourceParseError):
        parse_latest_actual_year(None)
    with pytest.raises(DataSourceParseError):
        parse_latest_actual_year("")


def test_parse_latest_actual_year_unparseable_raises():
    with pytest.raises(DataSourceParseError):
        parse_latest_actual_year("garbage")


@pytest.mark.asyncio
async def test_wrong_country_rejected():
    body = _imf_response("CHN", "2024", {2020: "50.0"})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="COUNTRY"):
            await adapter.fetch_indicator("USA", DEBT_CODE)


@pytest.mark.asyncio
async def test_wrong_indicator_rejected():
    body = _imf_response("USA", "2024", {2020: "50.0"})
    body["data"]["structures"][0]["dimensions"]["series"][1]["values"] = [{"id": "NGDP_RPCH"}]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="INDICATOR"):
            await adapter.fetch_indicator("USA", DEBT_CODE)


@pytest.mark.asyncio
async def test_wrong_frequency_rejected():
    body = _imf_response("USA", "2024", {2020: "50.0"})
    body["data"]["structures"][0]["dimensions"]["series"][2]["values"] = [{"id": "Q"}]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="FREQUENCY"):
            await adapter.fetch_indicator("USA", DEBT_CODE)


@pytest.mark.asyncio
async def test_null_value_skipped():
    obs = {2020: "100.0", 2021: None, 2022: "110.0"}
    body = _imf_response("USA", "2022", obs)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator("USA", DEBT_CODE)

    assert [o.period for o in observations] == [2020, 2022]


@pytest.mark.asyncio
async def test_nonfinite_value_rejected():
    obs = {2020: "NaN"}
    body = _imf_response("USA", "2020", obs)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="not finite"):
            await adapter.fetch_indicator("USA", DEBT_CODE)


@pytest.mark.asyncio
async def test_missing_boundary_raises():
    body = _imf_response("USA", "2024", {2020: "100.0"})
    body["data"]["dataSets"][0]["dimensionGroupAttributes"] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="dimensionGroupAttributes"):
            await adapter.fetch_indicator("USA", DEBT_CODE)


@pytest.mark.asyncio
async def test_unmapped_external_code_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    async with _make_adapter(handler) as adapter:
        with pytest.raises(SeriesMappingError):
            await adapter.fetch_indicator("USA", "WEO/{cc}.UNKNOWN.A")


@pytest.mark.asyncio
async def test_unknown_country_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceError, match="COUNTRY mapping"):
            await adapter.fetch_indicator("BRA", DEBT_CODE)


@pytest.mark.asyncio
async def test_http_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceHTTPError):
            await adapter.fetch_indicator("USA", DEBT_CODE)


@pytest.mark.asyncio
async def test_4xx_not_retried_at_adapter_level():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceHTTPError) as exc_info:
            await adapter.fetch_indicator("USA", DEBT_CODE)
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_start_end_year_filter():
    obs = {2018: "90.0", 2019: "95.0", 2020: "100.0", 2021: "105.0", 2022: "110.0"}
    body = _imf_response("USA", "2022", obs)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator(
            "USA", DEBT_CODE, start_year=2019, end_year=2021
        )

    assert [o.period for o in observations] == [2019, 2020, 2021]


@pytest.mark.asyncio
async def test_no_future_projection_persisted():
    obs = {2024: "100.0", 2025: "105.0", 2026: "110.0", 2030: "120.0"}
    body = _imf_response("USA", "2024", obs)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator("USA", DEBT_CODE)

    max_year = max(o.period for o in observations)
    assert max_year == 2024  # boundary year — no future projection


@pytest.mark.asyncio
async def test_raw_payload_provenance():
    obs = {2020: "100.0"}
    body = _imf_response("USA", "2024", obs, weo_version="9.0.0")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator("USA", DEBT_CODE)

    rp = observations[0].raw_payload
    assert rp["weo_version"] == "9.0.0"
    assert rp["provider_indicator"] == "GGXWDG_NGDP"
    assert rp["provider_country"] == "USA"
    assert rp["frequency"] == "A"
    assert rp["latest_actual_annual_data"] == "2024"
    assert rp["observation_status"] == "actual"
    assert rp["value"] == "100.0"


@pytest.mark.asyncio
async def test_all_tracked_8_countries_resolvable():
    """All 8 tracked countries have ISO3 mappings — no alias guess needed."""
    from app.data_sources.imf_weo_mappings import IMF_COUNTRY_BY_ISO3

    for iso3 in ["USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND"]:
        assert IMF_COUNTRY_BY_ISO3[iso3] == iso3


# --- Sprint 5.20 Part 0: hardening regressions --------------------------------


def test_parse_latest_actual_year_fiscal_century_rollover():
    """FY1999/00 -> 2000, FY2099/00 -> 2100 (century rollover)."""
    assert parse_latest_actual_year("FY1999/00") == 2000
    assert parse_latest_actual_year("FY2099/00") == 2100
    assert parse_latest_actual_year("FY2024/25") == 2025
    assert parse_latest_actual_year("FY2023/24") == 2024


@pytest.mark.asyncio
async def test_positive_infinity_rejected():
    obs = {2020: "Infinity"}
    body = _imf_response("USA", "2020", obs)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="not finite"):
            await adapter.fetch_indicator("USA", DEBT_CODE)


@pytest.mark.asyncio
async def test_negative_infinity_rejected():
    obs = {2020: "-Infinity"}
    body = _imf_response("USA", "2020", obs)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="not finite"):
            await adapter.fetch_indicator("USA", DEBT_CODE)


@pytest.mark.asyncio
async def test_nan_value_rejected():
    obs = {2020: "NaN"}
    body = _imf_response("USA", "2020", obs)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="not finite"):
            await adapter.fetch_indicator("USA", DEBT_CODE)


@pytest.mark.asyncio
async def test_missing_attributes_section_raises():
    """Structure without dataAttributes cannot locate LATEST_ACTUAL_ANNUAL_DATA."""
    body = _imf_response("USA", "2024", {2020: "100.0"})
    del body["data"]["structures"][0]["attributes"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="attributes"):
            await adapter.fetch_indicator("USA", DEBT_CODE)


@pytest.mark.asyncio
async def test_wrong_attribute_id_raises():
    """If LATEST_ACTUAL_ANNUAL_DATA is not in the dataAttributes list, raise."""
    body = _imf_response("USA", "2024", {2020: "100.0"})
    body["data"]["structures"][0]["attributes"]["dataAttributes"] = [
        {"id": "SOME_OTHER_ATTRIBUTE"},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="LATEST_ACTUAL_ANNUAL_DATA"):
            await adapter.fetch_indicator("USA", DEBT_CODE)


@pytest.mark.asyncio
async def test_attribute_positional_extraction():
    """Boundary is extracted by position from dataAttributes, not 'first'."""
    body = _imf_response("USA", "2024", {2020: "100.0", 2024: "110.0"})
    # Put LATEST_ACTUAL_ANNUAL_DATA at position 1, not 0
    body["data"]["structures"][0]["attributes"]["dataAttributes"] = [
        {"id": "OTHER_ATTR"},
        {"id": "LATEST_ACTUAL_ANNUAL_DATA"},
    ]
    # dimensionGroupAttributes must also have the value at position 1
    body["data"]["dataSets"][0]["dimensionGroupAttributes"] = {
        "0:0::": [None, ["2024"]],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator("USA", DEBT_CODE)

    # boundary = 2024, so 2024 is included
    assert [o.period for o in observations] == [2020, 2024]
