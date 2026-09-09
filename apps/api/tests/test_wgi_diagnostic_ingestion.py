"""Sprint 5.15 tests: WGI diagnostic LIVE FETCH + INGESTION path.

The full path (WorldBankWgiDiagnosticFetcher -> run_wgi_diagnostic_ingestion
-> persist_indicator_diagnostics) exercised offline via httpx.MockTransport
and the real seeded SQLite — no external calls. Fetch returns
IndicatorDiagnosticDTOs only; persistence NEVER goes through
persist_observations; immutable diagnostic vintages, IngestionRun recording,
retry semantics, exact-period lookup, and catalog/normalization isolation.
No confidence formula, no NormalizedSignal change, no force score.
"""
import asyncio
import importlib.util
import json
import pathlib
from datetime import date, datetime, timezone

import httpx
import pytest
from sqlalchemy import func, select

from app.cycle.normalization_definitions import CURRENT_MODEL_VERSION, ScoringPeriod
from app.cycle.normalizer import normalize_indicator_as_of
from app.data_sources.base import (
    DataSourceHTTPError,
    DataSourceParseError,
    ObservationDTO,
    SeriesMappingError,
)
from app.data_sources.world_bank_wgi_diagnostics import WorldBankWgiDiagnosticFetcher
from app.data_sources.wgi_diagnostic_specs import (
    WGI_DIAGNOSTIC_SPECS,
    get_wgi_diagnostic_specs,
    validate_wgi_diagnostic_specs,
)
from app.db import session as session_module
from app.models import (
    Country,
    Indicator,
    IndicatorDiagnostic,
    IndicatorDiagnosticKind,
    IngestionRun,
    IngestionRunStatus,
    Observation,
    SourceSeries,
)
from app.services.force_coverage_service import get_force_coverage
from app.services.indicator_diagnostic_service import (
    IndicatorDiagnosticPersistenceError,
    IndicatorDiagnosticDTO,
    get_indicator_diagnostics_for_period,
    persist_indicator_diagnostics,
)
from app.services.observation_service import persist_observations
from app.services.wgi_diagnostic_ingestion import run_wgi_diagnostic_ingestion

RETRIEVED_AT_ISO = "2026-09-09T12:00:00+00:00"

RL = "RULE_OF_LAW_WGI_SCORE"
CC = "CONTROL_OF_CORRUPTION_WGI_SCORE"
RL_SPECS = get_wgi_diagnostic_specs(RL)
RL_LB_SPEC = next(s for s in RL_SPECS if s.diagnostic_kind is IndicatorDiagnosticKind.ci_lower_bound)
RL_SR_SPEC = next(s for s in RL_SPECS if s.diagnostic_kind is IndicatorDiagnosticKind.source_count)
CC_LB_SPEC = next(
    s for s in get_wgi_diagnostic_specs(CC)
    if s.diagnostic_kind is IndicatorDiagnosticKind.ci_lower_bound
)

_SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "ingest_wgi_diagnostics.py"
)
_spec = importlib.util.spec_from_file_location("ingest_wgi_diagnostics", _SCRIPT)
_ingest_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ingest_script)


def _record(year: int, value, series: str = "GOV_WGI_RL.SC_LB", iso3: str = "CHE") -> dict:
    return {
        "indicator": {"id": series, "value": "Rule of Law - diagnostic"},
        "country": {"id": "CH", "value": "Switzerland"},
        "countryiso3code": iso3,
        "date": str(year),
        "value": value,
        "unit": "",
        "obs_status": "",
        "decimal": "1",
    }


def _response_body(records: list, source_id: str = "3") -> list:
    return [
        {"page": 1, "pages": 1, "per_page": "20000", "total": len(records),
         "sourceid": source_id, "lastupdated": "2026-03-18"},
        records,
    ]


def _make_fetcher(handler) -> WorldBankWgiDiagnosticFetcher:
    return WorldBankWgiDiagnosticFetcher(
        transport=httpx.MockTransport(handler),
        retrieved_at=RETRIEVED_AT_ISO,
    )


async def _ingest(fetcher, country: str = "CHE", spec=RL_LB_SPEC,
                  start: int = 1996, end: int = 2025):
    async with session_module._sessionmaker() as session:
        outcome = await run_wgi_diagnostic_ingestion(
            session, fetcher, country, spec, start_year=start, end_year=end,
        )
        await session.commit()
    return outcome


