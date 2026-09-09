"""Quick dimension inspection for OECD education dataflow."""
import asyncio
import csv
import io
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx


async def main():
    key = "USA._T.Y25T34.ISCED11A_5T8." + ".".join(["+"] * 12) + ".A"
    url = (
        "https://sdmx.oecd.org/public/rest/data/"
        "OECD.EDU.IMEP,DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA,1.0"
        f"/{key}?format=csvfilewithlabels"
    )
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.get(url)
    if r.status_code != 200:
        print(f"HTTP {r.status_code}: {r.text[:200]}")
        return
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    if not rows:
        print("No rows")
        return
    print(f"Total rows: {len(rows)}")
    print(f"Columns: {list(rows[0].keys())}")
    # Print unique values for each dimension
    for col in rows[0].keys():
        if col in ("TIME_PERIOD", "OBS_VALUE"):
            continue
        vals = set(r.get(col, "") for r in rows)
        if len(vals) > 1:
            print(f"  {col}: {sorted(vals)}")
        else:
            v = vals.pop() if vals else ""
            print(f"  {col}: {v} (single value)")
    # Print first 3 rows with key dimensions
    print()
    for row in rows[:3]:
        tp = row.get("TIME_PERIOD", "")
        ov = row.get("OBS_VALUE", "")
        sex = row.get("SEX", "")
        age = row.get("AGE", "")
        measure = row.get("MEASURE", "")
        unit = row.get("UNIT_MEASURE", "")
        edu_field = row.get("EDUCATION_FIELD", "")
        income = row.get("INCOME", "")
        bp = row.get("BIRTH_PLACE", "")
        stat_op = row.get("STATISTICAL_OPERATION", "")
        print(f"  {tp}: {ov} | SEX={sex} AGE={age} MEASURE={measure} UNIT={unit} EDU_FIELD={edu_field} INCOME={income} BP={bp} STAT_OP={stat_op}")


if __name__ == "__main__":
    asyncio.run(main())
