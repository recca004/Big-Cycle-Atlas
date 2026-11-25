"""Paper portfolio + watchlist API (Mission 5 §33-§36, §42).

SIMULATION ONLY — every response is labelled simulation=True. No real
money, no brokerage connection, no order routing. These mutation
endpoints are intended for the local-first deployment; public exposure
would require an auth layer that does not exist yet (documented
limitation, §34).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.models import PaperPortfolio, WatchlistEntry
from app.portfolio import service as portfolio_service
from app.portfolio.service import PortfolioError

router = APIRouter(
    prefix=f"{get_settings().api_prefix}/portfolio", tags=["portfolio"]
)


def _dec(v: str | float, field: str) -> Decimal:
    try:
        return Decimal(str(v))
    except InvalidOperation:
        raise PortfolioError(f"{field} must be a number") from None


class CreatePortfolio(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    base_currency: str = "CHF"
    starting_capital: float = Field(gt=0, le=1e15)


class TxnRequest(BaseModel):
    kind: str = Field(pattern="^(buy|sell|deposit)$")
    instrument_code: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    fee: float = 0.0
    executed_at: Optional[datetime] = None
    idempotency_key: str = Field(min_length=4, max_length=80)
    user_entered_price: bool = False


@router.post("")
async def create_portfolio(
    req: CreatePortfolio, session: AsyncSession = Depends(get_session)
):
    p = await portfolio_service.create_portfolio(
        session, req.name, req.base_currency.upper(),
        _dec(req.starting_capital, "starting_capital"),
    )
    await session.commit()
    return {"id": p.id, "name": p.name, "base_currency": p.base_currency,
            "starting_capital": float(p.starting_capital),
            "simulation": True}


@router.get("")
async def list_portfolios(session: AsyncSession = Depends(get_session)):
    rows = list(
        (await session.execute(
            select(PaperPortfolio).order_by(PaperPortfolio.id)
        )).scalars()
    )
    return {"portfolios": [
        {"id": p.id, "name": p.name, "base_currency": p.base_currency,
         "starting_capital": float(p.starting_capital),
         "archived": p.archived, "simulation": True}
        for p in rows
    ]}


async def _portfolio(session: AsyncSession, pid: int) -> PaperPortfolio:
    p = (
        await session.execute(
            select(PaperPortfolio).where(PaperPortfolio.id == pid)
        )
    ).scalar_one_or_none()
    if p is None:
        raise HTTPException(404, f"portfolio {pid} not found")
    return p


@router.get("/{pid}")
async def portfolio_detail(
    pid: int, session: AsyncSession = Depends(get_session)
):
    p = await _portfolio(session, pid)
    return await portfolio_service.valuation(session, p)


@router.get("/{pid}/transactions")
async def portfolio_transactions(
    pid: int, session: AsyncSession = Depends(get_session)
):
    await _portfolio(session, pid)
    txns = await portfolio_service._transactions(session, pid)
    return {"transactions": [
        {
            "id": t.id, "kind": t.kind,
            "instrument_id": t.instrument_id,
            "quantity": float(t.quantity), "price": float(t.price),
            "currency": t.currency, "base_value": float(t.base_value),
            "fee": float(t.fee),
            "user_entered_price": t.user_entered_price,
            "executed_at": t.executed_at.isoformat(),
            "idempotency_key": t.idempotency_key,
        }
        for t in txns
    ], "simulation": True}


@router.post("/{pid}/transactions")
async def post_transaction(
    pid: int, req: TxnRequest, session: AsyncSession = Depends(get_session)
):
    p = await _portfolio(session, pid)
    from app.models import MarketInstrument

    instrument_id = None
    trade_ccy = req.currency or p.base_currency
    if req.kind != "deposit":
        if not req.instrument_code:
            raise HTTPException(422, "instrument_code required")
        inst = (
            await session.execute(
                select(MarketInstrument).where(
                    MarketInstrument.code == req.instrument_code)
            )
        ).scalar_one_or_none()
        if inst is None:
            raise HTTPException(404, f"instrument {req.instrument_code!r} not found")
        instrument_id = inst.id
        trade_ccy = req.currency or inst.currency
        # default price = latest stored market price (never fabricated)
        if req.price is None:
            from app.models import MarketObservation

            px = (
                await session.execute(
                    select(MarketObservation.value)
                    .where(MarketObservation.instrument_id == inst.id)
                    .order_by(MarketObservation.obs_date.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if px is None:
                raise HTTPException(
                    422,
                    "no stored market price — supply price with "
                    "user_entered_price=true to record a simulation price",
                )
            req.price = float(px)
            req.user_entered_price = False
        elif not req.user_entered_price:
            # a supplied price is only accepted when explicitly flagged
            raise HTTPException(
                422,
                "explicit prices require user_entered_price=true "
                "(flagged as a simulation price, not market data)",
            )

    qty = _dec(req.quantity if req.quantity is not None else 1.0, "quantity")
    price = _dec(req.price if req.price is not None else 1.0, "price")
    try:
        t, created = await portfolio_service.post_transaction(
            session, p, req.kind, instrument_id, qty, price,
            trade_ccy.upper(), _dec(req.fee, "fee"),
            req.executed_at or datetime.now(timezone.utc),
            req.idempotency_key, req.user_entered_price,
        )
    except PortfolioError as e:
        raise HTTPException(422, str(e)) from e
    await session.commit()
    return {"id": t.id, "created": created, "kind": t.kind,
            "simulation": True}


@router.post("/{pid}/archive")
async def archive_portfolio(
    pid: int, session: AsyncSession = Depends(get_session)
):
    p = await _portfolio(session, pid)
    p.archived = True
    await session.commit()
    return {"id": p.id, "archived": True, "simulation": True}


# --- Watchlist (§42) ------------------------------------------------------------


class WatchlistReq(BaseModel):
    kind: str = Field(pattern="^(instrument|indicator|country|force|model)$")
    ref_code: str = Field(min_length=1, max_length=80)
    label: Optional[str] = Field(default=None, max_length=160)


@router.get("/watchlist/all")
async def get_watchlist(session: AsyncSession = Depends(get_session)):
    rows = list(
        (await session.execute(
            select(WatchlistEntry).order_by(
                WatchlistEntry.sort_order, WatchlistEntry.id)
        )).scalars()
    )
    return {"entries": [
        {"id": e.id, "kind": e.kind, "ref_code": e.ref_code,
         "label": e.label}
        for e in rows
    ]}


@router.post("/watchlist")
async def add_watchlist(
    req: WatchlistReq, session: AsyncSession = Depends(get_session)
):
    existing = (
        await session.execute(
            select(WatchlistEntry).where(
                WatchlistEntry.kind == req.kind,
                WatchlistEntry.ref_code == req.ref_code,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return {"id": existing.id, "created": False}
    e = WatchlistEntry(
        kind=req.kind, ref_code=req.ref_code, label=req.label,
        sort_order=0,
    )
    session.add(e)
    await session.commit()
    return {"id": e.id, "created": True}


@router.delete("/watchlist/{eid}")
async def remove_watchlist(
    eid: int, session: AsyncSession = Depends(get_session)
):
    e = (
        await session.execute(
            select(WatchlistEntry).where(WatchlistEntry.id == eid)
        )
    ).scalar_one_or_none()
    if e is None:
        raise HTTPException(404, "entry not found")
    await session.delete(e)
    await session.commit()
    return {"removed": True}
