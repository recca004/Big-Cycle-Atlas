"""READ-ONLY Gini calibration universe profile (Sprint 5.17, Parts 2, 5, 6).

Sprint 5.17.1 hardening: the global economy/aggregate filter now uses the
AUTHORITATIVE World Bank country-metadata endpoint (region.id != "NA" =>
real economy) instead of a hand-written aggregate-code blacklist, which
wrongly excluded real economies such as ZAF (South Africa) and PSE (West
Bank and Gaza). If the metadata cannot be retrieved or parsed reliably,
the GLOBAL live profile STOPS — it does NOT silently fall back to the old
blacklist. The tracked_8 DB profile may still run.

Research tool that profiles:
  - tracked_8 GINI_INDEX observations already imported (latest vintage per
    (country, period)) with per-country latest value + welfare-concept hint
  - the broader World Bank SI.POV.GINI universe via a READ-ONLY live WB API
    v2 query (no DB writes, no new ingestion path, no new connector)

This script is RESEARCH SUPPORT ONLY. It must NOT:
  - produce a level_score or any other score,
  - propose or imply a force score,
  - write to the DB (SELECT only),
  - add a persistent ingestion path or provider connector,
  - become an API endpoint,
  - be treated as proof that an empirical percentile is economic truth.

Descriptive statistics describe the current sample; they do not justify a
curve. All values are computed in-memory from read-only queries and printed
to stdout - nothing is persisted.

Example (from apps/api):

    uv run --no-sync python scripts/gini_calibration_profile.py
    uv run --no-sync python scripts/gini_calibration_profile.py --skip-live
"""
import argparse
import asyncio
import json
import statistics
import sys
from datetime import datetime

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, ".")

from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models import Country, Indicator, Observation


TRACKED_8 = ("USA", "CHE", "CHN", "DEU", "FRA", "GBR", "JPN", "IND")

# WB API v2 endpoint for SI.POV.GINI. Per_page=20000 to fetch the full
# country-year universe in one request. date range covers the full PIP
# reference span. This is the SAME public WB API v2 the existing
# world_bank_adapter uses; no new connector is created.
_WB_GINI_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/SI.POV.GINI"
    "?format=json&per_page=20000&date=1963:2025"
)

# WB API v2 country-metadata endpoint. The authoritative source for
# distinguishing real economies from aggregates: every record carries a
# nested `region` object; real economies have a real region id (NAC, SSF,
# MEA, EAS, SAS, ...) while aggregates carry region.id == "NA" and
# region.value == "Aggregates". This REPLACES the previous hand-written
# aggregate-code blacklist, which wrongly excluded real economies such as
# ZAF (South Africa, region SSF) and PSE (West Bank and Gaza, region MEA).
# No DB writes; no persistent connector; read-only research only.
_WB_COUNTRY_META_URL = (
    "https://api.worldbank.org/v2/country?format=json&per_page=20000"
)

# Region ids that mark a record as an aggregate (not a real economy).
# The WB API uses "NA" for aggregates; empty/None is treated defensively.
_AGGREGATE_REGION_IDS = {"NA", "", None}


def build_valid_economy_codes(country_records: list[dict]) -> set[str]:
    """Return the set of real-economy ISO3 codes from WB country metadata.

    A record is a real economy when its nested `region` object carries a
    real region id (NOT "NA", empty, or None). Aggregates (World, income
    groups, regional blocs) carry region.id == "NA" and
    region.value == "Aggregates". This is a PURE helper with no I/O — it
    is unit-tested offline with mocked provider metadata (no external HTTP
    in pytest).

    Real economies such as ZAF (region SSF) and PSE (region MEA) are
    RETAINED; aggregates such as WLD / EAP / HIC / SSF-as-aggregate are
    EXCLUDED. Note SSF appears BOTH as a real-economy region id (on ZAF's
    record) AND as an aggregate code (its own record has region.id == "NA")
    — the filter keys on the record's OWN region field, never on the code
    itself, so the two senses never collide.
    """
    valid: set[str] = set()
    for rec in country_records:
        if not isinstance(rec, dict):
            continue
        code = rec.get("id")
        if not code or not isinstance(code, str):
            continue
        region = rec.get("region") or {}
        region_id = region.get("id") if isinstance(region, dict) else None
        if region_id in _AGGREGATE_REGION_IDS:
            continue
        valid.add(code)
    return valid


def _percentile(sorted_values: list[float], pct: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    cut = statistics.quantiles(sorted_values, n=100, method="inclusive")
    return cut[round(pct) - 1]


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4g}"


