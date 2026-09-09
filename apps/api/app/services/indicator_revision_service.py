from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.indicator_revision import IndicatorRevision
from app.models.observation import Observation
from typing import Optional, List


async def list_indicator_revisions(
    session: AsyncSession, indicator_id: Optional[int] = None, limit: int = 100, offset: int = 0
) -> tuple[List[IndicatorRevision], int]:
    query = select(IndicatorRevision)
    if indicator_id:
        query = query.join(Observation, IndicatorRevision.new_observation_id == Observation.id).where(Observation.indicator_id == indicator_id)

    query = query.order_by(desc(IndicatorRevision.revision_date)).offset(offset).limit(limit)

    result = await session.execute(query)
    items = list(result.scalars().all())

    # Get total count for pagination
    count_query = select(func.count()).select_from(IndicatorRevision)
    if indicator_id:
        count_query = count_query.join(Observation, IndicatorRevision.new_observation_id == Observation.id).where(Observation.indicator_id == indicator_id)

    count_result = await session.execute(count_query)
    total_count = count_result.scalar_one()

    return items, total_count

async def get_indicator_revision_by_id(session: AsyncSession, revision_id: int) -> Optional[IndicatorRevision]:
    result = await session.execute(select(IndicatorRevision).where(IndicatorRevision.id == revision_id))
    return result.scalar_one_or_none()
