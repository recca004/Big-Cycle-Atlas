"""Build the clean, self-contained ChatGPT independent-review ZIP package (§29).

Output: `.dev/packages/BigCycleAtlas_ChatGPT_Review_V3.zip`

Strictly excludes:
- `.env*`, API keys, database passwords or credentials
- Private portfolio, watchlist, or personal workspace/settings records
- Raw noncommercial-review source bundles (`.dev/tmp/*`)
- Unnecessary raw market-price dumps
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEV = ROOT / ".dev"
REPORTS = DEV / "reports"
EXPORT = REPORTS / "export"
PACKAGES = DEV / "packages"
OUT_ZIP = PACKAGES / "BigCycleAtlas_ChatGPT_Review_V3.zip"

FORBIDDEN_SUBSTRINGS = (
    ".env",
    "secret",
    "credential",
    "password",
    "portfolio",
    "watchlist",
    "settings",
    "market_observations",
    "jstdatasetr6.xlsx",
    "wp2694.zip",
)


def main() -> None:
    PACKAGES.mkdir(parents=True, exist_ok=True)
    included: list[tuple[Path, str]] = []

    top_docs = [
        (REPORTS / "CHATGPT_HANDOVER.md", "CHATGPT_HANDOVER.md"),
        (REPORTS / "ATLAS_RESEARCH_1980_PRESENT.md", "ATLAS_RESEARCH_1980_PRESENT.md"),
        (REPORTS / "THEORY_VALIDATION_RESEARCH.md", "THEORY_VALIDATION_RESEARCH.md"),
        (REPORTS / "research_manifest.json", "research_manifest.json"),
        (DEV / "THEORY_VALIDATION_50.md", "docs/THEORY_VALIDATION_50.md"),
        (DEV / "SCIENTIFIC_RESEARCH_FOUNDATION.md", "docs/SCIENTIFIC_RESEARCH_FOUNDATION.md"),
        (DEV / "DATA_SOURCES.md", "docs/DATA_SOURCES.md"),
        (DEV / "HYPOTHESIS_REGISTRY.md", "docs/HYPOTHESIS_REGISTRY.md"),
        (DEV / "VALIDATION_QUESTION_REGISTRY.json", "docs/VALIDATION_QUESTION_REGISTRY.json"),
    ]
    for src, arc in top_docs:
        if src.is_file():
            included.append((src, arc))

    for c_md in sorted((REPORTS / "countries").glob("*.md")):
        included.append((c_md, f"countries/{c_md.name}"))

    for exp_file in sorted(EXPORT.iterdir()):
        if not exp_file.is_file():
            continue
        lower = exp_file.name.lower()
        if any(bad in lower for bad in FORBIDDEN_SUBSTRINGS):
            continue
        included.append((exp_file, f"export/{exp_file.name}"))

    # Audit every archive path and content against forbidden tokens / DSN leaks
    for src, arc in included:
        arc_low = arc.lower()
        if any(bad in arc_low for bad in FORBIDDEN_SUBSTRINGS):
            raise RuntimeError(f"Refusing to package restricted file {arc}")
        sample = src.read_text(encoding="utf-8", errors="ignore")
        if "BCA_FRED_API_KEY=" in sample and "your_32_char" not in sample:
            raise RuntimeError(f"Potential credential detected in {src}")
        if "postgresql+psycopg://" in sample:
            raise RuntimeError(f"Database DSN detected in {src}")

    with zipfile.ZipFile(OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        readme = {
            "package": "BigCycleAtlas_ChatGPT_Review_V3",
            "purpose": "Self-contained scientific validation & international-power research review package",
            "excluded_by_policy": [
                "API keys, .env files, database DSNs/passwords",
                "Private portfolio, watchlist and user workspace state",
                "Unnecessary daily market price dumps",
                "Raw JST R6 Excel bundle (CC-BY-NC-SA-4.0 review-gated)",
            ],
            "files_count": len(included),
            "files": [arc for _, arc in included],
        }
        zf.writestr("PACKAGE_INDEX.json", json.dumps(readme, indent=2))
        for src, arc in included:
            zf.write(src, arcname=arc)

    print({
        "zip_path": str(OUT_ZIP),
        "size_bytes": OUT_ZIP.stat().st_size,
        "files_included": len(included) + 1,
    })


if __name__ == "__main__":
    main()
