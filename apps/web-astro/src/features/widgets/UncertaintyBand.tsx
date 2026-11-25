import { useMemo } from "react";
import type { WidgetProps } from "@/features/workspace/widgetRegistry";
import {
  fetchCountryObservations,
  fetchIndicatorUncertaintyHistory,
} from "@/lib/api/client";
import { useFetch } from "@/lib/ui/shared";
import { EChart } from "@/lib/charts/EChart";
import { buildUncertaintyOption } from "@/lib/charts/uncertaintyChart";
import { indicatorLabel } from "./indicatorMeta";

interface Props {
  iso3: string;
  indicator: string;
  height?: number;
  title?: string;
  /** "fill" renders inside a workspace widget frame; "card" is a page card. */
  variant?: "card" | "fill";
}

/** Score + published WGI uncertainty band. Shows an explicit missing-
 *  diagnostics state rather than fabricating intervals (Mission 4 §9). */
export function UncertaintyBand({
  iso3,
  indicator,
  height = 240,
  title,
  variant = "card",
}: Props) {
  const label = indicatorLabel(indicator);
  const state = useFetch(async (c) => {
    const [obsPage, diag] = await Promise.all([
      fetchCountryObservations(
        iso3,
        { indicator, limit: 200 },
        { signal: c.signal },
      ),
      fetchIndicatorUncertaintyHistory(iso3, indicator, { signal: c.signal }),
    ]);
    return { obs: obsPage.items, diag: diag.points };
  }, [iso3, indicator]);

  const built = useMemo(() => {
    if (state.kind !== "ready") return null;
    return buildUncertaintyOption(state.data.obs, state.data.diag, label);
  }, [state, label]);

  const fill = variant === "fill";
  return (
    <div className={fill ? "widget-fill" : "glass chart-card"}>
      {!fill && (
        <p className="label-md text-tertiary">
          {title ?? `${label} — published uncertainty`}
        </p>
      )}
      {state.kind === "loading" ? (
        <p className="body-sm">Loading…</p>
      ) : state.kind === "error" ? (
        <p className="body-sm text-tertiary">Uncertainty data unavailable.</p>
      ) : built?.kind === "empty" ? (
        <p className="body-sm text-tertiary">{built.reason}</p>
      ) : built?.kind === "chart" ? (
        <>
          <EChart
            option={built.option}
            style={fill ? { height: "100%", width: "100%" } : { height, width: "100%" }}
            ariaLabel={`${label} for ${iso3} with published 90% confidence band`}
          />
          {!fill && !built.diagnosticsPresent && (
            <p className="section-note">
              No published confidence bounds for this indicator — the band is
              absent rather than estimated.
            </p>
          )}
          {!fill && (
            <p className="section-note">
              WGI 90% confidence bounds and source counts are provider-published
              values, period-aligned exactly; gaps are not interpolated.
            </p>
          )}
        </>
      ) : null}
    </div>
  );
}

/** Workspace widget wrapper (governance category). */
export function UncertaintyBandWidget({ config }: WidgetProps) {
  const iso3 = (config.country as string) || "USA";
  const indicator =
    (config.indicator as string) || "RULE_OF_LAW_WGI_SCORE";
  return <UncertaintyBand iso3={iso3} indicator={indicator} variant="fill" />;
}
