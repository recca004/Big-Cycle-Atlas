"""Contract tests for GET /api/countries/{iso3}/force-scores.

The endpoint must return all 17 forces, never invent scores (None, not 0),
and preserve the missing/deferred distinction. With an empty observation
store every force is deferred — which itself is a valid contract check.
"""

import pytest


@pytest.mark.asyncio
async def test_force_scores_returns_all_17_forces(client):
    response = await client.get("/api/countries/USA/force-scores")
    assert response.status_code == 200
    body = response.json()
    assert body["country"] == "USA"
    assert len(body["forces"]) == 17
    assert "normalization_version" in body
    assert "force_aggregation_version" in body


@pytest.mark.asyncio
async def test_force_scores_shape_and_no_invented_scores(client):
    body = (await client.get("/api/countries/CHE/force-scores")).json()
    for f in body["forces"]:
        assert set(f) == {
            "force_code",
            "force_name",
            "execution_status",
            "level_score",
            "relative_score",
            "momentum_score",
            "confidence",
            "coverage_status",
            "period",
            "model_version",
            "limitations",
            "reasons",
            "backtest_safe",
        }
        if f["execution_status"] == "deferred":
            # Deferred forces never present a numeric score.
            assert f["level_score"] is None
        assert isinstance(f["limitations"], list)
        assert isinstance(f["reasons"], list)
        assert f["backtest_safe"] is False


@pytest.mark.asyncio
async def test_force_scores_explicit_period(client):
    response = await client.get(
        "/api/countries/USA/force-scores", params={"period": "2024-Q4"}
    )
    assert response.status_code == 200
    body = response.json()
    assert all(f["period"] == "2024-Q4" for f in body["forces"])


@pytest.mark.asyncio
async def test_force_scores_invalid_period_422(client):
    response = await client.get(
        "/api/countries/USA/force-scores", params={"period": "not-a-period"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_force_scores_unknown_country_404(client):
    response = await client.get("/api/countries/ZZZ/force-scores")
    assert response.status_code == 404
