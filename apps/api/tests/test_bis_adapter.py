import httpx
import pytest
from datetime import date

from app.data_sources.base import (
    DataSourceError,
    DataSourceHTTPError,
    DataSourceParseError,
    SeriesMappingError,
)
from app.data_sources.bis import BISAdapter
from app.data_sources.bis_mappings import get_bis_mapping_by_external_code

RETRIEVED_AT_ISO = "2026-09-08T12:00:00+00:00"
GAP_CODE = "WS_CREDIT_GAP/Q.{cc}.P.A.C"
DSR_CODE = "WS_DSR/Q.{cc}.P"

GAP_HEADER = (
    "FREQ,BORROWERS_CTY,TC_BORROWERS,TC_LENDERS,CG_DTYPE,COLLECTION,"
    "DECIMALS,UNIT_MEASURE,UNIT_MULT,TIME_FORMAT,TITLE_TS,TIME_PERIOD,"
    "OBS_VALUE,OBS_STATUS,OBS_CONF,OBS_PRE_BREAK"
)


def _gap_row(iso2: str, time_period: str, value: str) -> str:
    return (
        f"Q,{iso2},P,A,C,E,1,770,0,,Test title,{time_period},{value},A,F,"
    )


def _make_adapter(handler) -> BISAdapter:
    return BISAdapter(
        transport=httpx.MockTransport(handler),
        retrieved_at=RETRIEVED_AT_ISO,
    )


