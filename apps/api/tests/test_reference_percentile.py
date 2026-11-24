"""Sprint 6.14 tests: REFERENCE_PERCENTILE level for LABOUR_PRODUCTIVITY_PER_HOUR
against the versioned OECD reference universe oecd_lpph_v1 (DEC-042 Option A).

Synthetic reference observations are written directly to the dedicated
reference_observations table; the tracked country's own observation goes
through the real persistence layer. No external calls.

Semantics under test:
- level = mid-rank percentile within the SAME-PERIOD universe distribution
- period-specific calibration: only same-year members count
- minimum-sample gate: thin distributions produce NO signal (never partial)
- the registry family alone never enables the path — the model-version
  config entry is the execution gate
- CHN/IND (non-OECD, no LPPH observations) get None, never a fabricated score
"""
from datetime import date, datetime, timezone

import pytest

from app.cycle.normalization_definitions import (
    CURRENT_MODEL_VERSION,
    NormalizationFamily,
    ScoringPeriod,
    get_normalization_spec,
)
from app.cycle.normalizer import (
    NormalizationNotImplementedError,
    normalize_indicator_as_of,
)
from app.cycle.reference_universes import (
    OECD_LPPH_V1,
    get_reference_universe,
    midrank_percentile,
)
from app.data_sources.base import ObservationDTO
from app.db import session as session_module
from app.models.reference_observation import ReferenceObservation
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
OECD_PROD = "DSD_PDB@DF_PDB/{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP"
LPPH = "LABOUR_PRODUCTIVITY_PER_HOUR"
SNAPSHOT = ScoringPeriod(2025, 4)


