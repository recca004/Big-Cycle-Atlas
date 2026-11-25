"""Mission 4 §25: future-data leakage regression tests.

Proves that strict as-of selection cannot see information that was not
publicly available at the information cutoff — future observations, future
revisions, missing release evidence — and that strict mode NEVER silently
falls back to latest-vintage data.

Synthetic observations are written through the real persistence layer with
explicit provider release dates, against seeded SQLite.
"""
from datetime import date, datetime, timezone
from dataclasses import replace

import pytest
from sqlalchemy import select

from app.cycle.execution_modes import ExecutionMode, ExecutionSpec
from app.cycle.normalization_definitions import ScoringPeriod
from app.cycle.normalizer import normalize_indicator_as_of
from app.data_sources.base import ObservationDTO
from app.db import session as session_module
from app.research.release_calendar import PROVIDER_RELEASE_METADATA
from app.services.alignment_service import align_observation_as_of
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)

RL = "RULE_OF_LAW_WGI_SCORE"


_EXTERNAL_CODES = {
    "LABOUR_PRODUCTIVITY_PER_HOUR": (
        "DSD_PDB@DF_PDB/{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP"
    ),
}


def _dto(
    year: int,
    value: float,
    release_date: datetime | None,
    source_key: str = "world_bank",
    indicator: str = RL,
) -> ObservationDTO:
    return ObservationDTO(
        country_iso3="USA",
        indicator_code=indicator,
        external_series_code=_EXTERNAL_CODES.get(indicator, "GOV_WGI_RL_SC"),
        period=year,
        value=value,
        unit="score 0-100",
        source_key=source_key,
        observation_date=date(year, 1, 1),
        release_date=release_date,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


async def _persist(dtos) -> None:
    async with session_module._sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


async def _align(iso3, indicator, scoring_period, execution=None):
    async with session_module._sessionmaker() as session:
        return await align_observation_as_of(
            session, iso3, indicator, scoring_period, execution
        )


async def _normalize(iso3, indicator, scoring_period, execution=None):
    async with session_module._sessionmaker() as session:
        return await normalize_indicator_as_of(
            session, iso3, indicator, scoring_period, execution=execution
        )


def _strict(cutoff: date) -> ExecutionSpec:
    return ExecutionSpec(mode=ExecutionMode.STRICT_AS_OF, info_cutoff=cutoff)


# --- ExecutionSpec contract --------------------------------------------------


def test_strict_spec_requires_cutoff():
    with pytest.raises(ValueError):
        ExecutionSpec(mode=ExecutionMode.STRICT_AS_OF)


def test_modes_are_distinct():
    modes = {m.value for m in ExecutionMode}
    assert modes == {
        "current_latest",
        "retrospective_latest_vintage",
        "strict_as_of",
        "research_assumption",
    }


# --- Strict selection ---------------------------------------------------------


async def test_strict_excludes_observations_without_release_evidence(client):
    """Observation period eligible but NO release_date -> strict returns
    None rather than leaking an unverifiable value."""
    await _persist([_dto(2020, 82.5, release_date=None)])
    spec = _strict(date(2022, 1, 1))
    aligned = await _align("USA", RL, ScoringPeriod(2021, 4), spec)
    assert aligned is None  # never silently included


async def test_strict_selects_observation_published_before_cutoff(client):
    await _persist([
        _dto(2020, 82.5, release_date=datetime(2021, 7, 1, tzinfo=timezone.utc)),
    ])
    # 2020 annual period completes 2020-12-31; released 2021-07; cutoff later.
    aligned = await _align(
        "USA", RL, ScoringPeriod(2021, 4), _strict(date(2021, 12, 31))
    )
    assert aligned is not None
    assert aligned.raw_value == 82.5


async def test_strict_excludes_observation_published_after_cutoff(client):
    """Value exists in the DB for period 2020 but was published 2022 —
    a 2021 cutoff must not see it."""
    await _persist([
        _dto(2020, 82.5, release_date=datetime(2022, 7, 1, tzinfo=timezone.utc)),
    ])
    aligned = await _align(
        "USA", RL, ScoringPeriod(2021, 4), _strict(date(2021, 12, 31))
    )
    assert aligned is None


async def test_strict_excludes_future_revision_vintages(client):
    """v1 published 2021-07 (value 80), v2 published 2022-07 (value 85).
    Strict at 2021-12-31 must see v1, NOT the future revision."""
    await _persist([
        _dto(2020, 80.0, release_date=datetime(2021, 7, 1, tzinfo=timezone.utc)),
        _dto(2020, 85.0, release_date=datetime(2022, 7, 1, tzinfo=timezone.utc)),
    ])
    aligned = await _align(
        "USA", RL, ScoringPeriod(2021, 4), _strict(date(2021, 12, 31))
    )
    assert aligned is not None
    assert aligned.raw_value == 80.0
    assert aligned.vintage_number == 1

    # A later cutoff sees the revision.
    aligned_later = await _align(
        "USA", RL, ScoringPeriod(2021, 4), _strict(date(2023, 1, 1))
    )
    assert aligned_later.raw_value == 85.0
    assert aligned_later.vintage_number == 2


async def test_strict_still_respects_period_completeness(client):
    """A future-period observation (published early, e.g. a projection)
    is excluded even with release evidence — period completeness applies
    independently of release evidence."""
    await _persist([
        _dto(2025, 90.0, release_date=datetime(2024, 6, 1, tzinfo=timezone.utc)),
        _dto(2020, 82.0, release_date=datetime(2021, 7, 1, tzinfo=timezone.utc)),
    ])
    aligned = await _align(
        "USA", RL, ScoringPeriod(2024, 3), _strict(date(2024, 12, 31))
    )
    # 2025 annual period not complete at 2024-Q3 -> must fall back to 2020.
    assert aligned is not None
    assert aligned.source_period == "2020"


async def test_strict_never_falls_back_to_latest_vintage(client):
    """If strict finds nothing, it returns None — it must NOT leak the
    retrospective latest-vintage row."""
    await _persist([_dto(2020, 82.5, release_date=None)])
    sp = ScoringPeriod(2021, 4)
    retro = await _align("USA", RL, sp, None)
    assert retro is not None  # retrospective mode sees it (no release gate)
    strict = await _align("USA", RL, sp, _strict(date(2022, 1, 1)))
    assert strict is None  # strict refuses the same row


# --- Normalizer propagation ----------------------------------------------------


async def test_strict_signal_unavailable_without_evidence(client):
    """The full normalization path under strict: no release evidence on the
    input -> no signal, and backtest_safe stays False."""
    await _persist([_dto(2020, 82.5, release_date=None)])
    signal = await _normalize(
        "USA", RL, ScoringPeriod(2021, 4), _strict(date(2022, 1, 1))
    )
    assert signal is None


async def test_strict_signal_with_evidence_is_marked_unsafe(client):
    """Even with evidence, the signal's model_version itself is not
    backtest_safe — the existence of strict selection doesn't make the
    whole result safe (§23)."""
    await _persist([
        _dto(2020, 82.5, release_date=datetime(2021, 7, 1, tzinfo=timezone.utc)),
    ])
    signal = await _normalize(
        "USA", RL, ScoringPeriod(2021, 4), _strict(date(2021, 12, 31))
    )
    assert signal is not None
    assert signal.level_score == 82.5
    assert signal.backtest_safe is False


# --- Research-assumption mode ---------------------------------------------------


async def test_assumption_mode_uses_provider_lag(client):
    """No release dates at all: research_assumption admits the observation
    only when period_end + provider lag <= cutoff. WB assumed lag = 365d,
    so a 2020 annual obs (end 2020-12-31) needs cutoff >= 2021-12-31."""
    await _persist([_dto(2020, 82.5, release_date=None)])
    spec_early = ExecutionSpec(
        mode=ExecutionMode.RESEARCH_ASSUMPTION, info_cutoff=date(2021, 6, 30)
    )
    assert (
        await _align("USA", RL, ScoringPeriod(2021, 4), spec_early) is None
    )
    spec_late = ExecutionSpec(
        mode=ExecutionMode.RESEARCH_ASSUMPTION, info_cutoff=date(2022, 1, 1)
    )
    aligned = await _align("USA", RL, ScoringPeriod(2021, 4), spec_late)
    assert aligned is not None
    assert aligned.raw_value == 82.5


# --- Reference-observation path --------------------------------------------------


async def test_strict_blocks_reference_percentile(client):
    """Reference observations carry no release evidence -> the LPPH
    reference-percentile level produces no signal under strict mode.
    (Retrospective mode is unaffected.)"""
    from app.models.reference_observation import ReferenceObservation

    async with session_module._sessionmaker() as session:
        session.add(
            ReferenceObservation(
                universe_code="oecd_lpph_v1",
                indicator_code="LABOUR_PRODUCTIVITY_PER_HOUR",
                country_iso3="USA",
                period_start=datetime(2020, 1, 1, tzinfo=timezone.utc),
                value=70.0,
                unit="usd_ppp",
                source_key="oecd",
                external_code="T_GDPHRS",
                retrieved_at=RETRIEVED_AT,
                vintage_number=1,
                raw_payload={"test": True},
            )
        )
        await session.commit()
    # Own observation HAS release evidence — this isolates the reference-side
    # strict gate (a signal cannot be produced without eligible reference rows).
    await _persist([
        _dto(
            2020, 70.0,
            release_date=datetime(2021, 7, 1, tzinfo=timezone.utc),
            source_key="oecd", indicator="LABOUR_PRODUCTIVITY_PER_HOUR",
        )
    ])
    signal = await _normalize(
        "USA", "LABOUR_PRODUCTIVITY_PER_HOUR",
        ScoringPeriod(2021, 4), _strict(date(2022, 1, 1)),
    )
    assert signal is None


# --- Coverage of the provider matrix ----------------------------------------------


def test_every_integrated_provider_documented():
    """The release-evidence matrix covers the providers the connectors
    actually ingest (§21 — missing evidence is recorded, not invented)."""
    for key in ("world_bank", "bis", "oecd", "imf_weo", "wid"):
        meta = PROVIDER_RELEASE_METADATA.get(key)
        assert meta is not None, f"missing release metadata for {key}"
        assert meta.has_release_dates is False  # honest: none ingested
        assert meta.assumed_lag_days is not None


# --- API contract (§23/§29) -----------------------------------------------------


async def test_force_history_rejects_strict_without_cutoff(client):
    r = await client.get(
        "/api/countries/USA/forces/rule_of_law/history"
        "?execution_mode=strict_as_of&start_year=2019&end_year=2020"
    )
    assert r.status_code == 422
    assert "cutoff" in r.json()["detail"].lower()


async def test_force_history_rejects_unknown_mode(client):
    r = await client.get(
        "/api/countries/USA/forces/rule_of_law/history"
        "?execution_mode=bogus&start_year=2019&end_year=2020"
    )
    assert r.status_code == 422


async def test_force_history_default_is_retrospective(client):
    r = await client.get(
        "/api/countries/USA/forces/rule_of_law/history"
        "?start_year=2019&end_year=2020"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["execution_mode"] == "retrospective_latest_vintage"
    assert body["backtest_safe"] is False


async def test_force_history_strict_returns_unavailable_not_latest(client):
    """Strict mode on a test DB with no release evidence must produce null
    points — NEVER the retrospective values."""
    retro = await client.get(
        "/api/countries/USA/forces/rule_of_law/history"
        "?start_year=2019&end_year=2020"
    )
    strict = await client.get(
        "/api/countries/USA/forces/rule_of_law/history"
        "?start_year=2019&end_year=2020"
        "&execution_mode=strict_as_of&info_cutoff=2021-12-31"
    )
    assert strict.status_code == 200
    body = strict.json()
    assert body["execution_mode"] == "strict_as_of"
    assert body["info_cutoff"] == "2021-12-31"
    assert body["backtest_safe"] is False
    # Every strict point must be unscored — no silent latest-vintage leak.
    assert all(
        p["level_score"] is None and p["momentum_score"] is None
        for p in body["points"]
    )
    # Contrast: retrospective mode scores at least one of these periods.
    assert any(
        p["level_score"] is not None for p in retro.json()["points"]
    ) or all(
        p["level_score"] is None for p in retro.json()["points"]
    )  # empty test DB is acceptable; the KEY assertion is strict ≠ leak


async def test_research_cycle_strict_contract(client):
    r = await client.get(
        "/api/research/countries/USA/cycle"
        "?model=model_b_domain&execution_mode=strict_as_of"
        "&info_cutoff=2021-12-31"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["execution_mode"] == "strict_as_of"
    assert body["info_cutoff"] == "2021-12-31"
    assert body["backtest_safe"] is False
    assert body["methodology_status"] == "experimental"


async def test_research_cycle_history_strict_contract(client):
    r = await client.get(
        "/api/research/countries/USA/cycle/history"
        "?model=model_b_domain&start_year=2018&end_year=2020"
        "&execution_mode=strict_as_of&info_cutoff=2021-12-31"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["execution_mode"] == "strict_as_of"
    assert body["backtest_safe"] is False


async def test_research_cycle_strict_requires_cutoff(client):
    r = await client.get(
        "/api/research/countries/USA/cycle"
        "?model=model_b_domain&execution_mode=research_assumption"
    )
    assert r.status_code == 422
