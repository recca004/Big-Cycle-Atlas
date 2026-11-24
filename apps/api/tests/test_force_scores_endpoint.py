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


async def test_force_history_endpoint_shape(client):
    response = await client.get(
        "/api/countries/USA/forces/productivity_output_growth/history",
        params={"start_year": 2018, "end_year": 2020},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["retrospective"] is True
    assert body["backtest_safe"] is False
    assert body["force_code"] == "productivity_output_growth"
    assert len(body["points"]) == 3
    for point in body["points"]:
        assert point["period"].endswith("-Q4")
        assert point["coverage_status"] in {
            "available", "partial", "defined_not_sourced", "no_data"
        }


async def test_force_history_unknown_force_404(client):
    response = await client.get(
        "/api/countries/USA/forces/not_a_force/history",
        params={"start_year": 2020, "end_year": 2020},
    )
    assert response.status_code == 404


async def test_force_history_rejects_reversed_range(client):
    response = await client.get(
        "/api/countries/USA/forces/education/history",
        params={"start_year": 2020, "end_year": 2018},
    )
    assert response.status_code == 422


async def test_uncertainty_endpoint_returns_published_bounds(client):
    response = await client.get("/api/countries/USA/uncertainty")
    assert response.status_code == 200
    body = response.json()
    assert body["country"] == "USA"
    for item in body["indicators"]:
        assert item["indicator_code"].endswith("_WGI_SCORE")
        if item["ci_lower_bound"] is not None:
            assert item["ci_lower_bound"] <= item["ci_upper_bound"]
        if item["source_count"] is not None:
            assert item["source_count"] > 0


async def test_uncertainty_unknown_country_404(client):
    assert (await client.get("/api/countries/ZZZ/uncertainty")).status_code == 404
