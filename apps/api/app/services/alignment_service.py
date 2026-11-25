"""As-of alignment — Sprint 5.6 (executable part of NORMALIZATION.md §3),
with period-complete eligibility (Part 0 hardening, DEC-015).

Given (country, indicator, scoring period), select the most recent
LATEST-VINTAGE observation whose OWN economic period has fully ENDED by the
scoring snapshot's quarter-end date, and wrap it in an AlignedValue with
provenance.

Semantics (NORMALIZATION.md §2/§3):

- Quarter-end as-of dates: 2025-Q2 snapshot -> as_of_date 2025-06-30.
- Period-completeness (Part 0): an observation is eligible only when its
  derived effective_period_end is at or before the snapshot date — an
  annual 2020 observation represents a period that is not complete until
  2020-12-31, so it must NOT be eligible at the 2020-Q1/Q2/Q3 snapshots
  even though its period_start (2020-01-01) precedes them. effective_period_end
  is computed in this DERIVED layer only (annual/irregular -> YYYY-12-31;
  quarterly -> quarter end); raw observations are never modified and no
  synthetic period-end dates are persisted.
- This is CURRENT/RESEARCH alignment based on observation periods. It is NOT
  release-date-safe alignment: every consumer must keep backtest_safe = False
  until Milestone 9 (release-date discipline). Period-completeness fixes
  period-in-progress leakage ONLY — it provides no historical release-date
  safety.
- Alignment SELECTS the latest prior observation; it never writes,
  forward-fills, or interpolates. Raw observations remain sparse — no
  synthetic rows are ever created (MISSING != ZERO).
- Every query is scoped by country AND indicator/source series at every
  layer (ISSUE-004): SourceSeries rows are shared across countries, so
  scoping only the subquery would leak rows.
"""
import re
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cycle.execution_modes import ExecutionMode, ExecutionSpec
from app.cycle.normalization_definitions import (
    AlignedValue,
    FreshnessClass,
    ScoringPeriod,
    get_normalization_spec,
)
from app.models import Country, DataSource, Indicator, Observation
from app.research.release_calendar import PROVIDER_RELEASE_METADATA

_QUARTER_END_MONTH_DAY = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}

_SCORING_PERIOD_RE = re.compile(r"^(\d{4})-Q([1-4])$")


class AlignmentError(Exception):
    """Alignment could not be performed (unknown country/indicator, bad period)."""


def parse_scoring_period(label: str) -> ScoringPeriod:
    """Parse a scoring-period label such as "2025-Q2" (inverse of ScoringPeriod.label)."""
    match = _SCORING_PERIOD_RE.match(label.strip())
    if match is None:
        raise AlignmentError(
            f"invalid scoring period {label!r} — expected 'YYYY-Qn' (e.g. '2025-Q2')"
        )
    return ScoringPeriod(year=int(match.group(1)), quarter=int(match.group(2)))


def quarter_end_date(scoring_period: ScoringPeriod) -> date:
    """The unambiguous as-of date of a scoring snapshot: its quarter's end day.

    2025-Q1 -> 2025-03-31, Q2 -> 06-30, Q3 -> 09-30, Q4 -> 12-31.
    """
    month, day = _QUARTER_END_MONTH_DAY[scoring_period.quarter]
    return date(scoring_period.year, month, day)


def shift_scoring_period_years(
    scoring_period: ScoringPeriod, years: int
) -> ScoringPeriod:
    """The scoring period `years` earlier, same quarter (Sprint 5.7 anchors).

    2025-Q2 minus 5y -> 2020-Q2; 2025-Q4 minus 3y -> 2022-Q4. Pure quarterly-
    clock arithmetic — the quarter never changes and no date math is done.
    Raises ValueError for negative years or a shift before the plausible-year
    floor (ScoringPeriod validates).
    """
    if years < 0:
        raise ValueError(f"years must be >= 0, got {years}")
    return ScoringPeriod(scoring_period.year - years, scoring_period.quarter)


