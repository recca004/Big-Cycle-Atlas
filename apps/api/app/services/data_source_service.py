from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.data_source import DataSource
from app.schemas.data_source import DataSource as DataSourceSchema
from typing import Optional


async def list_data_sources(session: AsyncSession) -> list[DataSource]:
    result = await session.execute(select(DataSource))
    return list(result.scalars().all())


async def get_data_source_by_key(session: AsyncSession, key: str) -> Optional[DataSource]:
    result = await session.execute(select(DataSource).where(DataSource.key == key))
    return result.scalar_one_or_none()


async def create_data_source(session: AsyncSession, data_source_data: dict) -> DataSource:
    new_source = DataSource(**data_source_data)
    session.add(new_source)
    await session.commit()
    await session.refresh(new_source)
    return new_source
