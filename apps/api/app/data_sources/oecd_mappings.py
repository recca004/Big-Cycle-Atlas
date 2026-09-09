"""Central mapping of canonical Big Cycle Atlas indicators to OECD dataflows.

Every external identity here was verified against the official OECD SDMX REST
API (https://sdmx.oecd.org/public/rest/, documented at
https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html) on
2026-09-08. Data query (SDMX API v1):
GET {base}/data/{agency_id},{dataflow_id},{version}/{resolved_key}?format=csvfilewithlabels
— SDMX-CSV where the first row uses dimension IDs as column names (REF_AREA,
FREQ, MEASURE, ...). The adapter and any future seed both consume this module
— do not scatter OECD dataflow/series keys elsewhere.

Canonical indicator codes are OWNER-APPROVED and seeded (2026-09-08):
LABOUR_PRODUCTIVITY_PER_HOUR and UNIT_LABOUR_COST_GROWTH are in the seeded
19-indicator catalog (app/db/seed.py) and each has a seeded OECD SourceSeries.
PRICE_BASE=LR stays a raw code: the series identity and values are verified
live, but the exact official LR label still requires OECD metadata
confirmation — do not attach an unverified human-readable label.

External identity design (same principles as BIS):
- agency_id + dataflow_id + version identify the dataset (dataflow alone is
  not a series identity — DF_PDB carries GDPHRS in several unit/price
  families: current vs constant prices, national currency vs USD PPP).
- sdmx_key_template is the country-independent SDMX key, with {cc} as the
  placeholder for the OECD REF_AREA code — REF_AREA is the FIRST dimension
  in OECD PDB keys (verified live: CHE.A.GDPHRS...). SourceSeries is shared
  across countries in Big Cycle Atlas (Country lives on Observation), so the
  stored external identity must stay country-independent.
- external_code = "{dataflow_id}/{sdmx_key_template}". The OECD REF_AREA
  dimension uses ISO3 codes identical to Big Cycle Atlas ISO3 codes for all
  8 tracked countries (verified from actual data responses for
  USA/CHE/DEU/FRA/GBR/JPN; CHN and IND are valid CL_AREA codes but have no
  data in these two dataflows), so {cc} resolves 1:1 with no alias needed.

Normalization cautions:
- LABOUR_PRODUCTIVITY_PER_HOUR is a USD-PPP level: cross-country level
  comparisons are meaningful, but the price basis is chain-linked volume
  (rebased), so it is an index-like real measure, not a nominal value.
- UNIT_LABOUR_COST_GROWTH is a growth rate (per cent per annum, seasonally
  adjusted) — meaningful through time without a base-year caveat. The
  alternative index family (ULCE/IX, base 2015) is NOT mapped: absolute
  index levels must never be compared between countries as economic levels.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class OecdMapping:
    indicator_code: str
    agency_id: str
    dataflow_id: str
    version: str
    sdmx_key_template: str
    external_code: str
    external_name: str
    external_unit: str
    frequency: str
    transform_notes: str
    # (column, expected value) pairs validated against every returned CSV row.
    # Columns absent from a response's header are skipped (DF_PDB has
    # ASSET_CODE where DF_PDB_ULC_Q has ADJUSTMENT).
    expected_dims: tuple[tuple[str, str], ...] = ()
    source_key: str = "oecd"


LABOUR_PRODUCTIVITY_PER_HOUR = OecdMapping(
    indicator_code="LABOUR_PRODUCTIVITY_PER_HOUR",
    agency_id="OECD.SDD.TPS",
    dataflow_id="DSD_PDB@DF_PDB",
    version="2.0",
    sdmx_key_template="{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP",
    external_code="DSD_PDB@DF_PDB/{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP",
    external_name="GDP per hour worked (total economy, constant prices, USD PPP)",
    external_unit="US dollars per hour, PPP converted",
    frequency="annual",
    transform_notes=(
        "GDP per hour worked, total economy (ACTIVITY=_T), constant-price "
        "volume basis PRICE_BASE=LR (the code and the selected series are "
        "verified live; the exact official LR label still requires OECD "
        "metadata confirmation), non-transformed (TRANSFORMATION=N), "
        "PPP-converted US dollars per hour (UNIT_MEASURE=USD_PPP_H, "
        "CONVERSION_TYPE=PPP). Cross-country level comparisons are meaningful "
        "thanks to PPP; the value is a real (volume) productivity level, not "
        "nominal output. Use the published level — never recompute locally. "
        "The same dataflow also carries XDC (national currency) families, "
        "current-price families and GY growth variants — none of those are "
        "mapped."
    ),
    expected_dims=(
        ("FREQ", "A"),
        ("MEASURE", "GDPHRS"),
        ("ACTIVITY", "_T"),
        ("UNIT_MEASURE", "USD_PPP_H"),
        ("PRICE_BASE", "LR"),
        ("TRANSFORMATION", "N"),
        ("ASSET_CODE", "_Z"),
        ("CONVERSION_TYPE", "PPP"),
    ),
)

UNIT_LABOUR_COST_GROWTH = OecdMapping(
    indicator_code="UNIT_LABOUR_COST_GROWTH",
    agency_id="OECD.SDD.TPS",
    dataflow_id="DSD_PDB@DF_PDB_ULC_Q",
    version="1.0",
    sdmx_key_template="{cc}.Q.ULCE._T.PA.V.GY.S.NC",
    external_code="DSD_PDB@DF_PDB_ULC_Q/{cc}.Q.ULCE._T.PA.V.GY.S.NC",
    external_name="Unit labour costs, employment based, growth rate over 1 year",
    external_unit="percent per annum",
    frequency="quarterly",
    transform_notes=(
        "Unit labour costs (employment based, MEASURE=ULCE, ACTIVITY=_T), "
        "growth rate over 1 year (TRANSFORMATION=GY) in per cent per annum "
        "(UNIT_MEASURE=PA), seasonally adjusted (ADJUSTMENT=S, not calendar "
        "adjusted). Chosen over the ULCE/IX index family because growth is "
        "meaningful through time without a base-year caveat; the index's "
        "absolute levels must never be compared between countries. Cost "
        "competitiveness is best read as changes relative to each country's "
        "own history and relative to trading partners' growth."
    ),
    expected_dims=(
        ("FREQ", "Q"),
        ("MEASURE", "ULCE"),
        ("ACTIVITY", "_T"),
        ("UNIT_MEASURE", "PA"),
        ("PRICE_BASE", "V"),
        ("TRANSFORMATION", "GY"),
        ("ADJUSTMENT", "S"),
        ("CONVERSION_TYPE", "NC"),
    ),
)

OECD_MAPPINGS: tuple[OecdMapping, ...] = (
    LABOUR_PRODUCTIVITY_PER_HOUR,
    UNIT_LABOUR_COST_GROWTH,
)

# OECD REF_AREA uses ISO3 codes. Verified 2026-09-08 against actual data
# responses (USA/CHE/DEU/FRA/GBR/JPN return data; CHN and IND have no
# observations in these selected OECD dataflows — legitimate missing
# coverage, never coerced). Identity mapping: no aliases.
OECD_REF_AREA_BY_ISO3: dict[str, str] = {
    "USA": "USA",
    "CHN": "CHN",
    "CHE": "CHE",
    "DEU": "DEU",
    "FRA": "FRA",
    "GBR": "GBR",
    "JPN": "JPN",
    "IND": "IND",
}

_MAPPING_BY_INDICATOR_CODE = {m.indicator_code: m for m in OECD_MAPPINGS}
_MAPPING_BY_EXTERNAL_CODE = {m.external_code: m for m in OECD_MAPPINGS}


def get_oecd_mapping(indicator_code: str) -> OecdMapping | None:
    return _MAPPING_BY_INDICATOR_CODE.get(indicator_code)


def get_oecd_mapping_by_external_code(external_code: str) -> OecdMapping | None:
    """Reverse lookup: OECD external identity → canonical indicator mapping."""
    return _MAPPING_BY_EXTERNAL_CODE.get(external_code)