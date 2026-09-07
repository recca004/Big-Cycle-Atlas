async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Big Cycle Atlas API"
    assert "version" in body


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert "version" in body