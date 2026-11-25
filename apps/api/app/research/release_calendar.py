"""Provider release-evidence matrix (Mission 4 §21).

Per integrated provider: what publication-date evidence actually exists in
the Atlas — NOT what we wish existed. `has_release_dates` reflects the
current ingestion reality: no connector currently receives provider
release timestamps, so every row is False and `release_date` stays NULL.

`assumed_lag_days` values are RESEARCH ASSUMPTIONS for the
research_assumption execution mode only — estimates of typical provider
lag used to approximate information availability. They are not verified
publication dates and must never be surfaced as such.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderReleaseMetadata:
    source_key: str
    provider: str
    has_release_dates: bool
    has_revision_dates: bool
    has_vintage_history: bool
    publication_calendar: str | None
    historical_archive: str | None
    assumed_lag_days: int | None
    notes: str


PROVIDER_RELEASE_METADATA: dict[str, ProviderReleaseMetadata] = {
    "world_bank": ProviderReleaseMetadata(
        source_key="world_bank",
        provider="World Bank (WDI/WGI)",
        has_release_dates=False,
        has_revision_dates=False,
        has_vintage_history=False,
        publication_calendar="WDI major updates ~April/December; WGI ~October. "
            "The API returns no per-observation publication timestamp.",
        historical_archive="WB keeps archived WDI releases; not ingested.",
        assumed_lag_days=365,
        notes="Annual indicators typically lag ~1 year; WGI estimates are "
            "published the following year. Assumption, not evidence.",
    ),
    "bis": ProviderReleaseMetadata(
        source_key="bis",
        provider="Bank for International Settlements",
        has_release_dates=False,
        has_revision_dates=False,
        has_vintage_history=False,
        publication_calendar="Quarterly series update ~4-5 months after the "
            "reference quarter; no per-series timestamp in the SDMX feed.",
        historical_archive="BIS data warehouse revisions are not versioned "
            "publicly per observation.",
        assumed_lag_days=150,
        notes="DSR / credit-gap series lag roughly one to two quarters. "
            "Assumption, not evidence.",
    ),
    "oecd": ProviderReleaseMetadata(
        source_key="oecd",
        provider="OECD (productivity, labour costs, attainment)",
        has_release_dates=False,
        has_revision_dates=False,
        has_vintage_history=False,
        publication_calendar="Irregular; productivity ~annual with a 1+ "
            "year lag. No per-observation timestamp in the SDMX response.",
        historical_archive=None,
        assumed_lag_days=400,
        notes="Annual productivity and attainment series lag 1-2 years. "
            "Assumption, not evidence.",
    ),
    "imf_weo": ProviderReleaseMetadata(
        source_key="imf_weo",
        provider="IMF World Economic Outlook",
        has_release_dates=False,
        has_revision_dates=False,
        has_vintage_history=True,
        publication_calendar="WEO vintages published ~April and ~October.",
        historical_archive="WEO vintage databases are archived per release; "
            "the Atlas ingests the latest vintage only.",
        assumed_lag_days=200,
        notes="April WEO covers the prior year; October WEO estimates the "
            "current year. Assumption, not evidence.",
    ),
    "wid": ProviderReleaseMetadata(
        source_key="wid",
        provider="World Inequality Database",
        has_release_dates=False,
        has_revision_dates=False,
        has_vintage_history=False,
        publication_calendar="Irregular major updates; no per-observation "
            "publication timestamps.",
        historical_archive=None,
        assumed_lag_days=730,
        notes="Distributional accounts typically lag ~2 years. "
            "Assumption, not evidence.",
    ),
}


def assumed_lag_days(source_key: str) -> int | None:
    meta = PROVIDER_RELEASE_METADATA.get(source_key)
    return meta.assumed_lag_days if meta else None
