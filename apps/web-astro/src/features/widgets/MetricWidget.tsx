import type { WidgetProps } from "@/features/workspace/widgetRegistry";
import { useObservations } from "./hooks";
import { resolveAsync } from "./common";
import {
  formatValue,
  indicatorFormat,
  indicatorLabel,
  INDICATOR_META,
} from "./indicatorMeta";
import { sourceLabel, yearOf, formatQuarter } from "@/lib/format";

/** Latest-value metric card for a country + indicator. */
export function MetricWidget({ config }: WidgetProps) {
  const iso3 = (config.country as string) || "USA";
  const indicator = (config.indicator as string) || "GDP_GROWTH";
  const state = useObservations(iso3, indicator, 8);

  return resolveAsync(
    state,
    (items) => {
      const latest = items[0];
      if (!latest) return null;
      const meta = INDICATOR_META[indicator];
      const isQuarterly = new Date(latest.period_start).getUTCMonth() !== 0;
      return (
        <div className="metric-widget">
          <p className="metric-widget-value">
            {formatValue(meta?.format ?? indicatorFormat(indicator), latest.value)}
          </p>
          <p className="body-sm">
            {meta?.unit ?? latest.unit ?? ""} ·{" "}
            {isQuarterly
              ? formatQuarter(latest.period_start)
              : yearOf(latest.period_start)}{" "}
            · {sourceLabel(latest.source_key)}
          </p>
          <p className="body-sm" style={{ fontSize: "var(--text-xs)" }}>
            {meta?.label ?? indicatorLabel(indicator)} · {iso3}
          </p>
        </div>
      );
    },
    (items) =>
      items.length === 0
        ? `No ${indicatorLabel(indicator)} observations for ${iso3}.`
        : null,
  );
}
