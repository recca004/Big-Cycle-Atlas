"""Strategy simulation + paper portfolio tests (Mission 5 §27-§36)."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.data_sources.fred import MarketPriceDTO
from app.market import service as market_service
from app.models import MarketInstrument, PaperPortfolio
from app.portfolio import service as pf
from app.portfolio.service import PortfolioError
from app.strategy import simulator
from app.strategy.definitions import (
    BENCHMARK_STRATEGIES,
    EvaluationCategory,
    fixed_weight_strategy,
)
from app.db import session as session_module


def _mdto(code, d, v):
    return MarketPriceDTO(
        external_code=code, obs_date=d, value=v,
        retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        raw_payload={"test": True},
    )


async def _seed(code: str, points: list[tuple[date, float]]):
    async with session_module._sessionmaker() as s:
        await market_service.seed_instruments(s)
        inst = (await s.execute(
            select(MarketInstrument).where(MarketInstrument.code == code)
        )).scalar_one()
        await market_service.persist_market_observations(
            s, inst, [_mdto(code, d, v) for d, v in points]
        )
        await s.commit()


def _session():
    return session_module._sessionmaker()


# --- Simulator (§27-§30) -------------------------------------------------------


async def test_simulate_buy_and_hold(client):
    """100 in Jan -> 200 in Mar with no trades: final=200, cum=100%."""
    await _seed("USA_EQUITY_PRICE_INDEX", [
        (date(2024, 1, 31), 100.0),
        (date(2024, 2, 29), 150.0),
        (date(2024, 3, 31), 200.0),
    ])
    async with _session() as s:
        res = await simulator.simulate(
            s, BENCHMARK_STRATEGIES["buy_and_hold_us_equity"],
            date(2024, 1, 1), date(2024, 3, 31), 1000.0, "USD",
            cost_bps=0, slippage_bps=0,
        )
    assert res["available"] is True
    assert res["final_value"] == pytest.approx(2000.0)
    assert res["cumulative_return"] == pytest.approx(1.0)
    assert res["category"] == "retrospective_market"
    assert res["backtest_safe"] is False


async def test_simulate_respects_costs(client):
    await _seed("USA_EQUITY_PRICE_INDEX", [
        (date(2024, 1, 31), 100.0), (date(2024, 3, 31), 100.0),
    ])
    async with _session() as s:
        res = await simulator.simulate(
            s, BENCHMARK_STRATEGIES["buy_and_hold_us_equity"],
            date(2024, 1, 1), date(2024, 3, 31), 1000.0, "USD",
            cost_bps=100, slippage_bps=0,
        )
    assert res["transaction_costs"] == pytest.approx(10.0)
    assert res["final_value"] < 1000.0  # cost ate into position


async def test_next_period_execution_rule(client):
    """A Dec-31 rebalance executes at the first stored price AFTER
    Dec-31 (Jan obs) — the decision close is never assumed executable."""
    pts_a = [(date(2023, 12, 31), 100.0), (date(2024, 6, 30), 100.0),
             (date(2024, 12, 31), 200.0), (date(2025, 1, 31), 200.0)]
    pts_b = [(date(2023, 12, 31), 100.0), (date(2024, 6, 30), 100.0),
             (date(2024, 12, 31), 100.0), (date(2025, 1, 31), 100.0)]
    await _seed("USA_EQUITY_PRICE_INDEX", pts_a)
    await _seed("US_SP500", pts_b)
    spec = fixed_weight_strategy(
        {"USA_EQUITY_PRICE_INDEX": 0.5, "US_SP500": 0.5},
        rebalance="annual",
    )
    async with _session() as s:
        res = await simulator.simulate(
            s, spec, date(2023, 12, 15), date(2025, 1, 31), 1000.0,
            "USD", 0, 0,
        )
    # entry trades at first obs on/after start (2023-12-31); the 2024
    # year-end rebalance must execute at the first price AFTER
    # 2024-12-31 — i.e. 2025-01-31.
    rebal_trades = [t for t in res["trades"] if t["date"] > "2023-12-31"]
    assert rebal_trades, "expected rebalance trades"
    assert all(t["date"] == "2025-01-31" for t in rebal_trades)


async def test_fx_gated_execution_slips_forward(client):
    """Entry requires a price AND an FX rate both available as of the
    execution date. If FX coverage starts after the first price, the
    trade slides to the first jointly executable point — it never uses
    a future FX rate and never silently skips the trade."""
    await _seed("USA_EQUITY_PRICE_INDEX", [
        (date(2024, 1, 31), 100.0),   # no CHF rate available yet
        (date(2024, 2, 29), 100.0),   # first joint point
        (date(2024, 3, 31), 200.0),
    ])
    await _seed("FX_CHF_USD", [
        (date(2024, 2, 15), 1.0),     # FX coverage begins mid-Feb
        (date(2024, 3, 31), 1.0),
    ])
    async with _session() as s:
        res = await simulator.simulate(
            s, BENCHMARK_STRATEGIES["buy_and_hold_us_equity"],
            date(2024, 1, 1), date(2024, 3, 31), 1000.0, "CHF",
            cost_bps=0, slippage_bps=0,
        )
    assert res["available"] is True
    assert res["trades"], "trade must happen once FX exists"
    assert res["trades"][0]["date"] == "2024-02-29"
    assert res["final_value"] == pytest.approx(2000.0)


async def test_weight_validation_rejected(client):
    spec = fixed_weight_strategy(
        {"USA_EQUITY_PRICE_INDEX": 0.5}, rebalance="annual"
    )
    async with _session() as s:
        res = await simulator.simulate(
            s, spec, date(2024, 1, 1), date(2024, 3, 31), 1000.0, "USD"
        )
    assert res["available"] is False
    assert "sum to 1.0" in res["unavailable_reason"]


async def test_non_investable_rejected(client):
    await _seed("US_GOV_10Y_YIELD_D", [(date(2024, 1, 31), 4.0)])
    spec = fixed_weight_strategy({"US_GOV_10Y_YIELD_D": 1.0})
    async with _session() as s:
        res = await simulator.simulate(
            s, spec, date(2024, 1, 1), date(2024, 3, 31), 1000.0, "USD"
        )
    assert res["available"] is False
    assert "not investable" in res["unavailable_reason"]


async def test_simulate_endpoint_contract(client):
    await _seed("USA_EQUITY_PRICE_INDEX", [
        (date(2024, 1, 31), 100.0), (date(2024, 3, 31), 110.0),
    ])
    r = await client.post("/api/strategies/simulate", json={
        "strategy": "buy_and_hold_us_equity",
        "start": "2024-01-01", "end": "2024-03-31",
        "initial_capital": 1000, "base_currency": "USD",
        "cost_bps": 0, "slippage_bps": 0,
    })
    assert r.status_code == 200
    body = r.json()
    for key in ("strategy_id", "model_version", "final_value",
                "cumulative_return", "max_drawdown", "run_manifest",
                "execution_assumptions", "category", "backtest_safe"):
        assert key in body


# --- Paper portfolio (§33-§36) --------------------------------------------------


async def _mk_portfolio(capital=Decimal("10000")):
    async with _session() as s:
        p = await pf.create_portfolio(s, "Test PF", "USD", capital)
        await s.commit()
        return p.id


async def test_portfolio_buy_sell_ledger(client):
    pid = await _mk_portfolio()
    await _seed("USA_EQUITY_PRICE_INDEX", [(date(2024, 1, 31), 100.0)])
    async with _session() as s:
        p = (await s.execute(
            select(PaperPortfolio).where(PaperPortfolio.id == pid)
        )).scalar_one()
        inst = (await s.execute(
            select(MarketInstrument).where(
                MarketInstrument.code == "USA_EQUITY_PRICE_INDEX")
        )).scalar_one()
        await pf.post_transaction(
            s, p, "buy", inst.id, Decimal("10"), Decimal("100"),
            "USD", Decimal(0), datetime.now(timezone.utc), "k1")
        await s.commit()
        v = await pf.valuation(s, p)
    assert v["cash"] == pytest.approx(9000.0)
    assert v["holdings"][0]["quantity"] == pytest.approx(10.0)
    assert v["simulation"] is True


async def test_insufficient_cash_and_holdings(client):
    pid = await _mk_portfolio(Decimal("100"))
    await _seed("USA_EQUITY_PRICE_INDEX", [(date(2024, 1, 31), 100.0)])
    async with _session() as s:
        p = (await s.execute(
            select(PaperPortfolio).where(PaperPortfolio.id == pid)
        )).scalar_one()
        inst = (await s.execute(
            select(MarketInstrument).where(
                MarketInstrument.code == "USA_EQUITY_PRICE_INDEX")
        )).scalar_one()
        with pytest.raises(PortfolioError, match="insufficient cash"):
            await pf.post_transaction(
                s, p, "buy", inst.id, Decimal("2"), Decimal("100"),
                "USD", Decimal(0), datetime.now(timezone.utc), "k2")
        with pytest.raises(PortfolioError, match="insufficient holdings"):
            await pf.post_transaction(
                s, p, "sell", inst.id, Decimal("1"), Decimal("100"),
                "USD", Decimal(0), datetime.now(timezone.utc), "k3")


async def test_idempotency_key_blocks_duplicates(client):
    pid = await _mk_portfolio()
    await _seed("USA_EQUITY_PRICE_INDEX", [(date(2024, 1, 31), 100.0)])
    async with _session() as s:
        p = (await s.execute(
            select(PaperPortfolio).where(PaperPortfolio.id == pid)
        )).scalar_one()
        inst = (await s.execute(
            select(MarketInstrument).where(
                MarketInstrument.code == "USA_EQUITY_PRICE_INDEX")
        )).scalar_one()
        t1, c1 = await pf.post_transaction(
            s, p, "buy", inst.id, Decimal("1"), Decimal("100"),
            "USD", Decimal(0), datetime.now(timezone.utc), "dup-key")
        t2, c2 = await pf.post_transaction(
            s, p, "buy", inst.id, Decimal("1"), Decimal("100"),
            "USD", Decimal(0), datetime.now(timezone.utc), "dup-key")
        await s.commit()
        v = await pf.valuation(s, p)
    assert c1 is True and c2 is False and t1.id == t2.id
    assert v["cash"] == pytest.approx(9900.0)  # only one buy posted


async def test_portfolio_api_flow(client):
    await _seed("USA_EQUITY_PRICE_INDEX", [(date(2024, 1, 31), 100.0)])
    r = await client.post("/api/portfolio", json={
        "name": "API PF", "base_currency": "USD", "starting_capital": 5000})
    assert r.status_code == 200
    pid = r.json()["id"]
    # default price = latest stored market price (no fabrication)
    r = await client.post(f"/api/portfolio/{pid}/transactions", json={
        "kind": "buy", "instrument_code": "USA_EQUITY_PRICE_INDEX",
        "quantity": 2, "idempotency_key": "api-txn-1"})
    assert r.status_code == 200
    assert r.json()["created"] is True
    r = await client.get(f"/api/portfolio/{pid}")
    assert r.json()["cash"] == pytest.approx(4800.0)
    assert r.json()["holdings"][0]["quantity"] == pytest.approx(2.0)


async def test_portfolio_blocks_unflagged_price(client):
    """An explicit price without user_entered_price=true is rejected —
    simulation prices are always flagged."""
    await _seed("USA_EQUITY_PRICE_INDEX", [(date(2024, 1, 31), 100.0)])
    pid = await _mk_portfolio()
    r = await client.post(f"/api/portfolio/{pid}/transactions", json={
        "kind": "buy", "instrument_code": "USA_EQUITY_PRICE_INDEX",
        "quantity": 1, "price": 99.0, "idempotency_key": "api-txn-2"})
    assert r.status_code == 422
    r = await client.post(f"/api/portfolio/{pid}/transactions", json={
        "kind": "buy", "instrument_code": "USA_EQUITY_PRICE_INDEX",
        "quantity": 1, "price": 99.0, "user_entered_price": True,
        "idempotency_key": "api-txn-3"})
    assert r.status_code == 200


async def test_watchlist_flow(client):
    r = await client.post("/api/portfolio/watchlist", json={
        "kind": "instrument", "ref_code": "US_SP500", "label": "S&P 500"})
    assert r.status_code == 200
    eid = r.json()["id"]
    # duplicate add is idempotent
    r2 = await client.post("/api/portfolio/watchlist", json={
        "kind": "instrument", "ref_code": "US_SP500"})
    assert r2.json()["created"] is False
    r = await client.get("/api/portfolio/watchlist/all")
    assert any(e["ref_code"] == "US_SP500" for e in r.json()["entries"])
    r = await client.delete(f"/api/portfolio/watchlist/{eid}")
    assert r.status_code == 200
    r = await client.get("/api/portfolio/watchlist/all")
    assert not any(e["ref_code"] == "US_SP500" for e in r.json()["entries"])
