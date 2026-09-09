"""Offline tests for OECD education attainment (Sprint 5.20 Part A).

Uses httpx.MockTransport — no external HTTP in pytest.
"""
import httpx
import pytest
from datetime import date

from app.data_sources.base import DataSourceNoDataError, DataSourceParseError, SeriesMappingError
from app.data_sources.oecd import OECDAdapter
from app.data_sources.oecd_mappings import get_oecd_mapping_by_external_code

ATTAINMENT_CODE = (
    "OECD.EDU.IMEP,DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA,1.0/"
    "{cc}._T.Y25T34.ISCED11A_5T8._T.POP._Z._T._Z."
    "ED_NED.POP._Z.PT_POP_SEX_AGE.OBS._Z.NEAC.A"
)
RETRIEVED_AT = "2026-09-10T12:00:00+00:00"


def _make_adapter(handler) -> OECDAdapter:
    return OECDAdapter(transport=httpx.MockTransport(handler), retrieved_at=RETRIEVED_AT)


def _oecd_csv(country: str, rows: list[tuple[str, str]]) -> str:
    """Build minimal OECD SDMX-CSV with labels for education attainment."""
    header = (
        "STRUCTURE,STRUCTURE_ID,STRUCTURE_NAME,ACTION,REF_AREA,Reference area,"
        "SEX,Sex,AGE,Age,ATTAINMENT_LEV,Educational attainment level,"
        "EDUCATION_FIELD,Field of education,MEASURE,Measure,INCOME,Income,"
        "BIRTH_PLACE,Place of birth,MIGRATION_AGE,Age at migration,"
        "EDU_STATUS,Education status,LABOUR_FORCE_STATUS,Labour force status,"
        "DURATION_UNEMP,Unemployment duration,UNIT_MEASURE,Unit of measure,"
        "STATISTICAL_OPERATION,Statistical operation,WORK_TIME_ARNGMNT,"
        "Work time arrangement,QUESTIONNAIRE,Questionnaire name,FREQ,"
        "Frequency of observation,TIME_PERIOD,Time period,OBS_VALUE,"
        "Observation value,OBS_STATUS,Observation status,CONF_STATUS,"
        "Confidentiality status,UNIT_MULT,Unit multiplier,DECIMALS,Decimals\n"
    )
    lines = [header]
    for year, value in rows:
        lines.append(
            f"DATAFLOW,OECD.EDU.IMEP:DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA(1.0),"
            f"Adults' educational attainment distribution,I,"
            f"{country},{country},_T,Total,Y25T34,From 25 to 34 years,"
            f"ISCED11A_5T8,Tertiary education,_T,Total,POP,Population,"
            f"_Z,Not applicable,_T,Total,_Z,Not applicable,"
            f"ED_NED,In education or not in education,POP,Population,"
            f"_Z,Not applicable,PT_POP_SEX_AGE,"
            f"Percentage of population in the same sex and age,"
            f"OBS,Observed,_Z,Not applicable,NEAC,LSO-NEAC regular data collection,"
            f"A,Annual,{year},{year},{value},A,Normal value,,0,Units,1,One\n"
        )
    return "".join(lines)


def test_attainment_mapping_exists():
    """The education attainment mapping is registered with exact dimensions."""
    mapping = get_oecd_mapping_by_external_code(ATTAINMENT_CODE)
    assert mapping is not None
    assert mapping.indicator_code == "TERTIARY_ATTAINMENT_25_34"
    assert mapping.agency_id == "OECD.EDU.IMEP"
    assert mapping.dataflow_id == "DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA"
    assert mapping.version == "1.0"
    assert "Y25T34" in mapping.sdmx_key_template
    assert "ISCED11A_5T8" in mapping.sdmx_key_template
    assert "OBS" in mapping.sdmx_key_template
    # No wildcard + in the production identity
    assert "+" not in mapping.sdmx_key_template


def test_no_wildcard_in_production_identity():
    """The production key has NO wildcard + characters — all 17 dims fixed."""
    mapping = get_oecd_mapping_by_external_code(ATTAINMENT_CODE)
    parts = mapping.sdmx_key_template.replace("{cc}", "USA").split(".")
    assert len(parts) == 17
    assert "+" not in parts


@pytest.mark.asyncio
async def test_attainment_parses_correctly():
    csv_text = _oecd_csv("USA", [("2020", "52.77"), ("2021", "53.50"), ("2022", "54.10")])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=csv_text)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator("USA", ATTAINMENT_CODE)

    assert len(observations) == 3
    assert observations[0].value == 52.77
    assert observations[0].indicator_code == "TERTIARY_ATTAINMENT_25_34"
    assert observations[0].source_key == "oecd"
    assert observations[0].unit == "percent"
    assert observations[0].observation_date == date(2020, 1, 1)


@pytest.mark.asyncio
async def test_wrong_sex_rejected():
    csv_text = _oecd_csv("USA", [("2020", "52.77")])
    # Replace SEX=_T with SEX=M
    csv_text = csv_text.replace(",_T,Total,Y25T34,", ",M,Male,Y25T34,")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=csv_text)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="SEX"):
            await adapter.fetch_indicator("USA", ATTAINMENT_CODE)


@pytest.mark.asyncio
async def test_wrong_age_rejected():
    csv_text = _oecd_csv("USA", [("2020", "52.77")])
    csv_text = csv_text.replace("Y25T34,From 25 to 34 years", "Y25T64,From 25 to 64 years")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=csv_text)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="AGE"):
            await adapter.fetch_indicator("USA", ATTAINMENT_CODE)


