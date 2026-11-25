"""Market regime engine tests (Mission 5 §19-§22)."""
from app.research.regime import (
    GrowthDirection,
    InflationDirection,
    Regime,
    RegimeConfig,
    classify_years,
    direction,
)


def test_direction_thresholds():
    assert direction(3.0, 2.0, 0.25, GrowthDirection) is GrowthDirection.improving
    assert direction(1.0, 2.0, 0.25, GrowthDirection) is GrowthDirection.weakening
    # sub-eps change -> None (caller carries prior direction)
    assert direction(2.1, 2.0, 0.25, GrowthDirection) is None
    assert direction(None, 2.0, 0.25, GrowthDirection) is None


def test_classify_needs_current_and_previous():
    gdp = {2020: 2.0, 2021: 4.0, 2022: 1.0}
    cpi = {2020: 1.0, 2021: 5.0, 2022: 2.0}
    out = classify_years(gdp, cpi)
    # first year: no prior data -> unclassified, never guessed
    assert out[0].regime is Regime.unclassified
    # 2021: growth +2pp improving, cpi +4pp rising -> REFLATION
    assert out[1].regime is Regime.reflation
    # 2022: growth -3pp weakening, cpi -3pp falling -> DISINFLATION_SLOWDOWN
    assert out[2].regime is Regime.disinflation_slowdown


def test_sub_eps_change_carries_prior_direction():
    gdp = {2020: 2.0, 2021: 4.0, 2022: 4.1}  # +0.1 < eps
    cpi = {2020: 1.0, 2021: 5.0, 2022: 4.9}  # -0.1 < eps
    out = classify_years(gdp, cpi)
    assert out[2].regime is Regime.reflation  # prior directions held


def test_missing_input_explicit():
    gdp = {2020: 2.0, 2021: 4.0}
    cpi = {2020: 1.0}  # 2021 CPI missing
    out = classify_years(gdp, cpi)
    r21 = next(r for r in out if r.year == 2021)
    assert "inflation_cpi" in r21.missing_inputs
    # growth direction known, inflation unknown -> unclassified
    assert r21.regime is Regime.unclassified
    assert r21.growth_direction is GrowthDirection.improving


async def test_regime_history_endpoint_shape(client):
    r = await client.get("/api/regimes/countries/USA/history")
    assert r.status_code == 200
    body = r.json()
    assert body["methodology_status"] == "experimental"
    assert body["backtest_safe"] is False
    assert "regimes" in body and "financial_conditions" in body
    assert body["coverage"]["classified"] == 0  # test DB has no macro obs


async def test_regime_asset_returns_endpoint(client):
    r = await client.get("/api/regimes/countries/USA/asset-returns")
    assert r.status_code == 200
    body = r.json()
    assert "by_regime" in body and "warning" in body
    assert "association" in body["warning"]
