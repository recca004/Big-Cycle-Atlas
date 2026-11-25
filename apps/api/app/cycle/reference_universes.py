"""Versioned calibration reference universes (DEC-042, Sprint 6.14).

A reference universe is a NAMED, VERSIONED population of countries whose
observations form the calibration distribution for a REFERENCE_PERCENTILE
level score. Membership is frozen per universe version: changing the member
set requires a new universe code, so a growing provider dataset can never
silently create artificial historical momentum in already-published scores.

Calibration is PERIOD-SPECIFIC: for scoring period P the distribution is the
set of universe members with an observation at exactly P (no interpolation,
no carry-forward — a member missing P simply drops out of that period's
distribution). If fewer than `minimum_sample_n` members report at P, the
period's distribution is unusable and the indicator produces NO level score
for P — never a partial-sample score pretending to be complete.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ReferenceUniverse:
    """A named, versioned calibration population."""

    universe_code: str  # e.g. "oecd_lpph_v1" — immutable once ingested
    indicator_code: str
    source_key: str
    external_code: str  # the country-independent source identity
    expected_member_iso3: frozenset[str]  # members expected to report data
    description: str


# DEC-042 Option A: full OECD membership for labour productivity per hour
# (DF_PDB GDPHRS, USD PPP per hour, chain-linked volume, annual). Expected
# members = the 38 OECD member states (ISO3 REF_AREA codes); actual usable
# membership is whatever the provider returns — Colombia/Costa Rica joined
# OECD in 2020/2021 and may have shorter series, which is handled per-period
# by the minimum-sample gate rather than by freezing membership.
OECD_LPPH_V1 = ReferenceUniverse(
    universe_code="oecd_lpph_v1",
    indicator_code="LABOUR_PRODUCTIVITY_PER_HOUR",
    source_key="oecd",
    external_code="DSD_PDB@DF_PDB/{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP",
    expected_member_iso3=frozenset({
        "AUS", "AUT", "BEL", "CAN", "CHE", "CHL", "COL", "CRI", "CZE", "DEU",
        "DNK", "ESP", "EST", "FIN", "FRA", "GBR", "GRC", "HUN", "IRL", "ISL",
        "ISR", "ITA", "JPN", "KOR", "LTU", "LUX", "LVA", "MEX", "NLD", "NOR",
        "NZL", "POL", "PRT", "SVK", "SVN", "SWE", "TUR", "USA",
    }),
    description=(
        "Full OECD membership, labour productivity per hour worked "
        "(GDP per hour, USD constant PPP, chain-linked). Calibration "
        "distribution for DEC-042 Option A — OECD reference percentile, "
        "never a global/world percentile: CHN and IND are not OECD members "
        "and therefore have no OECD-calibrated level (they receive "
        "unavailable, not a fabricated score)."
    ),
)

# V1 Mission 1 (delegated working model): the full WDI country universe for
# labour force participation. Membership is NOT hardcoded — it is the set of
# real WB economies (country catalog, region != aggregate) that reported
# data at the ingest vintage; the stored rows ARE the frozen membership for
# this universe version (re-ingestion writes new vintages, never members).
# expected_member_iso3 stays empty: membership is defined by the ingested
# rows, and the minimum-sample gate protects thin periods.
WDI_LFP_V1 = ReferenceUniverse(
    universe_code="wdi_lfp_v1",
    indicator_code="LABOUR_FORCE_PARTICIPATION_RATE",
    source_key="world_bank",
    external_code="SL.TLF.CACT.ZS",
    expected_member_iso3=frozenset(),
    description=(
        "All WDI economies (aggregates excluded), labour force "
        "participation rate ages 15+ (ILO modeled). World reference "
        "distribution for the economic-participation proxy of "
        "character_determination — a participation measure, never a "
        "judgment of national character."
    ),
)

REFERENCE_UNIVERSES: dict[str, ReferenceUniverse] = {
    OECD_LPPH_V1.universe_code: OECD_LPPH_V1,
    WDI_LFP_V1.universe_code: WDI_LFP_V1,
}


def get_reference_universe(universe_code: str) -> ReferenceUniverse | None:
    return REFERENCE_UNIVERSES.get(universe_code)


def midrank_percentile(value: float, distribution: list[float]) -> float:
    """Mid-rank percentile of `value` within `distribution`, 0-100.

    Plotting position 100 * (n_below + 0.5 * n_ties) / n — the same mid-rank
    convention as the tracked_8 relative scorer (DEC-017): ties share the
    average rank, so equal values score equal percentiles and no member can
    ever reach exactly 0 or 100.
    """
    n = len(distribution)
    if n == 0:
        raise ValueError("midrank_percentile requires a non-empty distribution")
    n_below = sum(1 for v in distribution if v < value)
    n_ties = sum(1 for v in distribution if v == value)
    return 100.0 * (n_below + 0.5 * n_ties) / n
