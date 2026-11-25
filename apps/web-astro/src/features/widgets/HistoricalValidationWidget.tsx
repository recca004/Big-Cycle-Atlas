/** Historical-validation workspace widget (Mission 6 §8).
 *  Compact availability-evidence summary per country: strict eligibility,
 *  provider publication evidence, atlas retrieval evidence, missing
 *  evidence, latest observation period. Retrieval evidence is always
 *  labelled as retrieval — never as provider publication. */
import { fetchCountryAvailability, fetchExecutionModes } from "@/lib/api/client";
import type { AvailabilityResponse, ExecutionModesResponse } from "@/types/research";
import { useFetch } from "@/lib/ui/shared";
import { useAsyncState } from "./hooks";
import { resolveAsync } from "./common";
import { formatDate } from "@/lib/format";
import type { WidgetProps } from "@/features/workspace/widgetRegistry";

export function HistoricalValidationWidget({ config }: WidgetProps) {
  const iso3 = String(config.country ?? "CHE");
  const avail = useAsyncState<AvailabilityResponse>(
    (signal) => fetchCountryAvailability(iso3, { signal }),
    [iso3],
  );
  const modes = useFetch<ExecutionModesResponse>(fetchExecutionModes, []);

  return resolveAsync(avail, (data) => {
    const inds = data.indicators;
    const total = inds.length;
    const strict = inds.filter((i) => i.strict_eligible).length;
    const released = inds.reduce((s, i) => s + i.with_release_evidence, 0);
    const retrieved = inds.reduce((s, i) => s + i.with_retrieval_evidence, 0);
    const obs = inds.reduce((s, i) => s + i.observation_count, 0);
    const missing = inds.filter(
      (i) => i.with_release_evidence === 0 && i.with_retrieval_evidence === 0,
    ).length;
    const latest = inds
      .map((i) => i.latest_period)
      .filter((p): p is string => p !== null)
      .sort()
      .at(-1);
    const strictMode = (modes.kind === "ready" ? modes.data : undefined)
      ?.modes?.find((m) => m.mode.includes("strict"));

    return (
      <div className="histval-widget">
        <div className="histval-grid">
          <div>
            <p className="metric-widget-value">{strict}/{total}</p>
            <p className="body-sm">strict-eligible indicators</p>
          </div>
          <div>
            <p className="metric-widget-value">{obs.toLocaleString()}</p>
            <p className="body-sm">observations</p>
          </div>
        </div>
        <table className="data-table">
          <tbody>
            <tr>
              <td>Provider publication evidence</td>
              <td>{released.toLocaleString()} obs</td>
            </tr>
            <tr>
              <td>Atlas retrieval evidence</td>
              <td>{retrieved.toLocaleString()} obs</td>
            </tr>
            <tr>
              <td>Missing all availability evidence</td>
              <td>{missing} indicators</td>
            </tr>
            <tr>
              <td>Latest observation period</td>
              <td>{latest ? formatDate(latest) : "—"}</td>
            </tr>
          </tbody>
        </table>
        {strictMode && (
          <p className="body-sm" style={{ fontSize: "var(--text-xs)" }}>
            Strict mode: {strictMode.mode}. Retrieval
            evidence marks when Atlas first stored a value — it is not the
            provider's publication date.
          </p>
        )}
      </div>
    );
  });
}
