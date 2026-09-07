from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Country


async def list_countries(session: AsyncSession) -> list[Country]:
    result = await session.execute(select(Country).order_by(Country.name))
    return list(result.scalars().all())


async def get_country(session: AsyncSession, iso3: str) -> Country | None:
    result = await session.execute(select(Country).where(Country.iso3 == iso3.upper()))
    return result.scalars().first()