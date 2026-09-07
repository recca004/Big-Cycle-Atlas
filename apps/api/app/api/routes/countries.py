from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.schemas import CountryRead
from app.services import country_service

router = APIRouter(prefix=f"{get_settings().api_prefix}/countries", tags=["countries"])


@router.get("", response_model=list[CountryRead])
async def list_countries(session: AsyncSession = Depends(get_session)):
    return await country_service.list_countries(session)


@router.get("/{iso3}", response_model=CountryRead)
async def get_country(iso3: str, session: AsyncSession = Depends(get_session)):
    country = await country_service.get_country(session, iso3)
    if country is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Country with ISO3 '{iso3}' not found",
        )
    return country