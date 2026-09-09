"""Sprint 5.14 tests: indicator diagnostics storage, persistence, lookup.

Auxiliary RAW provider diagnostics (DEC-022): immutable vintages, exact-
period lookup, country isolation, and catalog/coverage/normalization
isolation. Synthetic data via the real persistence layer against seeded
SQLite — no external calls, no live APIs. No confidence formula, no
NormalizedSignal change, no force score exists here.
"""
from datetime import date, datetime, timezone
from pathlib import Path
from typing import get_type_hints

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.cycle.normalization_definitions import CURRENT_MODEL_VERSION, NormalizedSignal, ScoringPeriod
from app.cycle.normalizer import normalize_indicator_as_of
from app.data_sources.base import ObservationDTO
from app.data_sources.wgi_diagnostic_specs import (
    WGI_DIAGNOSTIC_PROVIDER_SOURCE_CODE,
    WGI_DIAGNOSTIC_SPECS,
    get_wgi_diagnostic_specs,
    validate_wgi_diagnostic_specs,
)
from app.db import base as db_base
from app.db import session as session_module
from app.models import (
    Country,
    Indicator,
    IndicatorDiagnostic,
    IndicatorDiagnosticKind,
    Observation,
    SourceSeries,
)
from app.services.force_coverage_service import get_force_coverage
from app.services.indicator_diagnostic_service import (
    IndicatorDiagnosticAmbiguityError,
    IndicatorDiagnosticDTO,
    IndicatorDiagnosticLookupError,
    IndicatorDiagnosticPersistenceError,
    get_indicator_diagnostics_for_period,
    persist_indicator_diagnostics,
)
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)

RL = "RULE_OF_LAW_WGI_SCORE"
RL_SPECS = get_wgi_diagnostic_specs(RL)
ALL_KINDS = (
    IndicatorDiagnosticKind.ci_lower_bound,
    IndicatorDiagnosticKind.ci_upper_bound,
    IndicatorDiagnosticKind.source_count,
)


def _spec(kind: IndicatorDiagnosticKind, indicator: str = RL):
    matches = [s for s in get_wgi_diagnostic_specs(indicator) if s.diagnostic_kind is kind]
    assert len(matches) == 1
    return matches[0]


def _dto(
    iso3: str,
    kind: IndicatorDiagnosticKind,
    year: int,
    value: float,
    indicator: str = RL,
) -> IndicatorDiagnosticDTO:
    spec = _spec(kind, indicator)
    return IndicatorDiagnosticDTO(
        country_iso3=iso3,
        base_indicator_code=indicator,
        source_key=spec.source_key,
        provider_source_code=spec.provider_source_code,
        provider_series_code=spec.provider_series_code,
        diagnostic_kind=kind,
        period_start=date(year, 1, 1),
        value=value,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"date": str(year), "value": value},
    )


async def _persist_diagnostics(dtos) -> None:
    async with session_module._sessionmaker() as session:
        await persist_indicator_diagnostics(session, dtos, WGI_DIAGNOSTIC_SPECS)
        await session.commit()


async def _lookup(iso3: str, year: int, indicator: str = RL, specs=RL_SPECS):
    async with session_module._sessionmaker() as session:
        return await get_indicator_diagnostics_for_period(
            session, iso3, indicator, date(year, 1, 1), specs
        )


async def _count(model) -> int:
    async with session_module._sessionmaker() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar_one()


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
        retrieved_at=RETRIEVED_AT,
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
        retrieved_at=RETRIEVED_AT,
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
        retrieved_at=RETRIEVED_AT,
        raw_payload={"TIME_PERIOD": f"{year}-Q{quarter}", "OBS_VALUE": value},
    )


async def _persist_observations(dtos) -> None:
    async with session_module._sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


async def _normalize(iso3: str, indicator: str, scoring_period: ScoringPeriod):
    async with session_module._sessionmaker() as session:
        return await normalize_indicator_as_of(session, iso3, indicator, scoring_period)


