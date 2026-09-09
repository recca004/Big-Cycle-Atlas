"""Micro-Sprint 3.5: wire adapter fetch + persistence + IngestionRun recording.

`run_ingestion` executes one import (fetch from an adapter, persist the
resulting DTOs) and records the whole attempt as an IngestionRun — all inside
the caller's transaction: this module only adds/flushes and never commits.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_sources.base import (
    BaseDataSourceAdapter,
    DataSourceError,
    DataSourceNoDataError,
)
from app.models import DataSource, IngestionRun, IngestionRunStatus
from app.services.observation_service import (
    ObservationPersistenceError,
    PersistenceResult,
    persist_observations,
)


class IngestionError(Exception):
    """The ingestion could not even start — e.g. unknown data source key."""


@dataclass
class IngestionOutcome:
    run: IngestionRun
    persistence: Optional[PersistenceResult]
    error: Optional[str]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def run_ingestion(
    session: AsyncSession,
    adapter: BaseDataSourceAdapter,
    country_iso3: str,
    external_series_code: str,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> IngestionOutcome:
    """Fetch one external series for one country, persist it, record the run.

    Fetch failures are recorded on the run (status=failed) and returned as a
    non-raising outcome. Persistence identity errors raise
    ObservationPersistenceError — the session is then dirty and the caller
    must roll the whole transaction back.
    """
    source = (
        await session.execute(select(DataSource).where(DataSource.key == adapter.source_key))
    ).scalar_one_or_none()
    if source is None:
        raise IngestionError(f"Unknown data source key: {adapter.source_key!r}")

    run = IngestionRun(
        data_source_id=source.id,
        status=IngestionRunStatus.running,
        started_at=_utcnow(),
        run_metadata={
            "country_iso3": country_iso3,
            "external_series_code": external_series_code,
            "start_year": start_year,
            "end_year": end_year,
        },
    )
    session.add(run)
    await session.flush()

    try:
        dtos = await adapter.fetch_indicator(
            country_iso3, external_series_code, start_year=start_year, end_year=end_year
        )
    except DataSourceNoDataError as exc:
        # The source itself said "no observations exist for this request"
        # (e.g. OECD 404 NoRecordsFound for a known no-coverage country).
        # A clean no-data outcome, not an ingestion outage: the run is
        # recorded as a success with zero rows so a missing series never
        # looks like a connector failure.
        run.status = IngestionRunStatus.success
        run.completed_at = _utcnow()
        metadata = dict(run.run_metadata or {})
        metadata["no_data"] = True
        run.run_metadata = metadata
        await session.flush()
        return IngestionOutcome(
            run=run,
            persistence=PersistenceResult(received=0, inserted=0, skipped=0, revised=0),
            error=None,
        )
    except DataSourceError as exc:
        run.status = IngestionRunStatus.failed
        run.completed_at = _utcnow()
        run.error_count = 1
        run.errors = [{"type": type(exc).__name__, "message": str(exc)}]
        await session.flush()
        return IngestionOutcome(run=run, persistence=None, error=f"{type(exc).__name__}: {exc}")

    persistence = await persist_observations(session, dtos)

    run.status = IngestionRunStatus.success
    run.completed_at = _utcnow()
    run.rows_received = persistence.received
    run.rows_inserted = persistence.inserted
    run.rows_skipped = persistence.skipped
    run.rows_revised = persistence.revised
    await session.flush()

    return IngestionOutcome(run=run, persistence=persistence, error=None)