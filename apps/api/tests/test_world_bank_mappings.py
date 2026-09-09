import pytest
from sqlalchemy import select

from app.data_sources.world_bank_mappings import (
    WORLD_BANK_MAPPINGS,
    get_world_bank_mapping,
)
from app.db import session as session_module
from app.db.seed import seed
from app.models import DataSource, Indicator, SourceSeries


EXPECTED_MAPPINGS = {
    "GDP_GROWTH": "NY.GDP.MKTP.KD.ZG",
    "GDP_CURRENT_USD": "NY.GDP.MKTP.CD",
    "GDP_PER_CAPITA": "NY.GDP.PCAP.CD",
    "EXPORTS_GDP": "NE.EXP.GNFS.ZS",
    "IMPORTS_GDP": "NE.IMP.GNFS.ZS",
    "TRADE_BALANCE": "NE.RSB.GNFS.ZS",
    "CURRENT_ACCOUNT_GDP": "BN.CAB.XOKA.GD.ZS",
    "GROSS_CAPITAL_FORMATION_GDP": "NE.GDI.TOTL.ZS",
    "RULE_OF_LAW_WGI_SCORE": "GOV_WGI_RL_SC",
    "CONTROL_OF_CORRUPTION_WGI_SCORE": "GOV_WGI_CC_SC",
    "POLITICAL_STABILITY_WGI_SCORE": "GOV_WGI_PV_SC",
    "GINI_INDEX": "SI.POV.GINI",
    "INFLATION_CPI": "FP.CPI.TOTL.ZG",
    "MILITARY_EXPENDITURE_USD": "MS.MIL.XPND.CD",
    "MILITARY_EXPENDITURE_GDP": "MS.MIL.XPND.GD.ZS",
}


async def _load_series(session):
    rows = (await session.execute(select(SourceSeries))).scalars().all()
    sources = {
        s.id: s.key
        for s in (await session.execute(select(DataSource))).scalars().all()
    }
    indicators = {
        i.id: i.code
        for i in (await session.execute(select(Indicator))).scalars().all()
    }
    return [
        (indicators[s.indicator_id], sources[s.data_source_id], s.external_code)
        for s in rows
    ]


@pytest.mark.asyncio
async def test_module_has_exactly_fifteen_world_bank_mappings():
    assert len(WORLD_BANK_MAPPINGS) == 15
    assert {m.indicator_code for m in WORLD_BANK_MAPPINGS} == set(EXPECTED_MAPPINGS)


@pytest.mark.asyncio
async def test_lookup_by_canonical_indicator_code():
    mapping = get_world_bank_mapping("GDP_GROWTH")
    assert mapping is not None
    assert mapping.external_code == "NY.GDP.MKTP.KD.ZG"
    assert get_world_bank_mapping("UNKNOWN") is None


@pytest.mark.asyncio
async def test_seeded_series_match_verified_mappings(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        rows = await _load_series(session)

    wb_rows = [row for row in rows if row[1] == "world_bank"]
    assert len(wb_rows) == 15
    assert {(indicator, source, code) for indicator, source, code in wb_rows} == {
        (canonical, "world_bank", external)
        for canonical, external in EXPECTED_MAPPINGS.items()
    }


@pytest.mark.asyncio
async def test_external_codes_unique():
    codes = [m.external_code for m in WORLD_BANK_MAPPINGS]
    assert len(codes) == len(set(codes))


@pytest.mark.asyncio
async def test_seed_is_idempotent(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        before = (await session.execute(select(SourceSeries))).scalars().all()
        assert len(before) == 22  # 15 WB + 2 BIS + 3 OECD + 1 IMF + 1 WID

    await seed()  # re-run full seed against the same test DB

    async with sessionmaker() as session:
        after = (await session.execute(select(SourceSeries))).scalars().all()
        assert len(after) == 22
        assert {s.external_code for s in after} >= set(EXPECTED_MAPPINGS.values())


@pytest.mark.asyncio
async def test_all_mapped_indicators_exist_in_seed(client):
    sessionmaker = session_module._sessionmaker
    async with sessionmaker() as session:
        codes = {
            c
            for c in (
                await session.execute(select(Indicator.code))
            ).scalars().all()
        }
    assert {m.indicator_code for m in WORLD_BANK_MAPPINGS} <= codes