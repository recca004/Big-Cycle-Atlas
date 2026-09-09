import pytest


@pytest.mark.asyncio
async def test_list_indicators(client):
    response = await client.get("/api/indicators/")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 25
    codes = {indicator["code"] for indicator in body}
    assert "GDP_GROWTH" in codes
    assert "CREDIT_TO_GDP_GAP" in codes
    for indicator in body:
        assert set(indicator) == {
            "code",
            "name",
            "description",
            "category",
            "unit",
            "frequency",
            "strength_direction",
            "id",
            "created_at",
            "updated_at",
        }


@pytest.mark.asyncio
async def test_list_indicators_filter_by_category(client):
    response = await client.get("/api/indicators/", params={"category": "Demographics"})
    assert response.status_code == 200
    body = response.json()
    assert [indicator["code"] for indicator in body] == ["POPULATION"]


@pytest.mark.asyncio
async def test_list_indicators_filter_by_frequency(client):
    response = await client.get("/api/indicators/", params={"frequency": "monthly"})
    assert response.status_code == 200
    body = response.json()
    # INFLATION_CPI is annual since Milestone 5.3 (verified WB series FP.CPI.TOTL.ZG)
    assert {indicator["code"] for indicator in body} == {
        "UNEMPLOYMENT_RATE",
    }


@pytest.mark.asyncio
async def test_list_indicators_filter_unknown_category_returns_empty(client):
    response = await client.get("/api/indicators/", params={"category": "Nope"})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_indicator_by_code(client):
    response = await client.get("/api/indicators/GDP_GROWTH")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "GDP_GROWTH"
    assert body["category"] == "Economy"
    assert body["unit"] == "percent"
    assert body["frequency"] == "annual"
    assert body["strength_direction"] == "positive"


@pytest.mark.asyncio
async def test_get_indicator_unknown_code_returns_404(client):
    response = await client.get("/api/indicators/DOES_NOT_EXIST")
    assert response.status_code == 404
    assert "DOES_NOT_EXIST" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_indicator_revisions_known_indicator_no_revisions(client):
    response = await client.get("/api/indicators/GDP_GROWTH/revisions")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_indicator_revisions_unknown_indicator_returns_404(client):
    response = await client.get("/api/indicators/DOES_NOT_EXIST/revisions")
    assert response.status_code == 404
    assert "DOES_NOT_EXIST" in response.json()["detail"]