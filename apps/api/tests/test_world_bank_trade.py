"""Milestone 5.1 offline tests: World Bank trade/investment mappings, seeding,
persistence, and force promotion (Trade and capital flows + Infrastructure and
investment become available with data; Global openness stays missing).

Synthetic DTOs persisted via the real persistence layer against seeded SQLite;
no external World Bank calls. Coverage is data availability only — no scores.
"""
from datetime import date, datetime, timezone
import pytest

from sqlalchemy import func, select

from app.data_sources.world_bank_mappings import WORLD_BANK_MAPPINGS
from app.data_sources.world_bank import WorldBankAdapter
from app.db import session as session_module
from app.db.seed import DEFAULT_DATA_FILE, seed
from app.models import DataSource, Indicator, Observation, SourceSeries
from app.services.force_coverage_service import get_force_coverage

RETRIEVED_AT = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)

WB_EXPORTS = "NE.EXP.GNFS.ZS"
WB_IMPORTS = "NE.IMP.GNFS.ZS"
WB_TRADE_BALANCE = "NE.RSB.GNFS.ZS"
WB_CURRENT_ACCOUNT = "BN.CAB.XOKA.GD.ZS"
WB_GCF = "NE.GDI.TOTL.ZS"

EXPECTED_WB_CODES = {
    "GDP_GROWTH": "NY.GDP.MKTP.KD.ZG",
    "GDP_CURRENT_USD": "NY.GDP.MKTP.CD",
    "GDP_PER_CAPITA": "NY.GDP.PCAP.CD",
    "EXPORTS_GDP": WB_EXPORTS,
    "IMPORTS_GDP": WB_IMPORTS,
    "TRADE_BALANCE": WB_TRADE_BALANCE,
    "CURRENT_ACCOUNT_GDP": WB_CURRENT_ACCOUNT,
    "GROSS_CAPITAL_FORMATION_GDP": WB_GCF,
    "RULE_OF_LAW_WGI_SCORE": "GOV_WGI_RL_SC",
    "CONTROL_OF_CORRUPTION_WGI_SCORE": "GOV_WGI_CC_SC",
    "POLITICAL_STABILITY_WGI_SCORE": "GOV_WGI_PV_SC",
    "GINI_INDEX": "SI.POV.GINI",
    "INFLATION_CPI": "FP.CPI.TOTL.ZG",
    "MILITARY_EXPENDITURE_USD": "MS.MIL.XPND.CD",
    "MILITARY_EXPENDITURE_GDP": "MS.MIL.XPND.GD.ZS",
    "GOVERNMENT_EFFECTIVENESS_WGI_SCORE": "GOV_WGI_GE_SC",
    "POPULATION": "SP.POP.TOTL",
    "RND_EXPENDITURE_GDP": "GB.XPD.RSDV.GD.ZS",
    "SECONDARY_ENROLLMENT": "SE.SEC.ENRR",
    "TERTIARY_ENROLLMENT": "SE.TER.ENRR",
    "UNEMPLOYMENT_RATE": "SL.UEM.TOTL.ZS",
    "LABOUR_FORCE_PARTICIPATION_RATE": "SL.TLF.CACT.ZS",
    "FDI_NET_INFLOWS_GDP": "BX.KLT.DINV.WD.GD.ZS",
    "REER_INDEX": "PX.REX.REER",
    "BROADBAND_PER_100": "IT.NET.BBND.P2",
    "NATURAL_DISASTER_AFFECTED_PCT": "EN.CLC.MDAT.ZS",
    "GDP_PPP_CURRENT_INTL": "NY.GDP.MKTP.PP.CD",
    "GDP_REAL_CONSTANT_USD": "NY.GDP.MKTP.KD",
    "MERCHANDISE_EXPORTS_USD": "TX.VAL.MRCH.CD.WT",
    "MERCHANDISE_IMPORTS_USD": "TM.VAL.MRCH.CD.WT",
    "COMMERCIAL_SERVICE_EXPORTS_USD": "TX.VAL.SERV.CD.WT",
    "COMMERCIAL_SERVICE_IMPORTS_USD": "TM.VAL.SERV.CD.WT",
    "PATENT_APPLICATIONS_RESIDENT": "IP.PAT.RESD",
    "PATENT_APPLICATIONS_NONRESIDENT": "IP.PAT.NRES",
    "RESEARCHERS_PER_MILLION": "SP.POP.SCIE.RD.P6",
    "HIGH_TECHNOLOGY_EXPORTS_USD": "TX.VAL.TECH.CD",
    "STOCK_MARKET_CAP_GDP": "CM.MKT.LCAP.GD.ZS",
    "DOMESTIC_CREDIT_PRIVATE_GDP": "FS.AST.PRVT.GD.ZS",
    "BROAD_MONEY_GDP": "FM.LBL.BMNY.GD.ZS",
}

