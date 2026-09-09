import pytest

EXPECTED_SOURCE_KEYS = {
    "world_bank",
    "bis",
    "oecd",
    "fred",
    "eurostat",
    "ecb",
    "snb",
    "un_comtrade",
}


@pytest.mark.asyncio
async def test_list_sources(client):
    response = await client.get("/api/data/sources")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 8
    keys = {source["key"] for source in body}
    assert keys == EXPECTED_SOURCE_KEYS
    for source in body:
        assert set(source) == {
            "key",
            "name",
            "base_url",
            "auth_type",
            "status",
            "update_frequency",
            "documentation_url",
            "id",
            "created_at",
            "updated_at",
            "extra_metadata",
        }


@pytest.mark.asyncio
async def test_get_source_by_key(client):
    response = await client.get("/api/data/sources/world_bank")
    assert response.status_code == 200
    body = response.json()
    assert body["key"] == "world_bank"
    assert body["name"] == "World Bank"
    assert body["status"] == "planned"


@pytest.mark.asyncio
async def test_get_source_unknown_key_returns_404(client):
    response = await client.get("/api/data/sources/does_not_exist")
    assert response.status_code == 404
    assert "does_not_exist" in response.json()["detail"]