def _coverage_signature(iso3: str):
    async def _run():
        async with session_module._sessionmaker() as session:
            country = (
                await session.execute(select(Country).where(Country.iso3 == iso3))
            ).scalar_one()
            rows = await get_force_coverage(session, country.id)
            return [(r.definition.code, r.status) for r in rows]
    return _run()


# --- 1-3. Model / migration table shape -----------------------------------------


def test_table_shape_no_source_series_fk_unique_identity():
    table = db_base.Base.metadata.tables["indicator_diagnostics"]
    columns = set(table.columns.keys())
    assert columns == {
        "id", "country_id", "indicator_id", "data_source_id", "diagnostic_kind",
        "provider_source_code", "provider_series_code", "period_start", "value",
        "retrieved_at", "vintage_number", "raw_payload", "created_at",
    }
    # Part 1/2: deliberately no series FK — diagnostics are not SourceSeries.
    assert "source_series_id" not in columns
    assert {fk.target_fullname for fk in table.foreign_keys} == {
        "countries.id", "indicators.id", "data_sources.id",
    }
    constraint_names = {c.name for c in table.constraints}
    assert "uq_indicator_diagnostics_identity" in constraint_names
    index_names = {i.name for i in table.indexes}
    assert "ix_indicator_diagnostics_lookup" in index_names


def test_migration_file_matches_model_contract():
    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    migration_files = list(versions_dir.glob("*_add_indicator_diagnostics.py"))
    assert len(migration_files) == 1
    text = migration_files[0].read_text(encoding="utf-8")
    for required in (
        "uq_indicator_diagnostics_identity",
        "ix_indicator_diagnostics_lookup",
        "down_revision",
        "38fff2cf97c9",  # chains onto the previous production head
    ):
        assert required in text
    assert "source_series_id" not in text


def test_exactly_three_diagnostic_kinds():
    assert {kind.value for kind in IndicatorDiagnosticKind} == {
        "ci_lower_bound", "ci_upper_bound", "source_count",
    }
    # SE (estimate-scale standard error) is deliberately NOT a kind (DEC-022).
    assert "standard_error" not in {kind.value for kind in IndicatorDiagnosticKind}


# --- WGI diagnostic spec registry --------------------------------------------------


def test_wgi_spec_registry_structure():
    validate_wgi_diagnostic_specs()  # raises on any violation
    assert len(WGI_DIAGNOSTIC_SPECS) == 9  # 3 indicators x 3 kinds
    assert len(get_wgi_diagnostic_specs(RL)) == 3
    for spec in WGI_DIAGNOSTIC_SPECS:
        assert spec.source_key == "world_bank"
        assert spec.provider_source_code == WGI_DIAGNOSTIC_PROVIDER_SOURCE_CODE == "3"
        # dedicated WGI source id 3, distinct from the WDI source 2 that
        # carries the score series
        assert spec.provider_series_code.startswith("GOV_WGI_")
        assert spec.provider_series_code.endswith((".SC_LB", ".SC_UB", ".SR"))


# --- 4-8. Persistence: insert / skip / revise / retain ------------------------------


async def test_new_diagnostic_inserts_vintage_1_on_base_canonical_indicator(client):
    before = await _count(Indicator)
    await _persist_diagnostics([_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 82.04)])
    after = await _count(Indicator)

    # Part 4 of the sprint: the BASE canonical indicator is REUSED — no new
    # indicator rows ("25 -> 34" pollution is structurally impossible here).
    assert after == before == 27
    async with session_module._sessionmaker() as session:
        rows = (await session.execute(select(IndicatorDiagnostic))).scalars().all()
        assert len(rows) == 1
        row = rows[0]
        assert row.vintage_number == 1
        assert row.value == 82.04
        assert row.provider_series_code == "GOV_WGI_RL.SC_LB"
        assert row.provider_source_code == "3"
        assert row.raw_payload["date"] == "2024"
        base = (await session.execute(select(Indicator).where(Indicator.code == RL))).scalar_one()
        assert row.indicator_id == base.id


