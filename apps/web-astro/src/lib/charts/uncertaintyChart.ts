/** Uncertainty-band chart (Mission 4 §9).
 *  Score line + provider-published 90% CI band, aligned by exact period.
 *  Periods without published diagnostics are left as gaps — never
 *  interpolated. No confidence percentage is derived from source counts. */

import type * as echarts from "echarts";
import { baseChartOption } from "./EChart";

export interface ScorePoint {
  period_start: string;
  value: number;
}

export interface DiagnosticPoint {
  period_start: string;
  ci_lower_bound?: number | null;
  ci_upper_bound?: number | null;
  source_count?: number | null;
}

export type UncertaintyOption =
  | { kind: "chart"; option: echarts.EChartsOption; diagnosticsPresent: boolean }
  | { kind: "empty"; reason: string };

const yearOf = (iso: string) => iso.slice(0, 4);

/** Merge score observations and diagnostic points on their exact
 *  period_start. Returns null when there is nothing to draw. */
export function buildUncertaintyOption(
  scores: ScorePoint[],
  diagnostics: DiagnosticPoint[],
  label: string,
): UncertaintyOption {
  const periods = new Set<string>();
  for (const s of scores) periods.add(s.period_start);
  for (const d of diagnostics) periods.add(d.period_start);
  if (periods.size === 0) {
    return { kind: "empty", reason: `No ${label} observations or diagnostics.` };
  }
  const axis = [...periods].sort();
  const scoreBy = new Map(scores.map((s) => [s.period_start, s.value]));
  const lowerBy = new Map(
    diagnostics.map((d) => [d.period_start, d.ci_lower_bound ?? null]),
  );
  const upperBy = new Map(
    diagnostics.map((d) => [d.period_start, d.ci_upper_bound ?? null]),
  );
  const countBy = new Map(
    diagnostics.map((d) => [d.period_start, d.source_count ?? null]),
  );

  const hasBounds = diagnostics.some(
    (d) => d.ci_lower_bound != null && d.ci_upper_bound != null,
  );

  const lower = axis.map((p) => lowerBy.get(p) ?? null);
  const band = axis.map((p) => {
    const lo = lowerBy.get(p);
    const hi = upperBy.get(p);
    return lo != null && hi != null ? hi - lo : null;
  });
  const score = axis.map((p) => scoreBy.get(p) ?? null);

  const option: echarts.EChartsOption = {
    ...baseChartOption(),
    legend: { show: true, top: 0, textStyle: { fontSize: 10 } },
    xAxis: { type: "category", data: axis.map(yearOf) },
    yAxis: { type: "value", scale: true },
    series: [
      {
        name: "CI lower",
        type: "line",
        data: lower,
        stack: "ci",
        showSymbol: false,
        lineStyle: { opacity: 0 },
        tooltip: { show: false },
      },
      ...(hasBounds
        ? [
            {
              name: "90% CI (published)",
              type: "line" as const,
              data: band,
              stack: "ci",
              showSymbol: false,
              lineStyle: { opacity: 0 },
              areaStyle: { opacity: 0.25 },
            },
          ]
        : []),
      {
        name: "Score",
        type: "line",
        data: score,
        smooth: false,
        connectNulls: false,
        z: 3,
      },
    ],
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        const rows = params as { axisValue?: string }[];
        const axisValue = rows[0]?.axisValue;
        const idx =
          axisValue != null
            ? axis.findIndex((p) => yearOf(p) === axisValue)
            : -1;
        const period = idx >= 0 ? axis[idx] : undefined;
        if (period == null) return "";
        const parts = [`<b>${period.slice(0, 10)}</b>`];
        const s = scoreBy.get(period);
        if (s != null) parts.push(`Score: ${s.toFixed(1)}`);
        const lo = lowerBy.get(period);
        const hi = upperBy.get(period);
        if (lo != null && hi != null)
          parts.push(`90% CI: ${lo.toFixed(1)} – ${hi.toFixed(1)}`);
        const n = countBy.get(period);
        if (n != null) parts.push(`Sources: ${n}`);
        if (lo == null && s == null) parts.push("No published data");
        return parts.join("<br/>");
      },
    },
  };
  return { kind: "chart", option, diagnosticsPresent: hasBounds };
}
