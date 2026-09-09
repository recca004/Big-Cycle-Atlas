"""Verify exact no-wildcard OECD education key."""
import asyncio
import csv
import io
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx


async def main():
    key = "USA._T.Y25T34.ISCED11A_5T8._T.POP._Z._T._Z.ED_NED.POP._Z.PT_POP_SEX_AGE.OBS._Z.NEAC.A"
    url = (
        "https://sdmx.oecd.org/public/rest/data/"
        "OECD.EDU.IMEP,DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA,1.0"
        f"/{key}?format=csvfilewithlabels"
    )
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.get(url)
    print(f"HTTP {r.status_code}")
    if r.status_code == 200:
        reader = csv.DictReader(io.StringIO(r.text))
        rows = list(reader)
        print(f"Rows: {len(rows)}")
        if rows:
            years = sorted(set(row.get("TIME_PERIOD", "") for row in rows))
            print(f"Years: {years[0]}-{years[-1]} ({len(years)} unique)")
            print(f"First: {rows[0].get('TIME_PERIOD')}={rows[0].get('OBS_VALUE')}")
            print(f"Last: {rows[-1].get('TIME_PERIOD')}={rows[-1].get('OBS_VALUE')}")
    else:
        print(r.text[:300])


if __name__ == "__main__":
    asyncio.run(main())