def _lpph_dto(iso3: str, year: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code=LPPH,
        external_series_code=OECD_PROD,
        period=year,
        value=value,
        unit="USD per hour, PPP",
        source_key="oecd",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


async def _persist(dtos) -> None:
    async with session_module._sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


async def _persist_reference(members: dict[str, float], year: int = 2024) -> None:
    """Write universe distribution rows for one period (vintage 1)."""
    async with session_module._sessionmaker() as session:
        for iso3, value in members.items():
            session.add(
                ReferenceObservation(
                    universe_code=OECD_LPPH_V1.universe_code,
                    indicator_code=LPPH,
                    country_iso3=iso3,
                    period_start=datetime(year, 1, 1, tzinfo=timezone.utc),
                    period_end=datetime(year, 12, 31, tzinfo=timezone.utc),
                    value=value,
                    unit="USD per hour, PPP",
                    source_key="oecd",
                    external_code=OECD_PROD,
                    retrieved_at=RETRIEVED_AT,
                    vintage_number=1,
                )
            )
        await session.commit()


async def _normalize(iso3: str, scoring_period: ScoringPeriod = SNAPSHOT, indicator: str = LPPH, **kwargs):
    async with session_module._sessionmaker() as session:
        return await normalize_indicator_as_of(
            session, iso3, indicator, scoring_period, **kwargs
        )


# A 25-member toy distribution: values 10, 20, ..., 250.
TOY_25 = {f"M{i:02d}": float(i * 10) for i in range(1, 26)}


# --- 1. midrank_percentile math -------------------------------------------------


def test_midrank_percentile_top_member():
    # 25 members, value 250 = max -> (24 + 0.5)/25 = 98.0
    assert midrank_percentile(250.0, list(TOY_25.values())) == 98.0


def test_midrank_percentile_bottom_member():
    assert midrank_percentile(10.0, list(TOY_25.values())) == 2.0


def test_midrank_percentile_ties_share_average_rank():
    dist = [50.0] * 10 + [90.0] * 10  # 20 members: 10 below, 10 tied at top
    assert midrank_percentile(90.0, dist) == 75.0
    assert midrank_percentile(50.0, dist) == 25.0


def test_midrank_percentile_rejects_empty():
    with pytest.raises(ValueError):
        midrank_percentile(1.0, [])


# --- 2. universe registry --------------------------------------------------------


def test_oecd_lpph_v1_universe_is_frozen_and_named():
    universe = get_reference_universe("oecd_lpph_v1")
    assert universe is OECD_LPPH_V1
    assert universe.indicator_code == LPPH
    assert len(universe.expected_member_iso3) == 38
    # Tracked non-members are correctly absent from the OECD universe.
    assert "CHN" not in universe.expected_member_iso3
    assert "IND" not in universe.expected_member_iso3
    assert "USA" in universe.expected_member_iso3


def test_model_version_carries_lpph_reference_config():
    config = CURRENT_MODEL_VERSION.reference_percentile_configs[LPPH]
    assert config.universe_code == "oecd_lpph_v1"
    assert config.minimum_sample_n > 0
    spec = get_normalization_spec(LPPH)
    assert spec.level_family is NormalizationFamily.reference_percentile


# --- 3. score computation --------------------------------------------------------


async def test_level_score_is_same_period_midrank_percentile(client):
    # USA = 250 -> top of the 25-member 2024 distribution -> 98.0
    await _persist([_lpph_dto("USA", 2024, 250.0)])
    await _persist_reference(TOY_25, year=2024)
    signal = await _normalize("USA")
    assert signal is not None
    assert signal.method is NormalizationFamily.reference_percentile
    assert signal.level_score == 98.0
    assert signal.reference_universe_id == "oecd_lpph_v1"
    assert signal.momentum is None
    assert signal.relative_score is None


async def test_period_specific_calibration_uses_only_same_year(client):
    # 2024 distribution has the member at 250; USA's own 2024 value is 10
    # -> bottom percentile, NOT ranked against the (ignored) 2023 universe.
    await _persist([_lpph_dto("USA", 2024, 10.0)])
    await _persist_reference(TOY_25, year=2024)
    await _persist_reference({f"X{i}": 500.0 for i in range(30)}, year=2023)
    signal = await _normalize("USA")
    assert signal.level_score == 2.0


async def test_min_sample_gate_produces_no_signal(client):
    await _persist([_lpph_dto("USA", 2024, 100.0)])
    # Only 10 members at 2024 — below the 20-member minimum.
    await _persist_reference({f"M{i:02d}": float(i * 10) for i in range(1, 11)}, year=2024)
    assert await _normalize("USA") is None


async def test_missing_period_distribution_produces_no_signal(client):
    await _persist([_lpph_dto("USA", 2024, 100.0)])
    # Universe data exists only for a DIFFERENT period.
    await _persist_reference(TOY_25, year=2020)
    assert await _normalize("USA") is None


async def test_no_own_observation_produces_no_signal(client):
    # CHN is not an OECD member: full universe present, but CHN has no LPPH
    # observation -> None, never a fabricated score.
    await _persist_reference(TOY_25, year=2024)
    assert await _normalize("CHN") is None


# --- 4. config gate ---------------------------------------------------------------


async def test_registry_family_alone_never_enables(client):
    # Strip the config entry on a copied model version -> must raise, not
    # silently score. The config entry is the execution gate.
    import dataclasses

    stripped = dataclasses.replace(
        CURRENT_MODEL_VERSION, reference_percentile_configs={}
    )
    await _persist([_lpph_dto("USA", 2024, 100.0)])
    await _persist_reference(TOY_25, year=2024)
    with pytest.raises(NormalizationNotImplementedError):
        await _normalize("USA", model_config=stripped)


# --- 5. Option C: percent-change own-history momentum (DEC-042) -------------------


async def _persist_lpph_history(iso3: str, values: dict[int, float]) -> None:
    await _persist([_lpph_dto(iso3, year, v) for year, v in values.items()])


async def test_pct_momentum_primary_window(client):
    # Current 2024 = 110; 5y anchor 2020 = 100 -> primary momentum +10.0%.
    await _persist_lpph_history("USA", {2020: 100.0, 2022: 104.0, 2015: 90.0, 2024: 110.0})
    await _persist_reference(TOY_25, year=2024)
    signal = await _normalize("USA")
    assert signal.momentum == pytest.approx(10.0)
    assert signal.momentum_window_years == 5
    units = {w.window_years: w.change_unit for w in signal.momentum_windows}
    assert set(units) == {3, 5, 10}
    assert set(units.values()) == {"percent"}
    # 3y window: 2024 vs 2021... anchor 2022=104 -> (110-104)/104 = +5.77%
    w3 = next(w for w in signal.momentum_windows if w.window_years == 3)
    assert w3.change == pytest.approx(100 * 6 / 104, rel=1e-6)


async def test_pct_momentum_missing_anchor_is_none_not_zero(client):
    # Only current obs — no 5y anchor -> momentum None, window provenance kept.
    await _persist_lpph_history("USA", {2024: 110.0})
    await _persist_reference(TOY_25, year=2024)
    signal = await _normalize("USA")
    assert signal.momentum is None
    w5 = next(w for w in signal.momentum_windows if w.window_years == 5)
    assert w5.change is None


async def test_pct_momentum_uses_raw_not_percentile(client):
    # Momentum must be computed from the raw USD-PPP values, never from the
    # level percentile — DEC-042: a percentile move is not productivity growth.
    await _persist_lpph_history("USA", {2020: 100.0, 2024: 50.0})
    await _persist_reference(TOY_25, year=2024)
    signal = await _normalize("USA")
    assert signal.momentum == pytest.approx(-50.0)


async def test_pct_momentum_gate(client):
    import dataclasses
    stripped = dataclasses.replace(
        CURRENT_MODEL_VERSION, pct_momentum_approved_indicators=frozenset()
    )
    await _persist_lpph_history("USA", {2020: 100.0, 2024: 110.0})
    await _persist_reference(TOY_25, year=2024)
    signal = await _normalize("USA", model_config=stripped)
    assert signal.level_score is not None  # level unaffected
    assert signal.momentum is None


# --- 6. RELATIVE_SHARE dimension: MILITARY_EXPENDITURE_USD (V1 Mission 1) ---------


MIL_USD = "MILITARY_EXPENDITURE_USD"
MIL_CODE = "MS.MIL.XPND.CD"
TRACKED_8 = ("USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND")


def _mil_dto(iso3: str, year: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code=MIL_USD,
        external_series_code=MIL_CODE,
        period=year,
        value=value,
        unit="current US$",
        source_key="world_bank",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


async def _persist_mil_cross_section(year: int, values: dict[str, float]) -> None:
    await _persist([_mil_dto(iso3, year, v) for iso3, v in values.items()])


MIL_8 = {"USA": 900.0, "CHN": 300.0, "IND": 80.0, "GBR": 70.0,
         "FRA": 60.0, "DEU": 60.0, "JPN": 50.0, "CHE": 10.0}


async def test_relative_share_is_share_of_universe_total(client):
    await _persist_mil_cross_section(2024, MIL_8)
    signal = await _normalize("USA", indicator=MIL_USD)
    assert signal is not None
    assert signal.method is NormalizationFamily.relative_share
    # 900 / 1530 * 100
    assert signal.relative_score == pytest.approx(100.0 * 900.0 / 1530.0)
    assert signal.level_score is None  # dimension-only: no defensible level
    assert signal.reference_universe_usable_n == 8


async def test_relative_share_incomplete_universe_no_score(client):
    # 7/8 members -> complete-universe rule: no share for anyone.
    missing = {k: v for k, v in MIL_8.items() if k != "CHE"}
    await _persist_mil_cross_section(2024, missing)
    assert await _normalize("USA", indicator=MIL_USD) is None


async def test_relative_share_gate(client):
    import dataclasses
    stripped = dataclasses.replace(
        CURRENT_MODEL_VERSION, relative_share_approved_indicators=frozenset()
    )
    await _persist_mil_cross_section(2024, MIL_8)
    with pytest.raises(NormalizationNotImplementedError):
        await _normalize("USA", indicator=MIL_USD, model_config=stripped)