TRADE_DTOS_SPEC = [
    ("EXPORTS_GDP", WB_EXPORTS, 65.0),
    ("IMPORTS_GDP", WB_IMPORTS, 58.0),
    ("TRADE_BALANCE", WB_TRADE_BALANCE, 7.0),
    ("CURRENT_ACCOUNT_GDP", WB_CURRENT_ACCOUNT, 8.0),
    ("FDI_NET_INFLOWS_GDP", "BX.KLT.DINV.WD.GD.ZS", 3.0),
]


def _dto(iso3: str, indicator: str, external: str, value: float) -> object:
    from app.data_sources.base import ObservationDTO

    return ObservationDTO(
        country_iso3=iso3,
        indicator_code=indicator,
        external_series_code=external,
        period=2024,
        value=value,
        unit="test unit",
        source_key="world_bank",
        observation_date=date(2024, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


async def _persist(dtos) -> None:
    from app.services.observation_service import persist_observations

    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


async def coverage_by_code(iso3: str) -> dict:
    from app.models import Country

    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        country_id = (
            await session.execute(select(Country.id).where(Country.iso3 == iso3))
        ).scalar_one()
        items = await get_force_coverage(session, country_id)
        return {item.definition.code: item for item in items}


# --- 1: verified new WB mappings ------------------------------------------------


async def test_world_bank_mappings_verified_codes(client):
    assert len(WORLD_BANK_MAPPINGS) == 39  # 3 GDP + 5 trade/investment + 4 WGI + Gini + CPI + 2 military + 6 pop/rnd/enroll/unemp/lfp + 1 EM-DAT exposure (Mission 4 §18)
    by_indicator = {m.indicator_code: m for m in WORLD_BANK_MAPPINGS}
    for indicator_code, external_code in EXPECTED_WB_CODES.items():
        mapping = by_indicator.get(indicator_code)
        assert mapping is not None, f"{indicator_code} missing from WB mappings"
        assert mapping.external_code == external_code
    # Trade balance must be the published external-balance series, not derived
    assert "External balance" in by_indicator["TRADE_BALANCE"].external_name


async def test_world_bank_adapter_rejects_unmapped_series(client):
    adapter = WorldBankAdapter()
    try:
        parse = adapter.parse_response(
            [{"page": 1}, [{"country": {"id": "CHE"}, "date": "2024", "value": 1.0}]],
            "CHE",
            "NOT.A.REAL.CODE",
        )
        assert False, "unmapped series must raise"
    except Exception as exc:  # SeriesMappingError
        assert "no canonical" in str(exc)
    finally:
        await adapter.aclose()


# --- 2–3: SourceSeries seeding + idempotency ------------------------------------


async def test_trade_source_series_seeded(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        rows = (
            await session.execute(
                select(Indicator.code, SourceSeries.external_code)
                .join(SourceSeries, SourceSeries.indicator_id == Indicator.id)
                .join(DataSource, DataSource.id == SourceSeries.data_source_id)
                .where(DataSource.key == "world_bank")
            )
        ).all()
        seeded = {row[0]: row[1] for row in rows}
        assert seeded == EXPECTED_WB_CODES


async def test_seed_idempotent_no_duplicate_series(client):
    await seed(DEFAULT_DATA_FILE)
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        total = (
            await session.execute(select(func.count()).select_from(SourceSeries))
        ).scalar_one()
        # 22 = 15 WB + 2 BIS + 3 OECD + 1 IMF + 1 WID
        assert total == 46
        dup = (
            await session.execute(
                select(func.count())
                .select_from(SourceSeries)
                .group_by(SourceSeries.data_source_id, SourceSeries.indicator_id)
                .having(func.count() > 1)
            )
        ).all()
        assert dup == []


# --- 4: one new trade DTO → persistence -----------------------------------------


async def test_trade_balance_dto_persisted_and_readable(client):
    await _persist([_dto("CHE", "TRADE_BALANCE", WB_TRADE_BALANCE, 7.0)])
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        row = (
            await session.execute(
                select(Observation)
                .join(SourceSeries, SourceSeries.id == Observation.source_series_id)
                .where(SourceSeries.external_code == WB_TRADE_BALANCE)
                .limit(1)
            )
        ).scalar_one()
        assert row.value == 7.0
        assert row.vintage_number == 1


# --- 5: Trade and capital flows promoted to live, available with data ----------


async def test_trade_force_available_with_all_four_inputs(client):
    dtos = [
        _dto("CHE", indicator, external, value)
        for indicator, external, value in TRADE_DTOS_SPEC
    ]
    await _persist(dtos)
    coverage = await coverage_by_code("CHE")

    trade = coverage["trade_capital_flows"]
    assert trade.status == "available"
    live = {i.indicator_code: i for i in trade.live_inputs}
    assert set(live) == {
        "EXPORTS_GDP",
        "IMPORTS_GDP",
        "TRADE_BALANCE",
        "CURRENT_ACCOUNT_GDP",
        "FDI_NET_INFLOWS_GDP",
    }
    assert all(i.has_data for i in live.values())
    assert all(i.has_source_series for i in live.values())
    assert all(i.source == "world_bank" for i in live.values())


async def test_trade_force_partial_when_one_input_lacks_data(client):
    # only exports imported → live but incomplete
    await _persist([_dto("DEU", "EXPORTS_GDP", WB_EXPORTS, 43.0)])
    coverage = await coverage_by_code("DEU")
    assert coverage["trade_capital_flows"].status == "partial"


# --- 6: Infrastructure and investment available with GCF ------------------------


async def test_infrastructure_force_available_with_gcf(client):
    await _persist(
        [
            _dto("CHE", "GROSS_CAPITAL_FORMATION_GDP", WB_GCF, 26.5),
            _dto("CHE", "BROADBAND_PER_100", "IT.NET.BBND.P2", 42.0),
        ]
    )
    coverage = await coverage_by_code("CHE")
    infra = coverage["infrastructure_investment"]
    assert infra.status == "available"
    assert [i.indicator_code for i in infra.live_inputs] == [
        "GROSS_CAPITAL_FORMATION_GDP",
        "BROADBAND_PER_100",
    ]


# --- 7: catalog row / SourceSeries without data does not become live ------------


async def test_sourced_but_dataless_force_stays_defined_not_sourced(client):
    # GCF has a SourceSeries (seeded) but no observations persisted for CHN
    coverage = await coverage_by_code("CHN")
    assert coverage["infrastructure_investment"].status == "defined_not_sourced"
    assert coverage["trade_capital_flows"].status == "defined_not_sourced"


# --- 8: Global openness context profile is partial with trade data ----------------


async def test_global_openness_context_profile_with_trade_data(client):
    """Mission 4 §16: openness now has live trade/size inputs — with the five
    trade series present (but not POPULATION/GDP_CURRENT_USD), the coverage
    ceiling correctly reports 'partial', never 'available'."""
    dtos = [
        _dto("CHE", indicator, external, value)
        for indicator, external, value in TRADE_DTOS_SPEC
    ]
    dtos.append(_dto("CHE", "GROSS_CAPITAL_FORMATION_GDP", WB_GCF, 26.5))
    dtos.append(_dto("CHE", "BROADBAND_PER_100", "IT.NET.BBND.P2", 42.0))
    await _persist(dtos)
    coverage = await coverage_by_code("CHE")

    openness = coverage["global_openness"]
    assert openness.status == "partial"
    live = {i.indicator_code: i for i in openness.live_inputs}
    assert live["EXPORTS_GDP"].has_data
    # size context sits in candidates, not live inputs
    assert {i.indicator_code for i in openness.candidate_inputs} == {
        "POPULATION", "GDP_CURRENT_USD",
    }
    assert "trade" in (openness.definition.coverage_notes or "").lower()


# --- 9: country scoping ---------------------------------------------------------


async def test_trade_coverage_is_country_scoped(client):
    dtos = [
        _dto("CHE", indicator, external, value)
        for indicator, external, value in TRADE_DTOS_SPEC
    ]
    await _persist(dtos)

    che = await coverage_by_code("CHE")
    usa = await coverage_by_code("USA")
    assert che["trade_capital_flows"].status == "available"
    assert usa["trade_capital_flows"].status == "defined_not_sourced"
    usa_live = {i.indicator_code: i for i in usa["trade_capital_flows"].live_inputs}
    assert all(not i.has_data for i in usa_live.values())


# --- 10: API shape after promotion ----------------------------------------------


async def test_api_trade_and_infrastructure_available_no_scores(client):
    dtos = [
        _dto("CHE", indicator, external, value)
        for indicator, external, value in TRADE_DTOS_SPEC
    ]
    dtos.append(_dto("CHE", "GROSS_CAPITAL_FORMATION_GDP", WB_GCF, 26.5))
    dtos.append(_dto("CHE", "BROADBAND_PER_100", "IT.NET.BBND.P2", 42.0))
    await _persist(dtos)

    response = await client.get("/api/countries/CHE/force-coverage")
    assert response.status_code == 200
    data = response.json()
    by_code = {f["code"]: f for f in data["forces"]}

    assert by_code["trade_capital_flows"]["status"] == "available"
    assert by_code["infrastructure_investment"]["status"] == "available"
    assert by_code["global_openness"]["status"] == "partial"
    trade_live = by_code["trade_capital_flows"]["live_inputs"]
    assert {i["indicator_code"] for i in trade_live} == {
        "EXPORTS_GDP",
        "IMPORTS_GDP",
        "TRADE_BALANCE",
        "CURRENT_ACCOUNT_GDP",
        "FDI_NET_INFLOWS_GDP",
    }
    assert all(i["has_source_series"] and i["has_data"] for i in trade_live)

    def _keys(obj) -> set:
        keys = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                keys.add(k)
                keys |= _keys(v)
        elif isinstance(obj, list):
            for item in obj:
                keys |= _keys(item)
        return keys

    keys = _keys(data)
    assert not ({"score", "force_score", "phase", "weight"} & keys)

# --- Mission 4 §16/§18: deferred-force context profiles -----------------------


async def test_derived_trade_openness_endpoint(client):
    """§16: TRADE_OPENNESS_GDP exposed as a derived API series — exports +
    imports, with per-component provenance, never a strength score."""
    dtos = [
        _dto("CHE", "EXPORTS_GDP", WB_EXPORTS, 65.0),
        _dto("CHE", "IMPORTS_GDP", WB_IMPORTS, 58.0),
    ]
    await _persist(dtos)

    r = await client.get(
        "/api/countries/CHE/derived/trade-openness"
        "?start_year=2023&end_year=2024"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["derived_indicator_code"] == "TRADE_OPENNESS_GDP"
    assert body["formula_id"] == "trade_openness_gdp"
    assert body["execution_mode"] == "retrospective_latest_vintage"
    assert body["backtest_safe"] is False
    assert "not an Atlas strength" in body["interpretation"]
    pt = body["points"][-1]
    assert pt["derived_value"] == pytest.approx(123.0)
    codes = {c["indicator_code"] for c in pt["components"]}
    assert codes == {"EXPORTS_GDP", "IMPORTS_GDP"}


async def test_derived_trade_openness_missing_component_is_null(client):
    """MISSING != ZERO: only exports present -> derived_value null."""
    await _persist([_dto("CHE", "EXPORTS_GDP", WB_EXPORTS, 65.0)])
    r = await client.get(
        "/api/countries/CHE/derived/trade-openness"
        "?start_year=2024&end_year=2024"
    )
    assert r.status_code == 200
    pt = r.json()["points"][0]
    assert pt["derived_value"] is None
    missing = {
        c["indicator_code"]: c["missing_reason"]
        for c in pt["components"]
    }
    assert missing["IMPORTS_GDP"] is not None
    assert missing["EXPORTS_GDP"] is None


async def test_derived_trade_openness_strict_never_leaks(client):
    """§25: strict_as_of with no release evidence returns nulls, not the
    retrospective values."""
    dtos = [
        _dto("CHE", "EXPORTS_GDP", WB_EXPORTS, 65.0),
        _dto("CHE", "IMPORTS_GDP", WB_IMPORTS, 58.0),
    ]
    await _persist(dtos)
    r = await client.get(
        "/api/countries/CHE/derived/trade-openness"
        "?start_year=2024&end_year=2024"
        "&execution_mode=strict_as_of&info_cutoff=2025-12-31"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["execution_mode"] == "strict_as_of"
    assert body["points"][0]["derived_value"] is None


async def test_derived_trade_openness_strict_requires_cutoff(client):
    r = await client.get(
        "/api/countries/CHE/derived/trade-openness"
        "?execution_mode=strict_as_of"
    )
    assert r.status_code == 422


async def test_acts_of_nature_context_partial_with_data(client):
    """§18: one verified structural indicator -> coverage 'partial'
    (ceiling), never 'available' for an incomplete proxy."""
    await _persist([
        _dto("CHE", "NATURAL_DISASTER_AFFECTED_PCT", "EN.CLC.MDAT.ZS", 4.2)
    ])
    coverage = await coverage_by_code("CHE")
    aon = coverage["acts_of_nature"]
    assert aon.status == "partial"
    assert [i.indicator_code for i in aon.live_inputs] == [
        "NATURAL_DISASTER_AFFECTED_PCT"
    ]
    assert aon.live_inputs[0].has_data


async def test_acts_of_nature_defined_not_sourced_without_data(client):
    """The indicator is in the catalog but unsourced for a country without
    data — defined_not_sourced, never 'missing' (which would pretend no
    source exists) and never zero events."""
    coverage = await coverage_by_code("USA")
    aon = coverage["acts_of_nature"]
    assert aon.status == "defined_not_sourced"
    assert all(not i.has_data for i in aon.live_inputs)
