from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class IndicatorRevision(Base):
    __tablename__ = "indicator_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    prior_observation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("observations.id"))
    new_observation_id: Mapped[int] = mapped_column(ForeignKey("observations.id"))
    revision_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    old_value: Mapped[Optional[float]] = mapped_column(Float)
    new_value: Mapped[float] = mapped_column(Float)
    delta: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    prior_observation = relationship("Observation", foreign_keys=[prior_observation_id])
    new_observation = relationship("Observation", foreign_keys=[new_observation_id])