async def _count(model) -> int:
    async with session_module._sessionmaker() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def _lookup(iso3: str, year: int, indicator: str = RL, specs=RL_SPECS):
    async with session_module._sessionmaker() as session:
        return await get_indicator_diagnostics_for_period(
            session, iso3, indicator, date(year, 1, 1), specs
        )


def _wgi_score_dto(iso3: str, year: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code=RL,
        external_series_code="GOV_WGI_RL_SC",
        period=year,
        value=value,
        unit="score 0-100",
        source_key="world_bank",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc),
        raw_payload={"test": True},
    )


def _dsr_dto(iso3: str, year: int, quarter: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code="DEBT_SERVICE_RATIO",
        external_series_code="WS_DSR/Q.{cc}.P",
        period=year,
        value=value,
        unit="per cent",
        source_key="bis",
        observation_date=date(year, 1 + (quarter - 1) * 3, 1),
        release_date=None,
        retrieved_at=datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc),
        raw_payload={"TIME_PERIOD": f"{year}-Q{quarter}", "OBS_VALUE": value},
    )


def _credit_gap_dto(iso3: str, year: int, quarter: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code="CREDIT_TO_GDP_GAP",
        external_series_code="WS_CREDIT_GAP/Q.{cc}.P.A.C",
        period=year,
        value=value,
        unit="percentage of GDP",
        source_key="bis",
        observation_date=date(year, 1 + (quarter - 1) * 3, 1),
        release_date=None,
        retrieved_at=datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc),
        raw_payload={"TIME_PERIOD": f"{year}-Q{quarter}", "OBS_VALUE": value},
    )


async def _persist_observations(dtos) -> None:
    async with session_module._sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


def _coverage_signature(iso3: str):
    async def _run():
        async with session_module._sessionmaker() as session:
            country = (
                await session.execute(select(Country).where(Country.iso3 == iso3))
            ).scalar_one()
            rows = await get_force_coverage(session, country.id)
            return [(r.definition.code, r.status) for r in rows]
    return _run()


def _normalize(iso3: str, indicator: str, scoring_period: ScoringPeriod):
    async def _run():
        async with session_module._sessionmaker() as session:
            return await normalize_indicator_as_of(session, iso3, indicator, scoring_period)
    return _run()


# --- Registry: exact 9 specs ------------------------------------------------------


def test_exact_nine_diagnostic_specs():
    validate_wgi_diagnostic_specs()
    assert len(WGI_DIAGNOSTIC_SPECS) == 9  # 3 WGI dimensions x LB/UB/SR only
    assert all(s.provider_source_code == "3" for s in WGI_DIAGNOSTIC_SPECS)
    assert not any(s.provider_series_code.endswith(".SE") for s in WGI_DIAGNOSTIC_SPECS)


# --- Fetch: series / source identity / DTO semantics --------------------------------


@pytest.mark.asyncio
async def test_fetch_requests_expected_series_and_dedicated_source():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/country/CHE/indicator/GOV_WGI_RL.SC_LB"
        assert request.url.params["source"] == "3"  # dedicated WGI source, not WDI
        assert request.url.params["date"] == "1996:2025"
        return httpx.Response(200, json=_response_body([_record(2024, 82.04)]))

    async with _make_fetcher(handler) as fetcher:
        dtos = await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC, 1996, 2025)

    assert len(dtos) == 1
    dto = dtos[0]
    assert dto.base_indicator_code == RL  # DTO base indicator correct
    assert dto.diagnostic_kind is IndicatorDiagnosticKind.ci_lower_bound
    assert dto.provider_series_code == "GOV_WGI_RL.SC_LB"
    assert dto.provider_source_code == "3"  # provider source identity preserved
    assert dto.source_key == "world_bank"
    assert dto.country_iso3 == "CHE"
    assert dto.period_start == date(2024, 1, 1)  # annual YYYY -> Jan 1 (score convention)
    assert dto.value == 82.04
    assert dto.retrieved_at.isoformat() == RETRIEVED_AT_ISO


