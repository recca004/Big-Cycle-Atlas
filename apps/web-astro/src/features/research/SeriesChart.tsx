import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { EChart, baseChartOption } from "@/lib/charts/EChart";
import type { CrisisMarker, NamedSeries } from "@/types/research_modules";

/** "1995" | "1995-Q3" -> Date for the time axis. */
export function periodToDate(period: string): Date | null {
  const m = period.match(/^(\d{4})(?:-Q([1-4]))?$/);
  if (!m) return null;
  const y = Number(m[1]);
  const month = m[2] ? (Number(m[2]) - 1) * 3 : 0;
  return new Date(Date.UTC(y, month, 1));
}

interface SeriesChartProps {
  series: Record<string, NamedSeries | undefined>;
  title?: string | undefined;
  unit?: string | undefined;
  height?: number | undefined;
  logScale?: boolean | undefined;
  crisisMarks?: CrisisMarker[] | undefined;
  minYear?: number | undefined;
}

/**
 * Multi-entity line chart for research series ([period, value] points on a
 * time axis). Optional banking-crisis onset markers are drawn as vertical
 * reference lines — visual overlap is evidence display, never causation.
 */
export function SeriesChart({
  series, title, unit, height = 320, logScale, crisisMarks, minYear,
}: SeriesChartProps) {
  const option = useMemo<EChartsOption>(() => {
    const base = baseChartOption();
    const marks = (crisisMarks ?? [])
      .filter((m) => !minYear || m.year >= minYear)
      .map((m) => ({ xAxis: `${m.year}-01-01` }));
    const ecs = Object.entries(series)
      .filter(([, s]) => s?.points?.length)
      .map(([name, s]) => ({
        name,
        type: "line" as const,
        showSymbol: false,
        connectNulls: false,
        data: s!.points
          .map(([p, v]) => {
            const d = periodToDate(p);
            return d ? [d.getTime(), v] : null;
          })
          .filter((x): x is [number, number] => x !== null)
          .filter(([t]) => !minYear || new Date(t).getUTCFullYear() >= minYear),
        ...(marks.length
          ? {
              markLine: {
                silent: true,
                symbol: "none",
                lineStyle: { color: "#d16a6a", type: "dashed" as const, opacity: 0.55, width: 1 },
                data: marks,
                label: {
                  show: true, position: "insideEndTop" as const, fontSize: 9,
                  color: "#d16a6a",
                  formatter: (p: { value: unknown }) =>
                    String(new Date(Number(p.value)).getUTCFullYear()),
                },
              },
            }
          : {}),
      }));
    return {
      ...base,
      ...(title
        ? { title: { text: title, textStyle: { fontSize: 12, color: "#a8b3c7" }, left: 4 } }
        : {}),
      legend: { top: 0, right: 0, type: "scroll", textStyle: { fontSize: 10 } },
      tooltip: {
        ...((base.tooltip as object) ?? {}),
        trigger: "axis",
        valueFormatter: (v: unknown) =>
          `${typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: 3 }) : v}${unit ? ` ${unit}` : ""}`,
      },
      xAxis: {
        type: "time",
        ...(minYear ? { min: Date.UTC(minYear, 0, 1) } : {}),
      },
      yAxis: logScale
        ? { type: "log" as const, ...(unit ? { name: unit } : {}), nameTextStyle: { fontSize: 10 } }
        : { type: "value" as const, ...(unit ? { name: unit } : {}), nameTextStyle: { fontSize: 10 } },
      series: ecs,
    };
  }, [series, title, unit, logScale, crisisMarks, minYear]);
  return (
    <EChart
      option={option}
      style={{ height }}
      ariaLabel={title ?? "research series chart"}
    />
  );
}