def _quarter_index(d: date) -> int:
    return d.year * 4 + (d.month - 1) // 3


def effective_period_end(period_start: date, freshness_class: FreshnessClass) -> date:
    """The last day of the raw observation's OWN economic period.

    Derived only — never persisted, and raw observations are never modified:

    - annual/irregular YYYY -> YYYY-12-31 (irregular survey years such as
      Gini are year-dated, so the year end is the deterministic bound);
    - quarterly YYYY-Qn -> the quarter's end day (Q1 -> 03-31, Q2 -> 06-30,
      Q3 -> 09-30, Q4 -> 12-31; period_start is always a quarter-start date).
    """
    if freshness_class is FreshnessClass.quarterly:
        quarter = (period_start.month - 1) // 3 + 1
        month, day = _QUARTER_END_MONTH_DAY[quarter]
        return date(period_start.year, month, day)
    return date(period_start.year, 12, 31)


def _effective_end_index(freshness_class: FreshnessClass):
    """SQL expression: quarter index of the observation's effective period end."""
    obs_year = extract("year", Observation.period_start)
    if freshness_class is FreshnessClass.quarterly:
        obs_quarter = (extract("month", Observation.period_start) - 1) / 3
        return obs_year * 4 + obs_quarter
    # Annual and irregular periods are complete only at year end.
    return obs_year * 4 + 3


def _period_complete_condition(
    freshness_class: FreshnessClass, scoring_period: ScoringPeriod
):
    """SQL form of the eligibility rule effective_period_end <= snapshot end.

    Both sides are 0-based quarter indices on the scoring clock (2025-Q2 ->
    2025*4 + 1): the observation's effective-period-end index must not exceed
    the snapshot's index. Index arithmetic keeps this identical on SQLite
    (tests) and PostgreSQL (live) — no driver-specific date arithmetic.
    """
    effective_end_index = _effective_end_index(freshness_class)
    scoring_index = scoring_period.year * 4 + (scoring_period.quarter - 1)
    return effective_end_index <= scoring_index


_QUARTER_END_MD = {(3, 31), (6, 30), (9, 30), (12, 31)}


def _conservative_end_index(cutoff: date) -> int:
    """Largest effective-end quarter index eligible at `cutoff`.

    An observation's effective period end is always a quarter END, so it is
    <= cutoff iff its index < index(cutoff), or == index(cutoff) when cutoff
    is itself a quarter-end day. Expressing that as `<= conservative_index`
    keeps the comparison exact and portable across SQLite/PostgreSQL.
    """
    idx = cutoff.year * 4 + (cutoff.month - 1) // 3
    return idx if (cutoff.month, cutoff.day) in _QUARTER_END_MD else idx - 1


def _release_availability_conditions(
    execution: ExecutionSpec, freshness_class: FreshnessClass
):
    """SQL availability constraint for strict / assumption modes.

    Returns a list whose elements are AND-ed into both the vintage subquery
    and the outer query, plus whether a DataSource join is needed.

    STRICT_AS_OF: provider release evidence is mandatory — release_date IS
    NOT NULL and <= cutoff. Rows lacking evidence are ineligible, and
    revisions released after the cutoff never satisfy the vintage max.

    RESEARCH_ASSUMPTION: effective_period_end + assumed provider lag <=
    cutoff, where the lag is the provider's documented estimate — a
    research assumption, never evidence.
    """
    if execution.mode is ExecutionMode.STRICT_AS_OF:
        cutoff_dt = datetime.combine(
            execution.info_cutoff, time(23, 59, 59), tzinfo=timezone.utc
        )
        return [
            Observation.release_date.isnot(None),
            Observation.release_date <= cutoff_dt,
        ], False

    if execution.mode is ExecutionMode.RESEARCH_ASSUMPTION:
        effective_end_index = _effective_end_index(freshness_class)
        per_source = []
        for key, meta in PROVIDER_RELEASE_METADATA.items():
            if meta.assumed_lag_days is None:
                continue
            effective_cutoff = execution.info_cutoff - timedelta(
                days=meta.assumed_lag_days
            )
            cidx = _conservative_end_index(effective_cutoff)
            per_source.append(
                and_(DataSource.key == key, effective_end_index <= cidx)
            )
        if not per_source:
            return [False], False
        return [or_(*per_source)], True

    return [], False