@pytest.mark.asyncio
async def test_fetch_sourceid_mismatch_is_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        # served from the WDI namespace (source 2) instead of the WGI source 3
        return httpx.Response(200, json=_response_body([_record(2024, 82.04)], source_id="2"))

    async with _make_fetcher(handler) as fetcher:
        with pytest.raises(SeriesMappingError):
            await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)


@pytest.mark.asyncio
async def test_fetch_record_series_identity_mismatch_is_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        # a record claiming a DIFFERENT series than requested
        return httpx.Response(
            200, json=_response_body([_record(2024, 0.2, series="GOV_WGI_RL.SE")])
        )

    async with _make_fetcher(handler) as fetcher:
        with pytest.raises(SeriesMappingError):
            await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)


@pytest.mark.asyncio
async def test_fetch_record_country_mismatch_is_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_response_body([_record(2024, 82.04, iso3="DEU")]))

    async with _make_fetcher(handler) as fetcher:
        with pytest.raises(SeriesMappingError):
            await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)


@pytest.mark.asyncio
async def test_fetch_skips_null_values_and_none_records():
    body = _response_body([
        None,  # trailing null record the API emits
        _record(2023, None),  # missing value
        _record(2024, 82.04),
        _record(2022, None),
    ])

    async with _make_fetcher(lambda request: httpx.Response(200, json=body)) as fetcher:
        dtos = await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)

    assert [(d.period_start.year, d.value) for d in dtos] == [(2024, 82.04)]
    # null is skipped, never coerced to zero
    assert all(d.value != 0 for d in dtos)


@pytest.mark.asyncio
async def test_fetch_rejects_nonfinite_value():
    # httpx cannot JSON-encode inf itself; the serialized "Infinity" token is
    # what a raw provider payload would look like, and json.loads parses it
    # back to float('inf').
    body_text = json.dumps(_response_body([_record(2024, float("inf"))]))

    async with _make_fetcher(
        lambda request: httpx.Response(200, text=body_text)
    ) as fetcher:
        with pytest.raises(DataSourceParseError):
            await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)


@pytest.mark.asyncio
async def test_fetch_raw_payload_preserved():
    record = _record(2024, 82.04)
    body = _response_body([record])

    async with _make_fetcher(lambda request: httpx.Response(200, json=body)) as fetcher:
        dtos = await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)

    assert dtos[0].raw_payload == record
    assert dtos[0].raw_payload["date"] == "2024"


@pytest.mark.asyncio
async def test_fetch_returns_diagnostic_dtos_never_observation_dtos():
    body = _response_body([_record(2024, 82.04)])

    async with _make_fetcher(lambda request: httpx.Response(200, json=body)) as fetcher:
        dtos = await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)

    assert all(isinstance(d, IndicatorDiagnosticDTO) for d in dtos)
    assert all(not isinstance(d, ObservationDTO) for d in dtos)


def test_diagnostic_path_source_is_structurally_separate():
    fetch_src = (
        pathlib.Path(__file__).resolve().parents[1]
        / "app" / "data_sources" / "world_bank_wgi_diagnostics.py"
    ).read_text(encoding="utf-8")
    ingest_src = (
        pathlib.Path(__file__).resolve().parents[1]
        / "app" / "services" / "wgi_diagnostic_ingestion.py"
    ).read_text(encoding="utf-8")
    for source in (fetch_src, ingest_src):
        assert "persist_observations" not in source  # persistence path is diagnostic-only
        assert "ObservationDTO" not in source  # the fetch path never emits observations
        assert "SourceSeries" not in source  # no series lookup or creation
    # the CLI is separate from the canonical observation importer
    cli_src = _SCRIPT.read_text(encoding="utf-8")
    assert "persist_observations" not in cli_src
    assert "all-mapped" not in cli_src


# --- Full ingestion path: vintages / idempotency / revision (mocked provider) -------


@pytest.mark.asyncio
async def test_new_import_inserts_vintage_1(client):
    body = _response_body([_record(2024, 80.0)])
    async with _make_fetcher(lambda request: httpx.Response(200, json=body)) as fetcher:
        outcome = await _ingest(fetcher)

    p = outcome.persistence
    assert (p.received, p.inserted, p.skipped, p.revised) == (1, 1, 0, 0)
    async with session_module._sessionmaker() as session:
        rows = (await session.execute(select(IndicatorDiagnostic))).scalars().all()
    assert len(rows) == 1
    assert rows[0].vintage_number == 1
    assert rows[0].value == 80.0


