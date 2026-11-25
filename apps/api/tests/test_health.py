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
