"""Central mapping of canonical Big Cycle Atlas indicators to WID dataflows.

Every external identity here was verified against the official WID bulk
download (https://wid.world/bulk_download/wid_all_data.zip, 882 MB, 848 CSV
files, no API key) on 2026-09-10 (Sprint 5.19) and re-verified for
implementation in Sprint 5.20.

WID data format (semicolon-delimited CSV):
    country;variable;percentile;year;value;age;pop;data_quality

Country codes are ISO2 (US, CN, CH, DE, FR, GB, JP, IN) — NOT ISO3.

Canonical series (Sprint 5.19 verified):
- variable = shweal (share of net personal wealth, hweal)
- percentile = p90p100 (top 10% share)
- age = 992 (adults)
- pop = j (equal-split adults) — NOT pop=i (individuals). Pop=j is the ONLY
  series available for all 8 tracked countries. Pop=i exists only for USA
  and GBR.
- Values are fractions (0-1). Stored unchanged — never converted to
  percentages before persistence.

data_quality semantics (Sprint 5.20 Part B1):
- WID does NOT provide an official, authoritative code dictionary for the
  data_quality column. The values 0, 1, 2 were observed but their exact
  meaning (observed/interpolated/extrapolated) is NOT officially documented.
- Policy: DEFER filtering. Import ALL rows. Preserve data_quality in
  raw_payload. Do NOT delete provider data using an inferred code meaning.
- If official documentation is found later, a future sprint may add
  filtering.

Extrapolation counts observed (shwealj992, p90p100):
  USA 0, CHN 0, CHE 0, DEU 24, FRA 80, GBR 93, JPN 0, IND 0
(data_quality=2 rows — but since semantics are unverified, all rows are
imported and data_quality is preserved.)
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class WidMapping:
    indicator_code: str
    variable: str
    percentile: str
    age: str
    pop: str
    external_code: str
    external_name: str
    external_unit: str
    frequency: str
    transform_notes: str
    source_key: str = "wid"


WEALTH_SHARE_TOP_10 = WidMapping(
    indicator_code="WEALTH_SHARE_TOP_10",
    variable="shwealj992",
    percentile="p90p100",
    age="992",
    pop="j",
    external_code="WID/shwealj992/p90p100",
    external_name="Top 10% net personal wealth share (equal-split adults)",
    external_unit="share (0-1)",
    frequency="annual",
    transform_notes=(
        "WID world shwealj992 p90p100: top 10% share of net personal wealth "
        "(hweal). Population type j = equal-split adults, age 992 = adults. "
        "Pop=j is the ONLY series available for all 8 tracked countries "
        "(pop=i/individuals exists only for USA and GBR). Values are "
        "fractions 0-1, stored unchanged — never converted to percentages. "
        "data_quality column preserved in raw_payload but NOT used for "
        "filtering (official semantics unverified — Sprint 5.20 Part B1 "
        "policy: DEFER filtering). Higher share = greater wealth "
        "concentration = weaker (MONOTONIC_NEGATIVE direction). Force stays "
        "PARTIAL (DEC-009 ceiling — wealth share does not address "
        "opportunity or values/social gaps)."
    ),
)

WID_MAPPINGS: tuple[WidMapping, ...] = (WEALTH_SHARE_TOP_10,)

# WID uses ISO2 country codes. Explicit typed mapping for tracked_8.
WID_COUNTRY_BY_ISO3: dict[str, str] = {
    "USA": "US",
    "CHN": "CN",
    "CHE": "CH",
    "DEU": "DE",
    "FRA": "FR",
    "GBR": "GB",
    "JPN": "JP",
    "IND": "IN",
}

_MAPPING_BY_INDICATOR_CODE = {m.indicator_code: m for m in WID_MAPPINGS}
_MAPPING_BY_EXTERNAL_CODE = {m.external_code: m for m in WID_MAPPINGS}


def get_wid_mapping(indicator_code: str) -> WidMapping | None:
    return _MAPPING_BY_INDICATOR_CODE.get(indicator_code)


def get_wid_mapping_by_external_code(external_code: str) -> WidMapping | None:
    """Reverse lookup: WID external identity → canonical indicator mapping."""
    return _MAPPING_BY_EXTERNAL_CODE.get(external_code)
