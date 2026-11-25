"""Geography structural profile — Mission 2 §5.6 (Track I).

A VERSIONED profile of fixed geographical facts per tracked country.
These are structural constants — the module deliberately produces no
annual time series and no invented historical variation.

Facts verified against CIA World Factbook / WB country metadata
conventions (landlocked status, coastline, island status, land area).
Profile version: geo_profile_v1 — a new fact set = a new version, never
silent drift.
"""
from __future__ import annotations

from dataclasses import dataclass

GEO_PROFILE_VERSION = "geo_profile_v1"


@dataclass(frozen=True)
class GeographyFacts:
    iso3: str
    landlocked: bool
    coastline_km: int | None          # None = landlocked
    island_state: bool
    land_area_km2: float | None
    terrain_notes: str
    maritime_access: str              # "open" | "limited" | "landlocked"


GEO_PROFILE_V1: dict[str, GeographyFacts] = {
    "USA": GeographyFacts(
        "USA", landlocked=False, coastline_km=19924, island_state=False,
        land_area_km2=9147420,
        terrain_notes="Two-ocean access, navigable interior waterways",
        maritime_access="open",
    ),
    "CHN": GeographyFacts(
        "CHN", landlocked=False, coastline_km=14500, island_state=False,
        land_area_km2=9326410,
        terrain_notes="Pacific access; concentration on eastern seaboard",
        maritime_access="open",
    ),
    "JPN": GeographyFacts(
        "JPN", landlocked=False, coastline_km=29751, island_state=True,
        land_area_km2=364485,
        terrain_notes="Archipelago; total import dependence on raw materials",
        maritime_access="open",
    ),
    "DEU": GeographyFacts(
        "DEU", landlocked=False, coastline_km=2389, island_state=False,
        land_area_km2=348672,
        terrain_notes="North/Baltic sea access, dense inland network",
        maritime_access="open",
    ),
    "FRA": GeographyFacts(
        "FRA", landlocked=False, coastline_km=4853, island_state=False,
        land_area_km2=640427,
        terrain_notes="Atlantic + Mediterranean access",
        maritime_access="open",
    ),
    "GBR": GeographyFacts(
        "GBR", landlocked=False, coastline_km=12429, island_state=True,
        land_area_km2=241930,
        terrain_notes="Island state; maritime-oriented economy",
        maritime_access="open",
    ),
    "CHE": GeographyFacts(
        "CHE", landlocked=True, coastline_km=None, island_state=False,
        land_area_km2=39997,
        terrain_notes="Landlocked Alpine; Rhine access to North Sea "
                      "via Basel (inland navigation)",
        maritime_access="landlocked",
    ),
    "IND": GeographyFacts(
        "IND", landlocked=False, coastline_km=7000, island_state=False,
        land_area_km2=2973190,
        terrain_notes="Indian Ocean peninsula; long coastline",
        maritime_access="open",
    ),
}


def geography_profile(iso3: str) -> dict | None:
    facts = GEO_PROFILE_V1.get(iso3)
    if facts is None:
        return None
    return {
        "methodology_status": "context_only",
        "profile_version": GEO_PROFILE_VERSION,
        "country_iso3": facts.iso3,
        "landlocked": facts.landlocked,
        "coastline_km": facts.coastline_km,
        "island_state": facts.island_state,
        "land_area_km2": facts.land_area_km2,
        "maritime_access": facts.maritime_access,
        "terrain_notes": facts.terrain_notes,
        "limitations": [
            "Structural facts only — deliberately NOT a score and NOT "
            "time-varying",
            "Sources: CIA World Factbook / WB country metadata conventions",
        ],
    }
