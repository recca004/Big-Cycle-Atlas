"""Track B: OECD tertiary attainment verification (read-only, v10).

Find the exact series: SEX=_T, AGE=Y25T64, ATTAINMENT_LEV=ISCED11A_5T8 (Tertiary education)
"""
import asyncio
import sys
import csv
import io

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx

DATAFLOW = "DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA"
AGENCY = "OECD.EDU.IMEP"
BASE = "https://sdmx.oecd.org/public/rest"
TRACKED_8 = ["USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND"]


async def main():
    async with httpx.AsyncClient(timeout=120) as c:
        # Query USA data for the exact series: SEX=_T, AGE=Y25T64, ATTAINMENT_LEV=ISCED11A_5T8
        # Key: REF_AREA.SEX.AGE.ATTAINMENT_LEV.EDUCATION_FIELD.MEASURE.INCOME.BIRTH_PLACE.MIGRATION_AGE.EDU_STATUS.LABOUR_FORCE_STATUS.DURATION_UNEMP.UNIT_MEASURE.STATISTICAL_OPERATION.WORK_TIME_ARNGMNT.QUESTIONNAIRE.FREQ
        # USA._T.Y25T64.ISCED11A_5T8.+.+.+.+.+.+.+.+.+.+.+.+.+.A
        key = "USA._T.Y25T64.ISCED11A_5T8." + ".".join(["+"] * 12) + ".A"
        url = f"{BASE}/data/{AGENCY},{DATAFLOW},1.0/{key}?format=csvfilewithlabels"
        r = await c.get(url)
        print(f"=== USA tertiary total series: {r.status_code} ===")
        if r.status_code != 200 or not r.text.strip():
            print(r.text[:300])
            return

        reader = csv.DictReader(io.StringIO(r.text))
        rows = list(reader)
        print(f"  Total rows: {len(rows)}")
        if rows:
            print(f"  Columns: {list(rows[0].keys())}")
            for row in rows:
                year = row.get("TIME_PERIOD", "")
                val = row.get("OBS_VALUE", "")
                unit = row.get("UNIT_MEASURE", "")
                measure = row.get("MEASURE", "")
                print(f"  {year}: VAL={val} UNIT={unit} MEASURE={measure}")

        # Now check all 8 tracked countries
        print(f"\n=== All tracked_8: SEX=_T, AGE=Y25T64, ATTAINMENT_LEV=ISCED11A_5T8 ===")
        for country in TRACKED_8:
            key = f"{country}._T.Y25T64.ISCED11A_5T8." + ".".join(["+"] * 12) + ".A"
            url = f"{BASE}/data/{AGENCY},{DATAFLOW},1.0/{key}?format=csvfilewithlabels"
            r = await c.get(url)
            if r.status_code == 200 and r.text.strip():
                reader = csv.DictReader(io.StringIO(r.text))
                rows = list(reader)
                years_vals = [(row.get("TIME_PERIOD", ""), row.get("OBS_VALUE", "")) for row in rows]
                years_vals.sort()
                print(f"  {country}: {len(rows)} obs, years={years_vals[0][0] if years_vals else '?'}-{years_vals[-1][0] if years_vals else '?'}")
                for y, v in years_vals:
                    print(f"    {y}: {v}")
            else:
                print(f"  {country}: {r.status_code} - no data")


asyncio.run(main())
