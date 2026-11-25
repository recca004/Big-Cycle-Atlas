import type { EChartsOption } from "echarts";
import { baseChartOption } from "./EChart";
import type { CycleHistoryResponse } from "@/types/research";

export const STAGE_COLORS: Record<string, string> = {
  EARLY_RISE: "#86efac", RISE: "#4ade80", LATE_RISE: "#16a34a",
  PEAK: "#facc15", LATE_PEAK: "#eab308",
  EARLY_DECLINE: "#fb923c", DECLINE: "#f87171", RESET: "#dc2626",
};

/** Cycle-history chart: composite line + stage markers as a labelled
 *  scatter series (markers carry the stage in the tooltip instead of
 *  overlapping text labels). Fixes the crowded-markPoint and clipped
 *  y-axis-name defects reported on /research and /cycle. */
export function cycleHistoryOption(h: CycleHistoryResponse): EChartsOption {
  const pts = h.points;
  const stages = pts
    .filter((p) => p.stage && p.score != null)
    .map((p) => ({
      value: [p.period, p.score],
      stage: p.stage,
      itemStyle: { color: STAGE_COLORS[p.stage ?? ""] ?? "#94a3b8" },
    }));
  return {
    ...baseChartOption(),
    // extra top room for the marker symbols; no y-axis "name" (it clipped
    // at the left edge) — the axis meaning is in the caption instead.
    grid: { left: 8, right: 16, top: 34, bottom: 24, containLabel: true },
    tooltip: {
      trigger: "axis",
      formatter: (params: unknown) => {
        const arr = params as Array<{
          axisValue: string; seriesName: string; value: unknown;
          data?: { stage?: string };
        }>;
        const line = arr.find((a) => a.seriesName === "National conditions");
        const st = arr.find((a) => a.seriesName === "Stage");
        let out = `${line?.axisValue ?? ""}`;
        if (line) out += `<br/>conditions: ${String(line.value)}`;
        if (st?.data?.stage) out += `<br/>stage: ${st.data.stage}`;
        return out;
      },
    },
    xAxis: { type: "category", data: pts.map((p) => p.period) },
    yAxis: { type: "value", min: 0, max: 100 },
    series: [
      {
        type: "line",
        name: "National conditions",
        data: pts.map((p) => p.score),
        connectNulls: false,
        showSymbol: false,
        lineStyle: { width: 2 },
      },
      {
        type: "scatter",
        name: "Stage",
        symbol: "pin",
        symbolSize: 16,
        data: stages,
        tooltip: { trigger: "item" },
      },
    ],
  };
}