async def test_identical_reingest_skips_no_new_rows(client):
    await _persist_diagnostics([_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 82.04)])
    async with session_module._sessionmaker() as session:
        result = await persist_indicator_diagnostics(
            session, [_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 82.04)],
            WGI_DIAGNOSTIC_SPECS,
        )
        await session.commit()
    assert (result.received, result.inserted, result.skipped, result.revised) == (1, 0, 1, 0)
    assert await _count(IndicatorDiagnostic) == 1


async def test_changed_value_creates_new_vintage_and_old_retained(client):
    await _persist_diagnostics([_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 82.04)])
    async with session_module._sessionmaker() as session:
        result = await persist_indicator_diagnostics(
            session, [_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 81.9)],
            WGI_DIAGNOSTIC_SPECS,
        )
        await session.commit()
    assert (result.inserted, result.skipped, result.revised) == (0, 0, 1)
    async with session_module._sessionmaker() as session:
        rows = (await session.execute(select(IndicatorDiagnostic))).scalars().all()
    assert len(rows) == 2  # old vintage retained, never overwritten
    assert {r.vintage_number for r in rows} == {1, 2}
    assert {r.value for r in rows} == {82.04, 81.9}
    assert all(r.raw_payload is not None for r in rows)


async def test_unknown_and_mismatched_identities_rejected(client):
    # Unknown base indicator -> rejected.
    async with session_module._sessionmaker() as session:
        unknown_indicator = _dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 1.0)
        unknown_indicator.base_indicator_code = "NOT_AN_INDICATOR"
        with pytest.raises(IndicatorDiagnosticPersistenceError):
            await persist_indicator_diagnostics(
                session, [unknown_indicator], WGI_DIAGNOSTIC_SPECS,
            )
    # Unknown country -> rejected.
    async with session_module._sessionmaker() as session:
        with pytest.raises(IndicatorDiagnosticPersistenceError):
            await persist_indicator_diagnostics(
                session,
                [IndicatorDiagnosticDTO(
                    country_iso3="XYZ", base_indicator_code=RL,
                    source_key="world_bank", provider_source_code="3",
                    provider_series_code="GOV_WGI_RL.SC_LB",
                    diagnostic_kind=IndicatorDiagnosticKind.ci_lower_bound,
                    period_start=date(2024, 1, 1), value=1.0,
                    retrieved_at=RETRIEVED_AT,
                )],
                WGI_DIAGNOSTIC_SPECS,
            )
    # Known (indicator, kind) but WRONG provider series code -> rejected.
    bad = _dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 1.0)
    bad.provider_series_code = "GOV_WGI_RL.SE"  # a real series, but not the spec's
    async with session_module._sessionmaker() as session:
        with pytest.raises(IndicatorDiagnosticPersistenceError):
            await persist_indicator_diagnostics(session, [bad], WGI_DIAGNOSTIC_SPECS)
    # No spec at all for this (indicator, kind) pair -> unknown identity.
    async with session_module._sessionmaker() as session:
        with pytest.raises(IndicatorDiagnosticPersistenceError):
            await persist_indicator_diagnostics(
                session, [_dto("CHE", IndicatorDiagnosticKind.source_count, 2024, 10)], [],
            )
    assert await _count(IndicatorDiagnostic) == 0


# --- 9. DB-enforced unique identity ------------------------------------------------


