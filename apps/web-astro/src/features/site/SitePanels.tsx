import { useEffect, useMemo, useState } from "react";
import { fetchForceScores, fetchCountryObservations, fetchResearchProgress } from "@/lib/api/client";
import type { ResearchProgress } from "@/types/research";
import type { ForceScore, CountryObservation } from "@/types/api";
import {
  useLiveCountries,
  useDataSources,
  useIngestionRuns,
  useHealth,
  useIndicators,
  useForceCoverage,
} from "@/features/widgets/hooks";
import { formatDate } from "@/lib/format";
import { EChart } from "@/lib/charts/EChart";
import { indicatorLabel } from "@/features/widgets/indicatorMeta";
import {
  FORCE_PROGRESS,
  EXECUTABLE_COUNT,
  TOTAL_FORCES,
} from "@/features/forces/forceProgress";
import type { AsyncState } from "@/features/widgets/hooks";

function ready<T>(s: AsyncState<T>): T | undefined {
  return s.kind === "ready" ? s.data : undefined;
}
function isErr<T>(s: AsyncState<T>): boolean {
  return s.kind === "error";
}

/* ---------- shared ---------- */

function PanelState({ state, children }: { state: string; children?: React.ReactNode }) {
  return (
    <div className="glass-subtle state-box">
      <p className="body-sm">{state}</p>
      {children}
    </div>
  );
}

function CountrySelect({
  value,
  onChange,
  iso3s,
}: {
  value: string;
  onChange: (v: string) => void;
  iso3s: string[];
}) {
  return (
    <select
      className="config-select"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label="Select country"
    >
      {iso3s.map((c) => (
        <option key={c} value={c}>
          {c}
        </option>
      ))}
    </select>
  );
}

function useForceScores(iso3: string | undefined) {
  const [data, setData] = useState<ForceScore[] | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!iso3) return;
    const c = new AbortController();
    setData(null);
    fetchForceScores(iso3, undefined, { signal: c.signal })
      .then((r) => setData(r.forces))
      .catch(() => setError(true));
    return () => c.abort();
  }, [iso3]);
  return { data, error };
}

function ForceScoreCell({ score }: { score: ForceScore | undefined }) {
  if (!score) return <td className="num">—</td>;
  if (score.level_score == null)
    return (
      <td className="num text-tertiary" title={score.reasons.join("; ")}>
        deferred
      </td>
    );
  return (
    <td className="num" title={score.limitations.join("; ")}>
      {score.level_score.toFixed(1)}
    </td>
  );
}

/* ---------- /compare ---------- */

