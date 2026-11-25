import { useEffect, useMemo, useState } from "react";
import { fetchObservatoryCoverage } from "@/lib/api/client";
import type { CoverageSeries } from "@/types/observatory";

const COUNTRY_ORDER = ["USA", "CHN", "GBR", "DEU", "FRA", "JPN", "IND", "CHE"];

function year(period: string | null): string {
  return period ? period.slice(0, 4) : "—";
}

function SeriesCell({ series }: { series: CoverageSeries[] | undefined }) {
  const first = series?.[0];
  if (!first) return <td aria-label="No observations">—</td>;
  const latest = series.reduce((a, b) => ((a.latest_period ?? "") > (b.latest_period ?? "") ? a : b));
  const earliest = series.reduce((a, b) => ((a.earliest_period ?? "9999") < (b.earliest_period ?? "9999") ? a : b));
  const periods = series.reduce((total, item) => total + item.periods, 0);
  const sources = [...new Set(series.map((item) => item.source))].join(" + ");
  return (
    <td title={`${sources}; ${periods} distinct periods through ${latest.latest_period ?? "unknown"}`}>
      <strong>{year(earliest.earliest_period)}</strong>
      <span className="obs-muted"> {year(latest.latest_period)} · {periods}</span>
    </td>
  );
}

export function CoverageMatrix() {
  const [series, setSeries] = useState<CoverageSeries[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetchObservatoryCoverage()
      .then((payload) => {
        if (alive) setSeries(payload.series);
      })
      .catch((err: unknown) => {
        if (alive) setError(err instanceof Error ? err.message : "Coverage unavailable");
      });
    return () => {
      alive = false;
    };
  }, []);

  const rows = useMemo(() => {
    const byIndicator = new Map<string, { name: string; unit: string | null; cells: Map<string, CoverageSeries[]> }>();
    for (const item of series ?? []) {
      const row = byIndicator.get(item.indicator) ?? { name: item.indicator_name, unit: item.unit, cells: new Map() };
      row.cells.set(item.country, [...(row.cells.get(item.country) ?? []), item]);
      byIndicator.set(item.indicator, row);
    }
    return [...byIndicator.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [series]);

  if (error) return <p className="obs-muted">Coverage audit unavailable: {error}</p>;
  if (!series) return <p className="obs-muted">Loading verified raw-observation coverage…</p>;

  return (
    <div className="obs-coverage-wrap" role="region" aria-labelledby="coverage-caption" tabIndex={0}>
      <table className="obs-coverage">
        <caption id="coverage-caption">
          Raw observation coverage by indicator and tracked power. Cells show earliest year, latest year and distinct periods; missing cells mean no verified observations.
        </caption>
        <thead>
          <tr>
            <th scope="col">Indicator</th>
            {COUNTRY_ORDER.map((iso3) => <th key={iso3} scope="col">{iso3}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map(([code, row]) => (
            <tr key={code}>
              <th scope="row">
                <strong>{row.name}</strong>
                <span className="obs-muted">{code}{row.unit ? ` · ${row.unit}` : ""}</span>
              </th>
              {COUNTRY_ORDER.map((iso3) => <SeriesCell key={iso3} series={row.cells.get(iso3)} />)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
