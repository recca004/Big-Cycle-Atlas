"""Strategy research API (Mission 5 §30, §40).

All calculation stays in the backend; the frontend only renders results.
Requests are bounded (date range capped) and every result carries the
evaluation category — market-only benchmarks are never presented as
strict macro-signal backtests.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.strategy import simulator
from app.strategy.definitions import (
    BENCHMARK_STRATEGIES,
    EvaluationCategory,
    StrategySpec,
    equal_weight_strategy,
    fixed_weight_strategy,
)

router = APIRouter(
    prefix=f"{get_settings().api_prefix}/strategies", tags=["strategies"]
)

MAX_RANGE_DAYS = 366 * 40  # bounded evaluation range


@router.get("")
async def list_strategies():
    return {
        "benchmarks": [
            {
                "strategy_id": s.strategy_id,
                "version": s.version,
                "kind": s.kind.value,
                "allocations": dict(s.allocations),
                "rebalance": s.rebalance,
                "category": s.category.value,
                "description": s.description,
            }
            for s in BENCHMARK_STRATEGIES.values()
        ],
        "custom_kinds": ["fixed_weight", "equal_weight"],
        "categories": [c.value for c in EvaluationCategory],
        "note": (
            "regime/macro-signal strategies are GATED — no release-date "
            "evidence exists to run them under strict rules (§31)."
        ),
    }


class SimulateRequest(BaseModel):
    strategy: str = "buy_and_hold_us_equity"   # benchmark id or 'custom'
    kind: Optional[str] = None               # fixed_weight|equal_weight
    allocations: Optional[dict[str, float]] = None
    instruments: Optional[list[str]] = None  # for equal_weight
    start: date
    end: date
    initial_capital: float = Field(gt=0, le=1e12)
    base_currency: str = "CHF"
    rebalance: str = "annual"
    cost_bps: float = Field(default=10.0, ge=0, le=1000)
    slippage_bps: float = Field(default=5.0, ge=0, le=1000)
    benchmark: bool = False                  # attach buy_and_hold benchmark


@router.post("/simulate")
async def simulate(
    req: SimulateRequest, session: AsyncSession = Depends(get_session)
):
    if (req.end - req.start).days > MAX_RANGE_DAYS:
        raise HTTPException(422, "date range exceeds 40-year bound")
    if req.end <= req.start:
        raise HTTPException(422, "end must be after start")
    if req.base_currency not in ("CHF", "USD", "EUR", "GBP"):
        raise HTTPException(422, "unsupported base currency")

    if req.strategy in BENCHMARK_STRATEGIES:
        spec = BENCHMARK_STRATEGIES[req.strategy]
    elif req.kind == "equal_weight":
        if not req.instruments or len(req.instruments) < 2:
            raise HTTPException(422, "equal_weight needs >=2 instruments")
        spec = equal_weight_strategy(req.instruments, req.rebalance)
    else:
        if not req.allocations:
            raise HTTPException(
                422, "custom strategy needs allocations {code: weight}"
            )
        spec = fixed_weight_strategy(req.allocations, req.rebalance)

    errors = spec.validate()
    if errors:
        raise HTTPException(422, "; ".join(errors))

    bench = BENCHMARK_STRATEGIES["buy_and_hold_us_equity"] if req.benchmark else None
    return await simulator.simulate(
        session, spec, req.start, req.end, req.initial_capital,
        req.base_currency, req.cost_bps, req.slippage_bps, bench,
    )
