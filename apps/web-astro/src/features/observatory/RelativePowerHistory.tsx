import { useEffect, useMemo, useState } from "react";
import { fetchObservatorySeries } from "@/lib/api/client";
import type { MeasureHistory } from "@/types/observatory";

const MEASURES = [
  ["GDP_CURRENT_USD", "Nominal GDP"],
  ["GDP_PER_CAPITA", "GDP per capita"],
  ["EXPORTS_GDP", "Exports share of GDP"],
  ["MILITARY_EXPENDITURE_USD", "Military expenditure"],
  ["MILITARY_EXPENDITURE_GDP", "Military expenditure / GDP"],
  ["LABOUR_PRODUCTIVITY_PER_HOUR", "Labour productivity"],
  ["TERTIARY_ENROLLMENT", "Tertiary enrollment"],
  ["GOVERNMENT_DEBT_GDP", "Government debt / GDP"],
] as const;

const COLORS = ["#b78b2c", "#203858", "#3d7a8a", "#7a4b8c", "#8c5a3d", "#52643a", "#8c3d4b", "#637083"];

export function RelativePowerHistory({ rangeStart }: { rangeStart: number }) {
  const [indicator, setIndicator] = useState<string>(MEASURES[0][0]);
  const [payload, setPayload] = useState<MeasureHistory | null>(null);

  useEffect(() => {
    let alive = true;
    fetchObservatorySeries({ indicator, startYear: rangeStart })
      .then((next) => alive && setPayload(next));
    return () => { alive = false; };
  }, [indicator, rangeStart]);

  const chart = useMemo(() => {
    const countries = payload?.countries ?? [];
    const points = countries.flatMap((country) => country.points);
    if (!points.length) return null;
    const minX = Math.min(...points.map((p) => p.period));
    const maxX = Math.max(...points.map((p) => p.period));
    const maxY = Math.max(...points.map((p) => p.value));
    const minY = Math.min(0, ...points.map((p) => p.value));
    const x = (year: number) => 56 + ((year - minX) / Math.max(1, maxX - minX)) * 840;
    const y = (value: number) => 250 - ((value - minY) / Math.max(1e-12, maxY - minY)) * 210;
    return { countries, minX, maxX, maxY, x, y };
  }, [payload]);

  return (
    <div className="measure-history">
      <label className="obs-measure-picker">
        <span className="obs-picker-kicker">Verified measure</span>
        <select className="glass-button" value={indicator} onChange={(event) => setIndicator(event.target.value)}>
          {MEASURES.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
        </select>
      </label>
      {chart ? (
        <svg viewBox="0 0 940 285" className="measure-chart" role="img" aria-label={`${payload?.countries[0]?.indicator_name ?? "Historical measure"} by tracked power`}>
          {[chart.minX, Math.round((chart.minX + chart.maxX) / 2), chart.maxX].map((year) => (
            <g key={year}>
              <line x1={chart.x(year)} x2={chart.x(year)} y1="30" y2="252" className="measure-grid" />
              <text x={chart.x(year)} y="272" textAnchor="middle">{year}</text>
            </g>
          ))}
          {chart.countries.map((country, index) => {
            const path = country.points.map((point, i) => `${i ? "L" : "M"}${chart.x(point.period)},${chart.y(point.value)}`).join(" ");
            const last = country.points.at(-1);
            return (
              <g key={country.iso3}>
                <path d={path} fill="none" stroke={COLORS[index % COLORS.length]} strokeWidth="2" />
                {last && <text x={chart.x(last.period) - 4} y={chart.y(last.value) - 6} textAnchor="end" fill={COLORS[index % COLORS.length]}>{country.iso3}</text>}
              </g>
            );
          })}
        </svg>
      ) : <p className="obs-muted">No verified observations in this range.</p>}
      <p className="obs-muted">
        Latest vintages only; {payload?.countries[0]?.unit ?? "source units"} · {payload?.countries[0]?.source ?? "source unavailable"}. Gaps are actual missing periods.
      </p>
    </div>
  );
}
