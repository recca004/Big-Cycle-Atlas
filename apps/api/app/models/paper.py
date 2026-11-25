"""Paper portfolio + watchlist models (Mission 5 §32-§34, §42).

Simulation only — no real money, no brokerage. The ledger is fully
isolated from research observations: it references market_instruments
but never touches observation tables. Monetary fields use Numeric and
are processed with Decimal arithmetic.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PaperPortfolio(Base):
    __tablename__ = "paper_portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    base_currency: Mapped[str] = mapped_column(String(8))
    starting_capital: Mapped[float] = mapped_column(Numeric(24, 6))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PaperTransaction(Base):
    __tablename__ = "paper_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("paper_portfolios.id"), index=True
    )
    instrument_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("market_instruments.id"), index=True
    )  # NULL for cash deposits
    kind: Mapped[str] = mapped_column(String(12))   # buy|sell|deposit
    quantity: Mapped[float] = mapped_column(Numeric(28, 10))
    price: Mapped[float] = mapped_column(Numeric(28, 10))
    currency: Mapped[str] = mapped_column(String(8))  # trade currency
    # trade value converted to the portfolio base currency at the
    # execution date's latest stored FX — persisted for auditability.
    base_value: Mapped[float] = mapped_column(Numeric(28, 10))
    fee: Mapped[float] = mapped_column(Numeric(24, 6), default=0)
    # When no stored market price exists the user may enter an explicit
    # simulation price — flagged, never mistaken for market data.
    user_entered_price: Mapped[bool] = mapped_column(Boolean, default=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Duplicate-submission protection: clients supply a unique key; a
    # repeat submission returns the existing row instead of double-posting.
    idempotency_key: Mapped[str] = mapped_column(
        String(80), unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    # instrument | indicator | country | force | model
    ref_code: Mapped[str] = mapped_column(String(80), index=True)
    label: Mapped[Optional[str]] = mapped_column(String(160))
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
