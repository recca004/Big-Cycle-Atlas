import { useEffect, useMemo, useState } from "react";
import { fetchObservatorySeries } from "@/lib/api/client";
import type { MeasureHistory } from "@/types/observatory";

const MEASURES = [
  ["GDP_CURRENT_USD", "Nominal GDP", false],
  ["GDP_CURRENT_USD", "Nominal GDP — global share", true],
  ["GDP_PPP_CURRENT_INTL", "PPP GDP", false],
  ["GDP_PPP_CURRENT_INTL", "PPP GDP — global share", true],
  ["GDP_REAL_CONSTANT_USD", "Real GDP (2015 US$)", false],
  ["GDP_REAL_CONSTANT_USD", "Real GDP — global share", true],
  ["GDP_PER_CAPITA", "GDP per capita", false],
  ["MERCHANDISE_EXPORTS_USD", "Goods exports", false],
  ["MERCHANDISE_EXPORTS_USD", "Goods exports — global share", true],
  ["MERCHANDISE_IMPORTS_USD", "Goods imports", false],
  ["MERCHANDISE_IMPORTS_USD", "Goods imports — global share", true],
  ["COMMERCIAL_SERVICE_EXPORTS_USD", "Service exports", false],
  ["COMMERCIAL_SERVICE_EXPORTS_USD", "Service exports — global share", true],
  ["COMMERCIAL_SERVICE_IMPORTS_USD", "Service imports", false],
  ["COMMERCIAL_SERVICE_IMPORTS_USD", "Service imports — global share", true],
  ["EXPORTS_GDP", "Exports share of GDP", false],
  ["MILITARY_EXPENDITURE_USD", "Military expenditure", false],
  ["MILITARY_EXPENDITURE_USD", "Military expenditure — global share", true],
  ["MILITARY_EXPENDITURE_GDP", "Military expenditure / GDP", false],
  ["RND_EXPENDITURE_GDP", "R&D expenditure / GDP", false],
  ["PATENT_APPLICATIONS_RESIDENT", "Resident patents", false],
  ["PATENT_APPLICATIONS_RESIDENT", "Resident patents — global share", true],
  ["RESEARCHERS_PER_MILLION", "Researchers / million", false],
  ["HIGH_TECHNOLOGY_EXPORTS_USD", "High-tech exports", false],
  ["HIGH_TECHNOLOGY_EXPORTS_USD", "High-tech exports — global share", true],
  ["LABOUR_PRODUCTIVITY_PER_HOUR", "Labour productivity", false],
  ["TERTIARY_ENROLLMENT", "Tertiary enrollment", false],
  ["STOCK_MARKET_CAP_GDP", "Listed market cap / GDP", false],
  ["DOMESTIC_CREDIT_PRIVATE_GDP", "Private credit / GDP", false],
  ["BROAD_MONEY_GDP", "Broad money / GDP", false],
  ["GOVERNMENT_DEBT_GDP", "Government debt / GDP", false],
] as const;

const COLORS = ["#b78b2c", "#203858", "#3d7a8a", "#7a4b8c", "#8c5a3d", "#52643a", "#8c3d4b", "#637083"];

export function RelativePowerHistory({ rangeStart }: { rangeStart: number }) {
  const [selection, setSelection] = useState("0");
  const selected = MEASURES[Number(selection)] ?? MEASURES[0];
  const indicator = selected[0];
  const worldShare = selected[2];
  const [payload, setPayload] = useState<MeasureHistory | null>(null);

  useEffect(() => {
    let alive = true;
    fetchObservatorySeries({ indicator, startYear: rangeStart, worldShare })
      .then((next) => alive && setPayload(next));
    return () => { alive = false; };
  }, [indicator, rangeStart, worldShare]);

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
        <select className="glass-button" value={selection} onChange={(event) => setSelection(event.target.value)}>
          {MEASURES.map(([code, label, share], index) => <option key={`${code}:${share}`} value={index}>{label}</option>)}
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
        Latest vintages only; {payload?.countries[0]?.unit ?? "source units"} · {payload?.countries[0]?.source ?? "source unavailable"}
        {payload?.world_share ? ` · denominator ${payload.denominator_entity}` : ""}. Gaps are actual missing periods.
      </p>
    </div>
  );
}
