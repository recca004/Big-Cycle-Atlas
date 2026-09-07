from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    database = "unavailable"
    database_error: str | None = None
    try:
        async for session in get_session():
            await session.execute(text("SELECT 1"))
        database = "connected"
    except Exception as exc:
        database_error = str(exc)

    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.app_version,
        "database": database,
        "database_error": database_error,
    }