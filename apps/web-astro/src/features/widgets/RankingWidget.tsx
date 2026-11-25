import { useMemo } from "react";
import type { WidgetProps } from "@/features/workspace/widgetRegistry";
import { useMultiCountryObservations, useCountryList } from "./hooks";
import { resolveAsync } from "./common";
import { EChart, baseChartOption } from "@/lib/charts/EChart";
import type { EChartsOption } from "echarts";
import { formatValue, indicatorFormat, indicatorLabel } from "./indicatorMeta";
import { yearOf } from "@/lib/format";

/** Latest-value comparison of one indicator across all tracked countries. */
export function RankingWidget({ config }: WidgetProps) {
  const countries = useCountryList();
  const iso3s = countries.map((c) => c.iso3);
  const indicator = (config.indicator as string) || "GDP_GROWTH";
  const state = useMultiCountryObservations(iso3s, indicator);

  const option = useMemo(() => {
    if (state.kind !== "ready") return null;
    const rows = iso3s
      .map((iso3) => {
        const latest = (state.data[iso3] ?? [])[0];
        return latest ? { iso3, value: latest.value, year: yearOf(latest.period_start) } : null;
      })
      .filter((r): r is NonNullable<typeof r> => r !== null)
      .sort((a, b) => a.value - b.value);
    if (rows.length === 0) return null;
    const base = baseChartOption();
    return {
      ...base,
      xAxis: { ...base.xAxis, type: "value" as const },
      yAxis: {
        ...base.yAxis,
        type: "category" as const,
        data: rows.map((r) => `${r.iso3} '${String(r.year).slice(2)}`),
      },
      grid: { ...base.grid, left: 8 },
      tooltip: {
        ...base.tooltip,
        valueFormatter: (v: unknown) =>
          formatValue(indicatorFormat(indicator), Number(v)),
      },
      series: [
        {
          type: "bar" as const,
          data: rows.map((r) => r.value),
          label: {
            show: true,
            position: "right",
            formatter: (p: { value: unknown }) =>
              formatValue(indicatorFormat(indicator), Number(p.value)),
            color: undefined,
            fontSize: 10,
          },
        },
      ],
    } as EChartsOption;
  }, [state, iso3s, indicator]);

  return (
    <div className="widget-fill">
      {resolveAsync(
        state,
        () =>
          option ? (
            <EChart
              option={option}
              ariaLabel={`${indicatorLabel(indicator)} latest values across countries`}
            />
          ) : (
            <div className="widget-state">
              <p className="body-sm widget-state-title">No data</p>
            </div>
          ),
        (data) =>
          iso3s.every((c) => (data[c] ?? []).length === 0)
            ? `No ${indicatorLabel(indicator)} data for any tracked country.`
            : null,
      )}
    </div>
  );
}
