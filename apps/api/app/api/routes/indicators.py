from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.session import get_session
from app.schemas.indicator import Indicator as IndicatorSchema
from app.schemas.indicator_revision import IndicatorRevision as IndicatorRevisionSchema
from app.services import indicator_service, indicator_revision_service


router = APIRouter(prefix="/api/indicators", tags=["indicators"])


@router.get("/", response_model=list[IndicatorSchema])
async def list_indicators(
    session: AsyncSession = Depends(get_session),
    category: Optional[str] = Query(None),
    frequency: Optional[str] = Query(None),
):
    return await indicator_service.list_indicators(session, category=category, frequency=frequency)


@router.get("/{code}", response_model=IndicatorSchema)
async def get_indicator_by_code(code: str, session: AsyncSession = Depends(get_session)):
    indicator = await indicator_service.get_indicator_by_code(session, code)
    if indicator is None:
        raise HTTPException(
            status_code=404,
            detail=f"Indicator with code '{code}' not found",
        )
    return indicator


@router.get("/{code}/revisions", response_model=list[IndicatorRevisionSchema])
async def list_indicator_revisions(
    code: str,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    indicator = await indicator_service.get_indicator_by_code(session, code)
    if indicator is None:
        raise HTTPException(
            status_code=404,
            detail=f"Indicator with code '{code}' not found",
        )

    items, _ = await indicator_revision_service.list_indicator_revisions(
        session, indicator_id=indicator.id, limit=limit, offset=offset
    )
    return items