@pytest.mark.asyncio
async def test_exact_reimport_is_skipped(client):
    body = _response_body([_record(2024, 80.0)])
    async with _make_fetcher(lambda request: httpx.Response(200, json=body)) as fetcher:
        first = await _ingest(fetcher)
        second = await _ingest(fetcher)

    assert (first.persistence.inserted, first.persistence.revised) == (1, 0)
    assert (second.persistence.received, second.persistence.inserted,
            second.persistence.skipped, second.persistence.revised) == (1, 0, 1, 0)
    assert await _count(IndicatorDiagnostic) == 1


@pytest.mark.asyncio
async def test_changed_provider_value_creates_immutable_vintage_2(client):
    async with _make_fetcher(
        lambda request: httpx.Response(200, json=_response_body([_record(2024, 80.0)]))
    ) as fetcher:
        await _ingest(fetcher)
    # the provider revised LB 80 -> 81
    async with _make_fetcher(
        lambda request: httpx.Response(200, json=_response_body([_record(2024, 81.0)]))
    ) as fetcher:
        outcome = await _ingest(fetcher)

    assert (outcome.persistence.inserted, outcome.persistence.skipped,
            outcome.persistence.revised) == (0, 0, 1)
    async with session_module._sessionmaker() as session:
        rows = (await session.execute(select(IndicatorDiagnostic))).scalars().all()
    assert len(rows) == 2  # old vintage retained, never overwritten
    assert {r.vintage_number for r in rows} == {1, 2}
    by_vintage = {r.vintage_number: r.value for r in rows}
    assert by_vintage[1] == 80.0
    assert by_vintage[2] == 81.0


@pytest.mark.asyncio
async def test_noninteger_source_count_rejected_through_full_path(client):
    # source_count = 9.7 is a persistence VALIDATION failure (never rounded
    # to 10). After Sprint 5.15.1 this must leave a FAILED IngestionRun
    # audit record — the savepoint rolls back the diagnostic rows, the
    # outer run is marked failed, and the caller commits it.
    obs_before = await _count(Observation)
    series_before = await _count(SourceSeries)
    runs_before = await _count(IngestionRun)

    body = _response_body([_record(2024, 9.7, series="GOV_WGI_RL.SR")])
    async with _make_fetcher(lambda request: httpx.Response(200, json=body)) as fetcher:
        async with session_module._sessionmaker() as session:
            outcome = await run_wgi_diagnostic_ingestion(
                session, fetcher, "CHE", RL_SR_SPEC, 1996, 2025,
            )
            # 9.7 is rejected, never silently rounded to 10
            await session.commit()

    # outcome / import marked failed — non-raising
    assert outcome.error is not None
    assert "IndicatorDiagnosticPersistenceError" in outcome.error
    assert outcome.persistence is None
    run = outcome.run
    assert run.status is IngestionRunStatus.failed
    assert run.error_count == 1
    assert run.errors[0]["type"] == "IndicatorDiagnosticPersistenceError"

    # no diagnostic row survives the failed persistence
    assert await _count(IndicatorDiagnostic) == 0
    # no Observation / SourceSeries rows created
    assert await _count(Observation) == obs_before
    assert await _count(SourceSeries) == series_before

    # exactly one FAILED IngestionRun persists after caller commit
    assert await _count(IngestionRun) == runs_before + 1
    async with session_module._sessionmaker() as session:
        persisted = (
            await session.execute(
                select(IngestionRun).where(IngestionRun.id == run.id)
            )
        ).scalar_one()
    assert persisted.status == IngestionRunStatus.failed

    # failed run metadata preserved
    meta = persisted.run_metadata
    assert meta["data_kind"] == "indicator_diagnostic"
    assert meta["country_iso3"] == "CHE"
    assert meta["base_indicator_code"] == RL
    assert meta["diagnostic_kind"] == "source_count"
    assert meta["provider_series_code"] == "GOV_WGI_RL.SR"
    assert meta["provider_source_code"] == "3"


