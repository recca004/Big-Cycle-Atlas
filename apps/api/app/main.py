import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

if sys.platform == "win32":
    # psycopg async requires a selector-based event loop; uvicorn would default to Proactor
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.api.routes import markets, portfolios, regimes, research, search, strategies
from app.api.routes import countries, health
from app.api.routes.data import router as data_router
from app.api.routes.indicators import router as indicators_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(countries.router)
    app.include_router(data_router)
    app.include_router(indicators_router)
    app.include_router(research.router)
    app.include_router(markets.router)
    app.include_router(regimes.router)
    app.include_router(strategies.router)
    app.include_router(portfolios.router)
    app.include_router(search.router)

    web_dist = (
        (Path(__file__).resolve().parents[1] / settings.web_dist).resolve()
        if settings.web_dist
        else None
    )
    if web_dist is not None and web_dist.is_dir():
        # Native production mode: serve the Astro build same-origin so the
        # whole app runs on a single port behind uvicorn.
        app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="web")
    else:

        @app.get("/")
        async def root():
            return {"name": settings.app_name, "version": settings.app_version}

    return app


app = create_app()
