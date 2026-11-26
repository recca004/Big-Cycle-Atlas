"""Official multi-source research panels for currency, debt, banking and long-run productivity.

All rows persist into `research_observations` with explicit entity types (`country`,
`currency`, `currency_area`, `global_denominator`), dataset versions, release/vintage
metadata and documented methodology breaks. Nothing here overwrites the 46 canonical
Observatory `Observation` indicators or fabricates missing periods.
"""
from __future__ import annotations

import csv
import hashlib
import io
import math
import re
import ssl
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import certifi

IMFC_SOURCE_KEY = "imf_cofer"
IMFC_DATASET_VERSION = "COFER-SDMX-2.1"

BIS_FX_SOURCE_KEY = "bis_fx_turnover"
BIS_FX_DATASET_VERSION = "WS_DER_OTC_TOV"

BIS_LBS_SOURCE_KEY = "bis_lbs"
BIS_LBS_DATASET_VERSION = "WS_LBS_D_PUB"

BIS_CREDIT_SOURCE_KEY = "bis_credit_policy"
BIS_CREDIT_DATASET_VERSION = "WS_TC_CBPOL"

PWT_SOURCE_KEY = "pwt"
PWT_DATASET_VERSION = "11.0"
PWT_DATAVERSE_FILE_ID = 554105
PWT_RELEASE_DATE = date(2025, 10, 7)

MPD_SOURCE_KEY = "maddison"
MPD_DATASET_VERSION = "2023"
MPD_DATAVERSE_FILE_ID = 421302
MPD_RELEASE_DATE = date(2024, 4, 18)

RESEARCH_COUNTRY_PANEL: dict[str, str] = {
    "USA": "United States",
    "CHN": "China",
    "IND": "India",
    "JPN": "Japan",
    "DEU": "Germany",
    "GBR": "United Kingdom",
    "FRA": "France",
    "CHE": "Switzerland",
    "AUS": "Australia",
    "BEL": "Belgium",
    "CAN": "Canada",
    "DNK": "Denmark",
    "ESP": "Spain",
    "FIN": "Finland",
    "IRL": "Ireland",
    "ITA": "Italy",
    "NLD": "Netherlands",
    "NOR": "Norway",
    "PRT": "Portugal",
    "SWE": "Sweden",
}

BIS_ISO2_TO_ISO3 = {
    "US": ("USA", "United States", "country"),
    "CN": ("CHN", "China", "country"),
    "IN": ("IND", "India", "country"),
    "JP": ("JPN", "Japan", "country"),
    "DE": ("DEU", "Germany", "country"),
    "GB": ("GBR", "United Kingdom", "country"),
    "FR": ("FRA", "France", "country"),
    "CH": ("CHE", "Switzerland", "country"),
    "XM": ("EUR", "Euro area", "currency_area"),
    "5A": ("ALL_REPORTING", "All BIS reporting jurisdictions", "global_denominator"),
}

CURRENCY_LABELS: dict[str, tuple[str, str]] = {
    "USD": ("US dollar", "currency"),
    "EUR": ("Euro (shared currency area)", "currency_area"),
    "CNY": ("Chinese yuan renminbi", "currency"),
    "GBP": ("Pound sterling", "currency"),
    "JPY": ("Japanese yen", "currency"),
    "CHF": ("Swiss franc", "currency"),
    "INR": ("Indian rupee", "currency"),
    "AUD": ("Australian dollar", "currency"),
    "CAD": ("Canadian dollar", "currency"),
    "DEM": ("Deutsche mark (historical pre-1999)", "historical_currency"),
    "FRF": ("French franc (historical pre-1999)", "historical_currency"),
    "ECU": ("European Currency Unit (historical pre-1999)", "historical_currency"),
    "NLG": ("Netherlands guilder (historical pre-1999)", "historical_currency"),
    "OTHC": ("Other currencies (unseparated residual)", "currency_residual"),
    "ALL_CURRENCIES": ("All reported currencies", "global_denominator"),
}

