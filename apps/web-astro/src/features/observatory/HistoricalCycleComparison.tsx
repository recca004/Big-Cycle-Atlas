import { useMemo } from "react";
import type { ObservatoryCountry, ObservatoryHistoryPoint } from "@/types/observatory";
import { STAGES, STAGE_LABELS } from "./stages";

interface Props {
  countries: ObservatoryCountry[];
  selectedIso3: string | null;
  onSelect: (iso3: string) => void;
  demo?: boolean;
}

interface Segment {
  stage: string;
  phase: string;
  from: number;
  to: number;
}

const WIDTH = 1000;
const LEFT = 122;
const RIGHT = 28;
const TOP = 34;
const LANE = 34;
const AXIS_H = 30;

function periodPosition(period: string): number | null {
  const match = /^(\d{4})(?:-Q([1-4]))?$/.exec(period);
  if (!match) return null;
  const quarter = match[2] ? Number(match[2]) : 1;
  return Number(match[1]) + (quarter - 1) / 4;
}

function segmentsFromHistory(history: ObservatoryHistoryPoint[]): Segment[] {
  const segments: Segment[] = [];
  for (const point of history) {
    if (!point.stage) continue;
    const position = periodPosition(point.period);
    if (position === null) continue;
    const end = point.period.includes("-Q") ? position + 0.25 : position + 1;
    const phase = point.phase ?? "unclassified phase";
    const last = segments[segments.length - 1];
    if (last && last.stage === point.stage && last.phase === phase) {
      last.to = end;
    } else {
      segments.push({ stage: point.stage, phase, from: position, to: end });
    }
  }
  return segments;
}

const stageClass = (stage: string) => `stage-${stage.toLowerCase().replaceAll("_", "-")}`;

export function HistoricalCycleComparison({ countries, selectedIso3, onSelect, demo = false }: Props) {
  const rows = useMemo(
    () => countries.map((country) => ({ country, segments: segmentsFromHistory(country.history) })),
    [countries],
  );
  const positions = rows.flatMap((row) => row.segments.flatMap((segment) => [segment.from, segment.to]));
  const minYear = Math.floor(Math.min(...positions, 2000));
  const maxYear = Math.ceil(Math.max(...positions, minYear + 1));
  const plotWidth = WIDTH - LEFT - RIGHT;
  const height = TOP + rows.length * LANE + AXIS_H;
  const x = (position: number) => Number((LEFT + ((position - minYear) / Math.max(1, maxYear - minYear)) * plotWidth).toFixed(3));
  const ticks = Array.from({ length: 6 }, (_, index) => Math.round(minYear + ((maxYear - minYear) * index) / 5));

  return (
    <div className="history-comparison">
      <div className="history-country-strip" role="group" aria-label="Highlight a power">
        {countries.map((country) => (
          <button
            key={country.iso3}
            type="button"
            className={country.iso3 === selectedIso3 ? "glass-button active" : "glass-button"}
            aria-pressed={country.iso3 === selectedIso3}
            onClick={() => onSelect(country.iso3)}
          >
            {country.iso3}
          </button>
        ))}
      </div>

      <div className="history-chart-wrap" role="region" aria-label="Historical cycle comparison chart" tabIndex={0}>
        <svg viewBox={`0 0 ${WIDTH} ${height}`} className="history-chart" role="img" aria-label={`Stage bands for eight powers, ${minYear} through ${maxYear}`}>
          {ticks.map((year) => (
            <g key={year} className="history-axis-tick">
              <line x1={x(year)} y1={TOP - 8} x2={x(year)} y2={height - AXIS_H + 8} />
              <text x={x(year)} y={height - 8} textAnchor="middle">{year}</text>
            </g>
          ))}
          {rows.map(({ country, segments }, rowIndex) => {
            const y = TOP + rowIndex * LANE;
            const selected = country.iso3 === selectedIso3;
            return (
              <g key={country.iso3} className={selected ? "history-lane selected" : "history-lane"}>
                <text x={LEFT - 12} y={y + LANE / 2 + 4} textAnchor="end" className="history-country-label">
                  {country.iso3}
                </text>
                <line x1={LEFT} x2={WIDTH - RIGHT} y1={y + LANE / 2} y2={y + LANE / 2} className="history-lane-line" />
                {segments.map((segment) => (
                  <rect
                    key={`${country.iso3}-${segment.from}-${segment.stage}`}
                    x={x(segment.from)}
                    y={y + 7}
                    width={Number(Math.max(2, x(segment.to) - x(segment.from)).toFixed(3))}
                    height={LANE - 14}
                    rx="4"
                    className={`history-segment ${stageClass(segment.stage)}`}
                  >
                    <title>{`${country.name}: ${STAGE_LABELS[segment.stage] ?? segment.stage}, ${segment.from.toFixed(2)}–${segment.to.toFixed(2)}. ${segment.phase}. ${demo ? "Demonstration" : "Production"} classification.`}</title>
                  </rect>
                ))}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="history-legend" aria-label="Stage legend">
        {STAGES.map((stage) => (
          <span key={stage} className="history-legend-item">
            <span className={`history-key ${stageClass(stage)}`} aria-hidden="true" />
            {STAGE_LABELS[stage]}
          </span>
        ))}
      </div>

      <details className="history-data-details">
        <summary>Read the comparison as transition data</summary>
        <table className="obs-changes">
          <thead>
            <tr><th>Power</th><th>Transition</th><th>Period</th><th>Reason</th></tr>
          </thead>
          <tbody>
            {countries.flatMap((country) =>
              country.transitions.slice(-5).map((transition) => (
                <tr key={`${country.iso3}-${transition.period}-${transition.to}`}>
                  <td>{country.iso3}</td>
                  <td>{STAGE_LABELS[transition.to] ?? transition.to}</td>
                  <td>{transition.period}</td>
                  <td>{transition.reason}</td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </details>
    </div>
  );
}