async def test_unique_constraint_blocks_duplicate_same_vintage(client):
    await _persist_diagnostics([_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 82.04)])
    async with session_module._sessionmaker() as session:
        country = (await session.execute(select(Country).where(Country.iso3 == "CHE"))).scalar_one()
        base = (await session.execute(select(Indicator).where(Indicator.code == RL))).scalar_one()
        source = (
            await session.execute(select(func.distinct(IndicatorDiagnostic.data_source_id)))
        ).scalar_one()
        session.add(
            IndicatorDiagnostic(
                country_id=country.id, indicator_id=base.id, data_source_id=source,
                diagnostic_kind=IndicatorDiagnosticKind.ci_lower_bound,
                provider_source_code="3", provider_series_code="GOV_WGI_RL.SC_LB",
                period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
                value=82.04, retrieved_at=RETRIEVED_AT, vintage_number=1,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


# --- 10-11. Country isolation + latest vintage --------------------------------------


async def test_country_isolation_usa_che_and_latest_vintage(client):
    # Same base indicator, kind, provider series, period — different countries.
    await _persist_diagnostics([
        _dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 82.04),
        _dto("USA", IndicatorDiagnosticKind.ci_lower_bound, 2024, 69.25),
    ])
    che = await _lookup("CHE", 2024)
    usa = await _lookup("USA", 2024)
    assert che[IndicatorDiagnosticKind.ci_lower_bound] == 82.04
    assert usa[IndicatorDiagnosticKind.ci_lower_bound] == 69.25

    # Revise CHE only -> latest vintage selected, USA untouched.
    await _persist_diagnostics([_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 80.0)])
    che = await _lookup("CHE", 2024)
    usa = await _lookup("USA", 2024)
    assert che[IndicatorDiagnosticKind.ci_lower_bound] == 80.0  # vintage 2
    assert usa[IndicatorDiagnosticKind.ci_lower_bound] == 69.25

    # A country with NO diagnostics gets missing -> None, never the other's.
    deu = await _lookup("DEU", 2024)
    assert deu[IndicatorDiagnosticKind.ci_lower_bound] is None


# --- 12-14. Exact-period lookup: no fallback, no future leakage ---------------------


async def test_exact_period_lookup_only(client):
    await _persist_diagnostics([_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2023, 81.0)])
    hit = await _lookup("CHE", 2023)
    assert hit[IndicatorDiagnosticKind.ci_lower_bound] == 81.0

    # No prior-year fallback: 2023 score year with only 2022 diagnostics.
    await _persist_diagnostics([_dto("CHE", IndicatorDiagnosticKind.ci_upper_bound, 2022, 90.0)])
    miss = await _lookup("CHE", 2023)
    assert miss[IndicatorDiagnosticKind.ci_upper_bound] is None

    # No future-year borrowing either: 2022 lookup must not see 2023 rows.
    future = await _lookup("CHE", 2022)
    assert future[IndicatorDiagnosticKind.ci_lower_bound] is None


# --- 15. Expected provider-series identity enforced --------------------------------


async def test_lookup_raises_on_unexpected_provider_series(client):
    await _persist_diagnostics([_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 82.04)])
    # A rogue row under a DIFFERENT provider series for the same logical
    # identity (inserted directly; the persistence path would reject it).
    async with session_module._sessionmaker() as session:
        country = (await session.execute(select(Country).where(Country.iso3 == "CHE"))).scalar_one()
        base = (await session.execute(select(Indicator).where(Indicator.code == RL))).scalar_one()
        source = (
            await session.execute(select(func.distinct(IndicatorDiagnostic.data_source_id)))
        ).scalar_one()
        session.add(
            IndicatorDiagnostic(
                country_id=country.id, indicator_id=base.id, data_source_id=source,
                diagnostic_kind=IndicatorDiagnosticKind.ci_lower_bound,
                provider_source_code="3", provider_series_code="GOV_WGI_RL.SC_UB",
                period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
                value=92.6, retrieved_at=RETRIEVED_AT, vintage_number=1,
            )
        )
        await session.commit()

    with pytest.raises(IndicatorDiagnosticAmbiguityError):
        await _lookup("CHE", 2024)