COFER_METHODOLOGY_BREAKS: tuple[dict[str, str], ...] = (
    {
        "period": "1995–1998",
        "break_code": "cofer_annual_pre_euro",
        "description": (
            "Annual-only COFER observations prior to Euro launch; DEM, FRF, NLG and "
            "ECU are separately reported through 1998."
        ),
    },
    {
        "period": "1999-Q1",
        "break_code": "cofer_euro_introduction_quarterly",
        "description": (
            "Quarterly COFER reporting begins and EUR replaces legacy euro-area "
            "national currencies; EUR share belongs to the Eurosystem, never to "
            "Germany or France individually."
        ),
    },
    {
        "period": "2012-Q4",
        "break_code": "cofer_aud_cad_split",
        "description": "AUD and CAD separated out of Other currencies (OTHC).",
    },
    {
        "period": "2015-Q3",
        "break_code": "cofer_reporter_disclosure_reclassification",
        "description": (
            "IMF disclosed participating COFER reporters and discontinued advanced "
            "vs emerging-economy reserve breakdowns."
        ),
    },
    {
        "period": "2016-Q4",
        "break_code": "cofer_cny_split",
        "description": (
            "CNY separated out of Other currencies (OTHC); pre-2016Q4 CNY reserve "
            "holdings remain unseparated, never zero."
        ),
    },
    {
        "period": "2025-Q3 (revised back to 2000-Q1)",
        "break_code": "cofer_unallocated_imputation_revision",
        "description": (
            "IMF eliminated the unallocated residual back to 2000-Q1 by imputing "
            "currency shares across 100% of total FX reserves and added TFXRA_IMP "
            "(imputed share of total reserves) from 2025-Q3."
        ),
    },
)

_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_CELL_RE = re.compile(r"^([A-Z]+)([0-9]+)$")
_QUARTER_RE = re.compile(r"^(\d{4})-Q([1-4])$")
_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


def build_ssl_context() -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_default_certs()
    ctx.load_verify_locations(cadata=Path(certifi.where()).read_text(encoding="utf-8"))
    return ctx


def fetch_url_bytes(url: str, headers: dict[str, str] | None = None, timeout: int = 90) -> bytes:
    req = urllib.request.Request(
        url,
        headers=headers or {"User-Agent": "BigCycleAtlas-Research/1.1"},
    )
    with urllib.request.urlopen(req, timeout=timeout, context=build_ssl_context()) as resp:
        return resp.read()


