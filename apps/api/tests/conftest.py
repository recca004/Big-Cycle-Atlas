import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import base
from app.db.session import get_session
from app.models import Country  # noqa: F401 — registers models on Base.metadata
from app.db.seed import DEFAULT_DATA_FILE, seed


@pytest.fixture
async def client(tmp_path):
    data_file = tmp_path / "countries.json"
    data_file.write_text(DEFAULT_DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(base.Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    from app.db import session as session_module
    session_module._engine = engine
    session_module._sessionmaker = sessionmaker

    await seed(data_file)

    from app.main import app

    async def override_get_session():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()