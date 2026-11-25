/** Fixture charts for the dev-only component showcase.
 *  All values are synthetic demonstrations — never economic data. */
import { EChart, baseChartOption } from "@/lib/charts/EChart";

const fixture = [1.2, 1.5, 1.1, 1.8, 2.2, 1.9, 2.4, 2.1, 2.6, 2.9];

export function ShowcaseCharts() {
  const opt = {
    ...baseChartOption(),
    xAxis: { type: "category" as const, data: fixture.map((_, i) => 2015 + i) },
    yAxis: { type: "value" as const },
    series: [{ type: "line" as const, data: fixture, smooth: true }],
    grid: { left: 40, right: 10, top: 20, bottom: 25 },
  };
  return (
    <div style={{ height: "16rem" }}>
      <EChart option={opt} ariaLabel="Fixture line chart" />
    </div>
  );
}
