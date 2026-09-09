"""Auxiliary indicator diagnostics storage (DEC-022).

Diagnostics are RAW PROVIDER DATA about a base canonical indicator's
estimate (e.g. the WGI 90% CI bounds and source count). They are NOT
economic indicators, NOT SourceSeries rows, NOT observations, NOT force
inputs and NOT confidence. Diagnostics never enter alignment
(`align_observation_as_of`), force coverage, or the normalization
registry; the persistence path is structurally separate from
`persist_observations`.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class IndicatorDiagnosticKind(str, Enum):
    ci_lower_bound = "ci_lower_bound"
    ci_upper_bound = "ci_upper_bound"
    source_count = "source_count"


class IndicatorDiagnostic(Base):
    __tablename__ = "indicator_diagnostics"
    __table_args__ = (
        # Diagnostic identity is (country, base indicator, source, provider
        # source, provider series, kind, period) + vintage. The unique
        # constraint makes concurrent ingestion runs physically unable to
        # insert the same vintage twice — same principle as
        # uq_observations_identity, deliberately WITHOUT a SourceSeries.
        UniqueConstraint(
            "country_id", "indicator_id", "data_source_id", "provider_source_code",
            "provider_series_code", "diagnostic_kind", "period_start", "vintage_number",
            name="uq_indicator_diagnostics_identity",
        ),
        Index(
            "ix_indicator_diagnostics_lookup",
            "country_id", "indicator_id", "diagnostic_kind", "period_start",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), index=True)
    # The BASE canonical indicator the diagnostic describes (e.g.
    # RULE_OF_LAW_WGI_SCORE). No canonical diagnostic indicators exist.
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"), index=True)
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), index=True)
    diagnostic_kind: Mapped[IndicatorDiagnosticKind] = mapped_column(String(30))
    # Provider-side provenance the rejected SourceSeries rows would have
    # carried: e.g. WB dedicated WGI source id "3" and exact series
    # GOV_WGI_RL.SC_LB. Never collapse these identities.
    provider_source_code: Mapped[str] = mapped_column(String(50))
    provider_series_code: Mapped[str] = mapped_column(String(100))
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    value: Mapped[float] = mapped_column(Float)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    vintage_number: Mapped[int] = mapped_column(default=1)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Rows are immutable (new vintage on change, never UPDATE) — no
    # supersedes/revision-record machinery is needed; the vintages
    # themselves are the history (DEC-022).
    country = relationship("Country")
    indicator = relationship("Indicator")
    data_source = relationship("DataSource")