"""Central mapping of canonical Big Cycle Atlas indicators to BIS dataflows.

Every external identity here was verified against the official BIS Stats API
v1 (https://stats.bis.org/api-doc/v1/) on 2026-09-08. Data query:
GET {base}/data/{dataflow}/{key}/all?format=csv — SDMX-CSV with TIME_PERIOD
("YYYY-QN") and OBS_VALUE columns. The adapter and any future seed both
consume this module — do not scatter BIS dataflow/series keys elsewhere.

IMPORTANT — canonical indicator codes are OWNER-APPROVED (2026-09-08):
CREDIT_TO_GDP_GAP and DEBT_SERVICE_RATIO are part of the seeded 17-indicator
catalog (app/db/seed.py) and their SourceSeries are seeded from this module.

External identity design:
- dataflow_id identifies the BIS dataflow (e.g. WS_CREDIT_GAP). The dataflow
  alone is NOT a series identity: WS_CREDIT_GAP carries the ratio
  (CG_DTYPE=A), trend (CG_DTYPE=B) and gap (CG_DTYPE=C) series families,
  which map to different indicators.
- sdmx_key_template is the country-independent SDMX series key, with {cc} as
  the placeholder for the BIS ISO2 borrower-country code. SourceSeries is
  shared across countries in Big Cycle Atlas (Country lives on Observation),
  so the stored external identity must stay country-independent.
- external_code = "{dataflow_id}/{sdmx_key_template}" — embedding the key
  template prevents future collisions when more series families are mapped.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class BisMapping:
    indicator_code: str
    dataflow_id: str
    sdmx_key_template: str
    external_code: str
    external_name: str
    external_unit: str
    transform_notes: str
    # (column, expected value) pairs validated against every returned CSV row.
    # Columns absent from a response's header are skipped, so both BIS column
    # namings (DSR_BORROWERS vs TC_BORROWERS) can be covered.
    expected_dims: tuple[tuple[str, str], ...] = ()
    source_key: str = "bis"


CREDIT_TO_GDP_GAP = BisMapping(
    indicator_code="CREDIT_TO_GDP_GAP",
    dataflow_id="WS_CREDIT_GAP",
    sdmx_key_template="Q.{cc}.P.A.C",
    external_code="WS_CREDIT_GAP/Q.{cc}.P.A.C",
    external_name="Credit-to-GDP gap (private non-financial sector)",
    external_unit="percentage of GDP",
    transform_notes=(
        "BIS published gap (CG_DTYPE=C): credit-to-GDP ratio (CG_DTYPE=A) "
        "minus its one-sided Hodrick-Prescott long-run trend (CG_DTYPE=B). "
        "Use the published gap value — never recompute locally. Only the C "
        "family is mapped; A and B live in the same dataflow."
    ),
    expected_dims=(
        ("FREQ", "Q"),
        ("TC_BORROWERS", "P"),
        ("TC_LENDERS", "A"),
        ("CG_DTYPE", "C"),
    ),
)

DEBT_SERVICE_RATIO = BisMapping(
    indicator_code="DEBT_SERVICE_RATIO",
    dataflow_id="WS_DSR",
    sdmx_key_template="Q.{cc}.P",
    external_code="WS_DSR/Q.{cc}.P",
    external_name="Debt service ratio (private non-financial sector)",
    external_unit="per cent",
    transform_notes=(
        "Debt-service payments (interest + amortisation) as a proportion of "
        "income, total private non-financial sector (P). BIS methodological "
        "caution: DSR level comparisons across countries are less meaningful "
        "than changes relative to each country's own history — normalize "
        "within-country, not across countries."
    ),
    expected_dims=(
        ("FREQ", "Q"),
        ("DSR_BORROWERS", "P"),
        ("TC_BORROWERS", "P"),
    ),
)

BIS_MAPPINGS: tuple[BisMapping, ...] = (CREDIT_TO_GDP_GAP, DEBT_SERVICE_RATIO)

# BIS series keys identify countries by ISO2 codes (verified: 'US' matches,
# 'USA' 404s). Only the tracked countries need mappings; missing coverage is
# legitimate and never coerced.
BIS_ISO2_BY_ISO3: dict[str, str] = {
    "USA": "US",
    "CHN": "CN",
    "CHE": "CH",
    "DEU": "DE",
    "FRA": "FR",
    "GBR": "GB",
    "JPN": "JP",
    "IND": "IN",
}

_MAPPING_BY_INDICATOR_CODE = {m.indicator_code: m for m in BIS_MAPPINGS}
_MAPPING_BY_EXTERNAL_CODE = {m.external_code: m for m in BIS_MAPPINGS}


def get_bis_mapping(indicator_code: str) -> BisMapping | None:
    return _MAPPING_BY_INDICATOR_CODE.get(indicator_code)


def get_bis_mapping_by_external_code(external_code: str) -> BisMapping | None:
    """Reverse lookup: BIS external identity → canonical indicator mapping."""
    return _MAPPING_BY_EXTERNAL_CODE.get(external_code)