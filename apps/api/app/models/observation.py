from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, String, func, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (
        # Observation identity is (country, source series, period) + vintage.
        # The unique constraint makes concurrent ingestion runs physically
        # unable to insert the same vintage twice.
        UniqueConstraint(
            "country_id", "source_series_id", "period_start", "vintage_number",
            name="uq_observations_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), index=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"), index=True)
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), index=True)
    source_series_id: Mapped[int] = mapped_column(ForeignKey("source_series.id"), index=True)

    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    value: Mapped[float] = mapped_column()
    unit: Mapped[Optional[str]] = mapped_column(String(100))

    observation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    release_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    vintage_number: Mapped[int] = mapped_column(default=1)
    supersedes_observation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("observations.id"))

    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    country = relationship("Country", back_populates="observations")
    indicator = relationship("Indicator", back_populates="observations")
    data_source = relationship("DataSource", back_populates="observations")
    source_series = relationship("SourceSeries", back_populates="observations")
    superseded_by = relationship("Observation", remote_side=[id], back_populates="supersedes")
    supersedes = relationship("Observation", remote_side=[supersedes_observation_id], back_populates="superseded_by")
