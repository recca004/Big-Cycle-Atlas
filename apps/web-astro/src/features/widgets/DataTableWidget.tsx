import type { WidgetProps } from "@/features/workspace/widgetRegistry";
import { useObservations } from "./hooks";
import { resolveAsync } from "./common";
import { indicatorFormat, indicatorLabel } from "./indicatorMeta";
import { formatValue } from "./indicatorMeta";
import {
  formatQuarter,
  sourceLabel,
  yearOf,
} from "@/lib/format";

/** Raw observation table — latest vintage only (what the API serves). */
export function DataTableWidget({ config }: WidgetProps) {
  const iso3 = (config.country as string) || "USA";
  const indicator = (config.indicator as string) || undefined;
  const limit = Math.min(Number(config.limit ?? 12) || 12, 100);
  const state = useObservations(iso3, indicator, limit);

  return (
    <div className="widget-fill widget-scroll">
      {resolveAsync(
        state,
        (items) => (
          <table className="data-table">
            <thead>
              <tr>
                <th>Period</th>
                <th>Indicator</th>
                <th className="num">Value</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {items.slice(0, limit).map((o) => (
                <tr key={o.id}>
                  <td>
                    {new Date(o.period_start).getUTCMonth() === 0
                      ? yearOf(o.period_start)
                      : formatQuarter(o.period_start)}
                  </td>
                  <td>{indicatorLabel(o.indicator_code ?? "")}</td>
                  <td className="num">
                    {formatValue(
                      indicatorFormat(o.indicator_code ?? ""),
                      o.value,
                    )}
                  </td>
                  <td>
                    <span className="source-badge">
                      {sourceLabel(o.source_key)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ),
        (items) =>
          items.length === 0
            ? `No observations for ${iso3}${indicator ? ` · ${indicatorLabel(indicator)}` : ""}.`
            : null,
      )}
    </div>
  );
}
