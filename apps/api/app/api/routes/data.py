from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.session import get_session
from app.schemas.data_source import DataSource as DataSourceSchema
from app.schemas.ingestion_run import IngestionRun as IngestionRunSchema
from app.services import data_source_service, ingestion_run_service


router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/sources", response_model=list[DataSourceSchema])
async def list_sources(session: AsyncSession = Depends(get_session)):
    return await data_source_service.list_data_sources(session)


@router.get("/sources/{key}", response_model=DataSourceSchema)
async def get_source_by_key(key: str, session: AsyncSession = Depends(get_session)):
    source = await data_source_service.get_data_source_by_key(session, key)
    if source is None:
        raise HTTPException(
            status_code=404,
            detail=f"Data source with key '{key}' not found",
        )
    return source


@router.get("/ingestion-runs", response_model=list[IngestionRunSchema])
async def list_ingestion_runs(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    items, _ = await ingestion_run_service.list_ingestion_runs(
        session, limit=limit, offset=offset
    )
    return items
