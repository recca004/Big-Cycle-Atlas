import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_list_countries(client):
    response = await client.get("/api/countries")
    assert response.status_code == 200
    countries = response.json()
    assert len(countries) == 8
    names = {c["name"] for c in countries}
    assert "United States" in names
    assert "Switzerland" in names
    iso3s = {c["iso3"] for c in countries}
    assert iso3s == {"USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND"}


@pytest.mark.asyncio
async def test_list_countries_ordered_by_name(client):
    response = await client.get("/api/countries")
    countries = response.json()
    names = [c["name"] for c in countries]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_get_country_found(client):
    response = await client.get("/api/countries/CHE")
    assert response.status_code == 200
    country = response.json()
    assert country["iso3"] == "CHE"
    assert country["name"] == "Switzerland"
    assert country["region"] == "Europe"


@pytest.mark.asyncio
async def test_get_country_case_insensitive(client):
    response = await client.get("/api/countries/che")
    assert response.status_code == 200
    assert response.json()["iso3"] == "CHE"


@pytest.mark.asyncio
async def test_get_country_not_found(client):
    response = await client.get("/api/countries/ZZZ")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