def _source_period_label(period_start: date, freshness_class: FreshnessClass) -> str:
    """Human-readable label of the raw observation's own period.

    annual/irregular -> "2024"; quarterly -> "2025-Q2" (quarter-start dates).
    Irregular series (Gini) are survey-year dated, so the year is the label.
    """
    if freshness_class is FreshnessClass.quarterly and period_start.month in (1, 4, 7, 10):
        quarter = (period_start.month - 1) // 3 + 1
        return f"{period_start.year}-Q{quarter}"
    return f"{period_start.year}"


async def _select_observation_as_of(
    session: AsyncSession,
    country: Country,
    indicator: Indicator,
    spec,
    scoring_period: ScoringPeriod,
    execution: ExecutionSpec | None = None,
) -> Observation | None:
    """Shared observation-selection primitive (Sprint 6.11, DEC-038).

    Selects the latest latest-vintage observation whose own economic period
    is COMPLETE by the scoring snapshot's quarter-end date. ONE authoritative
    selection algorithm — used by both the normal AlignedValue path and the
    derived-component provenance path. No duplicate selection logic, no
    second as-of algorithm.

    Returns the raw Observation ORM object (with id, source_series_id,
    data_source_id, vintage_number, period_start, value) or None when no
    eligible observation exists. The caller builds AlignedValue and/or
    DerivedComponentProvenance from the result.

    Country scoping (ISSUE-004) applies at every layer — SourceSeries rows
    are shared across countries.
    """
    as_of_dt = datetime.combine(
        quarter_end_date(scoring_period), time(23, 59, 59), tzinfo=timezone.utc
    )
    period_complete = _period_complete_condition(spec.freshness_class, scoring_period)

    availability: list = []
    needs_source_join = False
    if execution is not None:
        availability, needs_source_join = _release_availability_conditions(
            execution, spec.freshness_class
        )

    latest_vintage_q = (
        select(
            Observation.source_series_id,
            Observation.period_start,
            func.max(Observation.vintage_number).label("max_vintage"),
        )
        .where(
            Observation.country_id == country.id,
            Observation.indicator_id == indicator.id,
            Observation.period_start <= as_of_dt,
            period_complete,
            *availability,
        )
        .group_by(Observation.source_series_id, Observation.period_start)
    )
    if needs_source_join:
        latest_vintage_q = latest_vintage_q.join(
            DataSource, Observation.data_source_id == DataSource.id
        )
    latest_vintage = latest_vintage_q.subquery()

    outer = (
        select(Observation)
        .join(
            latest_vintage,
            (Observation.source_series_id == latest_vintage.c.source_series_id)
            & (Observation.period_start == latest_vintage.c.period_start)
            & (Observation.vintage_number == latest_vintage.c.max_vintage),
        )
        .where(
            Observation.country_id == country.id,
            Observation.indicator_id == indicator.id,
            Observation.period_start <= as_of_dt,
            period_complete,
            *availability,
        )
        .order_by(
            Observation.period_start.desc(),
            Observation.vintage_number.desc(),
            Observation.id.desc(),
        )
        .limit(1)
    )
    if needs_source_join:
        outer = outer.join(
            DataSource, Observation.data_source_id == DataSource.id
        )

    observation = (await session.execute(outer)).scalar_one_or_none()

    return observation


