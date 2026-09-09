from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.indicator import Indicator
from typing import Optional


async def list_indicators(
    session: AsyncSession, category: Optional[str] = None, frequency: Optional[str] = None
) -> list[Indicator]:
    query = select(Indicator)
    if category:
        query = query.where(Indicator.category == category)
    if frequency:
        query = query.where(Indicator.frequency == frequency)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_indicator_by_code(session: AsyncSession, code: str) -> Optional[Indicator]:
    result = await session.execute(select(Indicator).where(Indicator.code == code))
    return result.scalar_one_or_none()
