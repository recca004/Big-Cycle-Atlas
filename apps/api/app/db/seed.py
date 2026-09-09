"""Create tables and seed the initial country set, data sources, and indicators.

Run from apps/api with the virtual environment active:

    python -m app.db.seed

Reads the canonical country list from packages/shared/data/initial-countries.json
(DEC-004). Idempotent: existing countries are updated, missing ones inserted.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import Base
from app.db.session import get_engine
from app.data_sources.bis_mappings import BIS_MAPPINGS
from app.data_sources.oecd_mappings import OECD_MAPPINGS
from app.data_sources.world_bank_mappings import WORLD_BANK_MAPPINGS
from app.models import (
    Country,
    DataSource,
    Indicator,
    SourceSeries,
    DataSourceStatus,
    IndicatorStrengthDirection,
)


DEFAULT_DATA_FILE = (
    Path(__file__).resolve().parents[4] / "packages" / "shared" / "data" / "initial-countries.json"
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
            {"key": "world_bank", "name": "World Bank"},
            {"key": "bis", "name": "Bank for International Settlements"},
            {"key": "oecd", "name": "OECD"},
            {"key": "fred", "name": "Federal Reserve Economic Data (FRED)"},
            {"key": "eurostat", "name": "Eurostat"},
            {"key": "ecb", "name": "European Central Bank"},
            {"key": "snb", "name": "Swiss National Bank"},
            {"key": "un_comtrade", "name": "UN Comtrade"},
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
                current.name = s_data["name"]
                updated_sources += 1

        # 3. Seed Indicators
        indicators_data = [
            {"code": "GDP_GROWTH", "name": "GDP Growth", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "GDP_CURRENT_USD", "name": "GDP (Current USD)", "category": "Economy", "unit": "USD", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "GDP_PER_CAPITA", "name": "GDP Per Capita", "category": "Economy", "unit": "USD", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "INFLATION_CPI", "name": "Inflation (CPI)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.contextual, "description": "Annual average consumer price inflation (annual %). Frequency corrected from the aspirational 'monthly' placeholder to 'annual' to match the verified World Bank series FP.CPI.TOTL.ZG (2026-09-08, Milestone 5.3)."},
            {"code": "UNEMPLOYMENT_RATE", "name": "Unemployment Rate", "category": "Economy", "unit": "percent", "frequency": "monthly", "strength_direction": IndicatorStrengthDirection.negative},
            {"code": "EXPORTS_GDP", "name": "Exports (% of GDP)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "IMPORTS_GDP", "name": "Imports (% of GDP)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.negative},
            {"code": "TRADE_BALANCE", "name": "Trade Balance (% of GDP)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "CURRENT_ACCOUNT_GDP", "name": "Current Account (% of GDP)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "GROSS_CAPITAL_FORMATION_GDP", "name": "Gross Capital Formation (% of GDP)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "GOVERNMENT_DEBT_GDP", "name": "Government Debt (% of GDP)", "category": "Economy", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.negative},
            {"code": "POPULATION", "name": "Population", "category": "Demographics", "unit": "count", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "TERTIARY_ENROLLMENT", "name": "Tertiary Enrollment (% of age 25-34)", "category": "Human Capital", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "SECONDARY_ENROLLMENT", "name": "Secondary Enrollment (% of age 15-19)", "category": "Human Capital", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "RND_EXPENDITURE_GDP", "name": "R&D Expenditure (% of GDP)", "category": "Human Capital", "unit": "percent", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "CREDIT_TO_GDP_GAP", "name": "Credit-to-GDP gap (private non-financial sector)", "category": "Debt & Credit", "unit": "percentage of GDP", "frequency": "quarterly", "strength_direction": IndicatorStrengthDirection.contextual, "description": "BIS-published gap between the private non-financial sector credit-to-GDP ratio and its long-run trend."},
            {"code": "DEBT_SERVICE_RATIO", "name": "Debt service ratio (private non-financial sector)", "category": "Debt & Credit", "unit": "per cent", "frequency": "quarterly", "strength_direction": IndicatorStrengthDirection.contextual, "description": "Debt-service payments as a proportion of income for the private non-financial sector."},
            {"code": "LABOUR_PRODUCTIVITY_PER_HOUR", "name": "Labour productivity — GDP per hour worked", "category": "Productivity", "unit": "US dollars per hour, PPP converted", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive},
            {"code": "UNIT_LABOUR_COST_GROWTH", "name": "Unit labour cost growth", "category": "Cost Competitiveness", "unit": "percent per annum", "frequency": "quarterly", "strength_direction": IndicatorStrengthDirection.contextual, "description": "Year-over-year employment-based unit labour cost growth, seasonally adjusted."},
            {"code": "RULE_OF_LAW_WGI_SCORE", "name": "Rule of Law — WGI governance score", "category": "Governance", "unit": "score 0-100", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank WGI (2025 revision) Rule of Law absolute governance score, 0-100. Perception-based composite; larger = better governance."},
            {"code": "CONTROL_OF_CORRUPTION_WGI_SCORE", "name": "Control of Corruption — WGI governance score", "category": "Governance", "unit": "score 0-100", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank WGI (2025 revision) Control of Corruption absolute governance score, 0-100. Higher = stronger control of corruption / less corruption; the raw value is never reversed."},
            {"code": "POLITICAL_STABILITY_WGI_SCORE", "name": "Political Stability — WGI governance score", "category": "Governance", "unit": "score 0-100", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.positive, "description": "World Bank WGI (2025 revision) Political Stability and Absence of Violence/Terrorism absolute governance score, 0-100. Perception-based composite; larger = more stable."},
            {"code": "GINI_INDEX", "name": "Gini index", "category": "Inequality", "unit": "index (0-100)", "frequency": "irregular", "strength_direction": IndicatorStrengthDirection.negative, "description": "World Bank Gini index (SI.POV.GINI): extent to which the income/consumption distribution deviates from perfect equality (0 = perfect equality, 100 = perfect inequality). Published irregularly; missing years are gaps, never zeros or forward-filled. Higher = more inequality."},
            {"code": "MILITARY_EXPENDITURE_USD", "name": "Military expenditure", "category": "Military", "unit": "current US$", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.contextual, "description": "Annual military expenditure in current US dollars, as published through World Bank WDI using SIPRI data (MS.MIL.XPND.CD; underlying source: SIPRI Military Expenditure Database). Input proxy for military strength, not a capability measure."},
            {"code": "MILITARY_EXPENDITURE_GDP", "name": "Military expenditure (% of GDP)", "category": "Military", "unit": "percent of GDP", "frequency": "annual", "strength_direction": IndicatorStrengthDirection.contextual, "description": "Military expenditure as a share of GDP, as published through World Bank WDI using SIPRI data (MS.MIL.XPND.GD.ZS; underlying source: SIPRI Military Expenditure Database). Input proxy for military strength, not a capability measure."},
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
        all_mappings = [*WORLD_BANK_MAPPINGS, *BIS_MAPPINGS, *OECD_MAPPINGS]
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
