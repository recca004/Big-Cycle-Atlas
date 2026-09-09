import httpx
import pytest
from datetime import date

from app.data_sources.base import (
    DataSourceError,
    DataSourceHTTPError,
    DataSourceNoDataError,
    DataSourceParseError,
    SeriesMappingError,
)
from app.data_sources.oecd import OECDAdapter
from app.data_sources.oecd_mappings import get_oecd_mapping_by_external_code

RETRIEVED_AT_ISO = "2026-09-08T12:00:00+00:00"
PROD_CODE = "DSD_PDB@DF_PDB/{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP"
ULC_CODE = "DSD_PDB@DF_PDB_ULC_Q/{cc}.Q.ULCE._T.PA.V.GY.S.NC"

PROD_HEADER = (
    "REF_AREA,FREQ,MEASURE,ACTIVITY,UNIT_MEASURE,PRICE_BASE,TRANSFORMATION,"
    "ASSET_CODE,CONVERSION_TYPE,TIME_PERIOD,OBS_VALUE,OBS_STATUS,UNIT_MULT,"
    "DECIMALS,BASE_PER"
)
ULC_HEADER = (
    "REF_AREA,FREQ,MEASURE,ACTIVITY,UNIT_MEASURE,PRICE_BASE,TRANSFORMATION,"
    "ADJUSTMENT,CONVERSION_TYPE,TIME_PERIOD,OBS_VALUE,OBS_STATUS,UNIT_MULT,"
    "DECIMALS"
)


def _prod_row(ref_area: str, time_period: str, value: str) -> str:
    return (
        f"{ref_area},A,GDPHRS,_T,USD_PPP_H,LR,N,_Z,PPP,{time_period},"
        f"{value},A,0,2,"
    )


def _ulc_row(ref_area: str, time_period: str, value: str) -> str:
    return f"{ref_area},Q,ULCE,_T,PA,V,GY,S,NC,{time_period},{value},A,0,2"


def _make_adapter(handler) -> OECDAdapter:
    return OECDAdapter(
        transport=httpx.MockTransport(handler),
        retrieved_at=RETRIEVED_AT_ISO,
    )


