"""Portfolio simulator (Mission 5 §27-§30).

Monthly-grid long-only unleveraged simulation over stored market prices.

Timing rules (§28): a rebalance decision scheduled at period end D
executes at the FIRST available price strictly AFTER D for each
instrument — a close price is never assumed to be both the signal and
the execution price. Initial positions are established at each
instrument's first stored price on or after the start date.

Missing prices (§27): a position with no stored price on a valuation
date keeps its last known value and the date is recorded under
missing_valuations — prices are never forward-fabricated for trades
(trades execute only when a real stored price exists).

Costs (§29): cost_bps + slippage_bps charged on |trade value|, paid from
cash. No interest on cash unless an instrumented cash instrument is
allocated (flat cash = cash_benchmark).
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.market import fx as fx_service
from app.models import MarketInstrument, MarketObservation
from app.strategy.definitions import (
    STRATEGY_ENGINE_VERSION,
    EvaluationCategory,
    StrategyKind,
    StrategySpec,
)

SIMULATOR_VERSION = "portfolio-sim-v0.1"

# Methodologies that can support a priced position.
INVESTABLE = {"price_index", "spot_price"}


def _month_ends(start: date, end: date) -> list[date]:
    out, y, m = [], start.year, start.month
    while True:
        if m == 12:
            me, ny, nm = date(y, 12, 31), y + 1, 1
        else:
            ny, nm = y, m + 1
            me = date(ny, nm, 1) - timedelta(days=1)
        if me >= start:
            out.append(min(me, end))
        if me >= end:
            return out
        y, m = ny, nm


def _rebalance_dates(month_ends: list[date], freq: str) -> set[date]:
    if freq == "none":
        return set()
    if freq == "monthly":
        return set(month_ends)
    if freq == "quarterly":
        return {d for d in month_ends if d.month in (3, 6, 9, 12)}
    return {d for d in month_ends if d.month == 12}  # annual


@dataclass
class _Series:
    code: str
    currency: str
    points: list[tuple[date, float]]   # ascending stored obs dates

    def price_on_or_before(self, d: date) -> float | None:
        val = None
        for p, v in self.points:
            if p <= d:
                val = v
            else:
                break
        return val

    def first_price_after(self, d: date, strict: bool = True) -> tuple[date, float] | None:
        for p, v in self.points:
            if (p > d) if strict else (p >= d):
                return p, v
        return None


async def _load_series(
    session: AsyncSession, code: str
) -> _Series | None:
    inst = (
        await session.execute(
            select(MarketInstrument).where(MarketInstrument.code == code)
        )
    ).scalar_one_or_none()
    if inst is None:
        return None
    if inst.return_methodology not in INVESTABLE:
        return _Series(code, "__not_investable__", [])
    rows = (
        await session.execute(
            select(MarketObservation.obs_date, MarketObservation.value)
            .where(MarketObservation.instrument_id == inst.id)
            .order_by(MarketObservation.obs_date)
        )
    ).all()
    return _Series(code, inst.currency, list(rows))


async def simulate(
    session: AsyncSession,
    spec: StrategySpec,
    start: date,
    end: date,
    initial_capital: float,
    base_ccy: str,
    cost_bps: float = 0.0,
    slippage_bps: float = 0.0,
    benchmark_spec: StrategySpec | None = None,
) -> dict:
    """Run the simulation; returns the §30 result contract."""
    errors = spec.validate()
    codes = [c for c, _ in spec.allocations]
    series = {}
    load_errors = []
    for c in codes:
        s = await _load_series(session, c)
        if s is None:
            load_errors.append(f"{c}: unknown instrument")
        elif s.currency == "__not_investable__":
            load_errors.append(
                f"{c}: {s.code} methodology not investable (yield/quote)"
            )
        elif not s.points:
            load_errors.append(f"{c}: no stored observations")
        else:
            series[c] = s
    if errors or load_errors:
        return {
            "available": False,
            "unavailable_reason": "; ".join(errors + load_errors),
            "strategy_id": spec.strategy_id,
            "model_version": SIMULATOR_VERSION,
            "category": spec.category.value,
        }

    month_ends = _month_ends(start, end)
    rebal_dates = _rebalance_dates(month_ends, spec.rebalance)

    # --- helpers ---------------------------------------------------------------
    async def price_base(s: _Series, d: date) -> float | None:
        """Instrument price converted to base_ccy at <=d FX (never future)."""
        p = s.price_on_or_before(d)
        if p is None:
            return None
        if s.currency == base_ccy:
            return p
        conv = await fx_service.convert(session, p, s.currency, base_ccy, d)
        return conv["value"] if conv["value"] is not None else None

    async def exec_price_base(s: _Series, after: date) -> tuple[date, float] | None:
        """Next stored price strictly after `after`, converted to base."""
        hit = s.first_price_after(after)
        if hit is None:
            return None
        d, p = hit
        if s.currency == base_ccy:
            return d, p
        conv = await fx_service.convert(session, p, s.currency, base_ccy, d)
        return (d, conv["value"]) if conv["value"] is not None else None

    async def value_positions(
        positions: dict[str, float], d: date, missing: set[str]
    ) -> float:
        total = 0.0
        for c, qty in positions.items():
            p = await price_base(series[c], d)
            if p is None:
                missing.add(d.isoformat())
            else:
                total += qty * p
        return total

    # --- run -------------------------------------------------------------------
    cash = float(initial_capital)
    positions: dict[str, float] = {}
    trades: list[dict] = []
    missing_valuations: set[str] = set()
    total_costs = 0.0
    turnover = 0.0

    async def buy(code: str, spend: float, after: date) -> None:
        nonlocal cash, total_costs, turnover
        hit = await exec_price_base(series[code], after)
        if hit is None or spend <= 0:
            return
        d, p = hit
        cost = spend * (cost_bps + slippage_bps) / 10000.0
        invest = spend - cost
        qty = invest / p
        positions[code] = positions.get(code, 0.0) + qty
        cash -= spend
        total_costs += cost
        turnover += invest
        trades.append({"date": d.isoformat(), "code": code,
                       "side": "buy", "qty": qty, "price": p,
                       "value": invest, "cost": cost})

    async def rebalance(d: date) -> None:
        nonlocal cash, total_costs, turnover
        target_value = cash + await value_positions(
            positions, d, missing_valuations
        )
        # sells first so buys never exceed cash (long-only, unleveraged)
        for code in list(positions):
            cur_p = await price_base(series[code], d)
            target_w = dict(spec.allocations).get(code, 0.0)
            cur_val = positions[code] * cur_p if cur_p else 0.0
            delta_val = target_w * target_value - cur_val
            if delta_val < -1e-9 and cur_p is not None:
                hit = await exec_price_base(series[code], d)
                if hit is None:
                    continue
                ed, ep = hit
                sell_val = min(-delta_val, positions[code] * ep)
                qty = sell_val / ep
                cost = sell_val * (cost_bps + slippage_bps) / 10000.0
                positions[code] -= qty
                if positions[code] <= 1e-12:
                    del positions[code]
                cash += sell_val - cost
                total_costs += cost
                turnover += sell_val
                trades.append({"date": ed.isoformat(), "code": code,
                               "side": "sell", "qty": qty, "price": ep,
                               "value": sell_val, "cost": cost})
        # buys
        total_value = cash + await value_positions(
            positions, d, missing_valuations
        )
        for code, w in spec.allocations:
            cur_p = await price_base(series[code], d)
            cur_val = positions.get(code, 0.0) * cur_p if cur_p else 0.0
            want = w * total_value - cur_val
            spend = min(want, cash)
            if spend > 1e-9:
                await buy(code, spend, d)

    # initial allocation — execute at first prices on/after start
    if spec.kind is not StrategyKind.cash_benchmark:
        for code, w in spec.allocations:
            await buy(code, initial_capital * w, start - timedelta(days=1))

    path = []
    for d in month_ends:
        if d in rebal_dates and spec.kind is not StrategyKind.cash_benchmark:
            await rebalance(d)
        mv = cash + await value_positions(
            positions, d, missing_valuations
        )
        path.append({"date": d.isoformat(), "value": mv, "cash": cash})

    values = [p["value"] for p in path]
    result = _stats(values, 12)
    bench_json = None
    if benchmark_spec is not None:
        bench = await simulate(
            session, benchmark_spec, start, end, initial_capital,
            base_ccy, cost_bps, slippage_bps,
        )
        bench_json = {
            "strategy_id": benchmark_spec.strategy_id,
            "cumulative_return": bench.get("cumulative_return"),
            "final_value": bench.get("final_value"),
        }

    return {
        "available": True,
        "strategy_id": spec.strategy_id,
        "strategy_version": spec.version,
        "model_version": SIMULATOR_VERSION,
        "engine_version": STRATEGY_ENGINE_VERSION,
        "category": spec.category.value,
        "methodology_status": "experimental",
        "date_range": [start.isoformat(), end.isoformat()],
        "initial_capital": initial_capital,
        "base_currency": base_ccy,
        "final_value": values[-1] if values else None,
        **result,
        "turnover": turnover,
        "transaction_costs": total_costs,
        "n_trades": len(trades),
        "trades": trades,
        "path": path,
        "missing_valuations": sorted(missing_valuations),
        "data_sources": {
            c: {"external_code": series[c].points and series[c].code,
                "observations": len(series[c].points),
                "first": series[c].points[0][0].isoformat() if series[c].points else None,
                "last": series[c].points[-1][0].isoformat() if series[c].points else None}
            for c in series
        },
        "execution_assumptions": {
            "timing": "rebalance decisions execute at the first stored "
                      "price strictly after the schedule date",
            "initial_entry": "first stored price on/after start",
            "costs": f"{cost_bps}bps + {slippage_bps}bps slippage per trade",
            "long_only_unleveraged": True,
            "grid": "monthly",
            "excluded": ["interest on cash", "taxes", "margin", "derivatives"],
        },
        "execution_mode": "retrospective_market",
        "backtest_safe": spec.category == EvaluationCategory.strict_eligible,
        "benchmark": bench_json,
        "run_manifest": {
            "simulator": SIMULATOR_VERSION,
            "spec": spec.strategy_id + "@" + spec.version,
            "grid": "monthly",
            "cost_bps": cost_bps,
            "slippage_bps": slippage_bps,
        },
        "warnings": [
            "monthly price-index simulation — dividends, roll and intramonth "
            "moves are not modelled; this is a research benchmark, never an "
            "achievable investment result" if cost_bps == 0 else
            "costs applied; still a research simulation",
        ],
    }


def _stats(values: list[float], periods_per_year: int) -> dict:
    if len(values) < 2:
        return {"cumulative_return": None}
    cum = values[-1] / values[0] - 1.0
    years = len(values) / periods_per_year
    rets = [b / a - 1 for a, b in zip(values, values[1:]) if a]
    peak, mdd = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    return {
        "cumulative_return": cum,
        "annualised_return": (values[-1] / values[0]) ** (1 / years) - 1
        if years > 0 and values[0] > 0 and values[-1] > 0 else None,
        "volatility": (
            statistics.pstdev(rets) * math.sqrt(periods_per_year)
            if len(rets) > 1 else None
        ),
        "max_drawdown": mdd,
    }
