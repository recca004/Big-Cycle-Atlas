"""Create tables and seed the initial country set, data sources, and indicators.

Run from apps/api with the virtual environment active:

    python -m app.db.seed

Reads the canonical country list from packages/shared/data/initial-countries.json
(DEC-004). Idempotent: existing countries are updated, missing ones inserted.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from enum import Enum

if asyncio.get_event_loop_policy().__class__.__name__ == "WindowsProactorEventLoopPolicy":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import Base
from app.db.session import get_engine
from app.data_sources.bis_mappings import BIS_MAPPINGS
from app.data_sources.imf_weo_mappings import IMF_WEO_MAPPINGS
from app.data_sources.oecd_mappings import OECD_MAPPINGS
from app.data_sources.wid_mappings import WID_MAPPINGS
from app.data_sources.world_bank_mappings import WORLD_BANK_MAPPINGS
from app.services.scientific_foundation import seed_scientific_foundation
from app.models import (
    Country,
    DataSource,
    Indicator,
    SourceSeries,
    DataSourceStatus,
    IndicatorStrengthDirection,
)


DEFAULT_DATA_FILE = Path(
    os.environ.get(
        "BCA_SEED_FILE",
        str(
            Path(__file__).resolve().parents[4]
            / "packages" / "shared" / "data" / "initial-countries.json"
        ),
    )
)


async def seed(data_file: Path = DEFAULT_DATA_FILE) -> None:
    engine = get_engine()

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # 1. Seed Countries
        payload = json.loads(data_file.read_text(encoding="utf-8"))
        countries_data = [
            Country(iso3=row["iso3"], iso2=row["iso2"], name=row["name"], region=row["region"])
            for row in payload["countries"]
        ]

        existing_countries = {
            c.iso3: c
            for c in (await session.execute(select(Country))).scalars().all()
        }
        inserted_countries = 0
        updated_countries = 0
        for c_data in countries_data:
            current = existing_countries.get(c_data.iso3)
            if current is None:
                session.add(c_data)
                inserted_countries += 1
            else:
                current.iso2 = c_data.iso2
                current.name = c_data.name
                current.region = c_data.region
                updated_countries += 1

        # 2. Seed Data Sources
        sources_data = [
            {"key": "world_bank", "name": "World Bank", "status": DataSourceStatus.active, "base_url": "https://api.worldbank.org/v2", "update_frequency": "daily", "documentation_url": "https://datahelpdesk.worldbank.org/knowledgebase/articles/898581", "rate_limit_notes": "Public API; bounded retries and failure isolation handled by the unified updater."},
            {"key": "bis", "name": "Bank for International Settlements", "status": DataSourceStatus.active, "base_url": "https://stats.bis.org/api/v2", "update_frequency": "daily", "documentation_url": "https://stats.bis.org/", "rate_limit_notes": "Public SDMX API; bounded retries and failure isolation handled by the unified updater."},
            {"key": "oecd", "name": "OECD", "status": DataSourceStatus.active, "base_url": "https://sdmx.oecd.org/public/rest", "update_frequency": "daily", "documentation_url": "https://sdmx.oecd.org/", "rate_limit_notes": "OECD request budget and one bounded 429 retry are enforced by collection code."},
            {"key": "imf", "name": "International Monetary Fund", "status": DataSourceStatus.active, "base_url": "https://api.imf.org", "update_frequency": "semi-annual", "documentation_url": "https://www.imf.org/external/datamapper/api/help", "rate_limit_notes": "WEO provider updates are less frequent; failures remain isolated."},
            {"key": "fred", "name": "Federal Reserve Economic Data (FRED)", "status": DataSourceStatus.planned},
            {"key": "alfred_fred", "name": "ALFRED / FRED historical vintages", "status": DataSourceStatus.planned, "base_url": "https://api.stlouisfed.org/fred", "update_frequency": "manual historical vintage import", "documentation_url": "https://fred.stlouisfed.org/docs/api/fred/alfred.html", "rate_limit_notes": "Requires BCA_FRED_API_KEY; no key is stored in the repository."},
            {"key": "jst_macrohistory", "name": "Jordà-Schularick-Taylor Macrohistory Database", "status": DataSourceStatus.active, "base_url": "https://www.macrohistory.net/database/", "update_frequency": "manual historical dataset release", "documentation_url": "https://www.macrohistory.net/database/", "rate_limit_notes": "Manual bulk historical import; CC BY-NC-SA 4.0."},
            {"key": "imf_laeven_valencia_banking_crises", "name": "IMF Laeven-Valencia Systemic Banking Crises", "status": DataSourceStatus.planned, "base_url": "https://www.imf.org/en/publications/wp/issues/2026/05/14/systemic-banking-crises-database-1970-2025-576036", "update_frequency": "manual dataset release", "documentation_url": "https://www.imf.org/en/publications/wp/issues/2026/05/14/systemic-banking-crises-database-1970-2025-576036", "rate_limit_notes": "Official supplemental ZIP currently unavailable; local-bundle importer is supported."},
            {"key": "eurostat", "name": "Eurostat", "status": DataSourceStatus.planned},
            {"key": "ecb", "name": "European Central Bank", "status": DataSourceStatus.planned},
            {"key": "snb", "name": "Swiss National Bank", "status": DataSourceStatus.planned},
            {"key": "un_comtrade", "name": "UN Comtrade", "status": DataSourceStatus.planned},
            {"key": "wid", "name": "World Inequality Database (WID)", "status": DataSourceStatus.active, "update_frequency": "manual bulk file", "documentation_url": "https://wid.world/", "rate_limit_notes": "Optional local bulk archive only; never auto-downloaded by the unified updater."},
        ]

        existing_sources = {
            s.key: s
            for s in (await session.execute(select(DataSource))).scalars().all()
        }
        inserted_sources = 0
        updated_sources = 0
        for s_data in sources_data:
            current = existing_sources.get(s_data["key"])
            if current is None:
                session.add(DataSource(**s_data))
                inserted_sources += 1
            else:
                for field in (
                    "name", "status", "base_url", "update_frequency",
                    "rate_limit_notes", "documentation_url",
                ):
                    setattr(current, field, s_data.get(field))
                updated_sources += 1

        await seed_scientific_foundation(session)

        # 3. Seed Indicators
        indicators_data = [
            {"code": "GDP_GROWTH", "name": "GDP Growth", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "GDP_CURRENT_USD", "name": "GDP (Current USD)", "category": "Economy", "unit": "USD", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "GDP_PER_CAPITA", "name": "GDP Per Capita", "category": "Economy", "unit": "USD", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "INFLATION_CPI", "name": "Inflation (CPI)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.contextual, "description": "Annual average consumer price inflation (annual %). Frequency corrected from the aspirational 'monthly' placeholder to 'annual' to match the verified World Bank series FP.CPI.TOTL.ZG (2026-09-08, Milestone 5.3)."},
            {"code": "UNEMPLOYMENT_RATE", "name": "Unemployment Rate (ILO modeled)", "category": "Economy", "unit": "percent of labor force", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.negative},
            {"code": "EXPORTS_GDP", "name": "Exports (% of GDP)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "IMPORTS_GDP", "name": "Imports (% of GDP)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.negative},
            {"code": "TRADE_BALANCE", "name": "Trade Balance (% of GDP)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "REER_INDEX", "name": "Real effective exchange rate index (2010=100)", "category": "Economy", "unit": "index", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.negative, "description": "World Bank PX.REX.REER. WB convention: RISING index = real appreciation = DECLINING price competitiveness. Appreciation is not automatically bad (productivity Balassa-Samuelson); depreciation is not automatically good. Direction is context, never auto-scored."},
            {"code": "BROADBAND_PER_100", "name": "Fixed broadband subscriptions (per 100 people)", "category": "Infrastructure", "unit": "per 100 people", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank IT.NET.BBND.P2. Digital-infrastructure context — coverage not quality."},
            {"code": "FDI_NET_INFLOWS_GDP", "name": "Foreign direct investment, net inflows (% of GDP)", "category": "Economy", "unit": "percent of GDP", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank BX.KLT.DINV.WD.GD.ZS: net FDI inflows as % of GDP. Capital-attraction input for the trade/capital-flows research module — not a standalone score."},
            {"code": "CURRENT_ACCOUNT_GDP", "name": "Current Account (% of GDP)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "GROSS_CAPITAL_FORMATION_GDP", "name": "Gross Capital Formation (% of GDP)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "GOVERNMENT_DEBT_GDP", "name": "Government Debt (% of GDP)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.negative},
            {"code": "POPULATION", "name": "Population", "category": "Demographics", "unit": "count", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "TERTIARY_ENROLLMENT", "name": "Tertiary Enrollment (% gross)", "category": "Human Capital", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "SECONDARY_ENROLLMENT", "name": "Secondary Enrollment (% gross)", "category": "Human Capital", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "RND_EXPENDITURE_GDP", "name": "R&D Expenditure (% of GDP)", "category": "Human Capital", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "CREDIT_TO_GDP_GAP", "name": "Credit-to-GDP gap (private non-financial sector)", "category": "Debt & Credit", "unit": "percentage of GDP", "frequency": "quarterly", "strength_direction": IndicatorStrengthDirection.contextual, "description": "BIS-published gap between the private non-financial sector credit-to-GDP ratio and its long-run trend."},
            {"code": "DEBT_SERVICE_RATIO", "name": "Debt service ratio (private non-financial sector)", "category": "Debt & Credit", "unit": "per cent", "frequency": "quarterly", "strength_direction": IndicatorStrengthDirection.contextual, "description": "Debt-service payments as a proportion of income for the private non-financial sector."},
            {"code": "LABOUR_PRODUCTIVITY_PER_HOUR", "name": "Labour productivity — GDP per hour worked", "category": "Productivity", "unit": "US dollars per hour, PPP converted", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "NATURAL_DISASTER_AFFECTED_PCT", "name": "Population affected by natural disasters (% of population)", "category": "Natural Hazards", "unit": "percent of population", "frequency": "multi-decadal", "strength_direction": IndicatorStrengthDirection.contextual, "description": "World Bank EN.CLC.MDAT.ZS (EM-DAT-derived): annual average % of population affected by droughts, floods or extreme-temperature events, averaged over 1990-2009 and published at date 2009. A structural EXPOSURE context measure — not an annual event count, not an Atlas score."},
            {"code": "UNIT_LABOUR_COST_GROWTH", "name": "Unit labour cost growth", "category": "Cost Competitiveness", "unit": "percent per annum", "frequency": "quarterly", "strength_direction": IndicatorStrengthDirection.contextual, "description": "Year-over-year employment-based unit labour cost growth, seasonally adjusted."},
            {"code": "RULE_OF_LAW_WGI_SCORE", "name": "Rule of Law — WGI governance score", "category": "Governance", "unit": "score 0-100", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank WGI (2025 revision) Rule of Law absolute governance score, 0-100. Perception-based composite; larger = better governance."},
            {"code": "CONTROL_OF_CORRUPTION_WGI_SCORE", "name": "Control of Corruption — WGI governance score", "category": "Governance", "unit": "score 0-100", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank WGI (2025 revision) Control of Corruption absolute governance score, 0-100. Higher = stronger control of corruption / less corruption; the raw value is never reversed."},
            {"code": "POLITICAL_STABILITY_WGI_SCORE", "name": "Political Stability — WGI governance score", "category": "Governance", "unit": "score 0-100", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank WGI (2025 revision) Political Stability and Absence of Violence/Terrorism absolute governance score, 0-100. Perception-based composite; larger = more stable."},
            {"code": "GOVERNMENT_EFFECTIVENESS_WGI_SCORE", "name": "Government Effectiveness — WGI governance score", "category": "Governance", "unit": "score 0-100", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank WGI (2025 revision) Government Effectiveness absolute governance score, 0-100. Quality of public services, civil service, policy formulation and implementation. Perception-based composite; larger = more effective government."},

            {"code": "GDP_PPP_CURRENT_INTL", "name": "GDP, PPP (current international $)", "category": "Economy", "unit": "current international $", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank NY.GDP.MKTP.PP.CD. PPP output measure; method/base-year specific and not mixed with other PPP bases."},
            {"code": "GDP_REAL_CONSTANT_USD", "name": "GDP (constant 2015 US$)", "category": "Economy", "unit": "constant 2015 US$", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank NY.GDP.MKTP.KD. Constant-price real GDP volume, fixed WDI 2015 base year."},
            {"code": "MERCHANDISE_EXPORTS_USD", "name": "Merchandise exports (current US$)", "category": "International Power", "unit": "current US$", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank TX.VAL.MRCH.CD.WT. Goods exports only; denominator-safe for global goods-export share."},
            {"code": "MERCHANDISE_IMPORTS_USD", "name": "Merchandise imports (current US$)", "category": "International Power", "unit": "current US$", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank TM.VAL.MRCH.CD.WT. Goods imports only; denominator-safe for global goods-import share."},
            {"code": "COMMERCIAL_SERVICE_EXPORTS_USD", "name": "Commercial service exports (current US$)", "category": "International Power", "unit": "current US$", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank TX.VAL.SERV.CD.WT. Commercial services excluding government services n.i.e."},
            {"code": "COMMERCIAL_SERVICE_IMPORTS_USD", "name": "Commercial service imports (current US$)", "category": "International Power", "unit": "current US$", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank TM.VAL.SERV.CD.WT. Commercial services excluding government services n.i.e."},
            {"code": "PATENT_APPLICATIONS_RESIDENT", "name": "Patent applications, residents", "category": "Innovation", "unit": "applications", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "WIPO via World Bank IP.PAT.RESD. Filing count is an innovation-output proxy, not patent quality."},
            {"code": "PATENT_APPLICATIONS_NONRESIDENT", "name": "Patent applications, nonresidents", "category": "Innovation", "unit": "applications", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.contextual, "description": "WIPO via World Bank IP.PAT.NRES. Foreign filing interest proxy; not a domestic invention count."},
            {"code": "RESEARCHERS_PER_MILLION", "name": "Researchers in R&D (per million people)", "category": "Innovation", "unit": "per million people", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "UNESCO via World Bank SP.POP.SCIE.RD.P6. Research-capacity density; not output or quality."},
            {"code": "HIGH_TECHNOLOGY_EXPORTS_USD", "name": "High-technology exports (current US$)", "category": "Innovation", "unit": "current US$", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank TX.VAL.TECH.CD. High-R&D-intensity product exports; classification and assembly effects apply."},
            {"code": "STOCK_MARKET_CAP_GDP", "name": "Market capitalization of listed domestic companies (% of GDP)", "category": "Financial Influence", "unit": "% of GDP", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.contextual, "description": "World Bank CM.MKT.LCAP.GD.ZS. Domestic listed-market depth; not an international financial-centre score."},
            {"code": "DOMESTIC_CREDIT_PRIVATE_GDP", "name": "Domestic credit to private sector (% of GDP)", "category": "Financial Influence", "unit": "% of GDP", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.contextual, "description": "World Bank FS.AST.PRVT.GD.ZS. Financial-system depth; separate from international banking and reserve status."},
            {"code": "BROAD_MONEY_GDP", "name": "Broad money (% of GDP)", "category": "Financial Influence", "unit": "% of GDP", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.contextual, "description": "World Bank FM.LBL.BMNY.GD.ZS. Monetary-system depth; not reserve status or international intermediation."},
            {"code": "GINI_INDEX", "name": "Gini index", "category": "Inequality", "unit": "index (0-100)", "frequency": "irregular", "strength_direction": IndicatorStrengthDirection.negative, "description": "World Bank Gini index (SI.POV.GINI): extent to which the income/consumption distribution deviates from perfect equality (0 = perfect equality, 100 = perfect inequality). Published irregularly; missing years are gaps, never zeros or forward-filled. Higher = more inequality."},
            {"code": "MILITARY_EXPENDITURE_USD", "name": "Military expenditure", "category": "Military", "unit": "current US$", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.contextual, "description": "Annual military expenditure in current US dollars, as published through World Bank WDI using SIPRI data (MS.MIL.XPND.CD; underlying source: SIPRI Military Expenditure Database). Input proxy for military strength, not a capability measure."},
            {"code": "MILITARY_EXPENDITURE_GDP", "name": "Military expenditure (% of GDP)", "category": "Military", "unit": "percent of GDP", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.contextual, "description": "Military expenditure as a share of GDP, as published through World Bank WDI using SIPRI data (MS.MIL.XPND.GD.ZS; underlying source: SIPRI Military Expenditure Database). Input proxy for military strength, not a capability measure."},
            {"code": "TERTIARY_ATTAINMENT_25_34", "name": "Tertiary educational attainment, age 25-34", "category": "Human Capital", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "OECD EAG LSO NEAC: percentage of 25-34 year-olds with tertiary education (ISCED 5-8). Attainment != enrollment. CHN/IND have sparse coverage."},
            {"code": "LABOUR_FORCE_PARTICIPATION_RATE", "name": "Labour force participation rate, total (% ages 15+)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank SL.TLF.CACT.ZS (modeled ILO estimate): proportion of the population ages 15+ that is economically active. Economic participation input — not a measure of national character."},
            {"code": "WEALTH_SHARE_TOP_10", "name": "Top 10% net personal wealth share", "category": "Inequality", "unit": "share (0-1)", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.negative, "description": "WID world shwealj992 p90p100: top 10% share of net personal wealth (equal-split adults, pop=j). Raw provider fraction preserved unchanged (0-1). Higher = greater wealth concentration."},
        ]

        existing_indicators = {
            i.code: i
            for i in (await session.execute(select(Indicator))).scalars().all()
        }
        inserted_indicators = 0
        updated_indicators = 0
        for i_data in indicators_data:
            current = existing_indicators.get(i_data["code"])
            if current is None:
                session.add(Indicator(**i_data))
                inserted_indicators += 1
            else:
                current.name = i_data["name"]
                current.description = i_data.get("description")
                current.category = i_data.get("category")
                current.unit = i_data.get("unit")
                current.frequency = i_data.get("frequency")
                current.strength_direction = i_data["strength_direction"]
                updated_indicators += 1

        await session.commit()

        # 4. Seed SourceSeries (canonical indicator → external source mappings)
        sources_by_key = {
            s.key: s
            for s in (await session.execute(select(DataSource))).scalars().all()
        }
        indicators_by_code = {
            i.code: i
            for i in (await session.execute(select(Indicator))).scalars().all()
        }
        existing_series = {
            (s.data_source_id, s.indicator_id): s
            for s in (await session.execute(select(SourceSeries))).scalars().all()
        }
        inserted_series = 0
        updated_series = 0
        all_mappings = [*WORLD_BANK_MAPPINGS, *BIS_MAPPINGS, *OECD_MAPPINGS, *IMF_WEO_MAPPINGS, *WID_MAPPINGS]
        for mapping in all_mappings:
            source = sources_by_key[mapping.source_key]
            indicator = indicators_by_code[mapping.indicator_code]
            key = (source.id, indicator.id)
            current = existing_series.get(key)
            if current is None:
                session.add(
                    SourceSeries(
                        data_source_id=source.id,
                        indicator_id=indicator.id,
                        external_code=mapping.external_code,
                        external_name=mapping.external_name,
                        external_unit=mapping.external_unit,
                        transform_notes=mapping.transform_notes,
                        is_active=True,
                    )
                )
                inserted_series += 1
            else:
                current.external_code = mapping.external_code
                current.external_name = mapping.external_name
                current.external_unit = mapping.external_unit
                current.transform_notes = mapping.transform_notes
                updated_series += 1

        await session.commit()

        print(f"Countries seeded: {inserted_countries} inserted, {updated_countries} updated, {len(countries_data)} total in file")
        print(f"Data sources seeded: {inserted_sources} inserted, {updated_sources} updated, {len(sources_data)} total")
        print(f"Indicators seeded: {inserted_indicators} inserted, {updated_indicators} updated, {len(indicators_data)} total")
        print(f"Source series seeded: {inserted_series} inserted, {updated_series} updated, {len(all_mappings)} mapped")


if __name__ == "__main__":
    asyncio.run(seed())
