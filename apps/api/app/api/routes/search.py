"""Global entity search (Mission 6 §8).

Searches real application entities — countries, indicators, financial
instruments — and returns typed hits the frontend merges with its static
entities (forces, composite models, pages, workspaces). Bounded results,
no pagination needed: the payload is small by construction.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import Country, Indicator
from app.models.market import MarketInstrument

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchHit(BaseModel):
    kind: str          # country | indicator | instrument
    key: str           # iso3 | indicator code | instrument code
    label: str
    detail: str | None = None


class SearchResponse(BaseModel):
    query: str
    countries: list[SearchHit]
    indicators: list[SearchHit]
    instruments: list[SearchHit]


@router.get("", response_model=SearchResponse)
@router.get("/", response_model=SearchResponse, include_in_schema=False)
async def search(
    q: str = Query(..., min_length=1, max_length=80),
    limit: int = Query(8, ge=1, le=25),
    session: AsyncSession = Depends(get_session),
):
    term = q.strip()
    like = f"%{term}%"

    countries = (
        await session.execute(
            select(Country)
            .where(or_(Country.name.ilike(like), Country.iso3.ilike(like), Country.iso2.ilike(like)))
            .order_by(Country.name)
            .limit(limit)
        )
    ).scalars().all()

    indicators = (
        await session.execute(
            select(Indicator)
            .where(or_(Indicator.name.ilike(like), Indicator.code.ilike(like)))
            .order_by(Indicator.code)
            .limit(limit)
        )
    ).scalars().all()

    instruments = (
        await session.execute(
            select(MarketInstrument)
            .where(
                MarketInstrument.active.is_(True),
                or_(MarketInstrument.name.ilike(like), MarketInstrument.code.ilike(like)),
            )
            .order_by(MarketInstrument.code)
            .limit(limit)
        )
    ).scalars().all()

    return SearchResponse(
        query=term,
        countries=[
            SearchHit(kind="country", key=c.iso3, label=c.name, detail=c.region)
            for c in countries
        ],
        indicators=[
            SearchHit(kind="indicator", key=i.code, label=i.name,
                      detail=i.category)
            for i in indicators
        ],
        instruments=[
            SearchHit(kind="instrument", key=m.code, label=m.name,
                      detail=f"{m.asset_class} · {m.currency}")
            for m in instruments
        ],
    )
