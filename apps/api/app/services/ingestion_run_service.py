from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ingestion_run import IngestionRun
from typing import Optional, List


async def list_ingestion_runs(
    session: AsyncSession, data_source_id: Optional[int] = None, limit: int = 100, offset: int = 0
) -> tuple[List[IngestionRun], int]:
    query = select(IngestionRun)
    if data_source_id:
        query = query.where(IngestionRun.data_source_id == data_source_id)

    query = query.order_by(desc(IngestionRun.created_at)).offset(offset).limit(limit)

    result = await session.execute(query)
    items = list(result.scalars().all())

    # Get total count for pagination
    count_query = select(func.count()).select_from(IngestionRun)
    if data_source_id:
        count_query = count_query.where(IngestionRun.data_source_id == data_source_id)

    count_result = await session.execute(count_query)
    total_count = count_result.scalar_one()

    return items, total_count

async def get_ingestion_run_by_id(session: AsyncSession, run_id: int) -> Optional[IngestionRun]:
    result = await session.execute(select(IngestionRun).where(IngestionRun.id == run_id))
    return result.scalar_one_or_none()
