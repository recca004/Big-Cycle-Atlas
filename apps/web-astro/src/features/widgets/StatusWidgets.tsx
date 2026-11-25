import type { WidgetProps } from "@/features/workspace/widgetRegistry";
import {
  useAsyncState,
  useDataSources,
  useHealth,
  useIngestionRuns,
  useLiveCountries,
  useMultiCountryObservations,
} from "./hooks";
import { fetchResearchProgress, fetchResearchVersions } from "@/lib/api/client";
import { resolveAsync, WidgetLoading, WidgetError } from "./common";
import { formatDate } from "@/lib/format";
import { INITIAL_COUNTRIES } from "@big-cycle-atlas/shared";

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

/** Engine versions — live from GET /api/research/versions. Never hardcoded
 *  (drift regression: this widget used to display stale v0.8/v0.3 strings). */
export function ModelVersionWidget(_props: WidgetProps) {
  const state = useAsyncState((s) => fetchResearchVersions({ signal: s }), []);
  return resolveAsync(state, (v) => (
    <div className="metric-widget">
      <p className="label-md text-tertiary">Normalization</p>
      <p className="metric-value" style={{ fontSize: "var(--text-lg)" }}>
        {v.normalization_version}
      </p>
      <p className="label-md text-tertiary" style={{ marginTop: "var(--space-3)" }}>
        Force aggregation
      </p>
      <p className="metric-value" style={{ fontSize: "var(--text-lg)" }}>
        {v.force_aggregation_version}
      </p>
      <p className="body-sm" style={{ fontSize: "var(--text-xs)", marginTop: "var(--space-2)" }}>
        app v{v.app_version} · backtest_safe: false — research scoring only,
        not backtest validated.
      </p>
    </div>
  ));
}

/** Research completion across the 17 forces — live engine metadata from
 *  GET /api/research/progress. Never hardcodes the classification counts:
 *  engine-level implementation (level published / dimension-only / context
 *  profile / deferred) is distinct from country-level data availability. */
const CLASS_LABELS: Record<string, string> = {
  level_published: "published level",
  dimension_only: "dimension-only",
  context_profile: "context profile",
  deferred: "deferred",
};

export function ResearchProgressWidget(_props: WidgetProps) {
  const state = useAsyncState(
    (s) => fetchResearchProgress({ signal: s }),
    [],
  );
  return resolveAsync(state, (progress) => (
    <div className="widget-fill widget-scroll">
      <p className="body-sm" style={{ marginBottom: "var(--space-3)" }}>
        <strong>{progress.counts.level_published ?? 0}</strong> published levels ·{" "}
        <strong>{progress.counts.dimension_only ?? 0}</strong> dimension-only ·{" "}
        <strong>{progress.counts.context_profile ?? 0}</strong> context profiles ·{" "}
        <strong>{progress.counts.deferred ?? 0}</strong> deferred
        <span className="body-sm" style={{ display: "block", color: "var(--text-tertiary)", marginTop: "2px" }}>
          engine-level implementation as of {progress.as_of_period} —
          country availability may differ
        </span>
      </p>
      <table className="data-table">
        <tbody>
          {progress.forces.map((f) => (
            <tr key={f.force_code}>
              <td>{f.force_name}</td>
              <td>
                <span
                  className={`status-pill status-${
                    f.primary_classification === "level_published"
                      ? "good"
                      : f.primary_classification === "deferred"
                        ? "warn"
                        : "neutral"
                  }`}
                >
                  {CLASS_LABELS[f.primary_classification] ??
                    f.primary_classification}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ));
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
