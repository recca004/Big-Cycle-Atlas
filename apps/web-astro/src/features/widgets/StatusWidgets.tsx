import type { WidgetProps } from "@/features/workspace/widgetRegistry";
import {
  useDataSources,
  useHealth,
  useIngestionRuns,
  useLiveCountries,
  useMultiCountryObservations,
} from "./hooks";
import { resolveAsync, WidgetLoading, WidgetError } from "./common";
import { formatDate } from "@/lib/format";
import { FORCES, INITIAL_COUNTRIES } from "@big-cycle-atlas/shared";

/** API liveness. */
export function ApiStatusWidget(_props: WidgetProps) {
  const state = useHealth();
  return resolveAsync(state, (h) => (
    <div className="metric-widget">
      <p className="metric-widget-value" style={{ fontSize: "var(--text-xl)" }}>
        {h.status === "ok" ? "Online" : "Degraded"}
      </p>
      <p className="body-sm">
        API v{h.version} · database {h.database}
        {h.database_error ? ` — ${h.database_error}` : ""}
      </p>
    </div>
  ));
}

/** Registered data sources and their status. */
export function SourceStatusWidget(_props: WidgetProps) {
  const state = useDataSources();
  return (
    <div className="widget-fill widget-scroll">
      {resolveAsync(state, (sources) => (
        <table className="data-table">
          <tbody>
            {sources.map((s) => (
              <tr key={s.id}>
                <td>{s.name ?? s.source_key}</td>
                <td>
                  <span
                    className={`status-pill status-${
                      s.status === "active"
                        ? "good"
                        : s.status === "testing"
                          ? "warn"
                          : s.status === "broken"
                            ? "bad"
                            : "neutral"
                    }`}
                  >
                    {s.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ))}
    </div>
  );
}

/** Recent ingestion run outcomes. */
export function IngestionStatusWidget(_props: WidgetProps) {
  const state = useIngestionRuns();
  return (
    <div className="widget-fill widget-scroll">
      {resolveAsync(
        state,
        (runs) => (
          <table className="data-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Status</th>
                <th className="num">+Obs</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {runs.slice(0, 15).map((r) => (
                <tr key={r.id}>
                  <td>{r.source_key ?? "—"}</td>
                  <td>
                    <span
                      className={`status-pill status-${
                        r.status === "success" ? "good" : "bad"
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="num">{r.observations_inserted ?? "—"}</td>
                  <td>{r.started_at ? formatDate(r.started_at) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ),
        (runs) => (runs.length === 0 ? "No ingestion runs recorded." : null),
      )}
    </div>
  );
}

/** Current model versions — static per normalization_definitions.py. */
export function ModelVersionWidget(_props: WidgetProps) {
  return (
    <div className="metric-widget">
      <p className="label-md text-tertiary">Normalization</p>
      <p className="metric-value" style={{ fontSize: "var(--text-lg)" }}>
        normalization-v0.8
      </p>
      <p className="label-md text-tertiary" style={{ marginTop: "var(--space-3)" }}>
        Force aggregation
      </p>
      <p className="metric-value" style={{ fontSize: "var(--text-lg)" }}>
        force-aggregation-v0.3
      </p>
      <p className="body-sm" style={{ fontSize: "var(--text-xs)", marginTop: "var(--space-2)" }}>
        backtest_safe: false — research scoring only, not backtest validated.
      </p>
    </div>
  );
}

/** Research completion across the 17 forces (metadata, not live scores). */
export function ResearchProgressWidget(_props: WidgetProps) {
  // 5/17 executable — mirrors force_aggregation_definitions.py. This widget
  // reads from a static manifest kept in sync with the backend; it never
  // claims a score exists that the engine cannot produce.
  const executable = [
    "rule_of_law",
    "corruption",
    "internal_conflict",
    "education",
    "wealth_opportunity_values_gaps",
  ];
  const sourced = new Set([
    ...executable,
    "productivity_output_growth",
    "cost_competitiveness",
    "trade_capital_flows",
    "infrastructure_investment",
    "indebtedness",
    "military_strength",
  ]);
  const nameOf = (code: string) =>
    code
      .replaceAll("_", " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <div className="widget-fill widget-scroll">
      <p className="body-sm" style={{ marginBottom: "var(--space-3)" }}>
        <strong>{executable.length}/17</strong> forces have executable scoring ·{" "}
        {sourced.size}/17 have live data inputs
      </p>
      <table className="data-table">
        <tbody>
          {FORCES.map((code) => {
            const isExec = executable.includes(code);
            const hasData = sourced.has(code);
            return (
              <tr key={code}>
                <td>{nameOf(code)}</td>
                <td>
                  <span
                    className={`status-pill status-${
                      isExec ? "good" : hasData ? "warn" : "neutral"
                    }`}
                  >
                    {isExec ? "executable" : hasData ? "deferred" : "not sourced"}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Coverage matrix — countries × a few key indicators, latest year. */
export function CoverageMatrixWidget(_props: WidgetProps) {
  const countries = useLiveCountries();
  const iso3s = INITIAL_COUNTRIES.map((c) => c.iso3);
  const obs = useMultiCountryObservations(iso3s, undefined);

  if (countries.kind === "loading" || obs.kind === "loading")
    return <WidgetLoading />;
  if (countries.kind === "error" || obs.kind === "error") return <WidgetError />;

  return (
    <div className="widget-fill widget-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Country</th>
            <th className="num">Indicators</th>
            <th className="num">Observations</th>
            <th className="num">Latest</th>
          </tr>
        </thead>
        <tbody>
          {countries.data.map((c) => (
            <tr key={c.iso3}>
              <td>{c.name}</td>
              <td className="num">{c.indicator_count ?? "—"}</td>
              <td className="num">{c.observation_count ?? "—"}</td>
              <td className="num">{c.latest_observation_year ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