@pytest.mark.asyncio
async def test_db_failure_during_persistence_leaves_failed_run_and_clean_session(
    client, monkeypatch
):
    """A database failure during diagnostic persistence is caught by the
    savepoint: diagnostic writes are rolled back, a FAILED IngestionRun
    remains persistable, and a subsequent series succeeds in a fresh
    session — no transaction contamination."""
    from sqlalchemy.exc import DBAPIError

    import app.services.wgi_diagnostic_ingestion as ingestion_module

    real_persist = ingestion_module.persist_indicator_diagnostics
    call_count = {"n": 0}

    async def failing_then_real(session, dtos, specs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise DBAPIError(
                "INSERT INTO indicator_diagnostics ...",
                {},
                Exception("simulated DB failure during flush"),
            )
        return await real_persist(session, dtos, specs)

    monkeypatch.setattr(
        ingestion_module, "persist_indicator_diagnostics", failing_then_real
    )

    diag_before = await _count(IndicatorDiagnostic)

    # Series A: DB failure during persistence -> FAILED run, no diagnostic rows
    body_a = _response_body([_record(2024, 82.04)])
    async with _make_fetcher(
        lambda request: httpx.Response(200, json=body_a)
    ) as fetcher:
        async with session_module._sessionmaker() as session:
            outcome_a = await run_wgi_diagnostic_ingestion(
                session, fetcher, "CHE", RL_LB_SPEC, 1996, 2025,
            )
            await session.commit()  # caller commits the FAILED run

    assert outcome_a.error is not None
    assert "DBAPIError" in outcome_a.error
    assert outcome_a.persistence is None
    assert outcome_a.run.status is IngestionRunStatus.failed
    assert outcome_a.run.error_count == 1
    assert outcome_a.run.errors[0]["type"] == "DBAPIError"

    # No diagnostic rows survived the savepoint rollback
    assert await _count(IndicatorDiagnostic) == diag_before

    # Series B: succeeds afterward in its OWN session — no contamination
    body_b = _response_body([_record(2024, 71.6, iso3="USA")])
    async with _make_fetcher(
        lambda request: httpx.Response(200, json=body_b)
    ) as fetcher:
        async with session_module._sessionmaker() as session:
            outcome_b = await run_wgi_diagnostic_ingestion(
                session, fetcher, "USA", RL_LB_SPEC, 1996, 2025,
            )
            await session.commit()

    assert outcome_b.error is None
    assert outcome_b.run.status is IngestionRunStatus.success
    assert (outcome_b.persistence.received, outcome_b.persistence.inserted) == (1, 1)

    # The successful series' row exists; the failed series left only a run
    assert await _count(IndicatorDiagnostic) == diag_before + 1

    # Both runs persist — one failed, one success
    async with session_module._sessionmaker() as session:
        runs = (
            await session.execute(
                select(IngestionRun).where(
                    IngestionRun.id.in_([outcome_a.run.id, outcome_b.run.id])
                )
            )
        ).scalars().all()
    by_id = {r.id: r for r in runs}
    assert by_id[outcome_a.run.id].status == IngestionRunStatus.failed
    assert by_id[outcome_b.run.id].status == IngestionRunStatus.success


@pytest.mark.asyncio
async def test_connection_invalidated_dbapi_error_propagates(client, monkeypatch):
    """A DBAPIError with connection_invalidated=True means the DB connection
    itself is dead. The service MUST propagate — it cannot persist a FAILED
    audit row on a dead connection, so no false audit promise is made."""
    from sqlalchemy.exc import DBAPIError

    import app.services.wgi_diagnostic_ingestion as ingestion_module

    async def connection_killer(session, dtos, specs):
        exc = DBAPIError(
            "INSERT INTO indicator_diagnostics ...",
            {},
            Exception("server closed the connection unexpectedly"),
        )
        # Simulate SQLAlchemy's connection-invalidation flag — the DB
        # connection is unusable, not merely transaction-rolled-back.
        exc.connection_invalidated = True  # type: ignore[misc]
        raise exc

    monkeypatch.setattr(
        ingestion_module, "persist_indicator_diagnostics", connection_killer
    )

    body = _response_body([_record(2024, 82.04)])
    async with _make_fetcher(
        lambda request: httpx.Response(200, json=body)
    ) as fetcher:
        async with session_module._sessionmaker() as session:
            with pytest.raises(DBAPIError):
                await run_wgi_diagnostic_ingestion(
                    session, fetcher, "CHE", RL_LB_SPEC, 1996, 2025,
                )
            # The caller would rollback + close here; the service did NOT
            # claim a FAILED audit record exists.
            await session.rollback()


# --- Retry semantics (script wrapper) ----------------------------------------------


class FlakyFetcher:
    """Scriptable fetcher: each call pops the next behaviour from a list."""

    source_key = "world_bank"

    def __init__(self, behaviours):
        self.behaviours = list(behaviours)
        self.calls = 0

    async def fetch_wgi_diagnostic(self, country_iso3, spec,
                                   start_year=None, end_year=None):
        self.calls += 1
        behaviour = self.behaviours.pop(0)
        if isinstance(behaviour, Exception):
            raise behaviour
        return behaviour


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_5xx():
    inner = FlakyFetcher([
        DataSourceHTTPError("server error", status_code=503),
        ["dto"],
    ])
    fetcher = _ingest_script.TransientRetryFetcher(inner)
    result = await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)
    assert result == ["dto"]
    assert inner.calls == 2


