"""Market data layer tests (Mission 5 §14, §17-§18, §23-§24)."""
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.data_sources.fred import MarketPriceDTO
from app.market import fx as fx_service
from app.market import service as market_service
from app.models import MarketInstrument, MarketObservation
from app.db import session as session_module


def _dto(code: str, d: date, v: float) -> MarketPriceDTO:
    return MarketPriceDTO(
        external_code=code, obs_date=d, value=v,
        retrieved_at=datetime(2026, 11, 25, tzinfo=timezone.utc),
        raw_payload={"test": True},
    )


async def _seed_and_obs(instrument_code: str, dtos):
    async with session_module._sessionmaker() as s:
        await market_service.seed_instruments(s)
        inst = (await s.execute(
            select(MarketInstrument).where(
                MarketInstrument.code == instrument_code)
        )).scalar_one()
        r = await market_service.persist_market_observations(s, inst, dtos)
        await s.commit()
        return r


async def test_seed_instruments_idempotent(client):
    async with session_module._sessionmaker() as s:
        r1 = await market_service.seed_instruments(s)
        r2 = await market_service.seed_instruments(s)
        await s.commit()
    assert r1["inserted"] == r1["total"] > 20
    assert r2["inserted"] == 0 and r2["updated"] == r1["total"]


async def test_persist_market_observations_idempotent(client):
    dtos = [_dto("X", date(2024, 1, 2), 100.0),
            _dto("X", date(2024, 1, 3), 101.5)]
    r1 = await _seed_and_obs("US_SP500", dtos)
    assert r1 == {"received": 2, "inserted": 2, "skipped": 0}
    # re-ingest same dates -> skipped, never overwritten
    changed = [_dto("X", date(2024, 1, 2), 999.0)]
    r2 = await _seed_and_obs("US_SP500", changed)
    assert r2 == {"received": 1, "inserted": 0, "skipped": 1}
    async with session_module._sessionmaker() as s:
        inst = (await s.execute(
            select(MarketInstrument).where(
                MarketInstrument.code == "US_SP500")
        )).scalar_one()
        vals = (await s.execute(
            select(MarketObservation.value).where(
                MarketObservation.instrument_id == inst.id,
                MarketObservation.obs_date == date(2024, 1, 2))
        )).scalars().all()
        assert vals == [100.0]  # original value preserved


async def test_instruments_endpoint(client):
    await _seed_and_obs("US_SP500", [_dto("X", date(2024, 1, 2), 100.0)])
    r = await client.get("/api/markets/instruments")
    assert r.status_code == 200
    body = r.json()
    codes = {i["code"] for i in body["instruments"]}
    assert "US_SP500" in codes and "FX_USD_EUR" in codes
    sp = next(i for i in body["instruments"] if i["code"] == "US_SP500")
    assert sp["return_methodology"] == "price_index"
    assert {i["asset_class"] for i in body["instruments"]} >= {
        "equity_index", "gov_bond_yield", "fx_rate", "policy_rate"}


async def test_history_and_returns_endpoints(client):
    dtos = [_dto("X", date(2024, 1, i), 100.0 + i) for i in range(2, 10)]
    await _seed_and_obs("US_SP500", dtos)
    r = await client.get("/api/markets/instruments/US_SP500/history")
    assert r.status_code == 200
    assert r.json()["count"] == 8
    r = await client.get("/api/markets/instruments/US_SP500/returns")
    assert r.status_code == 200
    body = r.json()
    assert body["return_methodology"] == "price_index"
    assert body["statistics"]["cumulative_return"] > 0
    assert len(body["returns"]) == 7


async def test_unknown_instrument_404(client):
    r = await client.get("/api/markets/instruments/NOPE/history")
    assert r.status_code == 404


async def test_fx_convert_same_and_missing(client):
    r = await client.get("/api/markets/fx/convert?amount=100&from=USD&to=USD")
    assert r.status_code == 200
    assert r.json()["value"] == 100.0


async def test_fx_convert_uses_past_rate_never_future(client):
    """A rate stored after the conversion date must not be used."""
    await _seed_and_obs(
        "FX_CHF_USD",
        [_dto("DEXSZUS", date(2024, 1, 5), 0.90),
         _dto("DEXSZUS", date(2024, 3, 1), 0.80)],
    )
    async with session_module._sessionmaker() as s:
        res = await fx_service.convert(
            s, 100.0, "USD", "CHF", date(2024, 2, 1)
        )
    # latest rate <= 2024-02-01 is 0.90 (the 0.80 from March is future)
    assert abs(res["value"] - 90.0) < 1e-9
    assert res["fx_used"][0]["rate_date"] == "2024-01-05"


async def test_fx_convert_unavailable_when_no_rate(client):
    await _seed_and_obs(
        "FX_CHF_USD", [_dto("DEXSZUS", date(2024, 6, 1), 0.90)]
    )
    async with session_module._sessionmaker() as s:
        res = await fx_service.convert(
            s, 100.0, "USD", "CHF", date(2020, 1, 1)
        )
    assert res["value"] is None
    assert "unavailable_reason" in res


async def test_correlations_shared_dates_only(client):
    await _seed_and_obs(
        "US_SP500", [_dto("S", date(2024, 1, i), 100 + i)
                     for i in range(2, 30)]
    )
    await _seed_and_obs(
        "US_GOV_10Y_YIELD_D", [_dto("Y", date(2024, 1, i), 4.0 + i / 100)
                               for i in range(2, 30)]
    )
    r = await client.get(
        "/api/markets/correlations?codes=US_SP500,US_GOV_10Y_YIELD_D"
    )
    assert r.status_code == 200
    pair = r.json()["pairs"]["US_GOV_10Y_YIELD_D|US_SP500"]
    assert pair["shared_obs"] == 27
    assert pair["correlation"] is not None
