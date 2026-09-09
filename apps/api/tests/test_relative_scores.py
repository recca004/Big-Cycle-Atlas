"""Sprint 5.8 tests: CROSS_SECTIONAL_RELATIVE relative scores for the WGI x3
on the frozen tracked_8 universe (DEC-017).

Synthetic observations persisted via the real persistence layer against
seeded SQLite — no external calls, no live APIs. Nothing is persisted by the
normalizer itself; no force score, weight, or phase exists here. Relative
scores are positions within tracked_8 — NEVER a global/world percentile.
"""
import json
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.cycle.normalization_definitions import (
    CURRENT_MODEL_VERSION,
    NormalizationFamily,
    REFERENCE_UNIVERSES,
    TRACKED_8_MEMBERS,
    ReferenceUniverseSpec,
    ScoringPeriod,
    get_normalization_spec,
)
from app.cycle.normalizer import (
    NormalizationDataError,
    NormalizationNotImplementedError,
    normalize_indicator_as_of,
)
from app.cycle.relative import (
    build_relative_cross_section,
    mid_rank_relative_scores,
)
from app.data_sources.base import ObservationDTO
from app.db import session as session_module
from app.db.seed import DEFAULT_DATA_FILE
from app.models import Country, Observation
from app.services.observation_service import persist_observations

RETRIEVED_AT = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)

WGI_RL = "GOV_WGI_RL_SC"

TRACKED_8 = ("USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND")

SNAPSHOT = ScoringPeriod(2025, 2)

# Mid-rank plotting position for n=8 (DEC-017): rank -> relative score.
EXPECTED_SCORES_N8 = {
    1: 6.25,
    2: 18.75,
    3: 31.25,
    4: 43.75,
    5: 56.25,
    6: 68.75,
    7: 81.25,
    8: 93.75,
}


def _wgi_dto(iso3: str, year: int, value: float) -> ObservationDTO:
    return ObservationDTO(
        country_iso3=iso3,
        indicator_code="RULE_OF_LAW_WGI_SCORE",
        external_series_code=WGI_RL,
        period=year,
        value=value,
        unit="score 0-100",
        source_key="world_bank",
        observation_date=date(year, 1, 1),
        release_date=None,
        retrieved_at=RETRIEVED_AT,
        raw_payload={"test": True},
    )


async def _persist(dtos: list[ObservationDTO]) -> None:
    async with session_module._sessionmaker() as session:
        await persist_observations(session, dtos)
        await session.commit()


async def _persist_cross_section(year: int, values: dict[str, float]) -> None:
    await _persist([_wgi_dto(iso3, year, value) for iso3, value in values.items()])


async def _normalize(iso3: str, scoring_period: ScoringPeriod, indicator: str = "RULE_OF_LAW_WGI_SCORE", **kwargs):
    async with session_module._sessionmaker() as session:
        return await normalize_indicator_as_of(
            session, iso3, indicator, scoring_period, **kwargs
        )


async def _cross_section(scoring_period: ScoringPeriod, indicator: str = "RULE_OF_LAW_WGI_SCORE"):
    async with session_module._sessionmaker() as session:
        return await build_relative_cross_section(
            session,
            indicator,
            scoring_period,
            REFERENCE_UNIVERSES["tracked_8"],
        )


async def _observation_count() -> int:
    async with session_module._sessionmaker() as session:
        return (
            await session.execute(select(func.count()).select_from(Observation))
        ).scalar_one()


# --- 1. tracked_8: exactly 8 unique fixed members, cross-checked canonical ----


def test_tracked_8_contains_exactly_eight_unique_fixed_members():
    universe = REFERENCE_UNIVERSES["tracked_8"]
    assert universe.id == "tracked_8"
    assert len(universe.members) == 8
    assert len(set(universe.members)) == 8
    assert set(universe.members) == set(TRACKED_8)
    assert TRACKED_8_MEMBERS == TRACKED_8


def test_tracked_8_membership_cross_checked_against_canonical_country_list():
    payload = json.loads(DEFAULT_DATA_FILE.read_text(encoding="utf-8"))
    canonical = {row["iso3"] for row in payload["countries"]}
    assert set(REFERENCE_UNIVERSES["tracked_8"].members) == canonical


