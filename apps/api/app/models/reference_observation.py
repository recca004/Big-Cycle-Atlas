"""Reference-universe observations for calibration (DEC-042).

Separate from `observations`: that table is keyed to the eight tracked
countries. A calibration reference universe (e.g. the full OECD membership
for labour productivity) covers countries we do NOT track — storing those
rows as Observations would wrongly imply tracked-country coverage and would
let country queries leak non-tracked members.

Rows here are calibration inputs only. Immutability and provenance rules
match observations: values are never edited in place; a re-ingestion of the
same period writes a new row with a higher vintage_number.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, JSON, String, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ReferenceObservation(Base):
    __tablename__ = "reference_observations"
    __table_args__ = (
        UniqueConstraint(
            "universe_code",
            "indicator_code",
            "country_iso3",
            "period_start",
            "vintage_number",
            name="uq_reference_obs_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    universe_code: Mapped[str] = mapped_column(String(100), index=True)
    indicator_code: Mapped[str] = mapped_column(String(100), index=True)
    country_iso3: Mapped[str] = mapped_column(String(3), index=True)

    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    value: Mapped[float] = mapped_column()
    unit: Mapped[Optional[str]] = mapped_column(String(100))

    source_key: Mapped[str] = mapped_column(String(50))
    external_code: Mapped[str] = mapped_column(String(200))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    vintage_number: Mapped[int] = mapped_column(default=1)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