@pytest.mark.asyncio
async def test_fetch_indicator_parses_gap_rows():
    body = "\n".join(
        [
            GAP_HEADER,
            _gap_row("US", "2024-Q3", "-10.2"),
            _gap_row("US", "2025-Q4", "-11.5378"),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "stats.bis.org"
        assert "/data/WS_CREDIT_GAP/Q.US.P.A.C/all" in str(request.url)
        assert request.url.params["format"] == "csv"
        return httpx.Response(200, text=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator(
            "USA", GAP_CODE, start_year=2024, end_year=2025
        )

    assert [obs.period for obs in observations] == [2024, 2025]
    assert observations[1].value == -11.5378
    assert observations[1].country_iso3 == "USA"
    assert observations[1].indicator_code == "CREDIT_TO_GDP_GAP"
    assert observations[1].external_series_code == GAP_CODE
    assert observations[1].source_key == "bis"
    assert observations[1].unit == "percentage of GDP"
    assert observations[1].release_date is None
    assert observations[1].raw_payload["TIME_PERIOD"] == "2025-Q4"


@pytest.mark.asyncio
async def test_quarters_map_to_distinct_quarter_start_dates():
    body = "\n".join(
        [
            GAP_HEADER,
            _gap_row("US", "2025-Q1", "1.0"),
            _gap_row("US", "2025-Q2", "2.0"),
            _gap_row("US", "2025-Q3", "3.0"),
            _gap_row("US", "2025-Q4", "4.0"),
        ]
    )

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        observations = await adapter.fetch_indicator("USA", GAP_CODE)

    dates = [obs.observation_date for obs in observations]
    assert dates == [
        date(2025, 1, 1),
        date(2025, 4, 1),
        date(2025, 7, 1),
        date(2025, 10, 1),
    ]
    assert all(obs.period == 2025 for obs in observations)
    assert len(set(dates)) == 4


@pytest.mark.asyncio
async def test_null_and_missing_values_are_skipped():
    body = "\n".join(
        [
            GAP_HEADER,
            _gap_row("US", "2024-Q4", ""),  # missing value
            _gap_row("US", "2025-Q1", "-12.6"),
            _gap_row("US", "2025-Q2", "   "),  # whitespace-only value
        ]
    )

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        observations = await adapter.fetch_indicator("USA", GAP_CODE)

    assert [obs.period for obs in observations] == [2025]
    assert observations[0].value == -12.6


@pytest.mark.asyncio
async def test_row_with_wrong_series_family_raises():
    # CG_DTYPE=A is the credit-to-GDP ratio, not the gap — must not be
    # silently relabelled as a CREDIT_TO_GDP_GAP observation.
    body = "\n".join(
        [
            GAP_HEADER,
            _gap_row("US", "2025-Q1", "141.6"),  # ratio row (CG_DTYPE=A is in row)
        ]
    )
    ratio_body = body.replace(",P,A,C,E,", ",P,A,A,E,")

    async with _make_adapter(
        lambda request: httpx.Response(200, text=ratio_body)
    ) as adapter:
        with pytest.raises(DataSourceParseError, match="CG_DTYPE"):
            await adapter.fetch_indicator("USA", GAP_CODE)


@pytest.mark.asyncio
async def test_row_from_wrong_country_raises():
    # Server returns US rows for a CHE request — identity violation.
    body = "\n".join([GAP_HEADER, _gap_row("US", "2025-Q4", "-11.5378")])

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        with pytest.raises(DataSourceParseError, match="BORROWERS_CTY"):
            await adapter.fetch_indicator("CHE", GAP_CODE)


@pytest.mark.asyncio
async def test_two_countries_in_one_fixture_scope_correctly():
    body = "\n".join(
        [
            GAP_HEADER,
            _gap_row("US", "2025-Q4", "-11.5378"),
            _gap_row("CH", "2025-Q4", "-17.0378"),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        # Emulate the BIS API: only rows for the requested country's key.
        key = request.url.path.split("/all")[0].split("/")[-1]  # e.g. Q.US.P.A.C
        iso2 = key.split(".")[1]
        rows = [row for row in body.splitlines() if row.startswith(f"Q,{iso2},")]
        return httpx.Response(200, text="\n".join([GAP_HEADER, *rows]))

    async with _make_adapter(handler) as adapter:
        usa_obs = await adapter.fetch_indicator("USA", GAP_CODE)
        che_obs = await adapter.fetch_indicator("CHE", GAP_CODE)

    assert [obs.value for obs in usa_obs] == [-11.5378]
    assert [obs.country_iso3 for obs in usa_obs] == ["USA"]
    assert [obs.value for obs in che_obs] == [-17.0378]
    assert [obs.country_iso3 for obs in che_obs] == ["CHE"]
    assert all(obs.indicator_code == "CREDIT_TO_GDP_GAP" for obs in che_obs)


@pytest.mark.asyncio
async def test_dsr_mapping_parses_with_bis_unit_terminology():
    dsr_header = (
        "FREQ,BORROWERS_CTY,DSR_BORROWERS,COLLECTION,UNIT_MEASURE,UNIT_MULT,"
        "DECIMALS,TITLE_TS,TIME_PERIOD,OBS_VALUE,OBS_CONF,OBS_PRE_BREAK,OBS_STATUS"
    )
    body = "\n".join(
        [
            dsr_header,
            f"Q,CH,P,,367,0,1,Switzerland DSR,2025-Q1,16.3,F,,A",
        ]
    )

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        observations = await adapter.fetch_indicator("CHE", DSR_CODE)

    assert len(observations) == 1
    obs = observations[0]
    assert obs.indicator_code == "DEBT_SERVICE_RATIO"
    assert obs.unit == "per cent"
    assert obs.observation_date == date(2025, 1, 1)
    assert obs.source_key == "bis"
    assert obs.raw_payload["DSR_BORROWERS"] == "P"


@pytest.mark.asyncio
async def test_unknown_external_series_raises_series_mapping_error():
    async with _make_adapter(
        lambda request: httpx.Response(200, text="")
    ) as adapter:
        with pytest.raises(SeriesMappingError):
            await adapter.fetch_indicator("USA", "WS_SOME_OTHER_FLOW/Q.{cc}.X")


@pytest.mark.asyncio
async def test_untracked_country_raises_data_source_error():
    async with _make_adapter(
        lambda request: httpx.Response(200, text="")
    ) as adapter:
        with pytest.raises(DataSourceError, match="ISO2"):
            await adapter.fetch_indicator("ZAF", GAP_CODE)


@pytest.mark.asyncio
async def test_missing_required_csv_columns_raises_parse_error():
    bad_header = "FREQ,BORROWERS_CTY,TIME_PERIOD,SOMETHING_ELSE"
    body = f"{bad_header}\nQ,US,2025-Q1,-11.5"

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        with pytest.raises(DataSourceParseError, match="TIME_PERIOD/OBS_VALUE"):
            await adapter.fetch_indicator("USA", GAP_CODE)


@pytest.mark.asyncio
async def test_unparseable_time_period_raises_parse_error():
    body = "\n".join([GAP_HEADER, _gap_row("US", "2025-M06", "-11.5")])

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        with pytest.raises(DataSourceParseError, match="TIME_PERIOD"):
            await adapter.fetch_indicator("USA", GAP_CODE)


@pytest.mark.asyncio
async def test_http_500_raises_data_source_http_error():
    async with _make_adapter(
        lambda request: httpx.Response(500, text="server error")
    ) as adapter:
        with pytest.raises(DataSourceHTTPError) as exc_info:
            await adapter.fetch_indicator("USA", GAP_CODE)
    assert exc_info.value.status_code == 500


def test_external_code_lookup_round_trips():
    mapping = get_bis_mapping_by_external_code(GAP_CODE)
    assert mapping is not None
    assert mapping.indicator_code == "CREDIT_TO_GDP_GAP"
    assert mapping.dataflow_id == "WS_CREDIT_GAP"
    assert mapping.sdmx_key_template == "Q.{cc}.P.A.C"

    dsr = get_bis_mapping_by_external_code(DSR_CODE)
    assert dsr is not None
    assert dsr.indicator_code == "DEBT_SERVICE_RATIO"
    assert dsr.external_unit == "per cent"