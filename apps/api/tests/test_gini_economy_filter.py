"""Offline regression for the WB authoritative economy filter (Sprint 5.17.1).

Tests the pure helper `build_valid_economy_codes` from the read-only Gini
calibration profile script with MOCKED provider metadata — no external HTTP.

The bug this sprint fixes: the previous hand-written `aggregate_codes`
blacklist in `gini_calibration_profile.py` listed real economies such as
ZAF (South Africa) and PSE (West Bank and Gaza) as aggregates. The
authoritative filter keys on the WB country-metadata `region.id` field
(real economies have a real region id; aggregates carry region.id == "NA"),
so ZAF and PSE are retained while genuine aggregates (WLD, EAP, HIC, ...) are
excluded.
"""
from scripts.gini_calibration_profile import build_valid_economy_codes


# Mocked WB /v2/country metadata records (the shape the live endpoint
# returns: id, name, region{id,value}, incomeLevel{id,value}). Real
# economies carry a real region.id; aggregates carry region.id == "NA".
_MOCK_COUNTRY_RECORDS = [
    # Real economies (region.id set to a real region)
    {"id": "USA", "name": "United States",
     "region": {"id": "NAC", "value": "North America"},
     "incomeLevel": {"id": "HIC", "value": "High income"}},
    {"id": "ZAF", "name": "South Africa",
     "region": {"id": "SSF", "value": "Sub-Saharan Africa "},
     "incomeLevel": {"id": "UMC", "value": "Upper middle income"}},
    {"id": "PSE", "name": "West Bank and Gaza",
     "region": {"id": "MEA", "value": "Middle East, North Africa, Afghanistan & Pakistan"},
     "incomeLevel": {"id": "LMC", "value": "Lower middle income"}},
    {"id": "CHN", "name": "China",
     "region": {"id": "EAS", "value": "East Asia & Pacific"},
     "incomeLevel": {"id": "UMC", "value": "Upper middle income"}},
    {"id": "IND", "name": "India",
     "region": {"id": "SAS", "value": "South Asia"},
     "incomeLevel": {"id": "LMC", "value": "Lower middle income"}},
    # Aggregates (region.id == "NA", region.value == "Aggregates")
    {"id": "WLD", "name": "World",
     "region": {"id": "NA", "value": "Aggregates"},
     "incomeLevel": {"id": "NA", "value": "Aggregates"}},
    {"id": "EAP", "name": "East Asia & Pacific (excluding high income)",
     "region": {"id": "NA", "value": "Aggregates"},
     "incomeLevel": {"id": "NA", "value": "Aggregates"}},
    {"id": "HIC", "name": "High income",
     "region": {"id": "NA", "value": "Aggregates"},
     "incomeLevel": {"id": "NA", "value": "Aggregates"}},
    {"id": "SSF", "name": "Sub-Saharan Africa ",
     "region": {"id": "NA", "value": "Aggregates"},
     "incomeLevel": {"id": "NA", "value": "Aggregates"}},
    # Edge cases: empty/None region
    {"id": "INX", "name": "Not classified",
     "region": {"id": "NA", "value": "Aggregates"},
     "incomeLevel": {"id": "NA", "value": "Aggregates"}},
]


def test_zaf_retained_as_real_economy():
    """ZAF (South Africa) must be retained — it was wrongly in the old blacklist."""
    codes = build_valid_economy_codes(_MOCK_COUNTRY_RECORDS)
    assert "ZAF" in codes


def test_pse_retained_as_real_economy():
    """PSE (West Bank and Gaza) must be retained — it was wrongly in the old blacklist."""
    codes = build_valid_economy_codes(_MOCK_COUNTRY_RECORDS)
    assert "PSE" in codes


def test_known_aggregates_excluded():
    """Genuine aggregates (region.id == 'NA') must be excluded."""
    codes = build_valid_economy_codes(_MOCK_COUNTRY_RECORDS)
    for aggregate in ("WLD", "EAP", "HIC", "SSF", "INX"):
        assert aggregate not in codes, f"{aggregate} should be excluded as an aggregate"


def test_real_economies_retained():
    """All real economies (region.id set) are retained."""
    codes = build_valid_economy_codes(_MOCK_COUNTRY_RECORDS)
    assert codes == {"USA", "ZAF", "PSE", "CHN", "IND"}


def test_ss_region_collision_handled():
    """SSF appears BOTH as a real-economy region id (on ZAF's record) AND as an
    aggregate code (its own record has region.id == 'NA'). The filter keys on
    the record's OWN region field, never on the code itself, so the two senses
    never collide: ZAF is retained, the SSF aggregate is excluded."""
    codes = build_valid_economy_codes(_MOCK_COUNTRY_RECORDS)
    assert "ZAF" in codes
    assert "SSF" not in codes


def test_malformed_records_skipped():
    """Non-dict records, missing ids, and missing region objects are skipped
    defensively (never raise)."""
    records = [
        "not a dict",
        None,
        {"id": "USA", "region": {"id": "NAC"}},
        {"id": "", "region": {"id": "NAC"}},
        {"id": "DEU"},  # no region -> region defaults to {} -> id None -> excluded
        {"id": "FRA", "region": None},
        {"id": "GBR", "region": {"id": "ECS"}},
    ]
    codes = build_valid_economy_codes(records)
    assert codes == {"USA", "GBR"}