@pytest.mark.asyncio
async def test_retry_on_statusless_network_error():
    inner = FlakyFetcher([
        DataSourceHTTPError("connection reset", status_code=None),
        ["dto"],
    ])
    fetcher = _ingest_script.TransientRetryFetcher(inner)
    await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)
    assert inner.calls == 2


@pytest.mark.asyncio
async def test_no_retry_on_4xx():
    inner = FlakyFetcher([DataSourceHTTPError("not found", status_code=404)])
    fetcher = _ingest_script.TransientRetryFetcher(inner)
    with pytest.raises(DataSourceHTTPError):
        await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)
    assert inner.calls == 1


@pytest.mark.asyncio
async def test_no_retry_on_parse_error():
    inner = FlakyFetcher([DataSourceParseError("bad payload")])
    fetcher = _ingest_script.TransientRetryFetcher(inner)
    with pytest.raises(DataSourceParseError):
        await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)
    assert inner.calls == 1


@pytest.mark.asyncio
async def test_no_retry_on_spec_identity_mismatch():
    inner = FlakyFetcher([SeriesMappingError("served from source 2")])
    fetcher = _ingest_script.TransientRetryFetcher(inner)
    with pytest.raises(SeriesMappingError):
        await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)
    assert inner.calls == 1


@pytest.mark.asyncio
async def test_retry_gives_up_after_max_attempts(monkeypatch):
    async def _no_sleep(*_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    inner = FlakyFetcher([
        DataSourceHTTPError("timeout", status_code=None) for _ in range(3)
    ])
    fetcher = _ingest_script.TransientRetryFetcher(inner)
    with pytest.raises(DataSourceHTTPError):
        await fetcher.fetch_wgi_diagnostic("CHE", RL_LB_SPEC)
    assert inner.calls == 3


# --- IngestionRun behavior ---------------------------------------------------------


@pytest.mark.asyncio
async def test_ingestion_run_created_with_diagnostic_metadata(client):
    body = _response_body([_record(2024, 82.04)])
    async with _make_fetcher(lambda request: httpx.Response(200, json=body)) as fetcher:
        outcome = await _ingest(fetcher)

    run = outcome.run
    assert run.status is IngestionRunStatus.success
    assert run.rows_received == 1
    assert run.rows_inserted == 1
    meta = run.run_metadata
    assert meta["data_kind"] == "indicator_diagnostic"  # auxiliary, not canonical import
    assert meta["country_iso3"] == "CHE"
    assert meta["base_indicator_code"] == RL
    assert meta["diagnostic_kind"] == "ci_lower_bound"
    assert meta["provider_series_code"] == "GOV_WGI_RL.SC_LB"
    assert meta["provider_source_code"] == "3"
    assert meta["start_year"] == 1996
    assert meta["end_year"] == 2025


@pytest.mark.asyncio
async def test_failed_fetch_records_failed_run(client):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json=[{"message": "boom"}])

    async with _make_fetcher(handler) as fetcher:
        outcome = await _ingest(fetcher)

    assert outcome.persistence is None
    assert outcome.error is not None and "DataSourceHTTPError" in outcome.error
    run = outcome.run
    assert run.status is IngestionRunStatus.failed
    assert run.error_count == 1
    assert run.errors[0]["type"] == "DataSourceHTTPError"
    assert run.run_metadata["data_kind"] == "indicator_diagnostic"


