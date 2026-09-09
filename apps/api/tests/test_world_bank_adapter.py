import json

import httpx
import pytest

from app.data_sources.base import (
    DataSourceHTTPError,
    DataSourceParseError,
)
from app.data_sources.world_bank import WorldBankAdapter

RETRIEVED_AT_ISO = "2026-09-08T12:00:00+00:00"


def _wb_record(year: int, value: float | None) -> dict:
    return {
        "indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP (current US$)"},
        "country": {"id": "US", "value": "United States"},
        "countryiso3code": "USA",
        "date": str(year),
        "value": value,
        "unit": "",
        "obs_status": "",
        "decimal": "0",
    }


def _wb_response_body(records: list) -> list:
    return [
        {"page": 1, "pages": 1, "per_page": "20000", "total": len(records)},
        records,
    ]


def _make_adapter(handler) -> WorldBankAdapter:
    return WorldBankAdapter(
        transport=httpx.MockTransport(handler),
        retrieved_at=RETRIEVED_AT_ISO,
    )


@pytest.mark.asyncio
async def test_fetch_indicator_parses_records(client=None):
    body = _wb_response_body(
        [
            _wb_record(2020, 21_060.0),
            _wb_record(2021, 23_315.1),
            _wb_record(2022, 25_744.1),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.worldbank.org"
        assert request.url.path.endswith("/country/USA/indicator/NY.GDP.MKTP.CD")
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator("USA", "NY.GDP.MKTP.CD")

    assert [obs.period for obs in observations] == [2020, 2021, 2022]
    assert observations[0].value == 21060.0
    assert observations[0].country_iso3 == "USA"
    assert observations[0].indicator_code == "GDP_CURRENT_USD"
    assert observations[0].external_series_code == "NY.GDP.MKTP.CD"
    assert observations[0].source_key == "world_bank"
    assert observations[0].observation_date.year == 2020
    assert observations[0].observation_date.month == 1
    assert observations[0].release_date is None
    assert observations[0].raw_payload["date"] == "2020"
    assert observations[0].retrieved_at.isoformat() == RETRIEVED_AT_ISO


@pytest.mark.asyncio
async def test_null_and_none_records_are_skipped():
    body = _wb_response_body(
        [
            None,  # trailing null record the API emits
            _wb_record(2019, None),  # missing value
            _wb_record(2020, 21_060.0),
            _wb_record(2021, None),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator("USA", "NY.GDP.MKTP.CD")

    assert [(obs.period, obs.value) for obs in observations] == [(2020, 21060.0)]


@pytest.mark.asyncio
async def test_date_range_param_is_sent():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["date"] == "2015:2020"
        return httpx.Response(
            200, json=_wb_response_body([_wb_record(2015, 18.2), _wb_record(2020, 21.0)])
        )

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator(
            "USA", "NY.GDP.MKTP.CD", start_year=2015, end_year=2020
        )

    assert len(observations) == 2


@pytest.mark.asyncio
async def test_http_error_status_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json=[{"message": [{"id": "120", "key": "Invalid value"}]}])

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceHTTPError) as exc_info:
            await adapter.fetch_indicator("XXX", "NY.GDP.MKTP.CD")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_network_error_wrapped_as_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceHTTPError):
            await adapter.fetch_indicator("USA", "NY.GDP.MKTP.CD")


@pytest.mark.asyncio
async def test_malformed_structure_raises_parse_error():
    async with _make_adapter(lambda request: httpx.Response(200, json={"oops": True})) as adapter:
        with pytest.raises(DataSourceParseError):
            await adapter.fetch_indicator("USA", "NY.GDP.MKTP.CD")


@pytest.mark.asyncio
async def test_malformed_json_raises_parse_error():
    async with _make_adapter(
        lambda request: httpx.Response(200, text="<html>Not JSON</html>")
    ) as adapter:
        with pytest.raises(DataSourceParseError):
            await adapter.fetch_indicator("USA", "NY.GDP.MKTP.CD")