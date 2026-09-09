"""Milestone 5.1 offline tests: World Bank trade/investment mappings, seeding,
persistence, and force promotion (Trade and capital flows + Infrastructure and
investment become available with data; Global openness stays missing).

Synthetic DTOs persisted via the real persistence layer against seeded SQLite;
no external World Bank calls. Coverage is data availability only — no scores.
"""
from datetime import date, datetime, timezone

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
}

TRADE_DTOS_SPEC = [
    ("EXPORTS_GDP", WB_EXPORTS, 65.0),
    ("IMPORTS_GDP", WB_IMPORTS, 58.0),
    ("TRADE_BALANCE", WB_TRADE_BALANCE, 7.0),
    ("CURRENT_ACCOUNT_GDP", WB_CURRENT_ACCOUNT, 8.0),
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
    assert len(WORLD_BANK_MAPPINGS) == 15  # 3 GDP + 5 trade/investment + 3 WGI + Gini + CPI + 2 military
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
        assert total == 22
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
        [_dto("CHE", "GROSS_CAPITAL_FORMATION_GDP", WB_GCF, 26.5)]
    )
    coverage = await coverage_by_code("CHE")
    infra = coverage["infrastructure_investment"]
    assert infra.status == "available"
    assert [i.indicator_code for i in infra.live_inputs] == [
        "GROSS_CAPITAL_FORMATION_GDP"
    ]


# --- 7: catalog row / SourceSeries without data does not become live ------------


async def test_sourced_but_dataless_force_stays_defined_not_sourced(client):
    # GCF has a SourceSeries (seeded) but no observations persisted for CHN
    coverage = await coverage_by_code("CHN")
    assert coverage["infrastructure_investment"].status == "defined_not_sourced"
    assert coverage["trade_capital_flows"].status == "defined_not_sourced"


# --- 8: Global openness stays missing even with full trade data ----------------


async def test_global_openness_stays_missing_with_trade_data(client):
    dtos = [
        _dto("CHE", indicator, external, value)
        for indicator, external, value in TRADE_DTOS_SPEC
    ]
    dtos.append(_dto("CHE", "GROSS_CAPITAL_FORMATION_GDP", WB_GCF, 26.5))
    await _persist(dtos)
    coverage = await coverage_by_code("CHE")

    openness = coverage["global_openness"]
    assert openness.status == "missing"
    assert openness.live_inputs == []
    assert openness.candidate_inputs == []
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
    await _persist(dtos)

    response = await client.get("/api/countries/CHE/force-coverage")
    assert response.status_code == 200
    data = response.json()
    by_code = {f["code"]: f for f in data["forces"]}

    assert by_code["trade_capital_flows"]["status"] == "available"
    assert by_code["infrastructure_investment"]["status"] == "available"
    assert by_code["global_openness"]["status"] == "missing"
    trade_live = by_code["trade_capital_flows"]["live_inputs"]
    assert {i["indicator_code"] for i in trade_live} == {
        "EXPORTS_GDP",
        "IMPORTS_GDP",
        "TRADE_BALANCE",
        "CURRENT_ACCOUNT_GDP",
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