from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, String, func, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class SourceSeries(Base):
    __tablename__ = "source_series"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), index=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"), index=True)
    external_code: Mapped[str] = mapped_column(String(100))
    external_name: Mapped[Optional[str]] = mapped_column(String(120))
    external_unit: Mapped[Optional[str]] = mapped_column(String(100))
    country_scope: Mapped[Optional[str]] = mapped_column(String(50))
    transform_notes: Mapped[Optional[str]] = mapped_column(String(2000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    data_source = relationship("DataSource", back_populates="source_series")
    indicator = relationship("Indicator", back_populates="source_series")
    observations = relationship("Observation", back_populates="source_series")