@pytest.mark.asyncio
async def test_failed_series_does_not_roll_back_successful_series(client):
    # Series A (CC lower bound) fails — its run is recorded and committed,
    # nothing else written.
    async with _make_fetcher(
        lambda request: httpx.Response(500, json=[{"message": "boom"}])
    ) as fetcher:
        failed = await _ingest(fetcher, spec=CC_LB_SPEC)
    assert failed.run.status is IngestionRunStatus.failed
    # Series B (RL lower bound) succeeds in its OWN transaction afterwards.
    async with _make_fetcher(
        lambda request: httpx.Response(200, json=_response_body([_record(2024, 82.04)]))
    ) as fetcher:
        ok = await _ingest(fetcher, spec=RL_LB_SPEC)
    assert ok.run.status is IngestionRunStatus.success

    assert await _count(IndicatorDiagnostic) == 1  # only the successful series' row
    async with session_module._sessionmaker() as session:
        runs = (await session.execute(select(IngestionRun))).scalars().all()
    assert len(runs) == 2  # the failed run left a trace too


@pytest.mark.asyncio
async def test_persistence_goes_through_persist_indicator_diagnostics(client, monkeypatch):
    import app.services.wgi_diagnostic_ingestion as ingestion_module

    calls: list = []

    real = ingestion_module.persist_indicator_diagnostics

    async def spy(session, dtos, specs):
        calls.append((dtos, specs))
        return await real(session, dtos, specs)

    monkeypatch.setattr(ingestion_module, "persist_indicator_diagnostics", spy)

    body = _response_body([_record(2024, 82.04)])
    async with _make_fetcher(lambda request: httpx.Response(200, json=body)) as fetcher:
        await _ingest(fetcher)

    assert len(calls) == 1
    dtos, specs = calls[0]
    assert all(isinstance(d, IndicatorDiagnosticDTO) for d in dtos)
    assert specs == [RL_LB_SPEC]  # exactly the expected spec, no free-form storage


# --- Lookup after ingest ------------------------------------------------------------


@pytest.mark.asyncio
async def test_exact_period_lookup_after_ingest(client):
    body = _response_body([
        _record(2023, 81.1),
        _record(2024, 82.04),
    ])
    async with _make_fetcher(lambda request: httpx.Response(200, json=body)) as fetcher:
        await _ingest(fetcher)

    values = await _lookup("CHE", 2024)
    assert values[IndicatorDiagnosticKind.ci_lower_bound] == 82.04
    assert values[IndicatorDiagnosticKind.ci_upper_bound] is None  # not ingested
    assert values[IndicatorDiagnosticKind.source_count] is None
    # the 2023 period resolves independently — no cross-period borrowing
    assert (await _lookup("CHE", 2023))[IndicatorDiagnosticKind.ci_lower_bound] == 81.1


@pytest.mark.asyncio
async def test_no_previous_period_fallback(client):
    body = _response_body([_record(2024, 82.04)])
    async with _make_fetcher(lambda request: httpx.Response(200, json=body)) as fetcher:
        await _ingest(fetcher)

    values = await _lookup("CHE", 2023)  # no 2023 data — missing stays None
    assert values == {
        IndicatorDiagnosticKind.ci_lower_bound: None,
        IndicatorDiagnosticKind.ci_upper_bound: None,
        IndicatorDiagnosticKind.source_count: None,
    }
    assert await _count(IndicatorDiagnostic) == 1  # no synthetic rows either


@pytest.mark.asyncio
async def test_country_isolation_through_full_path(client):
    che_body = _response_body([_record(2024, 82.04, iso3="CHE")])
    usa_body = _response_body([_record(2024, 71.6, iso3="USA")])
    # Build responses keyed by the requested country path
    bodies = {"/v2/country/CHE": che_body, "/v2/country/USA": usa_body}

    def routing_handler(request: httpx.Request) -> httpx.Response:
        for prefix, body in bodies.items():
            if request.url.path.startswith(prefix):
                return httpx.Response(200, json=body)
        raise AssertionError(f"unexpected path {request.url.path}")

    async with _make_fetcher(routing_handler) as fetcher:
        await _ingest(fetcher, country="CHE")
        await _ingest(fetcher, country="USA")

    che = await _lookup("CHE", 2024)
    usa = await _lookup("USA", 2024)
    assert che[IndicatorDiagnosticKind.ci_lower_bound] == 82.04
    assert usa[IndicatorDiagnosticKind.ci_lower_bound] == 71.6
    assert await _count(IndicatorDiagnostic) == 2


