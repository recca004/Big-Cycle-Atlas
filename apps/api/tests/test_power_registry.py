from app.research.power_registry import (
    CURRENCY_RESEARCH_ENTITIES,
    GLOBAL_DENOMINATOR_SERIES,
    HISTORICAL_BOUNDARIES,
    POWER_MEASURES_BY_INDICATOR,
)


def test_power_registry_uses_verified_world_denominators():
    assert POWER_MEASURES_BY_INDICATOR["GDP_CURRENT_USD"].global_denominator_code == "NY.GDP.MKTP.CD"
    assert POWER_MEASURES_BY_INDICATOR["MERCHANDISE_EXPORTS_USD"].global_denominator_code == "TX.VAL.MRCH.CD.WT"
    assert POWER_MEASURES_BY_INDICATOR["EXPORTS_GDP"].global_denominator_code is None
    assert GLOBAL_DENOMINATOR_SERIES["NY.GDP.MKTP.CD"]["entity"] == "WLD"


def test_currency_entities_preserve_currency_area_identity():
    eur = CURRENCY_RESEARCH_ENTITIES["EUR"]

    assert eur["scope"] == "currency_area"
    assert eur["country_iso3"] == ""
    assert CURRENCY_RESEARCH_ENTITIES["CNY"]["country_iso3"] == "CHN"
    assert CURRENCY_RESEARCH_ENTITIES["DEM"]["scope"] == "historical_currency"


def test_german_boundary_is_explicitly_dated():
    germany = [r for r in HISTORICAL_BOUNDARIES if r["country"] == "DEU"]

    assert len(germany) == 2
    assert any(r["applies_to"] == "1990-12-31" for r in germany)
    assert any(r["applies_from"] == "1991-01-01" for r in germany)
