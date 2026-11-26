"""Seed/version the scientific-foundation registries."""
from __future__ import annotations

from datetime import datetime, timezone, date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Country, DatasetRightsRegistry, EvidenceStatusEntry,
    HypothesisProtocol, ResearchPopulationMembership, TheoryRegistryEntry,
    ValidationQuestion,
)
from app.research.scientific_registry import (
    DATASET_RIGHTS, HYPOTHESIS_PROTOCOLS, THEORY_ENTRIES,
    THEORY_REGISTRY_VERSION, canonical_checksum,
)
from app.research.validation_questions import (
    VALIDATION_QUESTIONS, VALIDATION_REGISTRY_VERSION,
)


async def seed_scientific_foundation(session: AsyncSession) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    inserted = {"theory": 0, "protocols": 0, "questions": 0, "populations": 0, "rights": 0, "evidence": 0}

    existing_theory = {
        (r.theory_code, r.version)
        for r in (await session.execute(select(TheoryRegistryEntry))).scalars()
    }
    for entry in THEORY_ENTRIES:
        key = (entry.theory_code, THEORY_REGISTRY_VERSION)
        if key in existing_theory:
            continue
        payload = entry.payload() | {"version": THEORY_REGISTRY_VERSION}
        fields = entry.payload()
        fields.pop("publication_date")
        session.add(TheoryRegistryEntry(
            **fields, version=THEORY_REGISTRY_VERSION,
            publication_date=date.fromisoformat(entry.publication_date) if entry.publication_date else None,
            registered_at=now, content_checksum=canonical_checksum(payload),
            raw_payload={"registry_seed": True},
        ))
        inserted["theory"] += 1

    existing_protocols = {
        (r.hypothesis_code, r.protocol_version)
        for r in (await session.execute(select(HypothesisProtocol))).scalars()
    }
    for payload in HYPOTHESIS_PROTOCOLS:
        key = (payload["hypothesis_code"], payload["protocol_version"])
        if key in existing_protocols:
            continue
        fields = {k: v for k, v in payload.items() if k in HypothesisProtocol.__table__.columns}
        fields.update(registered_at=now, content_checksum=canonical_checksum(payload))
        session.add(HypothesisProtocol(**fields))
        inserted["protocols"] += 1

    existing_questions = {
        (r.question_code, r.registry_version)
        for r in (await session.execute(select(ValidationQuestion))).scalars()
    }
    for question in VALIDATION_QUESTIONS:
        key = (question.question_code, VALIDATION_REGISTRY_VERSION)
        if key in existing_questions:
            continue
        payload = question.payload()
        fields = {k: v for k, v in payload.items() if k in ValidationQuestion.__table__.columns}
        fields.update(
            last_reviewed_at=now,
            content_checksum=canonical_checksum(payload),
            raw_payload={"registry_seed": True, "wording_origin": "atlas_derived_v1"},
        )
        session.add(ValidationQuestion(**fields))
        inserted["questions"] += 1

    countries = (await session.execute(select(Country).order_by(Country.iso3))).scalars().all()
    existing_members = {
        (r.population_code, r.population_version, r.entity_code)
        for r in (await session.execute(select(ResearchPopulationMembership))).scalars()
    }
    for c in countries:
        key = ("primary_observatory_v1", "v1", c.iso3)
        if key not in existing_members:
            session.add(ResearchPopulationMembership(
                population_code="primary_observatory_v1", population_version="v1",
                entity_code=c.iso3, entity_name=c.name, entity_type="country",
                eligibility_rule="Canonical eight-country Observatory population preserved unchanged.",
                inclusion_reason="Existing primary Observatory country.",
                source_requirements={"minimum": "current Atlas tracked observations"},
                achieved_coverage={"tracked_country": True},
                limitations={"note": "Primary interface population is not the full research universe."},
            ))
            inserted["populations"] += 1

    existing_rights = {
        (r.source_key, r.dataset_version)
        for r in (await session.execute(select(DatasetRightsRegistry))).scalars()
    }
    for rights in DATASET_RIGHTS:
        key = (rights["source_key"], rights["dataset_version"])
        if key not in existing_rights:
            session.add(DatasetRightsRegistry(**rights))
            inserted["rights"] += 1

    for subject_type, subject_key, status, limitations in (
        ("engine", "observations", "observed_data", "latest production observations; release evidence varies by row"),
        ("engine", "force_signals", "experimental_model", "approved measurement methods; not independently evaluated forecasts"),
        ("engine", "cycle_stages", "retrospective_analysis", "Atlas operational labels; not validated historical stages"),
        ("source", "jst_macrohistory_R6", "retrospective_analysis", "historical dataset release, not real-time point-in-time data"),
        ("source", "imf_cofer_SDMX_2_1", "observed_data", "currency-level official reserve shares; revised back to 2000Q1 in Dec 2025 to impute unallocated reserves; INR not separately identified"),
        ("source", "bis_fx_turnover_WS_DER_OTC_TOV", "observed_data", "triennial survey 1989-2025 including INR; two-sided currency shares sum to 200%"),
        ("source", "bis_lbs_WS_LBS_D_PUB", "observed_data", "quarterly cross-border bank claims by currency and reporting jurisdiction"),
        ("source", "bis_credit_policy_WS_TC_CBPOL", "observed_data", "sectoral credit (govt/private/household/corporate) and central-bank policy rates"),
        ("source", "pwt_11_0", "retrospective_analysis", "2021 PPP and constant national-accounts output, inputs, human capital and TFP; do not mix with 2011 PPP or OECD indices"),
        ("source", "maddison_2023", "retrospective_analysis", "long-run reconstructed GDP per capita in 2011 international dollars; pre-modern series are historical reconstructions"),
        ("source", "alfred_fred", "unavailable_research_result", "registered API key required"),
        ("source", "imf_laeven_valencia_WP-2026-094", "unavailable_research_result", "official supplemental dataset URL returned HTTP 403/404"),
    ):
        exists = (await session.execute(select(EvidenceStatusEntry).where(
            EvidenceStatusEntry.subject_type == subject_type,
            EvidenceStatusEntry.subject_key == subject_key,
            EvidenceStatusEntry.evidence_version == "v1",
        ))).scalar_one_or_none()
        if exists is None:
            session.add(EvidenceStatusEntry(
                subject_type=subject_type, subject_key=subject_key,
                evidence_version="v1", evidence_status=status,
                source_versions={}, evaluation_versions={},
                limitations={"note": limitations}, assessed_at=now,
            ))
            inserted["evidence"] += 1
    return inserted