def _describe(values: list[float], indent: str = "    ") -> str:
    if not values:
        return f"{indent}(empty)"
    nums = sorted(values)
    lines = [
        f"{indent}n={len(nums)}  min={_fmt(nums[0])}  p10={_fmt(_percentile(nums, 10))}  "
        f"p25={_fmt(_percentile(nums, 25))}  median={_fmt(statistics.median(nums))}  "
        f"p75={_fmt(_percentile(nums, 75))}  p90={_fmt(_percentile(nums, 90))}  "
        f"max={_fmt(nums[-1])}",
    ]
    return "\n".join(lines)


def _period_label(period_start: datetime | None) -> str:
    if period_start is None:
        return "?"
    return period_start.date().isoformat()


async def _tracked_8_profile() -> dict:
    """Latest-vintage GINI_INDEX per (country, period) for tracked_8."""
    print("=" * 70)
    print("  PART 2 - TRACKED_8 GINI_INDEX COVERAGE (live DB, latest vintage)")
    print("=" * 70)
    print()
    async with get_sessionmaker()() as session:
        rows = (
            await session.execute(
                select(
                    Country.iso3,
                    Observation.period_start,
                    Observation.value,
                    Observation.vintage_number,
                )
                .join(Observation, Observation.country_id == Country.id)
                .join(Indicator, Observation.indicator_id == Indicator.id)
                .where(Indicator.code == "GINI_INDEX")
                .order_by(Country.iso3, Observation.period_start)
            )
        ).all()

    # Latest vintage per (country, period)
    by_country: dict[str, dict[datetime, tuple[int, float]]] = {}
    for iso3, period_start, value, vintage in rows:
        by_country.setdefault(iso3, {})
        slot = by_country[iso3].get(period_start)
        if slot is None or vintage > slot[0]:
            by_country[iso3][period_start] = (vintage, value)

    pooled: list[float] = []
    print(f"{'Country':<6} {'n':>4} {'first':>6} {'latest':>6} "
          f"{'min':>6} {'median':>7} {'max':>6} {'latest_val':>10}")
    print("-" * 60)
    for iso3 in TRACKED_8:
        periods = by_country.get(iso3, {})
        if not periods:
            print(f"{iso3:<6}    0   (no observations)")
            continue
        items = sorted(periods.items(), key=lambda kv: kv[0])
        vals = [v for _, (_, v) in items]
        first_year = items[0][0].date().year
        latest_year = items[-1][0].date().year
        latest_val = items[-1][1][1]
        print(f"{iso3:<6} {len(vals):>4} {first_year:>6} {latest_year:>6} "
              f"{min(vals):>6.2f} {statistics.median(vals):>7.2f} "
              f"{max(vals):>6.2f} {latest_val:>10.2f}")
        pooled.extend(vals)

    print()
    print("Pooled tracked_8 Gini distribution:")
    print(_describe(pooled))
    print()
    print("Welfare-concept hint (provider-methodology / country-level")
    print("welfare-concept classification — NOT a per-observation API field):")
    print("  - High-income economies (USA, CHE, DEU, FRA, GBR, JPN): income-based")
    print("    (LIS Database / EU-SILC; after-tax income).")
    print("  - CHN, IND: consumption-based (PIP groups China under grouped data;")
    print("    India under South Asia consumption surveys).")
    print("  - This is a provider-methodology / country-level welfare-concept")
    print("    classification drawn from official PIP documentation — NOT a")
    print("    per-observation metadata field exposed by SI.POV.GINI. The API")
    print("    does NOT tag every CHN observation as consumption; the tag is a")
    print("    methodology-level classification, not a per-row column.")
    print("  - The WB API does NOT expose a per-observation welfare-concept")
    print("    tag, so no defensible automated adjustment is possible from the")
    print("    data alone. No invented adjustments are applied.")
    print()
    return {"pooled": pooled, "by_country": {c: [v for _, (_, v) in sorted(by_country.get(c, {}).items(), key=lambda kv: kv[0])] for c in TRACKED_8}}


