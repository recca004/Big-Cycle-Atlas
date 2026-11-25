"""Market research data layer (Mission 5 §14-§15).

Deliberately separate from macroeconomic `observations`: market
instruments have their own semantics (asset class, currency, return
methodology) and must never be conflated with country indicators.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AssetClass(str, Enum):
    equity_index = "equity_index"
    gov_bond_yield = "gov_bond_yield"
    corporate_bond_yield = "corporate_bond_yield"
    cash_rate = "cash_rate"
    policy_rate = "policy_rate"
    fx_rate = "fx_rate"
    commodity_index = "commodity_index"
    real_estate_index = "real_estate_index"


class ReturnMethodology(str, Enum):
    """What a stored value IS — displayed beside every calculated result."""
    yield_quote = "yield_quote"          # bond yield — NOT a return
    price_index = "price_index"          # index level, dividends excluded
    spot_price = "spot_price"            # commodity spot — NOT futures return
    exchange_rate = "exchange_rate"      # FX quote
    policy_rate_quote = "policy_rate_quote"  # central-bank rate
    spread_quote = "spread_quote"        # credit spread (bp/pct)


class MarketInstrument(Base):
    __tablename__ = "market_instruments"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    asset_class: Mapped[str] = mapped_column(String(40), index=True)
    return_methodology: Mapped[str] = mapped_column(String(40))
    country_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("countries.id"), index=True
    )
    currency: Mapped[str] = mapped_column(String(8))
    unit: Mapped[str] = mapped_column(String(80))
    frequency: Mapped[str] = mapped_column(String(20))   # daily|monthly|quarterly
    data_source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.id"), index=True
    )
    external_code: Mapped[str] = mapped_column(String(160))
    quote_convention: Mapped[Optional[str]] = mapped_column(
        String(80)
    )  # e.g. "USD per EUR" — direction matters for FX
    active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[Optional[str]] = mapped_column(String(400))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MarketObservation(Base):
    __tablename__ = "market_observations"
    __table_args__ = (
        # Identity: one stored value per instrument per trading day.
        # Raw provider values are never overwritten — a changed provider
        # value is visible via retrieved_at + payload checksum, and the
        # revision is recorded on the ingestion run.
        UniqueConstraint(
            "instrument_id", "obs_date", name="uq_market_obs_identity"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("market_instruments.id"), index=True
    )
    obs_date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float] = mapped_column()
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
