import { useEffect, useMemo, useState } from "react";
import {
  fetchCompositeModels,
  fetchCountryCycle,
  fetchCycleHistory,
  fetchForceHistory,
  fetchResearchMethods,
  fetchResearchProgress,
} from "@/lib/api/client";
import type {
  CompositeModelInfo,
  CompositeResult,
  CycleHistoryResponse,
  ForceHistoryResponse,
  MethodInfo,
  ResearchProgress,
} from "@/types/research";
import { EChart, baseChartOption } from "@/lib/charts/EChart";
import { AddToWorkspace } from "@/features/workspace/AddToWorkspace";
import { HistoricalValidation } from "@/features/research/HistoricalValidation";
import type { EChartsOption } from "echarts";

const COUNTRIES = ["USA", "CHN", "JPN", "DEU", "FRA", "GBR", "CHE", "IND"];
const FORCES = [
  "rule_of_law", "corruption", "leadership_capabilities",
  "internal_conflict", "education", "productivity_output_growth",
  "indebtedness", "wealth_opportunity_values_gaps",
  "character_determination", "military_strength",
  "cost_competitiveness", "trade_capital_flows", "global_openness",
  "infrastructure_investment", "resource_allocation_efficiency",
  "geography", "acts_of_nature",
];

function Badge({ children, tone }: { children: React.ReactNode; tone?: string }) {
  return <span className={`badge badge-${tone ?? "muted"}`}>{children}</span>;
}