def _build_aligned_value(
    observation: Observation,
    indicator_code: str,
    country_iso3: str,
    scoring_period: ScoringPeriod,
    spec,
) -> AlignedValue:
    """Build an AlignedValue from a selected Observation (shared helper)."""
    source_date = observation.period_start.date()
    age_quarters = _quarter_index(quarter_end_date(scoring_period)) - _quarter_index(source_date)
    return AlignedValue(
        indicator_code=indicator_code,
        country_iso3=country_iso3,
        scoring_period=scoring_period,
        source_period=_source_period_label(source_date, spec.freshness_class),
        raw_value=observation.value,
        age_periods=age_quarters,
        effective_period_end=effective_period_end(source_date, spec.freshness_class),
        vintage_number=observation.vintage_number,
    )


async def _resolve_country_indicator(
    session: AsyncSession,
    country_iso3: str,
    indicator_code: str,
):
    """Resolve Country and Indicator ORM objects, raising AlignmentError."""
    country = (
        await session.execute(select(Country).where(Country.iso3 == country_iso3))
    ).scalar_one_or_none()
    if country is None:
        raise AlignmentError(f"unknown country iso3: {country_iso3!r}")

    indicator = (
        await session.execute(select(Indicator).where(Indicator.code == indicator_code))
    ).scalar_one_or_none()
    if indicator is None:
        raise AlignmentError(f"unknown indicator code: {indicator_code!r}")

    return country, indicator


async def align_observation_as_of(
    session: AsyncSession,
    country_iso3: str,
    indicator_code: str,
    scoring_period: ScoringPeriod,
    execution: ExecutionSpec | None = None,
) -> AlignedValue | None:
    """Latest latest-vintage observation whose period is COMPLETE by the snapshot.

    Eligibility is period-completeness (Part 0): the observation's derived
    effective_period_end must be at or before the scoring period's quarter
    end — an annual 2020 observation first becomes eligible at the 2020-Q4
    snapshot, a 2025-Q2 observation at the 2025-Q2 snapshot.

    Returns None when no eligible observation exists (e.g. scoring before the
    first observation) — the caller produces NO signal, never a zero.

    Country scoping (ISSUE-004) applies to the country lookup, the
    latest-vintage subquery, AND the outer query — SourceSeries rows are
    shared across countries.
    """
    country, indicator = await _resolve_country_indicator(
        session, country_iso3, indicator_code
    )
    spec = get_normalization_spec(indicator_code)

    observation = await _select_observation_as_of(
        session, country, indicator, spec, scoring_period, execution
    )
    if observation is None:
        return None

    return _build_aligned_value(
        observation, indicator_code, country_iso3, scoring_period, spec
    )


async def align_with_provenance_as_of(
    session: AsyncSession,
    country_iso3: str,
    indicator_code: str,
    scoring_period: ScoringPeriod,
    execution: ExecutionSpec | None = None,
):
    """Align and return both AlignedValue and source-identity provenance.

    Sprint 6.11 (DEC-038): the derived aligned layer needs Observation.id,
    source_series_id, and data_source_id — fields that AlignedValue does
    not carry. This function uses the SAME _select_observation_as_of
    primitive as align_observation_as_of (one authoritative selection
    algorithm, no second as-of path) and returns the additional provenance
    fields alongside the AlignedValue.

    Returns None when no eligible observation exists (MISSING != ZERO).

    Returns a tuple: (AlignedValue, observation_id, source_series_id,
    data_source_id, release_date).
    """
    country, indicator = await _resolve_country_indicator(
        session, country_iso3, indicator_code
    )
    spec = get_normalization_spec(indicator_code)

    observation = await _select_observation_as_of(
        session, country, indicator, spec, scoring_period, execution
    )
    if observation is None:
        return None

    aligned = _build_aligned_value(
        observation, indicator_code, country_iso3, scoring_period, spec
    )
    release_date = (
        observation.release_date.date() if observation.release_date else None
    )
    return (
        aligned,
        observation.id,
        observation.source_series_id,
        observation.data_source_id,
        release_date,
    )