def test_universe_spec_validates_membership():
    ReferenceUniverseSpec(id="ok", members=("A", "B"))
    with pytest.raises(ValueError):  # duplicate members
        ReferenceUniverseSpec(id="dup", members=("A", "A"))
    with pytest.raises(ValueError):  # empty
        ReferenceUniverseSpec(id="empty", members=())


# --- 2. The universe is NOT derived from DB contents ---------------------------


async def test_universe_not_derived_from_db_extra_country_never_participates(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0  # strongest tracked_8 member
    await _persist_cross_section(2024, values)
    # A 9th country exists in the DB with an even higher value.
    async with session_module._sessionmaker() as session:
        session.add(Country(iso3="BRA", iso2="BR", name="Brazil", region="Americas"))
        await session.commit()
    await _persist([_wgi_dto("BRA", 2024, 95.0)])
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal is not None
    # tracked_8 stays 8 members; BRA neither joins the count nor shifts CHE.
    assert signal.reference_universe_expected_n == 8
    assert signal.reference_universe_usable_n == 8
    assert signal.relative_score == pytest.approx(93.75)  # still 8 of 8, not 8 of 9


async def test_universe_not_derived_from_which_countries_have_data(client):
    # Only 2 of 8 members have data: usable_n stays 2/8 (membership is frozen,
    # not "whoever currently has observations"), so nothing is scored.
    await _persist([_wgi_dto("CHE", 2024, 90.0), _wgi_dto("USA", 2024, 80.0)])
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal is not None
    assert signal.reference_universe_expected_n == 8
    assert signal.reference_universe_usable_n == 2
    assert signal.relative_score is None


# --- 3-5. Mid-rank plotting position: exact n=8 score table -------------------


def test_mid_rank_scores_n8_full_rank_table():
    values = {  # ascending: CHN weakest ... CHE strongest
        "CHN": 40.0, "IND": 45.0, "FRA": 55.0, "GBR": 60.0,
        "JPN": 65.0, "DEU": 70.0, "USA": 80.0, "CHE": 90.0,
    }
    ranked = mid_rank_relative_scores(values)
    for member, (_, score) in ranked.items():
        rank = int(ranked[member][0])
        assert score == pytest.approx(EXPECTED_SCORES_N8[rank]), member
    assert ranked["CHE"] == (pytest.approx(8.0), pytest.approx(93.75))
    assert ranked["CHN"] == (pytest.approx(1.0), pytest.approx(6.25))


async def test_highest_of_n8_scores_93_75(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal.relative_rank == pytest.approx(8.0)
    assert signal.relative_score == pytest.approx(93.75)


async def test_lowest_of_n8_scores_6_25(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 10.0
    await _persist_cross_section(2024, values)
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal.relative_rank == pytest.approx(1.0)
    assert signal.relative_score == pytest.approx(6.25)


async def test_intermediate_ranks_correct(client):
    values = {
        "CHN": 40.0, "IND": 45.0, "FRA": 55.0, "GBR": 60.0,
        "JPN": 65.0, "DEU": 70.0, "USA": 80.0, "CHE": 90.0,
    }
    await _persist_cross_section(2024, values)
    for member, expected_rank in [
        ("CHN", 1), ("IND", 2), ("FRA", 3), ("GBR", 4),
        ("JPN", 5), ("DEU", 6), ("USA", 7), ("CHE", 8),
    ]:
        signal = await _normalize(member, SNAPSHOT)
        assert signal is not None, member
        assert signal.relative_rank == pytest.approx(float(expected_rank)), member
        assert signal.relative_score == pytest.approx(EXPECTED_SCORES_N8[expected_rank]), member


# --- 6-7. Ties: average rank, deterministic and order-independent ---------------


def test_ties_use_average_rank():
    ranked = mid_rank_relative_scores({"A": 80.0, "B": 80.0, "C": 60.0, "D": 40.0})
    # Ascending: D(40) rank 1, C(60) rank 2, A and B (80) share ranks 3-4 ->
    # average rank 3.5 -> identical scores of 75.0 (100 * (3.5 - 0.5) / 4).
    assert ranked["A"] == ranked["B"]
    assert ranked["A"][0] == pytest.approx(3.5)
    assert ranked["A"][1] == pytest.approx(75.0)
    assert ranked["C"] == (pytest.approx(2.0), pytest.approx(37.5))
    assert ranked["D"] == (pytest.approx(1.0), pytest.approx(12.5))


def test_tie_result_independent_of_input_order():
    values = {"A": 80.0, "B": 80.0, "C": 60.0, "D": 40.0, "E": 80.0}
    reversed_values = {k: values[k] for k in reversed(list(values))}
    assert mid_rank_relative_scores(values) == mid_rank_relative_scores(reversed_values)
    # Three-way tie at the top of n=5: ranks (3+4+5)/3 = 4 -> 70.0 each.
    ranked = mid_rank_relative_scores(values)
    assert ranked["A"] == ranked["B"] == ranked["E"]
    assert ranked["A"][0] == pytest.approx(4.0)
    assert ranked["A"][1] == pytest.approx(70.0)


async def test_db_tied_members_receive_identical_scores(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    values["USA"] = 90.0  # tied strongest
    await _persist_cross_section(2024, values)
    che = await _normalize("CHE", SNAPSHOT)
    usa = await _normalize("USA", SNAPSHOT)
    # Ranks 7-8 average to 7.5 -> identical scores for both; never broken by
    # ISO code, row id, or query order.
    assert che.relative_rank == pytest.approx(7.5)
    assert usa.relative_rank == pytest.approx(7.5)
    assert che.relative_score == usa.relative_score
    assert che.relative_score == pytest.approx(87.5)


# --- 8. WGI direction: higher value ranks stronger ------------------------------


async def test_higher_wgi_value_ranks_stronger(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    values["CHN"] = 30.0
    await _persist_cross_section(2024, values)
    cross = await _cross_section(SNAPSHOT)
    assert cross.member_for("CHE").rank > cross.member_for("CHN").rank
    assert cross.member_for("CHE").relative_score > cross.member_for("CHN").relative_score


# --- 9. Same as-of snapshot for every member ------------------------------------


async def test_all_members_aligned_at_the_same_scoring_snapshot(client):
    # CHE's latest is 2024, USA's latest is only 2022 — each member is ranked
    # on its own latest period-complete value AT THE SAME 2025-Q2 snapshot
    # (never "latest overall", never another country's snapshot).
    values = {iso3: 50.0 for iso3 in TRACKED_8 if iso3 != "USA"}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    await _persist([_wgi_dto("USA", 2022, 40.0)])
    cross = await _cross_section(SNAPSHOT)
    assert cross.is_complete
    assert cross.member_for("CHE").source_period == "2024"
    assert cross.member_for("USA").source_period == "2022"  # its own latest complete
    for member in cross.members:
        assert int(member.source_period) <= 2024  # nobody sees past the snapshot


# --- 10-11. Historical leakage / period-completeness (DEC-015 inherited) --------


async def test_historical_future_observation_never_enters_the_cross_section(client):
    # All 8 members have 2022, 2023, AND 2024 observations; scoring 2023-Q2
    # means annual 2023 is NOT period-complete (DEC-015): every member must
    # be ranked on 2022 — the stored 2024 value must never leak in.
    values_2022 = {iso3: 50.0 + 5.0 * i for i, iso3 in enumerate(TRACKED_8)}
    await _persist_cross_section(2022, values_2022)
    await _persist_cross_section(2023, {iso3: 100.0 for iso3 in TRACKED_8})
    await _persist_cross_section(2024, {iso3: 0.0 for iso3 in TRACKED_8})
    cross = await _cross_section(ScoringPeriod(2023, 2))
    assert cross.is_complete
    assert all(member.source_period == "2022" for member in cross.members)
    # Ranks come from the 2022 values, not the future 2023/2024 rows.
    assert cross.member_for("CHE").value == pytest.approx(values_2022["CHE"])
    signal = await _normalize("CHE", ScoringPeriod(2023, 2))
    assert signal.source_period == "2022"


async def test_period_incomplete_annual_member_makes_universe_incomplete(client):
    # The seven other members have 2023 observations (period-complete at the
    # 2024-Q2 snapshot); DEU has ONLY a 2024 observation — the annual 2024
    # period is not complete at 2024-Q2, so DEU is unusable -> 7/8 -> nobody
    # is scored. An incomplete-year observation never enters the cross-section.
    values = {iso3: 50.0 for iso3 in TRACKED_8 if iso3 != "DEU"}
    values["CHE"] = 90.0
    await _persist_cross_section(2023, values)
    await _persist([_wgi_dto("DEU", 2024, 99.0)])
    signal = await _normalize("CHE", ScoringPeriod(2024, 2))
    assert signal is not None
    assert signal.source_period == "2023"
    assert signal.reference_universe_usable_n == 7
    assert signal.relative_score is None


# --- 12. Latest vintage respected per member ------------------------------------


async def test_latest_vintage_respected_per_member(client):
    values = {iso3: 72.0 for iso3 in TRACKED_8}
    values["CHE"] = 70.0
    await _persist_cross_section(2024, values)
    await _persist([_wgi_dto("CHE", 2024, 75.0)])  # revision -> vintage 2
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal.raw_value == 75.0  # vintage 2, not the superseded 70.0
    # With 75 CHE is the strongest (93.75); with the stale vintage 70 it
    # would have been the weakest (6.25) — the rank must follow vintage 2.
    assert signal.relative_score == pytest.approx(93.75)


# --- 13. USA/CHE country isolation (ISSUE-004) ----------------------------------


async def test_usa_che_isolation_in_relative_scores(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["USA"] = 90.0
    values["CHE"] = 87.32
    await _persist_cross_section(2024, values)
    usa = await _normalize("USA", SNAPSHOT)
    che = await _normalize("CHE", SNAPSHOT)
    # SourceSeries rows are shared across countries: each country is ranked
    # on ITS OWN value, never the other's.
    assert usa.raw_value == 90.0 and che.raw_value == 87.32
    assert usa.relative_score == pytest.approx(93.75)
    assert che.relative_score == pytest.approx(81.25)
    assert usa.relative_rank == pytest.approx(8.0)
    assert che.relative_rank == pytest.approx(7.0)


# --- 14/15/16. Complete-universe rule --------------------------------------------


async def test_all_eight_usable_produces_relative_score(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal is not None
    assert signal.relative_score is not None
    assert signal.reference_universe_usable_n == 8


async def test_seven_of_eight_usable_scores_none_for_everyone(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8 if iso3 != "IND"}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    signal = await _normalize("CHE", SNAPSHOT)
    # IND has no data: a 7/8 cross-section is NEVER silently scored as
    # tracked_8 — nobody receives a relative score.
    assert signal is not None
    assert signal.level_score == 90.0  # level still produced
    assert signal.relative_score is None
    assert signal.relative_rank is None
    assert signal.reference_universe_expected_n == 8
    assert signal.reference_universe_usable_n == 7


async def test_missing_member_never_becomes_zero(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8 if iso3 != "IND"}
    await _persist_cross_section(2024, values)
    before = await _observation_count()
    cross = await _cross_section(SNAPSHOT)
    assert not cross.is_complete
    assert cross.members == ()  # IND was not zero-filled into the cross-section
    assert await _observation_count() == before  # no synthetic rows created


# --- 17-19. Freshness: gate usability, never scale the score --------------------


async def test_freshness_unusable_member_makes_universe_incomplete(client):
    # DEU's only observation is 2015: 10+ years old at 2025-Q2 — beyond the
    # annual unusable threshold (5y) -> member unusable -> 7/8 -> no score.
    values = {iso3: 50.0 for iso3 in TRACKED_8 if iso3 != "DEU"}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    await _persist([_wgi_dto("DEU", 2015, 50.0)])
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal is not None
    assert signal.reference_universe_usable_n == 7
    assert signal.relative_score is None


async def test_stale_but_usable_member_may_participate(client):
    # IND's latest observation is 2022: 3.25 years old at 2025-Q2 — stale
    # (past the 1-year full-confidence window) but still usable (under 5y),
    # so it participates and the universe stays complete.
    values = {iso3: 50.0 for iso3 in TRACKED_8 if iso3 != "IND"}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    await _persist([_wgi_dto("IND", 2022, 50.0)])
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal.reference_universe_usable_n == 8
    assert signal.relative_score == pytest.approx(93.75)


async def test_relative_score_never_multiplied_by_freshness_factor(client):
    # Every member's observation is stale-but-usable (2022 data at 2025-Q2,
    # freshness < 1): the rank-based score is exactly the formula value,
    # never decayed.
    values = {iso3: 40.0 + 5.0 * i for i, iso3 in enumerate(TRACKED_8)}
    values["CHE"] = 90.0  # strongest member
    await _persist_cross_section(2022, values)
    cross = await _cross_section(SNAPSHOT)
    assert cross.is_complete
    che = cross.member_for("CHE")  # rank 8 of 8
    assert che.value == pytest.approx(90.0)
    assert che.relative_score == pytest.approx(93.75)
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal.freshness_factor < 1.0  # stale, but usable
    assert signal.relative_score == pytest.approx(93.75)
    assert signal.relative_score != pytest.approx(93.75 * signal.freshness_factor)


# --- 20. Out-of-range member is a data error -------------------------------------


async def test_out_of_range_member_raises_data_error_no_clamp(client):
    # USA's value is revised to 101 (out of the provider 0-100 range): the
    # cross-section is a DATA ERROR — never clamped, never treated as
    # missing, never ranked.
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    await _persist([_wgi_dto("USA", 2024, 101.0)])  # USA revision -> vintage 2
    with pytest.raises(NormalizationDataError):
        await _normalize("CHE", SNAPSHOT)


# --- 21-24. Dimension independence -----------------------------------------------


async def test_level_score_unchanged_by_relative_scoring(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 87.32
    await _persist_cross_section(2024, values)
    signal = await _normalize("CHE", SNAPSHOT)
    # level_score stays the provider's absolute scale — never re-ranked or
    # rescaled by the relative dimension.
    assert signal.level_score == 87.32
    assert signal.raw_value == signal.level_score
    assert signal.relative_score == pytest.approx(93.75)
    assert signal.relative_score != signal.level_score


async def test_momentum_unchanged_by_relative_scoring(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    await _persist([_wgi_dto("CHE", 2019, 80.0)])
    signal = await _normalize("CHE", SNAPSHOT)
    # Momentum is still the plain signed 5y raw-point change.
    assert signal.momentum == pytest.approx(10.0)
    assert signal.relative_score == pytest.approx(93.75)


async def test_relative_may_exist_when_momentum_is_none(client):
    # Early historical snapshot: all 8 members have 1996/1997 data (a complete
    # same-period cross-section), but there is no alignable 5y anchor ->
    # relative exists, momentum None. Neither dimension suppresses the other.
    values = {iso3: 40.0 + 5.0 * i for i, iso3 in enumerate(TRACKED_8)}
    values["CHE"] = 90.0  # strongest member
    await _persist_cross_section(1996, values)
    await _persist_cross_section(1997, values)
    signal = await _normalize("CHE", ScoringPeriod(1998, 2))
    assert signal is not None
    assert signal.momentum is None  # no 1993 history for the 5y anchor
    assert signal.momentum_window_years is None
    assert signal.relative_score == pytest.approx(93.75)


async def test_confidence_remains_none(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal.confidence is None  # composition unresolved (§17) — never faked


# --- 25-26. Provenance -----------------------------------------------------------


async def test_reference_universe_id_carried(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal.reference_universe_id == "tracked_8"


async def test_expected_and_usable_n_provenance_correct(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8 if iso3 != "JPN"}
    await _persist_cross_section(2024, values)
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal.reference_universe_id == "tracked_8"
    assert signal.reference_universe_expected_n == 8
    assert signal.reference_universe_usable_n == 7
    assert signal.relative_score is None


# --- 27. Non-WGI CROSS_SECTIONAL_RELATIVE stays unimplemented --------------------


async def test_non_wgi_cross_sectional_relative_stays_unimplemented(client):
    # These four say CROSS_SECTIONAL_RELATIVE in the registry, but their level
    # families are not executable/approved — the level gate raises and their
    # relative scoring must NOT silently enable.
    for indicator in (
        "GDP_GROWTH",
        "GROSS_CAPITAL_FORMATION_GDP",
        "GINI_INDEX",
        "LABOUR_PRODUCTIVITY_PER_HOUR",
    ):
        spec = get_normalization_spec(indicator)
        assert spec.relative_family is NormalizationFamily.cross_sectional_relative
        with pytest.raises(NormalizationNotImplementedError):
            await _normalize("CHE", SNAPSHOT, indicator=indicator)


# --- 28-31. Version, no writes, no force scores ----------------------------------


async def test_backtest_safe_false_and_model_version_v0_5(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    signal = await _normalize("CHE", SNAPSHOT)
    assert signal.backtest_safe is False
    assert signal.model_version == "normalization-v0.8"
    assert CURRENT_MODEL_VERSION.version_id == "normalization-v0.8"


async def test_relative_scoring_never_writes_or_mutates_the_db(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    before = await _observation_count()
    for iso3 in TRACKED_8:
        signal = await _normalize(iso3, SNAPSHOT)
        assert signal is not None
        assert signal.relative_score is not None
    assert await _observation_count() == before  # read-only, no synthetic rows


async def test_no_force_scores_weights_or_phases_on_the_signal(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    signal = await _normalize("CHE", SNAPSHOT)
    for forbidden in ("force_score", "force_weight", "weight", "phase", "weights"):
        assert not hasattr(signal, forbidden)

# --- 32-36. Sprint 5.9 hardening: the direct helper cannot be misused ------------


async def test_direct_helper_rejects_non_approved_relative_indicators(client):
    # Registry entries that say CROSS_SECTIONAL_RELATIVE but whose level
    # methodology is NOT approved (no DIRECT_0_100) must raise at the
    # helper's own execution gate — not silently rank them.
    for indicator in (
        "GINI_INDEX",
        "GDP_GROWTH",
        "GROSS_CAPITAL_FORMATION_GDP",
        "LABOUR_PRODUCTIVITY_PER_HOUR",
    ):
        async with session_module._sessionmaker() as session:
            with pytest.raises(NormalizationNotImplementedError):
                await build_relative_cross_section(
                    session,
                    indicator,
                    SNAPSHOT,
                    REFERENCE_UNIVERSES["tracked_8"],
                )


async def test_direct_helper_rejects_contextual_deferred_relative_family(client):
    async with session_module._sessionmaker() as session:
        with pytest.raises(NormalizationNotImplementedError):
            await build_relative_cross_section(
                session,
                "INFLATION_CPI",
                SNAPSHOT,
                REFERENCE_UNIVERSES["tracked_8"],
            )


async def test_direct_helper_wgi_output_unchanged(client):
    # Hardening is behavioral only: the WGI x3 path through the direct helper
    # must produce the same mid-rank table as before Sprint 5.9.
    values = {iso3: 40.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    values["CHN"] = 10.0
    await _persist_cross_section(2024, values)
    cross_section = await _cross_section(SNAPSHOT)
    assert cross_section.is_complete is True
    assert cross_section.usable_n == cross_section.expected_n == 8
    assert cross_section.member_for("CHE").relative_score == pytest.approx(93.75)
    assert cross_section.member_for("CHE").rank == 8
    assert cross_section.member_for("CHN").relative_score == pytest.approx(6.25)
    assert cross_section.member_for("CHN").rank == 1


async def test_direct_helper_complete_universe_rule_unchanged(client):
    # 7/8 usable -> no member scored, usable/expected provenance carried.
    values = {iso3: 50.0 for iso3 in TRACKED_8 if iso3 != "IND"}
    await _persist_cross_section(2024, values)
    cross_section = await _cross_section(SNAPSHOT)
    assert cross_section.is_complete is False
    assert cross_section.expected_n == 8
    assert cross_section.usable_n == 7
    assert cross_section.members == ()


async def test_direct_helper_never_writes_or_mutates_the_db(client):
    values = {iso3: 50.0 for iso3 in TRACKED_8}
    values["CHE"] = 90.0
    await _persist_cross_section(2024, values)
    before = await _observation_count()
    cross_section = await _cross_section(SNAPSHOT)
    assert cross_section.is_complete is True
    assert await _observation_count() == before  # read-only
