import pytest

@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    # When the built web app exists, "/" serves the frontend; otherwise JSON.
    if "text/html" in response.headers.get("content-type", ""):
        assert b"html" in response.content[:200].lower()
    else:
        body = response.json()
        assert body["name"] == "Big Cycle Atlas API"
        assert "version" in body


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert "version" in body


@pytest.mark.asyncio
async def test_bare_collection_routes(client):
    """Collection endpoints must respond at the bare path (no trailing slash).
    Regression: the StaticFiles mount swallows Starlette's slash-redirect, so
    '/api/indicators' must match a real route, not redirect."""
    for path in ["/api/indicators", "/api/search?q=gdp", "/api/countries"]:
        response = await client.get(path)
        assert response.status_code == 200, f"{path} -> {response.status_code}"
