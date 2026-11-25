"""Paper portfolio ledger (Mission 5 §33-§36).

Deterministic calculations, Decimal arithmetic, average cost basis
(documented assumption — NOT tax accounting). Every transaction is
validated against the ledger state at write time; duplicate submissions
are blocked by a unique idempotency key.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.market import fx as fx_service
from app.models import (
    MarketInstrument,
    MarketObservation,
    PaperPortfolio,
    PaperTransaction,
)

PORTFOLIO_VERSION = "paper-portfolio-v1"
BASE_CURRENCIES = ("CHF", "USD", "EUR", "GBP")


class PortfolioError(Exception):
    """Validation failure — insufficient cash/holdings, bad quantity,
    unknown portfolio/instrument, missing price."""


@dataclass
class Position:
    instrument_id: int
    quantity: Decimal = Decimal(0)
    cost_basis: Decimal = Decimal(0)   # total cost of current holding (avg-cost)


async def create_portfolio(
    session: AsyncSession, name: str, base_currency: str,
    starting_capital: Decimal,
) -> PaperPortfolio:
    if not name.strip():
        raise PortfolioError("name required")
    if base_currency not in BASE_CURRENCIES:
        raise PortfolioError(f"base_currency must be one of {BASE_CURRENCIES}")
    if starting_capital <= 0:
        raise PortfolioError("starting_capital must be > 0")
    p = PaperPortfolio(
        name=name.strip(), base_currency=base_currency,
        starting_capital=starting_capital,
    )
    session.add(p)
    await session.flush()
    return p


async def _transactions(
    session: AsyncSession, portfolio_id: int
) -> list[PaperTransaction]:
    return list(
        (
            await session.execute(
                select(PaperTransaction)
                .where(PaperTransaction.portfolio_id == portfolio_id)
                .order_by(PaperTransaction.executed_at, PaperTransaction.id)
            )
        ).scalars()
    )


def _replay(
    txns: list[PaperTransaction], starting_capital: Decimal
) -> tuple[Decimal, dict[int, Position], Decimal]:
    """Pure ledger replay -> (cash, positions, realised_result).

    Trade amounts are in each transaction's own currency — cash is kept
    in portfolio base currency, so callers pass amounts already converted
    to base at write time (stored as `price`/`quantity` in trade ccy plus
    `fee` in base ccy; the base-ccy trade value is quantity*price*fx and
    is persisted on the transaction's `raw` — see post_transaction)."""
    cash = starting_capital
    positions: dict[int, Position] = {}
    realised = Decimal(0)
    for t in txns:
        qty = Decimal(str(t.quantity))
        px = Decimal(str(t.price))
        fee = Decimal(str(t.fee))
        base_value = Decimal(str(t.base_value))
        if t.kind == "deposit":
            cash += base_value
        elif t.kind == "buy":
            cash -= base_value + fee
            pos = positions.setdefault(t.instrument_id, Position(t.instrument_id))
            pos.quantity += qty
            pos.cost_basis += base_value + fee
        elif t.kind == "sell":
            pos = positions.get(t.instrument_id)
            if pos is None or pos.quantity < qty:
                raise PortfolioError("ledger invariant violated: oversold")
            # average cost basis — documented method, not tax accounting
            avg_cost = pos.cost_basis / pos.quantity if pos.quantity else Decimal(0)
            cost_of_sold = avg_cost * qty
            cash += base_value - fee
            realised += base_value - fee - cost_of_sold
            pos.quantity -= qty
            pos.cost_basis -= cost_of_sold
            if pos.quantity <= 0:
                del positions[t.instrument_id]
    return cash, positions, realised


async def cash_balance(session: AsyncSession, p: PaperPortfolio) -> Decimal:
    txns = await _transactions(session, p.id)
    cash, _, _ = _replay(txns, Decimal(str(p.starting_capital)))
    return cash


async def post_transaction(
    session: AsyncSession,
    p: PaperPortfolio,
    kind: str,
    instrument_id: int | None,
    quantity: Decimal,
    price: Decimal,
    currency: str,
    fee: Decimal,
    executed_at: datetime,
    idempotency_key: str,
    user_entered_price: bool = False,
) -> tuple[PaperTransaction, bool]:
    """Validate + append a ledger entry. Returns (txn, created).

    A repeated idempotency_key returns the original transaction with
    created=False — duplicate submissions can never double-post.
    """
    existing = (
        await session.execute(
            select(PaperTransaction).where(
                PaperTransaction.idempotency_key == idempotency_key
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False

    # Serialize mutations per portfolio: without the row lock two
    # concurrent buys could both pass the cash check and overspend.
    locked = (
        await session.execute(
            select(PaperPortfolio)
            .where(PaperPortfolio.id == p.id)
            .with_for_update()
        )
    ).scalar_one()
    p = locked

    if p.archived:
        raise PortfolioError("portfolio is archived")
    if kind not in ("buy", "sell", "deposit"):
        raise PortfolioError(f"unknown kind {kind!r}")
    if quantity <= 0 and kind != "deposit":
        raise PortfolioError("quantity must be > 0")
    if price <= 0:
        raise PortfolioError("price must be > 0")
    if fee < 0:
        raise PortfolioError("fee must be >= 0")

    # convert trade value into base currency at the execution date's
    # latest stored FX (never a future rate)
    trade_value = quantity * price
    if currency == p.base_currency:
        base_value = trade_value
    else:
        conv = await fx_service.convert(
            session, float(trade_value), currency, p.base_currency,
            executed_at.date(),
        )
        if conv["value"] is None:
            raise PortfolioError(
                conv.get("unavailable_reason", "FX conversion unavailable")
            )
        base_value = Decimal(str(conv["value"]))

    cash, positions, _ = _replay(
        await _transactions(session, p.id),
        Decimal(str(p.starting_capital)),
    )
    if kind == "buy" and base_value + fee > cash:
        raise PortfolioError(
            f"insufficient cash: need {base_value + fee}, have {cash}"
        )
    if kind == "sell":
        pos = positions.get(instrument_id)
        if pos is None or pos.quantity < quantity:
            have = pos.quantity if pos else Decimal(0)
            raise PortfolioError(
                f"insufficient holdings: selling {quantity}, have {have}"
            )
    if kind in ("buy", "sell"):
        inst = (
            await session.execute(
                select(MarketInstrument).where(
                    MarketInstrument.id == instrument_id)
            )
        ).scalar_one_or_none()
        if inst is None:
            raise PortfolioError("unknown instrument")
        if inst.return_methodology not in ("price_index", "spot_price"):
            raise PortfolioError(
                f"{inst.code} methodology {inst.return_methodology} is not "
                "an investable price series"
            )

    t = PaperTransaction(
        portfolio_id=p.id,
        instrument_id=instrument_id if kind != "deposit" else None,
        kind=kind,
        quantity=quantity,
        price=price,
        currency=currency,
        fee=fee,
        user_entered_price=user_entered_price,
        executed_at=executed_at,
        idempotency_key=idempotency_key,
        base_value=base_value,
    )
    session.add(t)
    await session.flush()
    return t, True


async def valuation(session: AsyncSession, p: PaperPortfolio) -> dict:
    """Holdings + market value + performance at latest stored prices."""
    txns = await _transactions(session, p.id)
    cash, positions, realised = _replay(
        txns, Decimal(str(p.starting_capital))
    )
    holdings = []
    total_mv = Decimal(0)
    missing_prices = []
    total_cost = Decimal(0)
    for iid, pos in positions.items():
        inst = (
            await session.execute(
                select(MarketInstrument).where(MarketInstrument.id == iid)
            )
        ).scalar_one()
        px_row = (
            await session.execute(
                select(MarketObservation.obs_date, MarketObservation.value)
                .where(MarketObservation.instrument_id == iid)
                .order_by(MarketObservation.obs_date.desc())
                .limit(1)
            )
        ).first()
        if px_row is None:
            missing_prices.append(inst.code)
            mv_base = None
            px_base = None
        else:
            px_date, px = px_row
            px_dec = Decimal(str(px))
            if inst.currency == p.base_currency:
                px_base = px_dec
            else:
                conv = await fx_service.convert(
                    session, float(px_dec), inst.currency,
                    p.base_currency, date.today(),
                )
                px_base = (
                    Decimal(str(conv["value"]))
                    if conv["value"] is not None else None
                )
            mv_base = px_base * pos.quantity if px_base is not None else None
            if mv_base is not None:
                total_mv += mv_base
        total_cost += pos.cost_basis
        holdings.append({
            "instrument": inst.code,
            "asset_class": inst.asset_class,
            "currency": inst.currency,
            "quantity": float(pos.quantity),
            "cost_basis_base": float(pos.cost_basis),
            "price_base": float(px_base) if px_base is not None else None,
            "price_date": px_row[0].isoformat() if px_row else None,
            "market_value_base": float(mv_base) if mv_base is not None else None,
        })
    total_value = cash + total_mv
    unrealised = total_mv - total_cost
    start = Decimal(str(p.starting_capital))
    return {
        "portfolio_id": p.id,
        "name": p.name,
        "base_currency": p.base_currency,
        "calc_version": PORTFOLIO_VERSION,
        "cash": float(cash),
        "market_value": float(total_mv),
        "total_value": float(total_value),
        "cost_basis_method": "average_cost (not tax accounting)",
        "realised_result": float(realised),
        "unrealised_result": float(unrealised),
        "total_return": float(total_value / start - 1) if start else None,
        "holdings": holdings,
        "missing_prices": missing_prices,
        "n_transactions": len(txns),
        "simulation": True,
    }
