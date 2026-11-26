"""Idempotent importer for verified Workstream B economic, currency & historical productivity datasets.

Imports into `research_observations` (without altering the 46 canonical Observatory
`Observation` series):
- IMF COFER official FX reserve currency shares & claims (1995-1998 annual + 1999Q1-latest quarterly)
- BIS Triennial Central Bank Survey FX turnover by currency (1989-2025, including INR)
- BIS Locational Banking Statistics cross-border claims by currency & reporting jurisdiction
- BIS Total Credit by borrower sector (public vs private vs household vs corporate) & policy rates
- Penn World Table 11.0 (1950-2023, 20-country panel, CC-BY-4.0)
- Maddison Project Database 2023 (1500-2022, 20-country panel, CC-BY-4.0)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
sys.path.insert(0, ".")

from sqlalchemy import select

from app.data_sources.research_panels import (
    BIS_CREDIT_SOURCE_KEY,
    BIS_FX_SOURCE_KEY,
    BIS_LBS_SOURCE_KEY,
    IMFC_SOURCE_KEY,
    MPD_DATAVERSE_FILE_ID,
    MPD_SOURCE_KEY,
    PWT_DATAVERSE_FILE_ID,
    PWT_SOURCE_KEY,
    fetch_url_bytes,
    parse_bis_credit_and_policy_csv,
    parse_bis_fx_turnover_csv,
    parse_bis_lbs_csv,
    parse_cofer_csv,
    parse_maddison2023_xlsx,
    parse_pwt11_xlsx,
)
from app.db.session import get_sessionmaker
from app.models import ResearchObservation

ROOT = Path(__file__).resolve().parents[3]
TMP = ROOT / ".dev" / "tmp"


async def _persist_batch(source_key: str, payloads: list[dict]) -> int:
    if not payloads:
        return 0
    session = get_sessionmaker()()
    async with session.begin():
        existing = {
            (
                r.source_key,
                r.dataset_version,
                r.entity_code,
                r.variable_code,
                r.period_start,
                r.vintage_date,
            )
            for r in (
                await session.execute(
                    select(
                        ResearchObservation.source_key,
                        ResearchObservation.dataset_version,
                        ResearchObservation.entity_code,
                        ResearchObservation.variable_code,
                        ResearchObservation.period_start,
                        ResearchObservation.vintage_date,
                    ).where(ResearchObservation.source_key == source_key)
                )
            ).all()
        }
        inserted = 0
        for item in payloads:
            key = (
                item["source_key"],
                item["dataset_version"],
                item["entity_code"],
                item["variable_code"],
                item["period_start"],
                item["vintage_date"],
            )
            if key in existing:
                continue
            session.add(ResearchObservation(**item))
            existing.add(key)
            inserted += 1
    return inserted


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import verified currency, debt and productivity research datasets.")
    parser.add_argument("--pwt-file", type=Path, default=TMP / "pwt110.xlsx")
    parser.add_argument("--mpd-file", type=Path, default=TMP / "mpd2023_web.xlsx")
    args = parser.parse_args()

    TMP.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    summary: dict[str, int] = {}

    # 1. IMF COFER (annual pre-1999 + quarterly 1999+)
    sdmx_headers = {
        "Accept": "application/vnd.sdmx.data+csv;version=1.0.0",
        "User-Agent": "BigCycleAtlas-Research/1.1",
    }
    cofer_a = fetch_url_bytes("https://api.imf.org/external/sdmx/2.1/data/COFER/G001....A", headers=sdmx_headers).decode("utf-8", errors="replace")
    cofer_q = fetch_url_bytes("https://api.imf.org/external/sdmx/2.1/data/COFER/G001....Q", headers=sdmx_headers).decode("utf-8", errors="replace")
    cofer_rows = (
        parse_cofer_csv(cofer_a, annual_pre_1999_only=True, retrieved_at=now)
        + parse_cofer_csv(cofer_q, annual_pre_1999_only=False, retrieved_at=now)
    )
    summary[IMFC_SOURCE_KEY] = await _persist_batch(IMFC_SOURCE_KEY, cofer_rows)

    # 2. BIS Triennial FX Turnover (including INR, CNY, USD, EUR, JPY, GBP, CHF, DEM, FRF)
    fx_csv = fetch_url_bytes(
        "https://stats.bis.org/api/v1/data/WS_DER_OTC_TOV/A.U.A.B.5J.A.5J.A.TO1+USD+EUR+JPY+GBP+CNY+CHF+INR+DEM+FRF.TO1.A.A.3.C/all?format=csv"
    ).decode("utf-8", errors="replace")
    summary[BIS_FX_SOURCE_KEY] = await _persist_batch(BIS_FX_SOURCE_KEY, parse_bis_fx_turnover_csv(fx_csv, retrieved_at=now))

    # 3. BIS Locational Banking Statistics (currency denomination + reporting financial centres)
    lbs_ccy = fetch_url_bytes(
        "https://stats.bis.org/api/v1/data/WS_LBS_D_PUB/Q.S.C.A.TO1+USD+EUR+JPY+GBP+CHF.A.5J.A.5A.A.5J.N/all?format=csv"
    ).decode("utf-8", errors="replace")
    lbs_cty = fetch_url_bytes(
        "https://stats.bis.org/api/v1/data/WS_LBS_D_PUB/Q.S.C.A.TO1.A.5J.A.5A+US+GB+DE+FR+JP+CH+CN+IN.A.5J.N/all?format=csv"
    ).decode("utf-8", errors="replace")
    summary[BIS_LBS_SOURCE_KEY] = await _persist_batch(BIS_LBS_SOURCE_KEY, parse_bis_lbs_csv(lbs_ccy, lbs_cty, retrieved_at=now))

    # 4. BIS Total Credit by Sector & Central Bank Policy Rates
    tc_m = fetch_url_bytes(
        "https://stats.bis.org/api/v1/data/WS_TC/Q.US+CN+IN+JP+DE+GB+FR+CH.G+P+H+N.A.M.770.A/all?format=csv"
    ).decode("utf-8", errors="replace")
    tc_n = fetch_url_bytes(
        "https://stats.bis.org/api/v1/data/WS_TC/Q.US+CN+IN+JP+DE+GB+FR+CH.G.A.N.770.A/all?format=csv"
    ).decode("utf-8", errors="replace")
    cbpol = fetch_url_bytes(
        "https://stats.bis.org/api/v1/data/WS_CBPOL/M.US+CN+IN+JP+DE+GB+FR+CH+XM/all?format=csv"
    ).decode("utf-8", errors="replace")
    summary[BIS_CREDIT_SOURCE_KEY] = await _persist_batch(
        BIS_CREDIT_SOURCE_KEY,
        parse_bis_credit_and_policy_csv(tc_m, tc_n, cbpol, retrieved_at=now),
    )

    # 5. Penn World Table 11.0
    pwt_path = args.pwt_file
    if not pwt_path.exists():
        pwt_path.write_bytes(fetch_url_bytes(f"https://dataverse.nl/api/access/datafile/{PWT_DATAVERSE_FILE_ID}", timeout=180))
    summary[PWT_SOURCE_KEY] = await _persist_batch(PWT_SOURCE_KEY, parse_pwt11_xlsx(pwt_path, retrieved_at=now))

    # 6. Maddison Project Database 2023
    mpd_path = args.mpd_file
    if not mpd_path.exists():
        mpd_path.write_bytes(fetch_url_bytes(f"https://dataverse.nl/api/access/datafile/{MPD_DATAVERSE_FILE_ID}", timeout=180))
    summary[MPD_SOURCE_KEY] = await _persist_batch(MPD_SOURCE_KEY, parse_maddison2023_xlsx(mpd_path, retrieved_at=now))

    print({"status": "imported", "inserted_by_source": summary, "total_inserted": sum(summary.values())})


if __name__ == "__main__":
    asyncio.run(main())