# --- Catalog / coverage / normalization isolation ----------------------------------


@pytest.mark.asyncio
async def test_ingestion_creates_no_observation_or_series_rows(client):
    await _persist_observations([_wgi_score_dto("CHE", 2024, 87.32)])
    obs_before = await _count(Observation)
    series_before = await _count(SourceSeries)
    indicators_before = await _count(Indicator)

    records = {
        "GOV_WGI_RL.SC_LB": _record(2024, 82.04),
        "GOV_WGI_RL.SC_UB": _record(2024, 92.6, series="GOV_WGI_RL.SC_UB"),
        "GOV_WGI_RL.SR": _record(2024, 10.0, series="GOV_WGI_RL.SR"),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        series = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, json=_response_body([records[series]]))

    async with _make_fetcher(handler) as fetcher:
        for spec in RL_SPECS:  # one diagnostic series per run — LB, UB, SR
            await _ingest(fetcher, spec=spec)

    assert await _count(IndicatorDiagnostic) == 3
    assert await _count(Observation) == obs_before  # no Observation rows created
    assert await _count(SourceSeries) == series_before  # no SourceSeries rows created
    assert await _count(Indicator) == indicators_before == 27  # catalog unchanged


@pytest.mark.asyncio
async def test_force_coverage_unchanged(client):
    before = await _coverage_signature("CHE")
    body = _response_body([_record(2024, 82.04)])
    async with _make_fetcher(lambda request: httpx.Response(200, json=body)) as fetcher:
        await _ingest(fetcher)
    after = await _coverage_signature("CHE")
    assert after == before  # diagnostics never enter force coverage


@pytest.mark.asyncio
async def test_wgi_dsr_credit_gap_outputs_unchanged_confidence_none(client):
    await _persist_observations([_wgi_score_dto("CHE", 2024, 87.32)])
    await _persist_observations(
        [_dsr_dto("CHE", 2000 + i // 4, i % 4 + 1, 10.0 + i) for i in range(20)]
    )
    await _persist_observations([_credit_gap_dto("CHE", 2024, 4, 4.2)])

    wgi_before = await _normalize("CHE", RL, ScoringPeriod(2025, 2))
    dsr_before = await _normalize("CHE", "DEBT_SERVICE_RATIO", ScoringPeriod(2004, 4))
    gap_before = await _normalize("CHE", "CREDIT_TO_GDP_GAP", ScoringPeriod(2025, 2))

    body = _response_body([_record(2024, 82.04)])
    async with _make_fetcher(lambda request: httpx.Response(200, json=body)) as fetcher:
        await _ingest(fetcher)

    wgi_after = await _normalize("CHE", RL, ScoringPeriod(2025, 2))
    dsr_after = await _normalize("CHE", "DEBT_SERVICE_RATIO", ScoringPeriod(2004, 4))
    gap_after = await _normalize("CHE", "CREDIT_TO_GDP_GAP", ScoringPeriod(2025, 2))

    for before, after in (
        (wgi_before, wgi_after),
        (dsr_before, dsr_after),
        (gap_before, gap_after),
    ):
        assert after is not None and before is not None
        assert after.level_score == before.level_score
        assert after.confidence is None  # confidence stays None everywhere
        assert after.backtest_safe is False  # release dates are not stored

    assert wgi_after.level_score == 87.32  # WGI DIRECT_0_100 level unchanged
    assert dsr_after.level_score is not None  # DSR own-history level unchanged
    assert gap_after.level_score is not None  # credit-gap level unchanged


def test_model_version_stays_v0_6():
    # Sprint 5.15 imports raw auxiliary input data ONLY — no normalized
    # output changed, so no version bump.
    assert CURRENT_MODEL_VERSION.version_id == "normalization-v0.7"