@pytest.mark.asyncio
async def test_fetch_indicator_parses_productivity_rows():
    body = "\n".join(
        [
            PROD_HEADER,
            _prod_row("CHE", "2019", "82.41"),
            _prod_row("CHE", "2024", "89.66"),
            _prod_row("CHE", "2025", "90.51776442200304"),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "sdmx.oecd.org"
        assert (
            "/data/OECD.SDD.TPS,DSD_PDB@DF_PDB,2.0/CHE.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP"
            in str(request.url)
        )
        assert request.url.params["format"] == "csvfilewithlabels"
        assert request.url.params["startPeriod"] == "2019"
        assert request.url.params["endPeriod"] == "2025"
        return httpx.Response(200, text=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator(
            "CHE", PROD_CODE, start_year=2019, end_year=2025
        )

    assert [obs.period for obs in observations] == [2019, 2024, 2025]
    assert observations[2].value == 90.51776442200304
    assert observations[2].country_iso3 == "CHE"
    assert observations[2].indicator_code == "LABOUR_PRODUCTIVITY_PER_HOUR"
    assert observations[2].external_series_code == PROD_CODE
    assert observations[2].source_key == "oecd"
    assert observations[2].unit == "US dollars per hour, PPP converted"
    assert observations[2].release_date is None
    assert observations[2].raw_payload["OBS_STATUS"] == "A"
    assert observations[2].raw_payload["PRICE_BASE"] == "LR"


@pytest.mark.asyncio
async def test_annual_period_maps_to_january_first():
    body = "\n".join([PROD_HEADER, _prod_row("CHE", "2024", "89.66")])

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        observations = await adapter.fetch_indicator("CHE", PROD_CODE)

    assert observations[0].observation_date == date(2024, 1, 1)
    assert observations[0].period == 2024


@pytest.mark.asyncio
async def test_quarters_map_to_distinct_quarter_start_dates():
    body = "\n".join(
        [
            ULC_HEADER,
            _ulc_row("CHE", "2025-Q1", "0.8"),
            _ulc_row("CHE", "2025-Q2", "1.1"),
            _ulc_row("CHE", "2025-Q3", "0.6"),
            _ulc_row("CHE", "2025-Q4", "0.4"),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["startPeriod"] == "2025-Q1"
        assert request.url.params["endPeriod"] == "2025-Q4"
        return httpx.Response(200, text=body)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator(
            "CHE", ULC_CODE, start_year=2025, end_year=2025
        )

    dates = [obs.observation_date for obs in observations]
    assert dates == [
        date(2025, 1, 1),
        date(2025, 4, 1),
        date(2025, 7, 1),
        date(2025, 10, 1),
    ]
    assert all(obs.period == 2025 for obs in observations)
    assert all(obs.indicator_code == "UNIT_LABOUR_COST_GROWTH" for obs in observations)
    assert observations[0].unit == "percent per annum"


@pytest.mark.asyncio
async def test_null_and_missing_values_are_skipped():
    body = "\n".join(
        [
            PROD_HEADER,
            _prod_row("CHE", "2023", ""),  # missing value
            _prod_row("CHE", "2024", "89.66"),
            _prod_row("CHE", "2025", "   "),  # whitespace-only value
        ]
    )

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        observations = await adapter.fetch_indicator("CHE", PROD_CODE)

    assert [obs.period for obs in observations] == [2024]
    assert observations[0].value == 89.66


@pytest.mark.asyncio
async def test_row_from_wrong_country_raises():
    # Server returns FRA rows for a CHE request — identity violation.
    body = "\n".join([PROD_HEADER, _prod_row("FRA", "2024", "95.5")])

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        with pytest.raises(DataSourceParseError, match="REF_AREA"):
            await adapter.fetch_indicator("CHE", PROD_CODE)


@pytest.mark.asyncio
async def test_row_with_wrong_measure_raises():
    # ULCH (hours-based ULC) in a ULCE (employment-based) response —
    # must not be silently relabelled.
    wrong_measure = _ulc_row("CHE", "2025-Q1", "1.0").replace(
        "CHE,Q,ULCE", "CHE,Q,ULCH"
    )
    body = "\n".join([ULC_HEADER, wrong_measure])

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        with pytest.raises(DataSourceParseError, match="MEASURE"):
            await adapter.fetch_indicator("CHE", ULC_CODE)


@pytest.mark.asyncio
async def test_row_with_wrong_unit_or_transformation_raises():
    # IX index row (TRANSFORMATION=IX) in a GY growth response, and a
    # national-currency row (UNIT_MEASURE=XDC) in a USD-PPP response.
    index_row = _ulc_row("CHE", "2025-Q1", "103.2").replace(",GY,", ",IX,")
    body = "\n".join([ULC_HEADER, index_row])

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        with pytest.raises(DataSourceParseError, match="TRANSFORMATION"):
            await adapter.fetch_indicator("CHE", ULC_CODE)

    xdc_row = _prod_row("CHE", "2024", "62.0").replace(
        "USD_PPP_H", "XDC_H"
    ).replace(",PPP,", ",NC,")
    body = "\n".join([PROD_HEADER, xdc_row])

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        with pytest.raises(DataSourceParseError, match="UNIT_MEASURE"):
            await adapter.fetch_indicator("CHE", PROD_CODE)


@pytest.mark.asyncio
async def test_missing_required_csv_columns_raises_parse_error():
    bad_header = "REF_AREA,FREQ,MEASURE,TIME_PERIOD,SOMETHING_ELSE"
    body = f"{bad_header}\nCHE,A,GDPHRS,2024,89.66"

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        with pytest.raises(DataSourceParseError, match="TIME_PERIOD/OBS_VALUE"):
            await adapter.fetch_indicator("CHE", PROD_CODE)


@pytest.mark.asyncio
async def test_unparseable_time_period_raises_parse_error():
    # Monthly period in an annual-frequency mapping.
    body = "\n".join([PROD_HEADER, _prod_row("CHE", "2024-M06", "89.66")])

    async with _make_adapter(
        lambda request: httpx.Response(200, text=body)
    ) as adapter:
        with pytest.raises(DataSourceParseError, match="TIME_PERIOD"):
            await adapter.fetch_indicator("CHE", PROD_CODE)


@pytest.mark.asyncio
async def test_http_404_raises_data_source_http_error():
    # A 404 that is NOT the clean NoRecordsFound signal (e.g. a bad
    # dataflow/key) stays a transport failure.
    async with _make_adapter(
        lambda request: httpx.Response(404, text="NotFound")
    ) as adapter:
        with pytest.raises(DataSourceHTTPError) as exc_info:
            await adapter.fetch_indicator("CHE", PROD_CODE)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_404_no_records_found_is_clean_no_data():
    # Verified live: OECD answers a no-observation key (e.g. CHN in DF_PDB)
    # with 404 + body "NoRecordsFound" — a legitimate no-coverage outcome,
    # never a failed run.
    async with _make_adapter(
        lambda request: httpx.Response(404, text="NoRecordsFound")
    ) as adapter:
        with pytest.raises(DataSourceNoDataError, match="no observations"):
            await adapter.fetch_indicator("CHN", PROD_CODE)


@pytest.mark.asyncio
async def test_unknown_external_series_raises_series_mapping_error():
    async with _make_adapter(
        lambda request: httpx.Response(200, text="")
    ) as adapter:
        with pytest.raises(SeriesMappingError):
            await adapter.fetch_indicator(
                "CHE", "DSD_PDB@DF_PDB/{cc}.A.GDPHRS._T.XDC_H.LR.N._Z.NC"
            )


@pytest.mark.asyncio
async def test_untracked_country_raises_data_source_error():
    async with _make_adapter(
        lambda request: httpx.Response(200, text="")
    ) as adapter:
        with pytest.raises(DataSourceError, match="REF_AREA"):
            await adapter.fetch_indicator("ZAF", PROD_CODE)


@pytest.mark.asyncio
async def test_two_countries_build_distinct_urls_and_keys():
    body_by_ref_area = {
        "CHE": "\n".join([PROD_HEADER, _prod_row("CHE", "2024", "89.66")]),
        "USA": "\n".join([PROD_HEADER, _prod_row("USA", "2024", "83.2")]),
    }
    requested_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(request.url.path)
        key = request.url.path.split("/")[-1]
        ref_area = key.split(".")[0]
        return httpx.Response(200, text=body_by_ref_area[ref_area])

    async with _make_adapter(handler) as adapter:
        che_obs = await adapter.fetch_indicator("CHE", PROD_CODE)
        usa_obs = await adapter.fetch_indicator("USA", PROD_CODE)

    assert requested_urls[0].endswith(
        "/data/OECD.SDD.TPS,DSD_PDB@DF_PDB,2.0/CHE.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP"
    )
    assert requested_urls[1].endswith(
        "/data/OECD.SDD.TPS,DSD_PDB@DF_PDB,2.0/USA.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP"
    )
    assert [obs.value for obs in che_obs] == [89.66]
    assert [obs.country_iso3 for obs in che_obs] == ["CHE"]
    assert [obs.value for obs in usa_obs] == [83.2]
    assert [obs.country_iso3 for obs in usa_obs] == ["USA"]


def test_external_code_lookup_round_trips():
    mapping = get_oecd_mapping_by_external_code(PROD_CODE)
    assert mapping is not None
    assert mapping.indicator_code == "LABOUR_PRODUCTIVITY_PER_HOUR"
    assert mapping.dataflow_id == "DSD_PDB@DF_PDB"
    assert mapping.version == "2.0"
    assert mapping.sdmx_key_template == "{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP"
    assert mapping.frequency == "annual"

    ulc = get_oecd_mapping_by_external_code(ULC_CODE)
    assert ulc is not None
    assert ulc.indicator_code == "UNIT_LABOUR_COST_GROWTH"
    assert ulc.external_unit == "percent per annum"
    assert ulc.sdmx_key_template == "{cc}.Q.ULCE._T.PA.V.GY.S.NC"