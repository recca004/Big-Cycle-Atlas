"""Central mapping of canonical Big Cycle Atlas indicators to IMF WEO dataflows.

Every external identity here was verified against the official IMF SDMX 3.0 API
(https://api.imf.org/external/sdmx/3.0) on 2026-09-10. Data query (SDMX 3.0):
GET {base}/data/dataflow/{agency_id}/{dataflow_id}/+/{key}
    ?format=jsondata&attributes=LATEST_ACTUAL_ANNUAL_DATA
— JSON with series observations + the LATEST_ACTUAL_ANNUAL_DATA dimension-group
attribute that marks the historical/forecast boundary. No authentication
required (verified live 2026-09-10; the SDMX 3.0 endpoint is publicly
accessible without an Ocp-Apim-Subscription-Key for WEO).

The adapter and any future seed both consume this module — do not scatter
IMF WEO dataflow/series keys elsewhere.

IMPORTANT — canonical indicator codes are OWNER-APPROVED:
GOVERNMENT_DEBT_GDP is part of the seeded 25-indicator catalog
(app/db/seed.py) and its SourceSeries is seeded from this module. DEC-008
requires a general-government gross debt concept; the rejected World Bank
central-government series (GC.DOD.TOTL.GD.ZS) is NOT used.

External identity design (same principles as BIS/OECD):
- agency_id + dataflow_id identify the dataset. The dataflow version is
  requested as "+" (latest WEO vintage) at fetch time; the actual version
  (e.g. "9.0.0") is captured from the response structure and stored in
  raw_payload for provenance.
- sdmx_key_template is the country-independent SDMX key, with {cc} as the
  placeholder for the IMF COUNTRY dimension (ISO3, identical to Atlas ISO3
  for all 8 tracked countries). SourceSeries is shared across countries
  (Country lives on Observation), so the stored external identity must stay
  country-independent.
- external_code = "{dataflow_id}/{sdmx_key_template}". The IMF COUNTRY
  dimension uses ISO3 codes identical to Big Cycle Atlas ISO3 codes for all
  8 tracked countries, so {cc} resolves 1:1 with no alias needed.

WEO-specific semantics:
- WEO is released twice yearly (April and October). The dataflow version
  corresponds to the WEO vintage.
- Historical data and projections are mixed in the same series. The
  LATEST_ACTUAL_ANNUAL_DATA attribute marks the last actual year; any year
  after that is a forecast and MUST be excluded from Atlas observations.
- For fiscal-year countries (e.g. IND), LATEST_ACTUAL_ANNUAL_DATA may be a
  fiscal-year label like "FY2024/25" — the adapter parses the ending calendar
  year to determine the boundary.
- No transformation is applied. The raw provider value (percent of GDP) is
  stored unchanged.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ImfWeoMapping:
    indicator_code: str
    agency_id: str
    dataflow_id: str
    sdmx_key_template: str
    external_code: str
    external_name: str
    external_unit: str
    frequency: str
    transform_notes: str
    source_key: str = "imf"


GOVERNMENT_DEBT_GDP = ImfWeoMapping(
    indicator_code="GOVERNMENT_DEBT_GDP",
    agency_id="IMF.RES",
    dataflow_id="WEO",
    sdmx_key_template="{cc}.GGXWDG_NGDP.A",
    external_code="WEO/{cc}.GGXWDG_NGDP.A",
    external_name="General government gross debt (% of GDP)",
    external_unit="percent of GDP",
    frequency="annual",
    transform_notes=(
        "IMF WEO GGXWDG_NGDP: general government gross debt as percent "
        "of GDP. General government covers central, state, local, and "
        "social security funds (GFSM 2001 concept). DEC-008 requires this "
        "general-government concept; the World Bank central-government "
        "series (GC.DOD.TOTL.GD.ZS) is NOT a substitute. WEO mixes "
        "historical actuals and projections in one series; the adapter "
        "uses LATEST_ACTUAL_ANNUAL_DATA to exclude forecast years. The "
        "raw provider value is stored unchanged — no transformation."
    ),
)

IMF_WEO_MAPPINGS: tuple[ImfWeoMapping, ...] = (GOVERNMENT_DEBT_GDP,)

# IMF WEO COUNTRY dimension uses ISO3 codes. Verified 2026-09-10 against
# actual data responses for all 8 tracked countries. Identity mapping.
IMF_COUNTRY_BY_ISO3: dict[str, str] = {
    "USA": "USA",
    "CHN": "CHN",
    "CHE": "CHE",
    "DEU": "DEU",
    "FRA": "FRA",
    "GBR": "GBR",
    "JPN": "JPN",
    "IND": "IND",
}

_MAPPING_BY_INDICATOR_CODE = {m.indicator_code: m for m in IMF_WEO_MAPPINGS}
_MAPPING_BY_EXTERNAL_CODE = {m.external_code: m for m in IMF_WEO_MAPPINGS}


def get_imf_weo_mapping(indicator_code: str) -> ImfWeoMapping | None:
    return _MAPPING_BY_INDICATOR_CODE.get(indicator_code)


def get_imf_weo_mapping_by_external_code(external_code: str) -> ImfWeoMapping | None:
    """Reverse lookup: IMF WEO external identity → canonical indicator mapping."""
    return _MAPPING_BY_EXTERNAL_CODE.get(external_code)
