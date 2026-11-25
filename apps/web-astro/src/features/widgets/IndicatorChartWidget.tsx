import { useMemo } from "react";
import type { WidgetProps } from "@/features/workspace/widgetRegistry";
import { useMultiCountryObservations } from "./hooks";
import { resolveAsync } from "./common";
import { EChart, baseChartOption } from "@/lib/charts/EChart";
import type { EChartsOption } from "echarts";
import { indicatorFormat, indicatorLabel } from "./indicatorMeta";
import { formatValue } from "./indicatorMeta";
import type { CountryObservation } from "@/types/api";

type ChartType = "line" | "area" | "bar";

function periodKey(obs: CountryObservation): string {
  return obs.period_start.slice(0, 10);
}

/** Historical chart for one indicator across 1..n countries. */
export function IndicatorChartWidget({ config }: WidgetProps) {
  const rawCountries = config.countries;
  const countries: string[] = Array.isArray(rawCountries)
    ? (rawCountries as string[]).filter((c) => typeof c === "string")
    : [((config.country as string) || "USA")];
  const iso3s = countries.length > 0 ? countries : ["USA"];
  const indicator = (config.indicator as string) || "GDP_GROWTH";
  const chartType = ((config.chartType as string) || "line") as ChartType;
  const showLegend = config.showLegend !== false;

  const state = useMultiCountryObservations(iso3s, indicator);

  const option = useMemo(() => {
    if (state.kind !== "ready") return null;
    const base = baseChartOption();
    const series = iso3s
      .map((iso3) => {
        const items = (state.data[iso3] ?? [])
          .slice()
          .sort((a, b) => a.period_start.localeCompare(b.period_start));
        return {
          name: iso3,
          type: chartType === "bar" ? ("bar" as const) : ("line" as const),
          areaStyle:
            chartType === "area" ? { opacity: 0.18 } : undefined,
          showSymbol: false,
          data: items.map((o) => [periodKey(o), o.value]),
        };
      })
      .filter((s) => s.data.length > 0);
    return {
      ...base,
      legend: showLegend
        ? { top: 0, textStyle: base.textStyle }
        : undefined,
      tooltip: {
        ...base.tooltip,
        valueFormatter: (v: unknown) =>
          formatValue(indicatorFormat(indicator), Number(v)),
      },
      xAxis: { ...base.xAxis, type: "time" as const },
      yAxis: {
        type: "value" as const,
        axisLabel: {
          formatter: (v: number) =>
            formatValue(indicatorFormat(indicator), v),
        },
        splitLine: { lineStyle: { color: "rgba(127,140,170,0.18)" } },
      },
      series,
    } as EChartsOption;
  }, [state, iso3s, indicator, chartType, showLegend]);

  const body = resolveAsync(
    state,
    () =>
      option && Array.isArray(option.series) && option.series.length > 0 ? (
        <EChart
          option={option}
          ariaLabel={`${indicatorLabel(indicator)} history for ${iso3s.join(", ")}`}
        />
      ) : (
        <div className="widget-state">
          <p className="body-sm widget-state-title">No data</p>
        </div>
      ),
    (data) =>
      iso3s.every((c) => (data[c] ?? []).length === 0)
        ? `No ${indicatorLabel(indicator)} data for ${iso3s.join(", ")}.`
        : null,
  );

  return <div className="widget-fill">{body}</div>;
}
