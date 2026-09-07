"""Create tables and seed the initial country set.

Run from apps/api with the virtual environment active:

    python -m app.db.seed

Reads the canonical country list from packages/shared/data/initial-countries.json
(DEC-004). Idempotent: existing countries are updated, missing ones inserted.
"""

import asyncio
import json
from pathlib import Path

from app.db.base import Base
from app.db.session import get_engine
from app.models import Country

DEFAULT_DATA_FILE = (
    Path(__file__).resolve().parents[4] / "packages" / "shared" / "data" / "initial-countries.json"
)


async def seed(data_file: Path = DEFAULT_DATA_FILE) -> list[Country]:
    payload = json.loads(data_file.read_text(encoding="utf-8"))
    countries = [
        Country(iso3=row["iso3"], iso2=row["iso2"], name=row["name"], region=row["region"])
        for row in payload["countries"]
    ]

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(engine) as session:
        existing = {
            c.iso3: c
            for c in (await session.execute(select(Country))).scalars().all()
        }
        inserted = 0
        updated = 0
        for country in countries:
            current = existing.get(country.iso3)
            if current is None:
                session.add(country)
                inserted += 1
            else:
                current.iso2 = country.iso2
                current.name = country.name
                current.region = country.region
                updated += 1
        await session.commit()

    print(f"Countries seeded: {inserted} inserted, {updated} updated, {len(countries)} total in file")
    return countries


if __name__ == "__main__":
    asyncio.run(seed())