@pytest.mark.asyncio
async def test_wrong_attainment_rejected():
    csv_text = _oecd_csv("USA", [("2020", "52.77")])
    csv_text = csv_text.replace("ISCED11A_5T8,Tertiary", "ISCED11A_0T2,Below upper secondary")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=csv_text)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="ATTAINMENT_LEV"):
            await adapter.fetch_indicator("USA", ATTAINMENT_CODE)


@pytest.mark.asyncio
async def test_wrong_unit_rejected():
    csv_text = _oecd_csv("USA", [("2020", "52.77")])
    csv_text = csv_text.replace("PT_POP_SEX_AGE", "PT_POP")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=csv_text)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="UNIT_MEASURE"):
            await adapter.fetch_indicator("USA", ATTAINMENT_CODE)


@pytest.mark.asyncio
async def test_wrong_statistical_operation_rejected():
    """SE (standard error) rows must be rejected — only OBS is canonical."""
    csv_text = _oecd_csv("USA", [("2020", "52.77")])
    csv_text = csv_text.replace("OBS,Observed", "SE,Standard error")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=csv_text)

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceParseError, match="STATISTICAL_OPERATION"):
            await adapter.fetch_indicator("USA", ATTAINMENT_CODE)


@pytest.mark.asyncio
async def test_null_value_skipped():
    csv_text = _oecd_csv("USA", [("2020", "52.77"), ("2021", ""), ("2022", "54.10")])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=csv_text)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator("USA", ATTAINMENT_CODE)

    assert [o.period for o in observations] == [2020, 2022]


@pytest.mark.asyncio
async def test_no_data_for_country():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="NoRecordsFound")

    async with _make_adapter(handler) as adapter:
        with pytest.raises(DataSourceNoDataError):
            await adapter.fetch_indicator("CHN", ATTAINMENT_CODE)


@pytest.mark.asyncio
async def test_sparse_history_preserved():
    """CHN may have only 1 data point — it is preserved, not zero-filled."""
    csv_text = _oecd_csv("CHN", [("2010", "17.95")])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=csv_text)

    async with _make_adapter(handler) as adapter:
        observations = await adapter.fetch_indicator("CHN", ATTAINMENT_CODE)

    assert len(observations) == 1
    assert observations[0].period == 2010
    assert observations[0].value == 17.95


# --- Sprint 5.20.1: exact provider identity regression tests ----------------


def test_exact_agency_in_external_code():
    """The exact OECD agency (OECD.EDU.IMEP) appears in the external_code."""
    mapping = get_oecd_mapping_by_external_code(ATTAINMENT_CODE)
    assert mapping is not None
    assert "OECD.EDU.IMEP" in mapping.external_code


def test_exact_dataflow_in_external_code():
    """The exact dataflow (DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA) appears."""
    mapping = get_oecd_mapping_by_external_code(ATTAINMENT_CODE)
    assert mapping is not None
    assert "DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA" in mapping.external_code


def test_version_in_external_code():
    """The version (1.0) appears in the external_code."""
    mapping = get_oecd_mapping_by_external_code(ATTAINMENT_CODE)
    assert mapping is not None
    assert ",1.0/" in mapping.external_code


def test_complete_sdmx_key_in_external_code():
    """The complete no-wildcard SDMX key appears in the external_code."""
    mapping = get_oecd_mapping_by_external_code(ATTAINMENT_CODE)
    assert mapping is not None
    expected_key = (
        "{cc}._T.Y25T34.ISCED11A_5T8._T.POP._Z._T._Z."
        "ED_NED.POP._Z.PT_POP_SEX_AGE.OBS._Z.NEAC.A"
    )
    assert expected_key in mapping.external_code


def test_external_code_is_country_independent():
    """The {cc} placeholder survives — identity is country-independent."""
    mapping = get_oecd_mapping_by_external_code(ATTAINMENT_CODE)
    assert mapping is not None
    assert "{cc}" in mapping.external_code


def test_external_code_exceeds_old_100_char_limit():
    """The exact identity is longer than the old varchar(100) limit.

    This proves the identity was NOT truncated to fit the old schema.
    """
    mapping = get_oecd_mapping_by_external_code(ATTAINMENT_CODE)
    assert mapping is not None
    assert len(mapping.external_code) > 100


def test_no_abbreviation_alias_in_external_code():
    """The retired 'EAG_LSO_NEAC' abbreviation must NOT appear."""
    mapping = get_oecd_mapping_by_external_code(ATTAINMENT_CODE)
    assert mapping is not None
    assert "EAG_LSO_NEAC/" not in mapping.external_code


@pytest.mark.asyncio
async def test_seed_updates_existing_series_not_duplicate(client):
    """Re-running seed updates the education SourceSeries in place, never
    creates a duplicate."""
    from app.db import session as session_module
    from app.db.seed import DEFAULT_DATA_FILE, seed
    from app.models import DataSource, SourceSeries
    from sqlalchemy import func, select

    sessionmaker = session_module._sessionmaker
    await seed(DEFAULT_DATA_FILE)
    async with sessionmaker() as session:
        oecd_source = (await session.execute(
            select(DataSource).where(DataSource.key == "oecd")
        )).scalar_one()
        edu_series = (await session.execute(
            select(SourceSeries).where(SourceSeries.data_source_id == oecd_source.id)
        )).scalars().all()
        # Exactly 3 OECD series (productivity, ULC, attainment) — no duplicate
        assert len(edu_series) == 3
        # The attainment series has the exact identity
        attainment = [s for s in edu_series if "{cc}._T.Y25T34" in s.external_code]
        assert len(attainment) == 1
        assert "OECD.EDU.IMEP" in attainment[0].external_code
        # Total SourceSeries stays 22
        total = (await session.execute(
            select(func.count()).select_from(SourceSeries)
        )).scalar_one()
        assert total == 22
