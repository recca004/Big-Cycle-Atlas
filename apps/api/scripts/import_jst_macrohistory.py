"""Download/import JST Macrohistory Database Release 6 into research tables."""
import argparse
import asyncio
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
sys.path.insert(0, ".")

import httpx
from sqlalchemy import select

from app.data_sources.jst_macrohistory import (
    JST_CRISIS_DEFINITION, JST_DATASET_VERSION, JST_R6_URL,
    JST_SOURCE_KEY, iter_jst_rows, research_observation_payload,
)
from app.db.session import get_sessionmaker
from app.models import (
    CrisisCoverage, CrisisEvent, DataSource, DataSourceStatus,
    IngestionRun, IngestionRunStatus, ResearchObservation,
    ResearchPopulationMembership,
)
from app.research.scientific_registry import canonical_checksum


async def _download(url: str, path: Path) -> Path:
    async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
        response = await client.get(url)
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, help="Local JSTdatasetR6.xlsx (otherwise downloads official URL)")
    parser.add_argument("--url", default=JST_R6_URL)
    parser.add_argument("--variables", nargs="*", help="Optional variable subset; default imports every numeric variable")
    parser.add_argument("--batch", type=int, default=2000)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    path = args.file or repo_root / ".dev" / "tmp" / "JSTdatasetR6.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.file is None or not path.exists():
        await _download(args.url, path)

    rows = list(iter_jst_rows(path))
    wanted = set(args.variables or [])
    retrieved = datetime.now(timezone.utc)
    file_sha = hashlib.sha256(path.read_bytes()).hexdigest()

    session = get_sessionmaker()()
    async with session.begin():
        source = (await session.execute(select(DataSource).where(DataSource.key == JST_SOURCE_KEY))).scalar_one_or_none()
        if source is None:
            source = DataSource(
                key=JST_SOURCE_KEY,
                name="Jordà-Schularick-Taylor Macrohistory Database",
                status=DataSourceStatus.active,
                base_url="https://www.macrohistory.net/database/",
                update_frequency="manual historical dataset release",
                documentation_url="https://www.macrohistory.net/database/",
                rate_limit_notes="Manual bulk historical import; CC BY-NC-SA 4.0.",
            )
            session.add(source)
            await session.flush()
        run = IngestionRun(data_source_id=source.id, status=IngestionRunStatus.running)
        session.add(run)
        await session.flush()

        existing_obs = {
            (r.source_key, r.dataset_version, r.entity_code, r.variable_code, r.period_start, r.vintage_date)
            for r in (await session.execute(select(
                ResearchObservation.source_key, ResearchObservation.dataset_version,
                ResearchObservation.entity_code, ResearchObservation.variable_code,
                ResearchObservation.period_start, ResearchObservation.vintage_date,
            ).where(ResearchObservation.source_key == JST_SOURCE_KEY))).all()
        }
        existing_events = {
            (r.source_key, r.dataset_version, r.source_event_key, r.revision_number)
            for r in (await session.execute(select(
                CrisisEvent.source_key, CrisisEvent.dataset_version,
                CrisisEvent.source_event_key, CrisisEvent.revision_number,
            ).where(CrisisEvent.source_key == JST_SOURCE_KEY))).all()
        }
        existing_cov = {
            (r.source_key, r.dataset_version, r.entity_code, r.event_type, r.period_start)
            for r in (await session.execute(select(
                CrisisCoverage.source_key, CrisisCoverage.dataset_version,
                CrisisCoverage.entity_code, CrisisCoverage.event_type,
                CrisisCoverage.period_start,
            ).where(CrisisCoverage.source_key == JST_SOURCE_KEY))).all()
        }
        existing_members = {
            (r.population_code, r.population_version, r.entity_code)
            for r in (await session.execute(select(
                ResearchPopulationMembership.population_code,
                ResearchPopulationMembership.population_version,
                ResearchPopulationMembership.entity_code,
            ))).all()
        }

        inserted_obs = inserted_events = inserted_cov = inserted_members = 0
        seen_entities = {}
        pending = []
        for row in rows:
            seen_entities[row.iso3] = row.country
            crisis_value = row.values.get("crisisJST")
            for variable, value in row.values.items():
                if wanted and variable not in wanted:
                    continue
                payload = research_observation_payload(row, variable, value, retrieved)
                key = (payload["source_key"], payload["dataset_version"], payload["entity_code"], payload["variable_code"], payload["period_start"], payload["vintage_date"])
                if key in existing_obs:
                    continue
                pending.append(ResearchObservation(**payload))
                existing_obs.add(key)
                inserted_obs += 1
                if len(pending) >= args.batch:
                    session.add_all(pending); pending.clear()
            if crisis_value is not None:
                start = datetime(row.year, 1, 1, tzinfo=timezone.utc)
                cov_key = (JST_SOURCE_KEY, JST_DATASET_VERSION, row.iso3, "banking_crisis", start)
                if cov_key not in existing_cov:
                    session.add(CrisisCoverage(
                        source_key=JST_SOURCE_KEY, dataset_version=JST_DATASET_VERSION,
                        entity_code=row.iso3, event_type="banking_crisis",
                        period_start=start,
                        period_end=datetime(row.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                        coverage_status="covered", variable_code="crisisJST",
                        raw_payload={"country": row.country, "value": crisis_value},
                    ))
                    existing_cov.add(cov_key); inserted_cov += 1
                if crisis_value == 1.0:
                    event_key = f"JST-R6:{row.iso3}:{row.year}:crisisJST"
                    key = (JST_SOURCE_KEY, JST_DATASET_VERSION, event_key, 1)
                    if key not in existing_events:
                        raw = {"country": row.country, "year": row.year, "variable": "crisisJST", "value": crisis_value}
                        session.add(CrisisEvent(
                            source_key=JST_SOURCE_KEY, dataset_version=JST_DATASET_VERSION,
                            source_event_key=event_key, entity_code=row.iso3,
                            entity_name=row.country, event_type="banking_crisis",
                            event_state="onset", classification="systemic",
                            start_period=start,
                            end_period=datetime(row.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                            dating_precision="annual",
                            coverage_scope="18 advanced economies, annual 1870-2020",
                            source_definition=JST_CRISIS_DEFINITION,
                            publication_date=datetime(2022, 7, 1, tzinfo=timezone.utc),
                            retrieved_at=retrieved,
                            source_reference="JST Macrohistory Database Release 6 / JST Financial Crisis Chronology",
                            raw_payload=raw, checksum=canonical_checksum(raw),
                        ))
                        existing_events.add(key); inserted_events += 1
        if pending:
            session.add_all(pending)

        for iso3, name in sorted(seen_entities.items()):
            key = ("jst_extended_research_v1", "v1", iso3)
            if key not in existing_members:
                session.add(ResearchPopulationMembership(
                    population_code="jst_extended_research_v1", population_version="v1",
                    entity_code=iso3, entity_name=name, entity_type="country",
                    eligibility_rule="Pre-existing JST R6 advanced-economy panel; outcome values were not used to select entities.",
                    inclusion_reason="Complete JST R6 country-year row coverage (1870-2020 where source rows exist).",
                    source_requirements={"source_key": JST_SOURCE_KEY, "dataset_version": JST_DATASET_VERSION},
                    achieved_coverage={"source_rows": sum(1 for r in rows if r.iso3 == iso3)},
                    limitations={"scope": "advanced-economy historical panel", "selection_bias_guard": "source-defined coverage"},
                ))
                inserted_members += 1

        run.status = IngestionRunStatus.success
        run.rows_received = sum(len(r.values) for r in rows)
        run.rows_inserted = inserted_obs + inserted_events + inserted_cov
        run.rows_skipped = run.rows_received - inserted_obs
        run.completed_at = datetime.now(timezone.utc)
        run.run_metadata = {
            "file_sha256": file_sha, "source_url": args.url,
            "country_year_rows": len(rows), "entities": len(seen_entities),
            "variables_requested": sorted(wanted) if wanted else "all_numeric",
            "crisis_events_inserted": inserted_events,
            "coverage_rows_inserted": inserted_cov,
            "population_members_inserted": inserted_members,
            "license": "CC-BY-NC-SA-4.0",
        }
    print({
        "rows": len(rows), "entities": len(seen_entities),
        "research_observations_inserted": inserted_obs,
        "crisis_events_inserted": inserted_events,
        "coverage_rows_inserted": inserted_cov,
        "population_members_inserted": inserted_members,
        "sha256": file_sha,
    })


if __name__ == "__main__":
    asyncio.run(main())