async def own_history_as_of(
    session: AsyncSession,
    country_iso3: str,
    indicator_code: str,
    scoring_period: ScoringPeriod,
    execution: ExecutionSpec | None = None,
) -> list[AlignedValue]:
    """The country's OWN expanding as-of history through the snapshot (DEC-019).

    One latest-vintage value per ACTUAL source period, from the first
    period-complete observation through the scoring snapshot — the calibration
    sample for OWN_HISTORY level normalization (Sprint 5.10, DSR only). Same
    selection semantics as align_observation_as_of: country scoping at every
    layer (ISSUE-004), latest vintage per source period, DEC-015
    period-complete eligibility, and no future observations (an observation
    stored "now" for a period after T is excluded when scoring T).

    The sample contains REAL observations only — it is never built from
    scoring snapshots: no forward-fill, no interpolation, no duplicated raw
    row across derived quarters, no synthesized missing periods, no
    zero-filled gaps. Read-only; nothing is written.

    The last element is the current aligned observation (the newest eligible
    period), ascending order throughout. Empty list when no eligible
    observation exists.
    """
    country = (
        await session.execute(select(Country).where(Country.iso3 == country_iso3))
    ).scalar_one_or_none()
    if country is None:
        raise AlignmentError(f"unknown country iso3: {country_iso3!r}")

    indicator = (
        await session.execute(select(Indicator).where(Indicator.code == indicator_code))
    ).scalar_one_or_none()
    if indicator is None:
        raise AlignmentError(f"unknown indicator code: {indicator_code!r}")

    spec = get_normalization_spec(indicator_code)
    as_of_dt = datetime.combine(
        quarter_end_date(scoring_period), time(23, 59, 59), tzinfo=timezone.utc
    )
    period_complete = _period_complete_condition(spec.freshness_class, scoring_period)

    availability: list = []
    needs_source_join = False
    if execution is not None:
        availability, needs_source_join = _release_availability_conditions(
            execution, spec.freshness_class
        )

    latest_vintage_q = (
        select(
            Observation.source_series_id,
            Observation.period_start,
            func.max(Observation.vintage_number).label("max_vintage"),
        )
        .where(
            Observation.country_id == country.id,
            Observation.indicator_id == indicator.id,
            Observation.period_start <= as_of_dt,
            period_complete,
            *availability,
        )
        .group_by(Observation.source_series_id, Observation.period_start)
    )
    if needs_source_join:
        latest_vintage_q = latest_vintage_q.join(
            DataSource, Observation.data_source_id == DataSource.id
        )
    latest_vintage = latest_vintage_q.subquery()

    outer = (
        select(Observation)
        .join(
            latest_vintage,
            (Observation.source_series_id == latest_vintage.c.source_series_id)
            & (Observation.period_start == latest_vintage.c.period_start)
            & (Observation.vintage_number == latest_vintage.c.max_vintage),
        )
        .where(
            Observation.country_id == country.id,
            Observation.indicator_id == indicator.id,
            Observation.period_start <= as_of_dt,
            period_complete,
            *availability,
        )
        # Ascending: the calibration sample reads first-to-current; the
        # last element IS the current aligned observation.
        .order_by(
            Observation.period_start.asc(),
            Observation.vintage_number.desc(),
            Observation.id.desc(),
        )
    )
    if needs_source_join:
        outer = outer.join(
            DataSource, Observation.data_source_id == DataSource.id
        )

    observations = (await session.execute(outer)).scalars().all()

    scoring_index = _quarter_index(quarter_end_date(scoring_period))
    history: list[AlignedValue] = []
    for observation in observations:
        source_date = observation.period_start.date()
        history.append(
            AlignedValue(
                indicator_code=indicator_code,
                country_iso3=country_iso3,
                scoring_period=scoring_period,
                source_period=_source_period_label(source_date, spec.freshness_class),
                raw_value=observation.value,
                age_periods=scoring_index - _quarter_index(source_date),
                effective_period_end=effective_period_end(
                    source_date, spec.freshness_class
                ),
                vintage_number=observation.vintage_number,
            )
        )
    return history