from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import DateTime, String, func, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class DataSourceStatus(str, Enum):
    planned = "planned"
    testing = "testing"
    active = "active"
    broken = "broken"

class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    base_url: Mapped[Optional[str]] = mapped_column(String(255))
    auth_type: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[DataSourceStatus] = mapped_column(String(20), default=DataSourceStatus.planned)
    update_frequency: Mapped[Optional[str]] = mapped_column(String(50))
    rate_limit_notes: Mapped[Optional[str]] = mapped_column(Text)
    documentation_url: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    source_series = relationship("SourceSeries", back_populates="data_source")
    ingestion_runs = relationship("IngestionRun", back_populates="data_source")
    observations = relationship("Observation", back_populates="data_source")

    # Metadata about the source (e.g. provenance)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