function useFetch<T>(fn: (c: AbortController) => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<
    { kind: "loading" | "ready" | "error"; data?: T; error?: string }
  >({ kind: "loading" });
  useEffect(() => {
    const c = new AbortController();
    setState({ kind: "loading" });
    fn(c)
      .then((data) => setState({ kind: "ready", data }))
      .catch((e) => setState({ kind: "error", error: String(e) }));
    return () => c.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

const STATE_LABEL: Record<string, string> = {
  approved_production: "Approved",
  validated_candidate: "Validated candidate",
  experimental: "Experimental",
  context_only: "Context only",
  deferred: "Deferred",
};
const STATUS_LABEL: Record<string, string> = {
  level_published: "Level published",
  dimension_only: "Dimension only",
  context_profile: "Context profile",
  deferred: "Deferred",
};

export function ResearchLab() {
  const [iso3, setIso3] = useState("USA");
  const [model, setModel] = useState("model_b_domain");
  const [force, setForce] = useState("rule_of_law");

  const models = useFetch<CompositeModelInfo[]>(fetchCompositeModels, []);
  const methods = useFetch<MethodInfo[]>(fetchResearchMethods, []);
  const progress = useFetch<ResearchProgress>(fetchResearchProgress, []);
  const cycle = useFetch<CompositeResult>(
    (c) => fetchCountryCycle(iso3, model, { signal: c.signal }),
    [iso3, model],
  );
  const history = useFetch<CycleHistoryResponse>(
    (c) => fetchCycleHistory(iso3, model, 2000, { signal: c.signal }),
    [iso3, model],
  );
  const forceHistory = useFetch<ForceHistoryResponse>(
    (c) => fetchForceHistory(iso3, force, 1996, { signal: c.signal }),
    [iso3, force],
  );

  const historyOption = useMemo(() => {
    if (history.kind !== "ready" || !history.data) return null;
    const pts = history.data.points;
    const stageColor: Record<string, string> = {
      RISE: "#4ade80", EARLY_RISE: "#86efac", LATE_RISE: "#22c55e",
      PEAK: "#facc15", LATE_PEAK: "#eab308",
      EARLY_DECLINE: "#fb923c", DECLINE: "#f87171", RESET: "#ef4444",
    };
    return {
      ...baseChartOption(),
      tooltip: { trigger: "axis" },
      xAxis: { type: "category", data: pts.map((p) => p.period) },
      yAxis: { type: "value", name: "Composite (experimental)" },
      series: [
        {
          type: "line",
          name: "National conditions",
          data: pts.map((p) => p.score),
          connectNulls: false,
          markPoint: {
            data: pts
              .filter((p) => p.stage)
              .map((p) => ({
                coord: [p.period, p.score],
                itemStyle: { color: stageColor[p.stage ?? ""] ?? "#94a3b8" },
                value: p.stage,
              })),
          },
        },
      ],
    } as EChartsOption;
  }, [history]);

  const forceOption = useMemo(() => {
    if (forceHistory.kind !== "ready" || !forceHistory.data) return null;
    const pts = forceHistory.data.points;
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
    } as EChartsOption;
  }, [forceHistory]);

  const composite = cycle.kind === "ready" ? cycle.data : undefined;

  return (
    <div className="section-stack">
      {/* Controls */}
      <div className="glass-subtle research-controls">
        <label>
          Country{" "}
          <select className="config-select" value={iso3}
                  onChange={(e) => setIso3(e.target.value)}>
            {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
        <label>
          Experimental model{" "}
          <select className="config-select" value={model}
                  onChange={(e) => setModel(e.target.value)}>
            {(models.data ?? []).map((m) => (
              <option key={m.model_id} value={m.model_id}>
                {m.model_id} ({m.kind})
              </option>
            ))}
            {models.kind !== "ready" && <option value={model}>{model}</option>}
          </select>
        </label>
        <Badge tone="warn">EXPERIMENTAL — research output, not production</Badge>
      </div>

      {/* Composite result */}
      <div className="glass">
        <h2 className="headline-sm panel-title">
          Composite national conditions — {iso3}
        </h2>
        {cycle.kind === "loading" && <p className="body-sm">Loading…</p>}
        {cycle.kind === "error" && (
          <p className="body-sm">Unavailable: {cycle.error}</p>
        )}
        {composite && (
          <div className="research-grid">
            <div className="metric-card glass-subtle">
              <p className="label-md text-tertiary">Score ({composite.period})</p>
              <p className="metric-value">
                {composite.composite.score?.toFixed(1) ?? "unavailable"}
              </p>
              <p className="body-sm">
                coverage {(composite.composite.coverage_ratio * 100).toFixed(0)}%
                · model {composite.composite.model_version}
              </p>
            </div>
            <div>
              <p className="label-md text-tertiary">Weights</p>
              <ul className="body-sm weight-list">
                {Object.entries(composite.composite.weights).map(([f, w]) => (
                  <li key={f}>
                    <code>{f}</code> — {(w * 100).toFixed(1)}%
                  </li>
                ))}
              </ul>
              {composite.composite.missing_forces.length > 0 && (
                <p className="body-sm">
                  Missing: {composite.composite.missing_forces.join(", ")}
                </p>
              )}
              {composite.composite.excluded_forces.map((e) => (
                <p className="body-sm" key={e}>Excluded — {e}</p>
              ))}
              {[...composite.composite.warnings,
                ...composite.composite.limitations].map((w) => (
                <p className="body-sm" key={w}>⚠ {w}</p>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Cycle history */}
      <div className="glass">
        <h2 className="headline-sm panel-title">
          Experimental cycle history — {iso3}
        </h2>
        <AddToWorkspace typeId="cycle-history"
          config={{ country: iso3, model, startYear: 2000 }} />
        {history.kind === "ready" && historyOption ? (
          <>
            <EChart option={historyOption} style={{ height: 320 }}
                    ariaLabel="Experimental cycle history" />
            {history.data && (
              <p className="body-sm">
                {history.data.transitions.length} stage transitions ·{" "}
                coverage {(history.data.coverage_ratio * 100).toFixed(0)}% ·{" "}
                retrospective, backtest_safe=false
              </p>
            )}
          </>
        ) : (
          <p className="body-sm">
            {history.kind === "error"
              ? `Unavailable: ${history.error}`
              : "Loading…"}
          </p>
        )}
      </div>

      {/* Force history explorer */}
      <div className="glass">
        <h2 className="headline-sm panel-title">Force history explorer</h2>
        <AddToWorkspace typeId="force-history"
          config={{ country: iso3, force, startYear: 1996 }} />
        <label>
          Force{" "}
          <select className="config-select" value={force}
                  onChange={(e) => setForce(e.target.value)}>
            {FORCES.map((f) => <option key={f}>{f}</option>)}
          </select>
        </label>
        {forceHistory.kind === "ready" && forceOption ? (
          <EChart option={forceOption} style={{ height: 300 }}
                  ariaLabel="Force history" />
        ) : (
          <p className="body-sm">
            {forceHistory.kind === "error"
              ? `Unavailable: ${forceHistory.error}`
              : "Loading…"}
          </p>
        )}
      </div>

      {/* Historical validation (Mission 4 §30) */}
      <HistoricalValidation iso3={iso3} model={model} />

      {/* Methodology registry */}
      <div className="glass">
        <h2 className="headline-sm panel-title">Methodology registry</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>Method</th><th>Force</th><th>Dimension</th>
                  <th>State</th><th>Approval</th></tr>
            </thead>
            <tbody>
              {(methods.data ?? []).map((m) => (
                <tr key={m.method_id}>
                  <td><code>{m.method_id}</code></td>
                  <td>{m.force_code}</td>
                  <td>{m.dimension}</td>
                  <td>{STATE_LABEL[m.state] ?? m.state}</td>
                  <td>{m.approval_decision ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Authoritative progress */}
      <div className="glass">
        <h2 className="headline-sm panel-title">
          Engine implementation status (authoritative)
        </h2>
        {progress.data && (
          <>
            <p className="body-sm">
              As of {progress.data.as_of_period}:{" "}
              {Object.entries(progress.data.counts)
                .map(([k, v]) => `${STATUS_LABEL[k] ?? k} ${v}`)
                .join(" · ")}
            </p>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr><th>Force</th><th>Primary class</th><th>Approval</th>
                      <th>Dimensions</th><th>Ceiling</th></tr>
                </thead>
                <tbody>
                  {progress.data.forces.map((f) => (
                    <tr key={f.force_code}>
                      <td>{f.force_name}</td>
                      <td>{STATUS_LABEL[f.primary_classification] ??
                            f.primary_classification}</td>
                      <td>{f.approval_state === "none" ? "—" : f.approval_state}</td>
                      <td>{f.published_dimensions.join(", ") || "—"}</td>
                      <td>{f.coverage_ceiling ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
