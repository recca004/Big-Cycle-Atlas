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
    "alfred_fred": ProviderReleaseMetadata(
        source_key="alfred_fred",
        provider="ALFRED / FRED",
        has_release_dates=True,
        has_revision_dates=True,
        has_vintage_history=True,
        publication_calendar="Official realtime_start/realtime_end vintage "
            "evidence via the FRED API.",
        historical_archive="ALFRED historical vintages are first-class API "
            "output.",
        assumed_lag_days=None,
        notes="Implemented adapter; BCA_FRED_API_KEY is required and "
            "currently unconfigured.",
    ),
    "jst_macrohistory": ProviderReleaseMetadata(
        source_key="jst_macrohistory",
        provider="Jorda-Schularick-Taylor Macrohistory Database",
        has_release_dates=True,
        has_revision_dates=False,
        has_vintage_history=True,
        publication_calendar="Discrete dataset release (R6, July 2022), not "
            "per-observation publication dates.",
        historical_archive="Official R6 workbook; later releases are distinct "
            "dataset versions.",
        assumed_lag_days=None,
        notes="Dataset-release evidence only; values must not be treated as "
            "known in their historical year.",
    ),
    "imf_cofer": ProviderReleaseMetadata(
        source_key="imf_cofer",
        provider="IMF COFER (SDMX 2.1)",
        has_release_dates=True,
        has_revision_dates=False,
        has_vintage_history=False,
        publication_calendar="Quarterly COFER release ~3 months after reference quarter; "
            "SDMX feed includes dataset PUBLICATION_DATE, not historical point-in-time vintages.",
        historical_archive="IMF revised 2000Q1+ series in December 2025 to impute formerly unallocated reserves.",
        assumed_lag_days=95,
        notes="Dataset publication timestamp only; not historical vintage evidence.",
    ),
    "bis_fx_turnover": ProviderReleaseMetadata(
        source_key="bis_fx_turnover",
        provider="BIS Triennial Central Bank Survey (WS_DER_OTC_TOV)",
        has_release_dates=False,
        has_revision_dates=False,
        has_vintage_history=False,
        publication_calendar="Triennial April survey published ~September/December of survey year.",
        historical_archive=None,
        assumed_lag_days=240,
        notes="No per-observation release timestamp in SDMX feed.",
    ),
    "bis_lbs": ProviderReleaseMetadata(
        source_key="bis_lbs",
        provider="BIS Locational Banking Statistics (WS_LBS_D_PUB)",
        has_release_dates=False,
        has_revision_dates=False,
        has_vintage_history=False,
        publication_calendar="Quarterly cross-border banking statistics lag ~4 months.",
        historical_archive=None,
        assumed_lag_days=135,
        notes="No per-observation release timestamp in SDMX feed.",
    ),
    "bis_credit_policy": ProviderReleaseMetadata(
        source_key="bis_credit_policy",
        provider="BIS Total Credit & Policy Rates (WS_TC / WS_CBPOL)",
        has_release_dates=False,
        has_revision_dates=False,
        has_vintage_history=False,
        publication_calendar="WS_TC lags ~5 months; WS_CBPOL updates monthly.",
        historical_archive=None,
        assumed_lag_days=150,
        notes="Retrospective latest SDMX series; no vintage timestamps.",
    ),
    "pwt": ProviderReleaseMetadata(
        source_key="pwt",
        provider="Penn World Table 11.0 (GGDC)",
        has_release_dates=True,
        has_revision_dates=False,
        has_vintage_history=True,
        publication_calendar="Discrete academic release (PWT 11.0 published 2025-10-07).",
        historical_archive="Prior PWT editions (8.0–10.01) archived on DataverseNL with distinct PPP benchmarks.",
        assumed_lag_days=None,
        notes="Dataset-release evidence only; retrospective 2021 PPP benchmark.",
    ),
    "maddison": ProviderReleaseMetadata(
        source_key="maddison",
        provider="Maddison Project Database 2023 (GGDC)",
        has_release_dates=True,
        has_revision_dates=False,
        has_vintage_history=True,
        publication_calendar="Discrete academic release (MPD 2023).",
        historical_archive="MPD 2018/2020/2023 editions archived on DataverseNL.",
        assumed_lag_days=None,
        notes="Dataset-release evidence only; reconstructed historical estimates in 2011 international dollars.",
    ),
}


def assumed_lag_days(source_key: str) -> int | None:
    meta = PROVIDER_RELEASE_METADATA.get(source_key)
    return meta.assumed_lag_days if meta else None