def _parse_period_bounds(period_text: str) -> tuple[datetime, datetime] | None:
    s = period_text.strip()
    if re.fullmatch(r"\d{1,4}", s):
        yr = int(s)
        if yr < 1:
            return None
        return (
            datetime(yr, 1, 1, tzinfo=timezone.utc),
            datetime(yr, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        )
    qm = _QUARTER_RE.match(s)
    if qm:
        yr, q = int(qm.group(1)), int(qm.group(2))
        start_month = (q - 1) * 3 + 1
        end_month = start_month + 2
        end_day = 31 if end_month in {3, 12} else 30
        return (
            datetime(yr, start_month, 1, tzinfo=timezone.utc),
            datetime(yr, end_month, end_day, 23, 59, 59, tzinfo=timezone.utc),
        )
    mm = _MONTH_RE.match(s)
    if mm:
        yr, m = int(mm.group(1)), int(mm.group(2))
        if m == 12:
            next_start = datetime(yr + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_start = datetime(yr, m + 1, 1, tzinfo=timezone.utc)
        end_dt = next_start - timedelta(seconds=1)
        return (datetime(yr, m, 1, tzinfo=timezone.utc), end_dt)
    return None


def _finite_float(raw: Any) -> float | None:
    if raw in (None, "", "NaN", "nan", "NA", "."):
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if math.isfinite(val) else None


def parse_cofer_csv(csv_text: str, *, annual_pre_1999_only: bool, retrieved_at: datetime) -> list[dict[str, Any]]:
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    out: list[dict[str, Any]] = []
    for r in rows:
        val = _finite_float(r.get("OBS_VALUE"))
        if val is None:
            continue
        tp = (r.get("TIME_PERIOD") or "").strip()
        if annual_pre_1999_only and (not tp.isdigit() or int(tp) >= 1999):
            continue
        bounds = _parse_period_bounds(tp)
        if bounds is None:
            continue
        ind = (r.get("INDICATOR") or "").strip()
        raw_ccy = (r.get("FXR_CURRENCY") or "").strip()
        trans = (r.get("TYPE_OF_TRANSFORMATION") or "").strip()
        ccy = "ALL_CURRENCIES" if raw_ccy == "CI_T" else raw_ccy.removeprefix("CI_")
        if ccy not in CURRENCY_LABELS:
            continue
        if ind == "AFXRA" and trans == "SHRO_PT":
            var_code = "COFER_RESERVE_SHARE_PCT"
            var_name = "Official FX reserve share (IMF COFER)"
            unit = "percent_of_fx_reserves"
        elif ind == "AFXRA" and trans == "NV_USD":
            var_code = "COFER_RESERVE_CLAIMS_USD"
            var_name = "Official FX reserve claims (IMF COFER)"
            unit = "USD"
        elif ind == "TFXRA_IMP" and trans == "SHRO_PT" and ccy == "ALL_CURRENCIES":
            var_code = "COFER_IMPUTED_SHARE_PCT"
            var_name = "Imputed share of total FX reserves (IMF COFER)"
            unit = "percent_of_fx_reserves"
        else:
            continue
        pub_raw = (r.get("PUBLICATION_DATE") or "").strip()
        pub_dt = None
        if pub_raw:
            try:
                pub_dt = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
            except ValueError:
                pub_dt = None
        entity_name, entity_type = CURRENCY_LABELS[ccy]
        out.append({
            "source_key": IMFC_SOURCE_KEY,
            "dataset_version": IMFC_DATASET_VERSION,
            "entity_code": ccy,
            "entity_name": entity_name,
            "entity_type": entity_type,
            "variable_code": var_code,
            "variable_name": var_name,
            "period_start": bounds[0],
            "period_end": bounds[1],
            "value": val,
            "unit": unit,
            "vintage_date": pub_dt.date() if pub_dt else None,
            "release_date": pub_dt,
            "release_evidence_type": "provider_dataset_publication_timestamp" if pub_dt else "none",
            "retrieved_at": retrieved_at,
            "source_version": r.get("DATAFLOW") or "IMF.STA:COFER",
            "source_url": "https://api.imf.org/external/sdmx/2.1/data/COFER",
            "license_code": "IMF Terms of Use (attribution required; non-commercial)",
            "raw_payload": {
                "time_period": tp,
                "frequency": r.get("FREQUENCY"),
                "indicator": ind,
                "fxr_currency": raw_ccy,
                "transformation": trans,
                "methodology_breaks": [b["break_code"] for b in COFER_METHODOLOGY_BREAKS],
            },
        })
    return out


def parse_bis_fx_turnover_csv(csv_text: str, *, retrieved_at: datetime) -> list[dict[str, Any]]:
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    by_year: dict[str, dict[str, float]] = {}
    for r in rows:
        val = _finite_float(r.get("OBS_VALUE"))
        if val is None:
            continue
        if (
            r.get("DER_TYPE") == "U"
            and r.get("DER_INSTR") == "A"
            and r.get("DER_RISK") == "B"
            and r.get("DER_REP_CTY") == "5J"
            and r.get("DER_SECTOR_CPY") == "A"
            and r.get("DER_CPC") == "5J"
            and r.get("DER_CURR_LEG2") == "TO1"
            and r.get("DER_EX_METHOD") == "3"
            and r.get("DER_BASIS") == "C"
        ):
            by_year.setdefault(r["TIME_PERIOD"].strip(), {})[r["DER_CURR_LEG1"].strip()] = val

    out: list[dict[str, Any]] = []
    for tp, ccy_vals in sorted(by_year.items()):
        bounds = _parse_period_bounds(tp)
        if bounds is None:
            continue
        total = ccy_vals.get("TO1")
        for raw_ccy, val in sorted(ccy_vals.items()):
            ccy = "ALL_CURRENCIES" if raw_ccy == "TO1" else raw_ccy
            if ccy not in CURRENCY_LABELS:
                continue
            entity_name, entity_type = CURRENCY_LABELS[ccy]
            out.append({
                "source_key": BIS_FX_SOURCE_KEY,
                "dataset_version": BIS_FX_DATASET_VERSION,
                "entity_code": ccy,
                "entity_name": entity_name,
                "entity_type": entity_type,
                "variable_code": "FX_TURNOVER_DAILY_USD_MN",
                "variable_name": "Daily FX turnover (BIS Triennial Survey, net-net)",
                "period_start": bounds[0],
                "period_end": bounds[1],
                "value": val,
                "unit": "USD_millions_per_day",
                "vintage_date": None,
                "release_date": None,
                "release_evidence_type": "none",
                "retrieved_at": retrieved_at,
                "source_version": "BIS WS_DER_OTC_TOV",
                "source_url": "https://stats.bis.org/api/v1/data/WS_DER_OTC_TOV",
                "license_code": "BIS statistical terms (attribution required)",
                "raw_payload": {"time_period": tp, "convention": "April survey average, net-net basis"},
            })
            if ccy != "ALL_CURRENCIES" and total and total > 0:
                out.append({
                    "source_key": BIS_FX_SOURCE_KEY,
                    "dataset_version": BIS_FX_DATASET_VERSION,
                    "entity_code": ccy,
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "variable_code": "FX_TURNOVER_SHARE_200PCT",
                    "variable_name": "FX turnover currency share (BIS two-sided 200% sum)",
                    "period_start": bounds[0],
                    "period_end": bounds[1],
                    "value": val / total * 100.0,
                    "unit": "percent_of_global_fx_turnover_200sum",
                    "vintage_date": None,
                    "release_date": None,
                    "release_evidence_type": "none",
                    "retrieved_at": retrieved_at,
                    "source_version": "BIS WS_DER_OTC_TOV",
                    "source_url": "https://stats.bis.org/api/v1/data/WS_DER_OTC_TOV",
                    "license_code": "BIS statistical terms (attribution required)",
                    "raw_payload": {
                        "time_period": tp,
                        "denominator_usd_mn": total,
                        "convention": "Two currencies per FX transaction; shares sum to 200%",
                    },
                })
    return out


def parse_bis_lbs_csv(
    ccy_csv: str,
    cty_csv: str,
    *,
    retrieved_at: datetime,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    ccy_rows = list(csv.DictReader(io.StringIO(ccy_csv)))
    by_q_ccy: dict[str, dict[str, float]] = {}
    for r in ccy_rows:
        val = _finite_float(r.get("OBS_VALUE"))
        if val is not None and r.get("L_REP_CTY") == "5A" and r.get("L_POS_TYPE") == "N":
            by_q_ccy.setdefault(r["TIME_PERIOD"].strip(), {})[r["L_DENOM"].strip()] = val
    for tp, vals in sorted(by_q_ccy.items()):
        bounds = _parse_period_bounds(tp)
        if bounds is None:
            continue
        total = vals.get("TO1")
        for raw_ccy, val in sorted(vals.items()):
            ccy = "ALL_CURRENCIES" if raw_ccy == "TO1" else raw_ccy
            if ccy not in CURRENCY_LABELS:
                continue
            entity_name, entity_type = CURRENCY_LABELS[ccy]
            out.append({
                "source_key": BIS_LBS_SOURCE_KEY,
                "dataset_version": BIS_LBS_DATASET_VERSION,
                "entity_code": ccy,
                "entity_name": entity_name,
                "entity_type": entity_type,
                "variable_code": "LBS_CROSS_BORDER_CLAIMS_USD_MN",
                "variable_name": "Cross-border bank claims by currency (BIS LBS)",
                "period_start": bounds[0],
                "period_end": bounds[1],
                "value": val,
                "unit": "USD_millions",
                "vintage_date": None,
                "release_date": None,
                "release_evidence_type": "none",
                "retrieved_at": retrieved_at,
                "source_version": "BIS WS_LBS_D_PUB",
                "source_url": "https://stats.bis.org/api/v1/data/WS_LBS_D_PUB",
                "license_code": "BIS statistical terms (attribution required)",
                "raw_payload": {"time_period": tp, "dimension": "currency_denomination"},
            })
            if ccy != "ALL_CURRENCIES" and total and total > 0:
                out.append({
                    "source_key": BIS_LBS_SOURCE_KEY,
                    "dataset_version": BIS_LBS_DATASET_VERSION,
                    "entity_code": ccy,
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "variable_code": "LBS_CROSS_BORDER_CLAIMS_SHARE_PCT",
                    "variable_name": "Cross-border bank claims share by currency (BIS LBS)",
                    "period_start": bounds[0],
                    "period_end": bounds[1],
                    "value": val / total * 100.0,
                    "unit": "percent_of_all_currencies",
                    "vintage_date": None,
                    "release_date": None,
                    "release_evidence_type": "none",
                    "retrieved_at": retrieved_at,
                    "source_version": "BIS WS_LBS_D_PUB",
                    "source_url": "https://stats.bis.org/api/v1/data/WS_LBS_D_PUB",
                    "license_code": "BIS statistical terms (attribution required)",
                    "raw_payload": {"time_period": tp, "denominator_usd_mn": total},
                })

    cty_rows = list(csv.DictReader(io.StringIO(cty_csv)))
    by_q_cty: dict[str, dict[str, float]] = {}
    for r in cty_rows:
        val = _finite_float(r.get("OBS_VALUE"))
        if val is not None and r.get("L_DENOM") == "TO1" and r.get("L_POS_TYPE") == "N":
            by_q_cty.setdefault(r["TIME_PERIOD"].strip(), {})[r["L_REP_CTY"].strip()] = val
    for tp, vals in sorted(by_q_cty.items()):
        bounds = _parse_period_bounds(tp)
        if bounds is None:
            continue
        total = vals.get("5A")
        for iso2, val in sorted(vals.items()):
            mapped = BIS_ISO2_TO_ISO3.get(iso2)
            if mapped is None:
                continue
            ent_code, ent_name, ent_type = mapped
            out.append({
                "source_key": BIS_LBS_SOURCE_KEY,
                "dataset_version": BIS_LBS_DATASET_VERSION,
                "entity_code": ent_code,
                "entity_name": ent_name,
                "entity_type": ent_type,
                "variable_code": "LBS_REPORTING_CLAIMS_USD_MN",
                "variable_name": "Cross-border bank claims booked in jurisdiction (BIS LBS)",
                "period_start": bounds[0],
                "period_end": bounds[1],
                "value": val,
                "unit": "USD_millions",
                "vintage_date": None,
                "release_date": None,
                "release_evidence_type": "none",
                "retrieved_at": retrieved_at,
                "source_version": "BIS WS_LBS_D_PUB",
                "source_url": "https://stats.bis.org/api/v1/data/WS_LBS_D_PUB",
                "license_code": "BIS statistical terms (attribution required)",
                "raw_payload": {"time_period": tp, "dimension": "reporting_country"},
            })
            if ent_code != "ALL_REPORTING" and total and total > 0:
                out.append({
                    "source_key": BIS_LBS_SOURCE_KEY,
                    "dataset_version": BIS_LBS_DATASET_VERSION,
                    "entity_code": ent_code,
                    "entity_name": ent_name,
                    "entity_type": ent_type,
                    "variable_code": "LBS_REPORTING_CLAIMS_SHARE_PCT",
                    "variable_name": "Global share of cross-border bank claims booked in jurisdiction (BIS LBS)",
                    "period_start": bounds[0],
                    "period_end": bounds[1],
                    "value": val / total * 100.0,
                    "unit": "percent_of_bis_reporting_total",
                    "vintage_date": None,
                    "release_date": None,
                    "release_evidence_type": "none",
                    "retrieved_at": retrieved_at,
                    "source_version": "BIS WS_LBS_D_PUB",
                    "source_url": "https://stats.bis.org/api/v1/data/WS_LBS_D_PUB",
                    "license_code": "BIS statistical terms (attribution required)",
                    "raw_payload": {"time_period": tp, "denominator_usd_mn": total},
                })
    return out


def parse_bis_credit_and_policy_csv(
    tc_market_csv: str,
    tc_nominal_govt_csv: str,
    cbpol_csv: str,
    *,
    retrieved_at: datetime,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    sector_map = {
        ("G", "M"): ("CREDIT_GOVT_MARKET_GDP", "General government credit at market value (% of GDP, BIS)"),
        ("G", "N"): ("CREDIT_GOVT_NOMINAL_GDP", "General government credit at nominal value (% of GDP, BIS)"),
        ("P", "M"): ("CREDIT_PRIVATE_NF_GDP", "Private non-financial sector credit (% of GDP, BIS)"),
        ("H", "M"): ("CREDIT_HOUSEHOLDS_GDP", "Household & NPISH credit (% of GDP, BIS)"),
        ("N", "M"): ("CREDIT_CORP_NF_GDP", "Non-financial corporate credit (% of GDP, BIS)"),
    }
    for csv_text in (tc_market_csv, tc_nominal_govt_csv):
        for r in csv.DictReader(io.StringIO(csv_text)):
            val = _finite_float(r.get("OBS_VALUE"))
            if val is None or r.get("UNIT_TYPE") != "770" or r.get("TC_ADJUST") != "A":
                continue
            mapped = BIS_ISO2_TO_ISO3.get((r.get("BORROWERS_CTY") or "").strip())
            vinfo = sector_map.get(((r.get("TC_BORROWERS") or "").strip(), (r.get("VALUATION") or "").strip()))
            bounds = _parse_period_bounds((r.get("TIME_PERIOD") or "").strip())
            if mapped is None or vinfo is None or bounds is None:
                continue
            ent_code, ent_name, ent_type = mapped
            var_code, var_name = vinfo
            out.append({
                "source_key": BIS_CREDIT_SOURCE_KEY,
                "dataset_version": BIS_CREDIT_DATASET_VERSION,
                "entity_code": ent_code,
                "entity_name": ent_name,
                "entity_type": ent_type,
                "variable_code": var_code,
                "variable_name": var_name,
                "period_start": bounds[0],
                "period_end": bounds[1],
                "value": val,
                "unit": "percent_of_gdp",
                "vintage_date": None,
                "release_date": None,
                "release_evidence_type": "none",
                "retrieved_at": retrieved_at,
                "source_version": "BIS WS_TC",
                "source_url": "https://stats.bis.org/api/v1/data/WS_TC",
                "license_code": "BIS statistical terms (attribution required)",
                "raw_payload": {
                    "time_period": r.get("TIME_PERIOD"),
                    "borrower_sector": r.get("TC_BORROWERS"),
                    "valuation": r.get("VALUATION"),
                },
            })

    # Keep December (year-end) + latest available month per entity for policy rates so
    # annual/quarterly historical comparisons stay clean without exploding row volume,
    # while preserving exact monthly period_start/period_end.
    cb_rows_by_area: dict[str, list[tuple[str, float]]] = {}
    for r in csv.DictReader(io.StringIO(cbpol_csv)):
        val = _finite_float(r.get("OBS_VALUE"))
        if val is None:
            continue
        area = (r.get("REF_AREA") or "").strip()
        tp = (r.get("TIME_PERIOD") or "").strip()
        if area in BIS_ISO2_TO_ISO3 and _MONTH_RE.match(tp):
            cb_rows_by_area.setdefault(area, []).append((tp, val))
    for area, items in sorted(cb_rows_by_area.items()):
        items.sort()
        ent_code, ent_name, ent_type = BIS_ISO2_TO_ISO3[area]
        latest_tp = items[-1][0]
        for tp, val in items:
            if not (tp.endswith("-12") or tp.endswith("-03") or tp.endswith("-06") or tp.endswith("-09") or tp == latest_tp):
                continue
            bounds = _parse_period_bounds(tp)
            if bounds is None:
                continue
            out.append({
                "source_key": BIS_CREDIT_SOURCE_KEY,
                "dataset_version": BIS_CREDIT_DATASET_VERSION,
                "entity_code": ent_code,
                "entity_name": ent_name,
                "entity_type": ent_type,
                "variable_code": "POLICY_RATE_PCT",
                "variable_name": "Central bank policy rate (BIS WS_CBPOL)",
                "period_start": bounds[0],
                "period_end": bounds[1],
                "value": val,
                "unit": "percent_per_annum",
                "vintage_date": None,
                "release_date": None,
                "release_evidence_type": "none",
                "retrieved_at": retrieved_at,
                "source_version": "BIS WS_CBPOL",
                "source_url": "https://stats.bis.org/api/v1/data/WS_CBPOL",
                "license_code": "BIS statistical terms (attribution required)",
                "raw_payload": {
                    "time_period": tp,
                    "ref_area": area,
                    "euro_transition_note": (
                        "DE and FR national central-bank policy rates end in 1998-12; "
                        "ECB policy rate is recorded under EUR (XM) from 1999-01."
                        if area in {"DE", "FR", "XM"}
                        else None
                    ),
                },
            })
    return out


def _col_index(ref: str) -> int:
    m = _CELL_RE.match(ref)
    if m is None:
        raise ValueError(f"invalid cell ref {ref!r}")
    idx = 0
    for ch in m.group(1):
        idx = idx * 26 + ord(ch) - 64
    return idx - 1


def _iter_xlsx_dicts(path: Path, worksheet_xml: str) -> Iterable[dict[str, str | None]]:
    with ZipFile(path) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sroot = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sroot.findall("a:si", _NS):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{_NS['a']}}}t")))
        root = ET.fromstring(zf.read(worksheet_xml))
        headers: list[str] = []
        for r_idx, row in enumerate(root.findall("a:sheetData/a:row", _NS)):
            vals: list[str | None] = []
            for cell in row.findall("a:c", _NS):
                c_idx = _col_index(cell.attrib["r"])
                while len(vals) < c_idx:
                    vals.append(None)
                v_el = cell.find("a:v", _NS)
                if cell.attrib.get("t") == "inlineStr":
                    vals.append("".join(t.text or "" for t in cell.iter(f"{{{_NS['a']}}}t")))
                elif v_el is not None and v_el.text is not None:
                    vals.append(shared[int(v_el.text)] if cell.attrib.get("t") == "s" else v_el.text)
                else:
                    vals.append(None)
            if r_idx == 0:
                headers = [str(v).strip() if v is not None else "" for v in vals]
                continue
            yield {headers[i]: vals[i] for i in range(min(len(headers), len(vals))) if headers[i]}


def parse_pwt11_xlsx(
    path: Path,
    *,
    retrieved_at: datetime,
    allowed_iso3: set[str] | None = None,
) -> list[dict[str, Any]]:
    universe = allowed_iso3 or set(RESEARCH_COUNTRY_PANEL)
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    direct_vars = (
        ("rgdpo", "PWT_RGDPO_PPP2021_MN", "Output-side real GDP at chained PPPs (PWT 11.0)", "millions_2021_ppp_usd"),
        ("rgdpna", "PWT_RGDPNA_CONST2021_MN", "Real GDP at constant 2021 national prices (PWT 11.0)", "millions_2021_usd_const_na"),
        ("emp", "PWT_EMP_MILLIONS", "Persons engaged (PWT 11.0)", "millions_persons"),
        ("avh", "PWT_AVH_HOURS", "Average annual hours worked per person engaged (PWT 11.0)", "hours_per_worker"),
        ("hc", "PWT_HUMAN_CAPITAL_INDEX", "Human capital index (PWT 11.0)", "index"),
        ("cn", "PWT_CAPITAL_STOCK_PPP2021_MN", "Capital stock at current PPPs (PWT 11.0)", "millions_2021_ppp_usd"),
        ("rnna", "PWT_CAPITAL_STOCK_CONST2021_MN", "Capital stock at constant 2021 national prices (PWT 11.0)", "millions_2021_usd_const_na"),
        ("ctfp", "PWT_CTFP_USA1", "TFP level at current PPPs, USA=1 (PWT 11.0)", "ratio_usa_eq_1"),
        ("rtfpna", "PWT_RTFPNA_2021_1", "TFP at constant national prices, 2021=1 (PWT 11.0)", "index_2021_eq_1"),
    )
    out: list[dict[str, Any]] = []
    release_dt = datetime(2025, 10, 7, tzinfo=timezone.utc)
    for rec in _iter_xlsx_dicts(path, "xl/worksheets/sheet3.xml"):
        iso3 = (rec.get("countrycode") or "").strip().upper()
        if iso3 not in universe or not rec.get("year"):
            continue
        yr = int(float(rec["year"]))
        bounds = _parse_period_bounds(str(yr))
        if bounds is None:
            continue
        cname = str(rec.get("country") or RESEARCH_COUNTRY_PANEL.get(iso3, iso3))
        for raw_col, var_code, var_name, unit in direct_vars:
            val = _finite_float(rec.get(raw_col))
            if val is None:
                continue
            out.append({
                "source_key": PWT_SOURCE_KEY,
                "dataset_version": PWT_DATASET_VERSION,
                "entity_code": iso3,
                "entity_name": cname,
                "entity_type": "country",
                "variable_code": var_code,
                "variable_name": var_name,
                "period_start": bounds[0],
                "period_end": bounds[1],
                "value": val,
                "unit": unit,
                "vintage_date": PWT_RELEASE_DATE,
                "release_date": release_dt,
                "release_evidence_type": "dataset_release",
                "retrieved_at": retrieved_at,
                "source_version": f"Penn World Table 11.0 (sha256:{sha256[:12]})",
                "source_url": "https://doi.org/10.34894/FABVLR",
                "license_code": "CC-BY-4.0",
                "raw_payload": {"ppp_benchmark_year": 2021, "raw_column": raw_col},
            })
        rgdpo = _finite_float(rec.get("rgdpo"))
        emp = _finite_float(rec.get("emp"))
        avh = _finite_float(rec.get("avh"))
        if rgdpo is not None and emp is not None and emp > 0:
            out.append({
                "source_key": PWT_SOURCE_KEY,
                "dataset_version": PWT_DATASET_VERSION,
                "entity_code": iso3,
                "entity_name": cname,
                "entity_type": "country",
                "variable_code": "PWT_GDP_PER_WORKER_PPP2021",
                "variable_name": "Output-side real GDP per worker at chained 2021 PPPs (PWT 11.0)",
                "period_start": bounds[0],
                "period_end": bounds[1],
                "value": rgdpo / emp,
                "unit": "2021_ppp_usd_per_worker",
                "vintage_date": PWT_RELEASE_DATE,
                "release_date": release_dt,
                "release_evidence_type": "dataset_release",
                "retrieved_at": retrieved_at,
                "source_version": f"Penn World Table 11.0 (sha256:{sha256[:12]})",
                "source_url": "https://doi.org/10.34894/FABVLR",
                "license_code": "CC-BY-4.0",
                "raw_payload": {"formula": "rgdpo / emp", "ppp_benchmark_year": 2021},
            })
            if avh is not None and avh > 0:
                out.append({
                    "source_key": PWT_SOURCE_KEY,
                    "dataset_version": PWT_DATASET_VERSION,
                    "entity_code": iso3,
                    "entity_name": cname,
                    "entity_type": "country",
                    "variable_code": "PWT_GDP_PER_HOUR_PPP2021",
                    "variable_name": "Output-side real GDP per hour at chained 2021 PPPs (PWT 11.0)",
                    "period_start": bounds[0],
                    "period_end": bounds[1],
                    "value": rgdpo / (emp * avh) * 1_000_000.0,
                    "unit": "2021_ppp_usd_per_hour",
                    "vintage_date": PWT_RELEASE_DATE,
                    "release_date": release_dt,
                    "release_evidence_type": "dataset_release",
                    "retrieved_at": retrieved_at,
                    "source_version": f"Penn World Table 11.0 (sha256:{sha256[:12]})",
                    "source_url": "https://doi.org/10.34894/FABVLR",
                    "license_code": "CC-BY-4.0",
                    "raw_payload": {"formula": "rgdpo_mn * 1e6 / (emp_mn * 1e6 * avh)", "ppp_benchmark_year": 2021},
                })
    return out


def parse_maddison2023_xlsx(
    path: Path,
    *,
    retrieved_at: datetime,
    allowed_iso3: set[str] | None = None,
    min_year: int = 1500,
) -> list[dict[str, Any]]:
    universe = allowed_iso3 or set(RESEARCH_COUNTRY_PANEL)
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    release_dt = datetime(2024, 4, 18, tzinfo=timezone.utc)
    out: list[dict[str, Any]] = []
    for rec in _iter_xlsx_dicts(path, "xl/worksheets/sheet5.xml"):
        iso3 = (rec.get("countrycode") or "").strip().upper()
        if iso3 not in universe or not rec.get("year"):
            continue
        yr = int(float(rec["year"]))
        if yr < min_year:
            continue
        bounds = _parse_period_bounds(str(yr))
        if bounds is None:
            continue
        cname = str(rec.get("country") or RESEARCH_COUNTRY_PANEL.get(iso3, iso3))
        for raw_col, var_code, var_name, unit in (
            ("gdppc", "MPD_GDPPC_2011INTL", "Historical real GDP per capita in 2011 international $ (Maddison 2023)", "2011_intl_dollars"),
            ("pop", "MPD_POP_THOUSANDS", "Historical mid-year population (Maddison 2023)", "thousands_persons"),
        ):
            val = _finite_float(rec.get(raw_col))
            if val is None:
                continue
            out.append({
                "source_key": MPD_SOURCE_KEY,
                "dataset_version": MPD_DATASET_VERSION,
                "entity_code": iso3,
                "entity_name": cname,
                "entity_type": "country",
                "variable_code": var_code,
                "variable_name": var_name,
                "period_start": bounds[0],
                "period_end": bounds[1],
                "value": val,
                "unit": unit,
                "vintage_date": MPD_RELEASE_DATE,
                "release_date": release_dt,
                "release_evidence_type": "dataset_release",
                "retrieved_at": retrieved_at,
                "source_version": f"Maddison Project Database 2023 (sha256:{sha256[:12]})",
                "source_url": "https://doi.org/10.34894/INZBF2",
                "license_code": "CC-BY-4.0",
                "raw_payload": {
                    "ppp_benchmark_year": 2011,
                    "region": rec.get("region"),
                    "note": "Reconstructed historical series; modern national-accounts definitions do not apply to pre-modern years.",
                },
            })
    return out
