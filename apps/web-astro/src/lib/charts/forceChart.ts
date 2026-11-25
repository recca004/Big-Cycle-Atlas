import type { EChartsOption } from "echarts";
import { baseChartOption } from "./EChart";
import type { ForceHistoryResponse } from "@/types/research";

/** Force-history chart: level + relative lines, momentum bars.
 *  Missing values never connect across gaps (connectNulls:false). */
export function forceHistoryOption(h: ForceHistoryResponse): EChartsOption {
  const pts = h.points;
  return {
    ...baseChartOption(),
    tooltip: { trigger: "axis" },
    legend: {},
    xAxis: { type: "category", data: pts.map((p) => p.period) },
    yAxis: { type: "value" },
    series: [
      {
        type: "line", name: "level",
        data: pts.map((p) => p.level_score), connectNulls: false,
      },
      {
        type: "line", name: "relative",
        data: pts.map((p) => p.relative_score), connectNulls: false,
      },
      {
        type: "bar", name: "momentum",
        data: pts.map((p) => p.momentum_score), yAxisIndex: 0,
        itemStyle: { opacity: 0.4 },
      },
    ],
  };
}
