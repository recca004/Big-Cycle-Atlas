"""Per-country data-coverage computation for the 17 Big Cycle forces.

Deterministic status rules (coverage is not strength — no scores exist here):

- available          — all currently-mapped LIVE inputs have observations for
                       the country (latest vintage only), unless the force
                       declares a conceptual coverage_ceiling (proxy-only
                       forces like Gini-for-wealth-gaps cap at PARTIAL)
- partial            — at least one live input has observations, another does
                       not (e.g. CHN productivity: GDP growth yes, OECD
                       labour productivity no)
- defined_not_sourced — no live input has data, but the force has defined
                       inputs (live or candidate catalog indicators) — the
                       concept exists, the data does not
- missing            — no defined usable input exists yet

Candidate inputs never raise a status: promotion to live is a deliberate
config change. Superseded vintages never count toward coverage.

All coverage is computed from a small fixed number of aggregate queries (catalog
indicators, sourced indicator codes, one per-country latest-vintage aggregate) —
never 17 x N per-force queries.
"""
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cycle.force_definitions import (
    FORCE_DEFINITIONS,
    ForceCoverageStatus,
    ForceDefinition,
)
from app.models import DataSource, Indicator, Observation, SourceSeries


@dataclass
class ForceInputCoverage:
    indicator_code: str
    name: str | None = None
    has_data: bool = False
    has_source_series: bool = False
    source: str | None = None
    latest_period: date | None = None


@dataclass
class ForceCoverage:
    definition: ForceDefinition
    status: ForceCoverageStatus
    live_inputs: list[ForceInputCoverage] = field(default_factory=list)
    candidate_inputs: list[ForceInputCoverage] = field(default_factory=list)


def _force_status(
    force: ForceDefinition,
    live_with_data: int,
    catalog_codes: set[str],
) -> ForceCoverageStatus:
    live_total = len(force.live_indicator_codes)
    if live_total and live_with_data == live_total:
        # Conceptual ceiling: mapped inputs may be an explicitly incomplete
        # proxy for the force — complete data still cannot report "available".
        if force.coverage_ceiling is ForceCoverageStatus.partial:
            return ForceCoverageStatus.partial
        return ForceCoverageStatus.available
    if live_with_data > 0:
        return ForceCoverageStatus.partial
    defined_codes = set(force.live_indicator_codes) | set(
        force.candidate_indicator_codes
    )
    if defined_codes & catalog_codes:
        return ForceCoverageStatus.defined_not_sourced
    return ForceCoverageStatus.missing


async def get_force_coverage(
    session: AsyncSession, country_id: int
) -> list[ForceCoverage]:
    """Coverage for all 17 forces for one country, from 3 aggregate queries."""
    indicator_rows = (
        await session.execute(select(Indicator.code, Indicator.name))
    ).all()
    catalog_names: dict[str, str] = dict(indicator_rows)
    catalog_codes: set[str] = set(catalog_names)

    sourced_indicator_ids = set(
        (
            await session.execute(
                select(func.distinct(SourceSeries.indicator_id))
            )
        ).scalars().all()
    )
    indicator_ids = dict(
        (await session.execute(select(Indicator.id, Indicator.code))).all()
    )
    sourced_codes = {
        indicator_ids[iid] for iid in sourced_indicator_ids if iid in indicator_ids
    }

    # Latest-vintage observations for the country, aggregated per indicator
    # and source: count + latest period_start. Superseded vintages excluded.
    latest_vintage = (
        select(
            Observation.source_series_id,
            Observation.period_start,
            func.max(Observation.vintage_number).label("max_vintage"),
        )
        .where(Observation.country_id == country_id)
        .group_by(Observation.source_series_id, Observation.period_start)
        .subquery()
    )
    rows = (
        await session.execute(
            select(
                Observation.indicator_id,
                DataSource.key,
                func.count().label("observation_count"),
                func.max(Observation.period_start).label("latest_period"),
            )
            .join(
                latest_vintage,
                and_(
                    Observation.source_series_id == latest_vintage.c.source_series_id,
                    Observation.period_start == latest_vintage.c.period_start,
                    Observation.vintage_number == latest_vintage.c.max_vintage,
                ),
            )
            .join(DataSource, DataSource.id == Observation.data_source_id)
            .where(Observation.country_id == country_id)
            .group_by(Observation.indicator_id, DataSource.key)
        )
    ).all()

    # indicator_code -> (latest_period, source_key of the most recent source)
    per_indicator: dict[int, tuple[date | None, str | None]] = {}
    for row in rows:
        current = per_indicator.get(row.indicator_id)
        if current is None or (row.latest_period or date.min) > (current[0] or date.min):
            per_indicator[row.indicator_id] = (row.latest_period, row.key)

    def _input(code: str) -> ForceInputCoverage:
        has_data = any(
            indicator_ids.get(iid) == code for iid in per_indicator
        )
        latest_period = None
        source = None
        if has_data:
            for iid, (period, key) in per_indicator.items():
                if indicator_ids.get(iid) == code:
                    latest_period = period
                    source = key
        return ForceInputCoverage(
            indicator_code=code,
            name=catalog_names.get(code),
            has_data=has_data,
            has_source_series=code in sourced_codes,
            source=source,
            latest_period=latest_period,
        )

    result: list[ForceCoverage] = []
    for force in FORCE_DEFINITIONS:
        live_inputs = [_input(code) for code in force.live_indicator_codes]
        candidate_inputs = [
            _input(code) for code in force.candidate_indicator_codes
        ]
        live_with_data = sum(1 for i in live_inputs if i.has_data)
        result.append(
            ForceCoverage(
                definition=force,
                status=_force_status(force, live_with_data, catalog_codes),
                live_inputs=live_inputs,
                candidate_inputs=candidate_inputs,
            )
        )
    return result