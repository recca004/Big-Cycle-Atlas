"""Import IMF Laeven–Valencia systemic banking-crisis bundles.

The importer accepts a locally downloaded IMF ZIP/CSV because the advertised
official URL may be temporarily unavailable. It never invents monthly dates:
annual start/end fields retain annual precision.
"""
import argparse
import asyncio
import csv
import io
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
sys.path.insert(0, ".")

import httpx
from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models import CrisisEvent, DataSource, IngestionRun, IngestionRunStatus
from app.research.scientific_registry import canonical_checksum

SOURCE_KEY = "imf_laeven_valencia_banking_crises"
DATASET_VERSION = "WP-2026-094"
OFFICIAL_ZIP = "https://www.imf.org/-/media/files/publications/wp/2026/datasets/wp2694.zip"


def _norm(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _find(row: dict, *names: str):
    normalized = {_norm(k): v for k, v in row.items() if k}
    for name in names:
        key = _norm(name)
        if normalized.get(key) not in (None, ""):
            return normalized[key]
    return None


def _iter_csv_records(path: Path):
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            for name in names:
                text = zf.read(name).decode("utf-8-sig", errors="replace")
                yield name, list(csv.DictReader(io.StringIO(text)))
        return
    yield path.name, list(csv.DictReader(path.open(encoding="utf-8-sig")))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, help="Local IMF ZIP or extracted CSV")
    parser.add_argument("--url", default=OFFICIAL_ZIP)
    args = parser.parse_args()

    path = args.file
    if path is None:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            response = await client.get(args.url)
        if response.status_code != 200:
            print({"status": "blocked", "official_url": args.url, "http_status": response.status_code, "imported": 0})
            return
        path = Path(__file__).resolve().parents[3] / ".dev" / "tmp" / "wp2694.zip"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)

    session = get_sessionmaker()()
    retrieved = datetime.now(timezone.utc)
    inserted = 0
    async with session.begin():
        source = (await session.execute(select(DataSource).where(DataSource.key == SOURCE_KEY))).scalar_one_or_none()
        run = None
        if source is not None:
            run = IngestionRun(data_source_id=source.id, status=IngestionRunStatus.running)
            session.add(run); await session.flush()
        existing = {
            (r.source_key, r.dataset_version, r.source_event_key, r.revision_number)
            for r in (await session.execute(select(CrisisEvent.source_key, CrisisEvent.dataset_version, CrisisEvent.source_event_key, CrisisEvent.revision_number))).all()
        }
        errors = []
        for member, records in _iter_csv_records(path):
            for idx, row in enumerate(records, start=2):
                country = _find(row, "country", "economy", "country name")
                iso3 = _find(row, "iso", "iso3", "country code")
                start = _find(row, "crisis start", "start year", "year", "start")
                end = _find(row, "crisis end", "end year", "end")
                if not country or not start:
                    continue
                try:
                    year = int(float(str(start).strip()[:4]))
                except ValueError:
                    continue
                entity = str(iso3 or country).upper()[:40]
                event_key = f"IMF-WP2026-094:{entity}:{year}:banking:{idx}"
                key = (SOURCE_KEY, DATASET_VERSION, event_key, 1)
                if key in existing:
                    continue
                raw = {"member": member, "row": row}
                session.add(CrisisEvent(
                    source_key=SOURCE_KEY, dataset_version=DATASET_VERSION,
                    source_event_key=event_key, entity_code=entity,
                    entity_name=str(country), event_type="banking_crisis",
                    event_state="onset", classification="systemic_or_borderline_source_defined",
                    start_period=datetime(year, 1, 1, tzinfo=timezone.utc),
                    end_period=datetime(int(float(str(end).strip()[:4])), 12, 31, 23, 59, 59, tzinfo=timezone.utc) if end else None,
                    dating_precision="annual",
                    coverage_scope="IMF WP 2026/094 supplemental dataset, 1970-2025",
                    source_definition="IMF Laeven–Valencia systemic banking-crisis definition; source CSV fields preserved verbatim.",
                    publication_date=datetime(2026, 5, 15, tzinfo=timezone.utc),
                    retrieved_at=retrieved,
                    source_reference="IMF Working Paper 2026/094 supplemental data",
                    raw_payload=raw, checksum=canonical_checksum(raw),
                ))
                existing.add(key); inserted += 1
        if run is not None:
            run.status = IngestionRunStatus.success if not errors else IngestionRunStatus.partial
            run.rows_inserted = inserted; run.completed_at = datetime.now(timezone.utc)
            run.run_metadata = {"file": str(path), "errors": errors}
    print({"status": "imported", "file": str(path), "events_inserted": inserted})


if __name__ == "__main__":
    asyncio.run(main())
