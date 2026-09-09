"""Sprint 5.15: WGI diagnostic live ingestion — fetch + persist + IngestionRun.

Narrow path mirroring `run_ingestion` (Micro-Sprint 3.5) but for AUXILIARY
diagnostics: fetches one diagnostic series via a WGI diagnostic fetcher
and persists ONLY through the diagnostics persistence helper — never the
canonical observation persistence path, never a series row, never an
observation row. The IngestionRun metadata makes the auxiliary nature
explicit (data_kind = "indicator_diagnostic").

Caller owns the transaction: this module adds/flushes, never commits.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_sources.base import DataSourceError
from app.data_sources.wgi_diagnostic_specs import WgiDiagnosticSpec
from app.models import DataSource, IngestionRun, IngestionRunStatus
from app.services.indicator_diagnostic_service import (
    DiagnosticPersistenceResult,
    IndicatorDiagnosticPersistenceError,
    persist_indicator_diagnostics,
)


class WgiDiagnosticIngestionError(Exception):
    """The ingestion could not even start — e.g. unknown data source key."""


@dataclass
class WgiDiagnosticIngestionOutcome:
    run: IngestionRun
    persistence: Optional[DiagnosticPersistenceResult]
    error: Optional[str]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def run_wgi_diagnostic_ingestion(
    session: AsyncSession,
    fetcher,
    country_iso3: str,
    spec: WgiDiagnosticSpec,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> WgiDiagnosticIngestionOutcome:
    """Fetch one diagnostic series for one country, persist it via the
    diagnostics path, record the run.

    Fetch failures AND expected persistence/database failures are recorded
    on the run (status=failed) and returned as a non-raising outcome so the
    caller can commit the FAILED audit record. Persistence runs inside a
    SAVEPOINT (nested transaction): on an expected failure only the
    diagnostic work is rolled back — the outer IngestionRun row is retained,
    marked failed, and committed by the caller. Programmer bugs (anything
    outside the project's persistence/domain/database failure classes)
    still propagate.

    EXCEPTION: a DBAPIError whose connection_invalidated is True (the DB
    connection itself is dead) propagates — the outer transaction cannot
    persist a FAILED audit row on a dead connection, so no false audit
    promise is made. The invariant is: every attempted diagnostic series
    leaves SUCCESS or FAILED audit history when the database transaction
    remains writable; a connection-invalidating outage cannot guarantee
    persistence of the audit record.
    """
    source = (
        await session.execute(
            select(DataSource).where(DataSource.key == fetcher.source_key)
        )
    ).scalar_one_or_none()
    if source is None:
        raise WgiDiagnosticIngestionError(
            f"Unknown data source key: {fetcher.source_key!r}"
        )

    run = IngestionRun(
        data_source_id=source.id,
        status=IngestionRunStatus.running,
        started_at=_utcnow(),
        run_metadata={
            "data_kind": "indicator_diagnostic",
            "country_iso3": country_iso3,
            "base_indicator_code": spec.base_indicator_code,
            "diagnostic_kind": spec.diagnostic_kind.value,
            "provider_series_code": spec.provider_series_code,
            "provider_source_code": spec.provider_source_code,
            "start_year": start_year,
            "end_year": end_year,
        },
    )
    session.add(run)
    await session.flush()

    try:
        dtos = await fetcher.fetch_wgi_diagnostic(
            country_iso3, spec, start_year=start_year, end_year=end_year
        )
    except DataSourceError as exc:
        run.status = IngestionRunStatus.failed
        run.completed_at = _utcnow()
        run.error_count = 1
        run.errors = [{"type": type(exc).__name__, "message": str(exc)}]
        await session.flush()
        return WgiDiagnosticIngestionOutcome(
            run=run, persistence=None, error=f"{type(exc).__name__}: {exc}"
        )

    # Persistence runs inside a SAVEPOINT so that an expected persistence
    # or database failure rolls back ONLY the diagnostic rows (and any
    # half-added rows from a multi-DTO batch) while retaining the outer
    # IngestionRun row. The run is then marked FAILED and returned as a
    # non-raising outcome — the caller commits the failed audit record
    # exactly as it already does for fetch failures.
    #
    # Only the project's expected persistence/domain/database failure
    # classes are caught. Programmer bugs (anything else) propagate.
    #
    # EXCEPTION: a DBAPIError with connection_invalidated=True means the
    # database connection itself is unusable (e.g. the server dropped the
    # session, a TCP reset, a postmaster restart). The outer transaction
    # CANNOT persist a FAILED audit row on a dead connection — attempting
    # the flush would either raise again or silently fail. Such an error
    # MUST propagate so the caller's rollback/cleanup runs; we do NOT
    # claim an audit record exists when the DB connection is gone.
    try:
        async with session.begin_nested():
            persistence = await persist_indicator_diagnostics(session, dtos, [spec])
    except (IndicatorDiagnosticPersistenceError, DBAPIError) as exc:
        if isinstance(exc, DBAPIError) and exc.connection_invalidated:
            # The connection is dead — the outer transaction cannot
            # persist the FAILED run. Propagate so the caller can
            # rollback / close / retry at a higher level.
            raise
        # The savepoint has been rolled back automatically; the outer
        # transaction and its flushed IngestionRun row remain usable.
        run.status = IngestionRunStatus.failed
        run.completed_at = _utcnow()
        run.error_count = 1
        run.errors = [{"type": type(exc).__name__, "message": str(exc)}]
        await session.flush()
        return WgiDiagnosticIngestionOutcome(
            run=run, persistence=None, error=f"{type(exc).__name__}: {exc}"
        )

    run.status = IngestionRunStatus.success
    run.completed_at = _utcnow()
    run.rows_received = persistence.received
    run.rows_inserted = persistence.inserted
    run.rows_skipped = persistence.skipped
    run.rows_revised = persistence.revised
    await session.flush()

    return WgiDiagnosticIngestionOutcome(run=run, persistence=persistence, error=None)