export function ComparePanel() {
  const countriesState = useLiveCountries();
  const countries = ready(countriesState);
  const iso3s = countries?.map((c) => c.iso3) ?? [];
  const [a, setA] = useState("USA");
  const [b, setB] = useState("CHN");
  const scoresA = useForceScores(a);
  const scoresB = useForceScores(b);

  const rows = useMemo(() => {
    if (!scoresA.data || !scoresB.data) return [];
    return scoresA.data.map((fa) => ({
      fa,
      fb: scoresB.data?.find((x) => x.force_code === fa.force_code),
    }));
  }, [scoresA.data, scoresB.data]);

  return (
    <div className="section-stack">
      <div className="glass compare-controls">
        <CountrySelect value={a} onChange={setA} iso3s={iso3s} />
        <span className="text-tertiary">vs</span>
        <CountrySelect value={b} onChange={setB} iso3s={iso3s} />
      </div>
      {!scoresA.data || !scoresB.data ? (
        <PanelState state="Loading force scores…" />
      ) : (
        <div className="glass table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Force</th>
                <th className="num">{a}</th>
                <th className="num">{b}</th>
                <th className="num">Δ (A−B)</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ fa, fb }) => (
                <tr key={fa.force_code}>
                  <td>{fa.force_name}</td>
                  <ForceScoreCell score={fa} />
                  <ForceScoreCell score={fb} />
                  <td className="num">
                    {fa.level_score != null && fb?.level_score != null
                      ? (fa.level_score - fb.level_score).toFixed(1)
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ---------- /forces overview ---------- */

export function ForcesOverview() {
  const countriesState = useLiveCountries();
  const countries = ready(countriesState);
  const iso3s = countries?.map((c) => c.iso3) ?? [];
  const [iso3, setIso3] = useState("USA");
  const { data, error } = useForceScores(iso3);

  if (error) return <PanelState state="Force scores are currently unavailable." />;
  return (
    <div className="section-stack">
      <div className="glass compare-controls">
        <CountrySelect value={iso3} onChange={setIso3} iso3s={iso3s} />
      </div>
      {!data ? (
        <PanelState state="Loading force scores…" />
      ) : (
        <div className="force-grid">
          {data.map((f) => (
            <div key={f.force_code} className="glass force-card">
              <p className="label-md text-tertiary">{f.force_name}</p>
              <p className="force-card-score">
                {f.level_score != null ? f.level_score.toFixed(1) : "—"}
              </p>
              <p className="force-card-meta">
                <span className={`status-dot status-${f.coverage_status}`} />
                {f.execution_status === "scored" ? "Scored" : "Deferred"} ·{" "}
                {f.coverage_status.replace(/_/g, " ")}
              </p>
              {f.momentum_score != null && (
                <p className="body-sm">Momentum: {f.momentum_score.toFixed(1)}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- domain pages (/economy /debt /trade) ---------- */

export function DomainForces({
  forceCodes,
  indicators,
}: {
  forceCodes: string[];
  indicators: string[];
}) {
  const countriesState = useLiveCountries();
  const countries = ready(countriesState);
  const iso3s = countries?.map((c) => c.iso3) ?? [];
  const [iso3, setIso3] = useState("USA");
  const { data, error } = useForceScores(iso3);

  const domainForces = data?.filter((f) => forceCodes.includes(f.force_code));

  return (
    <div className="section-stack">
      <div className="glass compare-controls">
        <CountrySelect value={iso3} onChange={setIso3} iso3s={iso3s} />
      </div>
      {error ? (
        <PanelState state="Force scores are currently unavailable." />
      ) : !domainForces ? (
        <PanelState state="Loading…" />
      ) : (
        <div className="force-grid">
          {domainForces.map((f) => (
            <div key={f.force_code} className="glass force-card">
              <p className="label-md text-tertiary">{f.force_name}</p>
              <p className="force-card-score">
                {f.level_score != null ? f.level_score.toFixed(1) : "—"}
              </p>
              <p className="force-card-meta">
                <span className={`status-dot status-${f.coverage_status}`} />
                {f.execution_status === "scored" ? "Scored" : "Deferred"} ·{" "}
                {f.coverage_status.replace(/_/g, " ")}
              </p>
              {f.reasons.length > 0 && (
                <p className="force-card-why">{f.reasons[0]}</p>
              )}
            </div>
          ))}
        </div>
      )}
      <DomainCharts iso3={iso3} indicators={indicators} />
    </div>
  );
}

function DomainCharts({ iso3, indicators }: { iso3: string; indicators: string[] }) {
  return (
    <div className="chart-grid">
      {indicators.map((code) => (
        <DomainChart key={code} iso3={iso3} indicator={code} />
      ))}
    </div>
  );
}

function DomainChart({ iso3, indicator }: { iso3: string; indicator: string }) {
  const [obs, setObs] = useState<CountryObservation[] | null>(null);
  useEffect(() => {
    const c = new AbortController();
    setObs(null);
    fetchCountryObservations(iso3, { indicator, limit: 200 }, { signal: c.signal })
      .then((r) => setObs(r.items))
      .catch(() => setObs([]));
    return () => c.abort();
  }, [iso3, indicator]);

  const option = useMemo(() => {
    if (!obs || obs.length === 0) return null;
    const sorted = [...obs].sort((a, b) =>
      a.period_start.localeCompare(b.period_start),
    );
    return {
      grid: { left: 48, right: 16, top: 24, bottom: 32 },
      xAxis: {
        type: "category" as const,
        data: sorted.map((o) => o.period_start.slice(0, 4)),
      },
      yAxis: { type: "value" as const, scale: true },
      series: [{ type: "line" as const, data: sorted.map((o) => o.value), smooth: true }],
      tooltip: { trigger: "axis" as const },
    };
  }, [obs]);

  return (
    <div className="glass chart-card">
      <p className="label-md text-tertiary">{indicatorLabel(indicator)}</p>
      {obs === null ? (
        <p className="body-sm">Loading…</p>
      ) : option ? (
        <EChart option={option} style={{ height: 220, width: "100%" }} />
      ) : (
        <p className="body-sm text-tertiary">No observations for {indicator}.</p>
      )}
    </div>
  );
}

/* ---------- /data ---------- */

export function DataExplorer() {
  const indicatorsState = useIndicators();
  const indicators = ready(indicatorsState);
  const countriesState = useLiveCountries();
  const countries = ready(countriesState);
  const iso3s = countries?.map((c) => c.iso3) ?? [];
  const [iso3, setIso3] = useState("USA");
  const [code, setCode] = useState<string>("");
  const [obs, setObs] = useState<CountryObservation[] | null>(null);

  useEffect(() => {
    if (!code) return;
    const c = new AbortController();
    setObs(null);
    fetchCountryObservations(iso3, { indicator: code, limit: 300 }, { signal: c.signal })
      .then((r) => setObs(r.items))
      .catch(() => setObs([]));
    return () => c.abort();
  }, [iso3, code]);

  return (
    <div className="section-stack">
      <div className="glass compare-controls">
        <CountrySelect value={iso3} onChange={setIso3} iso3s={iso3s} />
        <select
          className="config-select"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          aria-label="Select indicator"
        >
          <option value="">Select indicator…</option>
          {(indicators ?? []).map((i) => (
            <option key={i.code} value={i.code}>
              {i.code}
            </option>
          ))}
        </select>
      </div>
      {!code ? (
        <PanelState state="Choose a country and indicator to inspect observations." />
      ) : obs === null ? (
        <PanelState state="Loading observations…" />
      ) : obs.length === 0 ? (
        <PanelState state="No observations for this selection." />
      ) : (
        <div className="glass table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Period</th>
                <th className="num">Value</th>
                <th>Source</th>
                <th>Vintage</th>
              </tr>
            </thead>
            <tbody>
              {obs.map((o) => (
                <tr key={o.id}>
                  <td>{formatDate(o.period_start)}</td>
                  <td className="num">{o.value}</td>
                  <td>{o.source_key ?? "—"}</td>
                  <td>{o.vintage_number ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ---------- /sources ---------- */

export function SourcesPanel() {
  const sourcesState = useDataSources();
  const sources = ready(sourcesState);
  const sErr = isErr(sourcesState);
  const runsState = useIngestionRuns();
  const runs = ready(runsState);
  const rErr = isErr(runsState);

  return (
    <div className="section-stack">
      <div className="glass">
        <h2 className="headline-sm panel-title">Registered data sources</h2>
        {sErr ? (
          <PanelState state="Sources unavailable." />
        ) : !sources ? (
          <PanelState state="Loading…" />
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Key</th>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={s.source_key}>
                    <td>{s.source_key}</td>
                    <td>{s.name}</td>
                    <td>{s.status}</td>
                    <td>{s.description ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <div className="glass">
        <h2 className="headline-sm panel-title">Ingestion runs</h2>
        {rErr ? (
          <PanelState state="Ingestion runs unavailable." />
        ) : !runs ? (
          <PanelState state="Loading…" />
        ) : runs.length === 0 ? (
          <PanelState state="No ingestion runs recorded." />
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Started</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th className="num">Rows</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id}>
                    <td>{r.started_at ? formatDate(r.started_at) : "—"}</td>
                    <td>{r.source_key ?? "—"}</td>
                    <td>{r.status}</td>
                    <td className="num">{r.observations_inserted ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------- /progress ---------- */

export function ProgressPanel() {
  const countriesState = useLiveCountries();
  const countries = ready(countriesState);
  const iso3 = countries?.[0]?.iso3 ?? "USA";
  const coverageState = useForceCoverage(iso3);
  const coverage = ready(coverageState);
  const health = useHealth();
  const healthData = ready(health);
  const runsState = useIngestionRuns();
  const runs = ready(runsState);

  const scored = coverage?.forces.filter(
    (f) => f.status === "available",
  ).length;
  const partial = coverage?.forces.filter((f) => f.status === "partial").length;

  return (
    <div className="section-stack">
      <div className="metric-grid">
        <div className="glass metric-card">
          <p className="label-md text-tertiary">Executable forces</p>
          <p className="metric-value">{EXECUTABLE_COUNT}<span className="metric-denom">/{TOTAL_FORCES}</span></p>
          <p className="body-sm">6 ratified forces (DEC-040 ratified).</p>
        </div>
        <div className="glass metric-card">
          <p className="label-md text-tertiary">Coverage — {iso3}</p>
          <p className="metric-value">
            {scored ?? "—"}<span className="metric-denom"> available</span>
          </p>
          <p className="body-sm">{partial ?? "—"} partial. Coverage ≠ score.</p>
        </div>
        <div className="glass metric-card">
          <p className="label-md text-tertiary">API</p>
          <p className="metric-value">
            {healthData ? healthData.status : "…"}
          </p>
          <p className="body-sm">
            DB: {healthData?.database ?? "unknown"}
          </p>
        </div>
        <div className="glass metric-card">
          <p className="label-md text-tertiary">Ingestion runs</p>
          <p className="metric-value">{runs?.length ?? "—"}</p>
          <p className="body-sm">Recorded provider pulls.</p>
        </div>
      </div>
      <div className="glass">
        <h2 className="headline-sm panel-title">Force coverage — {iso3}</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Force</th>
                <th>Status</th>
                <th>Live inputs</th>
              </tr>
            </thead>
            <tbody>
              {(coverage?.forces ?? []).map((f) => (
                <tr key={f.code}>
                  <td>{f.name}</td>
                  <td>
                    <span className={`status-dot status-${f.status}`} />
                    {f.status.replace(/_/g, " ")}
                  </td>
                  <td>
                    {f.live_inputs.length > 0
                      ? f.live_inputs
                          .map((i) => i.indicator_code)
                          .join(", ")
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <AuthoritativeStatus />
      <div className="glass">
        <h2 className="headline-sm panel-title">Force research stages (manual tracking)</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Force</th>
                <th>Research</th>
                <th>Data</th>
                <th>Method proposed</th>
                <th>Method approved</th>
                <th>Implemented</th>
                <th>Tests</th>
                <th>API</th>
                <th>Frontend</th>
                <th>Ratification</th>
              </tr>
            </thead>
            <tbody>
              {FORCE_PROGRESS.map((f) => (
                <tr key={f.code} title={f.note}>
                  <td>{f.name}</td>
                  {[
                    f.researchCompleted,
                    f.dataSourced,
                    f.methodologyProposed,
                    f.methodologyApproved,
                    f.implemented,
                    f.testsPassing,
                    f.apiAvailable,
                    f.frontendConnected,
                  ].map((ok, i) => (
                    <td key={i} className="num">
                      {ok ? "✓" : "—"}
                    </td>
                  ))}
                  <td>
                    <span
                      className={`status-pill ${
                        f.ratification === "ratified"
                          ? "status-available"
                          : f.ratification === "provisional"
                            ? "status-partial"
                            : ""
                      }`}
                    >
                      {f.ratification}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="section-note" style={{ padding: "0 var(--space-4) var(--space-3)" }}>
          Derived from <code>src/features/forces/forceProgress.ts</code> — the
          maintained research metadata, not hardcoded percentages.
        </p>
      </div>
    </div>
  );
}

/* ---------- /settings ---------- */

export function SettingsPanel() {
  const [theme, setTheme] = useState<string>("dark");

  useEffect(() => {
    const current = document.documentElement.dataset.theme;
    if (current && current !== theme) setTheme(current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("bca-theme", theme);
    } catch {
      /* private mode */
    }
  }, [theme]);

  return (
    <div className="section-stack">
      <div className="glass settings-section">
        <h2 className="headline-sm panel-title">Appearance</h2>
        <div className="settings-row">
          <span>Theme</span>
          <span className="pill-row">
            {(["dark", "light"] as const).map((t) => (
              <button
                key={t}
                type="button"
                className={`glass-button ${theme === t ? "btn-active" : ""}`}
                onClick={() => setTheme(t)}
                aria-pressed={theme === t}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </span>
        </div>
      </div>
      <div className="glass settings-section">
        <h2 className="headline-sm panel-title">Local data</h2>
        <div className="settings-row">
          <span>Workspace layouts</span>
          <button
            type="button"
            className="glass-button widget-btn-danger"
            onClick={() => {
              if (confirm("Delete all saved workspaces and layouts?")) {
                localStorage.removeItem("bca-workspaces");
                location.reload();
              }
            }}
          >
            Clear saved workspaces
          </button>
        </div>
      </div>
    </div>
  );
}


/** Authoritative engine status — derived from the backend methodology
 *  registry via /api/research/progress (Mission 2 §22). Replaces manual
 *  booleans for the executable-status view; the manual table below remains
 *  for process-stage tracking. */
function AuthoritativeStatus() {
  const [state, setState] = useState<
    { kind: "loading" | "ready" | "error"; data?: ResearchProgress; error?: string }
  >({ kind: "loading" });
  useEffect(() => {
    const c = new AbortController();
    fetchResearchProgress({ signal: c.signal })
      .then((data) => setState({ kind: "ready", data }))
      .catch((e) => setState({ kind: "error", error: String(e) }));
    return () => c.abort();
  }, []);
  if (state.kind !== "ready" || !state.data) {
    return (
      <div className="glass">
        <h2 className="headline-sm panel-title">Engine status (authoritative)</h2>
        <p className="body-sm">
          {state.kind === "error" ? `Unavailable: ${state.error}` : "Loading…"}
        </p>
      </div>
    );
  }
  const labels: Record<string, string> = {
    approved_level: "Approved level", partial: "Partial proxy",
    dimension_only: "Dimension only", context_only: "Context module",
    deferred: "Deferred",
  };
  return (
    <div className="glass">
      <h2 className="headline-sm panel-title">
        Engine status — authoritative ({state.data.as_of_period})
      </h2>
      <p className="body-sm">
        {Object.entries(state.data.counts)
          .map(([k, v]) => `${labels[k] ?? k}: ${v}`)
          .join(" · ")}
      </p>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr><th>Force</th><th>Status</th><th>Dimensions</th><th>Ceiling</th></tr>
          </thead>
          <tbody>
            {state.data.forces.map((f) => (
              <tr key={f.force_code}>
                <td>{f.force_name}</td>
                <td>{labels[f.implementation_status] ?? f.implementation_status}</td>
                <td>{f.dimensions.join(", ") || "—"}</td>
                <td>{f.coverage_ceiling ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