async def test_lookup_with_replaced_expected_spec_finds_nothing(client):
    from dataclasses import replace

    await _persist_diagnostics([_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 82.04)])
    wrong_series = [replace(_spec(IndicatorDiagnosticKind.ci_lower_bound), provider_series_code="GOV_WGI_CC.SC_LB")]
    result = await _lookup("CHE", 2024, specs=wrong_series)
    # Tied to the EXPECTED identity: it does not silently accept whichever
    # series happens to exist.
    assert result[IndicatorDiagnosticKind.ci_lower_bound] is None


# --- 16. Missingness -----------------------------------------------------------------


async def test_missing_diagnostic_is_none_and_score_stays_usable(client):
    await _persist_diagnostics([_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 82.04)])
    result = await _lookup("CHE", 2024)
    assert result[IndicatorDiagnosticKind.ci_lower_bound] == 82.04
    assert result[IndicatorDiagnosticKind.ci_upper_bound] is None  # missing != 0
    assert result[IndicatorDiagnosticKind.source_count] is None

    # A base Observation remains fully usable when diagnostics are absent.
    await _persist_observations([_wgi_score_dto("CHE", 2024, 87.32)])
    signal = await _normalize("CHE", RL, ScoringPeriod(2025, 2))
    assert signal is not None
    assert signal.level_score == 87.32


# --- 17-18. Value validation ---------------------------------------------------------


async def test_source_count_must_be_nonnegative_integer(client):
    async with session_module._sessionmaker() as session:
        with pytest.raises(IndicatorDiagnosticPersistenceError):
            await persist_indicator_diagnostics(
                session, [_dto("CHE", IndicatorDiagnosticKind.source_count, 2024, 9.7)],
                WGI_DIAGNOSTIC_SPECS,
            )
        with pytest.raises(IndicatorDiagnosticPersistenceError):
            await persist_indicator_diagnostics(
                session, [_dto("CHE", IndicatorDiagnosticKind.source_count, 2024, -1.0)],
                WGI_DIAGNOSTIC_SPECS,
            )
        await session.rollback()

    # 10.0 IS an integer-valued count — accepted, no rounding involved.
    await _persist_diagnostics([_dto("CHE", IndicatorDiagnosticKind.source_count, 2024, 10.0)])
    result = await _lookup("CHE", 2024)
    assert result[IndicatorDiagnosticKind.source_count] == 10.0


async def test_nonfinite_values_rejected(client):
    for bad_value in (float("inf"), float("-inf"), float("nan")):
        async with session_module._sessionmaker() as session:
            with pytest.raises(IndicatorDiagnosticPersistenceError):
                await persist_indicator_diagnostics(
                    session,
                    [_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, bad_value)],
                    WGI_DIAGNOSTIC_SPECS,
                )
            await session.rollback()
    assert await _count(IndicatorDiagnostic) == 0


async def test_lookup_rejects_unknown_identities(client):
    async with session_module._sessionmaker() as session:
        with pytest.raises(IndicatorDiagnosticLookupError):
            await get_indicator_diagnostics_for_period(
                session, "XYZ", RL, date(2024, 1, 1), RL_SPECS
            )
        with pytest.raises(IndicatorDiagnosticLookupError):
            await get_indicator_diagnostics_for_period(
                session, "CHE", "NOT_AN_INDICATOR", date(2024, 1, 1), RL_SPECS
            )


# --- 19-23. Catalog / coverage isolation ---------------------------------------------


async def test_diagnostics_never_become_observations_or_series(client):
    await _persist_observations([_wgi_score_dto("CHE", 2024, 87.32)])
    obs_before = await _count(Observation)
    series_before = await _count(SourceSeries)
    indicators_before = await _count(Indicator)

    await _persist_diagnostics([
        _dto("CHE", kind, 2024, value)
        for kind, value in (
            (IndicatorDiagnosticKind.ci_lower_bound, 82.04),
            (IndicatorDiagnosticKind.ci_upper_bound, 92.6),
            (IndicatorDiagnosticKind.source_count, 10.0),
        )
    ])

    assert await _count(Observation) == obs_before  # no Observation rows created
    assert await _count(SourceSeries) == series_before  # no diagnostic SourceSeries
    assert await _count(Indicator) == indicators_before == 27