async def _live_global_profile() -> None:
    """Read-only WB API v2 query for the broader Gini universe."""
    print("=" * 70)
    print("  PART 5 - GLOBAL WB GINI UNIVERSE (read-only live WB API v2 query)")
    print("=" * 70)
    print()
    print(f"Endpoint: {_WB_GINI_URL}")
    print("No DB writes. No new connector. No persistence. Read-only research.")
    print()
    try:
        import httpx
    except ImportError:
        print("httpx not available - skipping live global profile.")
        return

    # Use the same SSL/timeout conventions as the existing WB adapter
    # (certifi cadata — this machine's python.exe lacks OPENSSL_Applink, so
    # FILE*-based CA loading crashes; cadata bypasses the file BIO).
    import ssl
    import certifi
    from pathlib import Path
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_default_certs()
    pem = Path(certifi.where()).read_text(encoding="utf-8")
    ctx.load_verify_locations(cadata=pem)

    async with httpx.AsyncClient(timeout=60.0, verify=ctx) as client:
        # ---- STEP 1: fetch AUTHORITATIVE country metadata FIRST ----
        # The economy/aggregate distinction comes from the official WB
        # country-metadata endpoint (region.id == "NA" => aggregate), NOT
        # from a hand-written blacklist. If this cannot be retrieved or
        # parsed reliably, the GLOBAL live profile STOPS — it does NOT
        # silently fall back to the old blacklist (which wrongly excluded
        # real economies such as ZAF and PSE). The tracked_8 DB profile
        # above is unaffected and may still run.
        print("Fetching authoritative WB country metadata (economy filter)...")
        print(f"  Endpoint: {_WB_COUNTRY_META_URL}")
        try:
            meta_resp = await client.get(_WB_COUNTRY_META_URL)
            meta_resp.raise_for_status()
        except Exception as exc:
            print(f"Country-metadata fetch failed: {exc!r}")
            print("STOPPING GLOBAL live profile — provider metadata unavailable.")
            print("No fallback to a manual aggregate blacklist (the old blacklist")
            print("wrongly excluded real economies such as ZAF and PSE). The")
            print("tracked_8 DB profile above remains valid.")
            return
        try:
            meta_payload = meta_resp.json()
        except Exception as exc:
            print(f"Country-metadata JSON decode failed: {exc!r}")
            print("STOPPING GLOBAL live profile — provider metadata unparseable.")
            return

        if not isinstance(meta_payload, list) or len(meta_payload) < 2:
            print("Unexpected WB country-metadata response shape — STOPPING.")
            print("GLOBAL live profile unavailable (no fallback to blacklist).")
            return
        country_records = meta_payload[1]
        if not isinstance(country_records, list) or not country_records:
            print("WB country-metadata returned no records — STOPPING.")
            print("GLOBAL live profile unavailable (no fallback to blacklist).")
            return

        valid_economy_codes = build_valid_economy_codes(country_records)
        print(f"  Authoritative economy filter: {len(valid_economy_codes)} real")
        print(f"  economies identified (region.id != 'NA'). Aggregates excluded")
        print(f"  via provider metadata, NOT a manual blacklist.")
        # Explicit ZAF/PSE retention check (the bug this sprint fixes).
        for code in ("ZAF", "PSE"):
            status = "RETAINED" if code in valid_economy_codes else "WRONGLY EXCLUDED"
            print(f"  {code}: {status}")
        print()

        # ---- STEP 2: fetch the SI.POV.GINI universe ----
        print(f"Endpoint: {_WB_GINI_URL}")
        print("No DB writes. No new connector. No persistence. Read-only research.")
        try:
            resp = await client.get(_WB_GINI_URL)
            resp.raise_for_status()
        except Exception as exc:
            print(f"Live Gini query failed: {exc!r}")
            print("STOPPING GLOBAL live profile — Gini data unavailable.")
            return
        try:
            payload = resp.json()
        except Exception as exc:
            print(f"Gini JSON decode failed: {exc!r}")
            print("STOPPING GLOBAL live profile — Gini data unparseable.")
            return

    # WB API v2 JSON format: [metadata_page, [records...]]
    if not isinstance(payload, list) or len(payload) < 2:
        print("Unexpected WB Gini response shape — STOPPING.")
        return
    records = payload[1]
    if records is None:
        print("WB API returned no Gini records.")
        return

    # Filter to non-null values whose country is a REAL economy per the
    # authoritative metadata (region.id != "NA"). The GINI record carries
    # `countryiso3code` (3-letter, e.g. USA/ZAF/PSE) which matches the
    # metadata endpoint's `id` field; `country.id` is a 2-letter WB code and
    # must NOT be used for the economy match. This replaces the previous
    # hand-written aggregate_codes blacklist, which (a) wrongly listed real
    # economies such as ZAF and PSE as aggregates and (b) matched against
    # the 2-letter country.id so the blacklist was in fact ineffective. The
    # authoritative metadata filter is correct on both axes. No inference
    # from code length, capitalization, or a manual blacklist.
    valid: list[tuple[str, str, int, float]] = []  # (iso3, country_name, year, value)
    excluded_aggregates: set[str] = set()
    for rec in records:
        try:
            value = rec.get("value")
            if value is None:
                continue
            iso3 = rec.get("countryiso3code", "") or ""
            cname = (rec.get("country", {}) or {}).get("value", "") or ""
            if not iso3:
                continue
            if iso3 not in valid_economy_codes:
                excluded_aggregates.add(iso3)
                continue
            year = int(rec.get("date", "0")[:4])
            valid.append((iso3, cname, year, float(value)))
        except (TypeError, ValueError):
            continue

    if not valid:
        print("No valid country-year observations parsed.")
        return

    print(f"Filter excluded {len(excluded_aggregates)} aggregate/non-economy codes")
    print(f"(via authoritative metadata): {sorted(excluded_aggregates)}")
    print()

    print(f"Total valid country-year observations: {len(valid)}")
    countries = sorted({iso3 for iso3, _, _, _ in valid})
    print(f"Distinct countries/economies: {len(countries)}")
    years = [y for _, _, y, _ in valid]
    print(f"Year span: {min(years)} - {max(years)}")
    print()

    # Explicit ZAF/PSE verification (the bug this sprint fixes: the old
    # hand-written blacklist listed ZAF and PSE as aggregates).
    for code in ("ZAF", "PSE"):
        obs = [v for c, _, _, v in valid if c == code]
        if obs:
            print(f"  {code}: RETAINED — {len(obs)} observations "
                  f"(min={_fmt(min(obs))} median={_fmt(statistics.median(obs))} "
                  f"max={_fmt(max(obs))})")
        else:
            print(f"  {code}: NOT FOUND in valid observations (check filter)")
    print()

    all_vals = [v for _, _, _, v in valid]
    print("Global pooled Gini distribution (all country-years):")
    print(_describe(all_vals))
    print()

    # Same-year cross-sections for representative years.
    for rep_year in (2000, 2010, 2020, max(years)):
        yr_vals = [v for _, _, y, v in valid if y == rep_year]
        if not yr_vals:
            continue
        print(f"Same-year cross-section {rep_year} (n={len(yr_vals)} countries):")
        print(_describe(yr_vals))
        print()

    # Latest sufficiently populated year (n >= 30 — a reasonable cross-section
    # threshold; descriptive, NOT an approved calibration cutoff).
    by_year_n: dict[int, int] = {}
    for _, _, y, _ in valid:
        by_year_n[y] = by_year_n.get(y, 0) + 1
    sufficiently_populated = sorted(
        (y for y, n in by_year_n.items() if n >= 30), reverse=True
    )
    if sufficiently_populated:
        latest_pop_year = sufficiently_populated[0]
        yr_vals = [v for _, _, y, v in valid if y == latest_pop_year]
        print(f"Latest sufficiently populated year (n>=30): {latest_pop_year} "
              f"(n={len(yr_vals)})")
        print(_describe(yr_vals))
        print()
    else:
        print("No year reaches the n>=30 sufficiently-populated threshold.")
        print()

    # Distribution by decade (median per decade)
    print("Median Gini by decade (descriptive only):")
    for decade_start in (1960, 1970, 1980, 1990, 2000, 2010, 2020):
        decade_vals = [v for _, _, y, v in valid if decade_start <= y < decade_start + 10]
        if not decade_vals:
            continue
        nums = sorted(decade_vals)
        print(f"  {decade_start}s: n={len(nums)}  median={_fmt(statistics.median(nums))}  "
              f"p10={_fmt(_percentile(nums, 10))}  p90={_fmt(_percentile(nums, 90))}")
    print()

    # Country count by decade (composition shift)
    print("Country count by decade (composition shift indicator):")
    for decade_start in (1960, 1970, 1980, 1990, 2000, 2010, 2020):
        decade_countries = {iso3 for iso3, _, y, _ in valid if decade_start <= y < decade_start + 10}
        if not decade_countries:
            continue
        print(f"  {decade_start}s: {len(decade_countries)} countries")
    print()

    print("NOTE: The global distribution shifts materially by decade and the")
    print("country composition changes. A fixed full-history pooled percentile")
    print("would encode future information and composition changes. Descriptive")
    print("only - NOT an approved calibration.")


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-live",
        action="store_true",
        help="skip the live WB API global query (tracked_8 DB profile only)",
    )
    args = parser.parse_args()

    print()
    print("Gini Calibration Universe Profile (Sprint 5.17.1 — authoritative")
    print("economy-filter hardening)")
    print("=" * 70)
    print("READ-ONLY research tool. No writes. No level_score produced.")
    print("Descriptive statistics only - not proof of economic truth.")
    print("Economy/aggregate filter: authoritative WB country metadata")
    print("(region.id != 'NA'), NOT a hand-written blacklist.")
    print()

    await _tracked_8_profile()

    if not args.skip_live:
        await _live_global_profile()

    print("=" * 70)
    print("  END OF PROFILE - see NORMALIZATION.md for the decision matrix")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