async def test_api_catalog_and_indicator_count_unchanged(client):
    indicators_before = (await client.get("/api/indicators/")).json()
    countries_before = (await client.get("/api/countries")).json()

    await _persist_diagnostics([_dto("CHE", IndicatorDiagnosticKind.ci_lower_bound, 2024, 82.04)])

    assert (await client.get("/api/indicators/")).json() == indicators_before
    assert (await client.get("/api/countries")).json() == countries_before
    # The catalog still reports exactly the 25 canonical indicators.
    assert len(indicators_before) == 27


async def test_force_coverage_unchanged(client):
    before = await _coverage_signature("CHE")
    await _persist_diagnostics([
        _dto("CHE", kind, 2024, value)
        for kind, value in (
            (IndicatorDiagnosticKind.ci_lower_bound, 82.04),
            (IndicatorDiagnosticKind.ci_upper_bound, 92.6),
            (IndicatorDiagnosticKind.source_count, 10.0),
        )
    ])
    after = await _coverage_signature("CHE")
    assert after == before  # diagnostics never enter force coverage statuses


# --- 24-29. Normalization outputs unchanged; confidence None; version ----------------


async def test_wgi_dsr_credit_gap_outputs_unchanged_and_confidence_none(client):
    await _persist_observations([_wgi_score_dto("CHE", 2024, 87.32)])
    # 20 consecutive quarters 2000-Q1 .. 2004-Q4 (ascending DSR history).
    await _persist_observations(
        [_dsr_dto("CHE", 2000 + i // 4, i % 4 + 1, 10.0 + i) for i in range(20)]
    )
    await _persist_observations([_credit_gap_dto("CHE", 2024, 4, 4.2)])

    wgi_before = await _normalize("CHE", RL, ScoringPeriod(2025, 2))
    dsr_before = await _normalize("CHE", "DEBT_SERVICE_RATIO", ScoringPeriod(2004, 4))
    gap_before = await _normalize("CHE", "CREDIT_TO_GDP_GAP", ScoringPeriod(2025, 2))

    await _persist_diagnostics([
        _dto("CHE", kind, 2024, value)
        for kind, value in (
            (IndicatorDiagnosticKind.ci_lower_bound, 82.04),
            (IndicatorDiagnosticKind.ci_upper_bound, 92.6),
            (IndicatorDiagnosticKind.source_count, 10.0),
        )
    ])

    wgi_after = await _normalize("CHE", RL, ScoringPeriod(2025, 2))
    dsr_after = await _normalize("CHE", "DEBT_SERVICE_RATIO", ScoringPeriod(2004, 4))
    gap_after = await _normalize("CHE", "CREDIT_TO_GDP_GAP", ScoringPeriod(2025, 2))

    for before, after in ((wgi_before, wgi_after), (dsr_before, dsr_after), (gap_before, gap_after)):
        assert after is not None and before is not None
        assert after.level_score == before.level_score
        assert after.confidence is None  # confidence stays None everywhere
        assert after.backtest_safe is False

    assert wgi_after.level_score == 87.32  # DIRECT_0_100 identity untouched
    assert dsr_after.level_score is not None  # DSR own-history level computed
    assert gap_after.level_score is not None  # credit-gap one-sided level computed


def test_model_version_unchanged_and_no_force_fields():
    # Sprint 5.14 changes raw auxiliary-data capability ONLY.
    assert CURRENT_MODEL_VERSION.version_id == "normalization-v0.8"
    signal_fields = set(get_type_hints(NormalizedSignal))
    for forbidden in ("force_score", "weight", "phase", "stage", "measurement_uncertainty"):
        assert forbidden not in signal_fields
    diagnostic_fields = set(get_type_hints(IndicatorDiagnostic))
    for forbidden in ("force_score", "weight", "confidence", "level_score"):
        assert forbidden not in diagnostic_fields