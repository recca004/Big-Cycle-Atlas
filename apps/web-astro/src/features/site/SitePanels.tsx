import { useEffect, useMemo, useState } from "react";
import { fetchForceScores, fetchCountryObservations, fetchResearchProgress } from "@/lib/api/client";
import type { ResearchProgress } from "@/types/research";
import type { ForceScore, CountryObservation } from "@/types/api";
import {
  useLiveCountries,
  useDataSources,
  useIngestionRuns,
  useHealth,
  useForceCoverage,
} from "@/features/widgets/hooks";
import { formatDate } from "@/lib/format";
import { INITIAL_COUNTRIES } from "@big-cycle-atlas/shared";
import {
  loadPrefs,
  savePrefs,
  resetPrefs,
  type Prefs,
} from "@/lib/prefs";
import { EChart } from "@/lib/charts/EChart";
import { AddToWorkspace } from "@/features/workspace/AddToWorkspace";
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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p className="label-md text-tertiary">{indicatorLabel(indicator)}</p>
        <AddToWorkspace typeId="indicator-chart"
                        config={{ countries: [iso3], indicator }} label="＋" />
      </div>
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
  const [prefs, setPrefs] = useState<Prefs>(() => loadPrefs());
  const update = (next: Partial<Prefs>) => setPrefs(savePrefs(next));

  return (
    <div className="section-stack">
      <div className="glass settings-section">
        <h2 className="headline-sm panel-title">Appearance</h2>
        <div className="settings-row">
          <span>Theme</span>
          <span className="pill-row">
            {(["system", "dark", "light"] as const).map((t) => (
              <button
                key={t}
                type="button"
                className={`glass-button ${prefs.theme === t ? "btn-active" : ""}`}
                onClick={() => update({ theme: t })}
                aria-pressed={prefs.theme === t}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </span>
        </div>
        <div className="settings-row">
          <span>Reduced motion</span>
          <button
            type="button"
            className={`glass-button ${prefs.reducedMotion ? "btn-active" : ""}`}
            onClick={() => update({ reducedMotion: !prefs.reducedMotion })}
            aria-pressed={prefs.reducedMotion}
          >
            {prefs.reducedMotion ? "On" : "Off"}
          </button>
        </div>
        <div className="settings-row">
          <span>Reduced transparency</span>
          <button
            type="button"
            className={`glass-button ${prefs.reducedTransparency ? "btn-active" : ""}`}
            onClick={() => update({ reducedTransparency: !prefs.reducedTransparency })}
            aria-pressed={prefs.reducedTransparency}
          >
            {prefs.reducedTransparency ? "On" : "Off"}
          </button>
        </div>
      </div>

      <div className="glass settings-section">
        <h2 className="headline-sm panel-title">Defaults</h2>
        <div className="settings-row">
          <label htmlFor="pref-country">Default country</label>
          <select
            id="pref-country"
            className="config-select"
            value={prefs.defaultCountry}
            onChange={(e) => update({ defaultCountry: e.target.value })}
          >
            {INITIAL_COUNTRIES.map((c) => (
              <option key={c.iso3} value={c.iso3}>
                {c.iso3} — {c.name}
              </option>
            ))}
          </select>
        </div>
        <div className="settings-row">
          <label htmlFor="pref-range">Default date range</label>
          <select
            id="pref-range"
            className="config-select"
            value={prefs.defaultDateRange}
            onChange={(e) =>
              update({ defaultDateRange: e.target.value as Prefs["defaultDateRange"] })
            }
          >
            <option value="5y">Last 5 years</option>
            <option value="10y">Last 10 years</option>
            <option value="25y">Since 2000</option>
            <option value="max">All available</option>
          </select>
        </div>
        <div className="settings-row">
          <label htmlFor="pref-ws">Default workspace</label>
          <select
            id="pref-ws"
            className="config-select"
            value={prefs.defaultWorkspace ?? ""}
            onChange={(e) => update({ defaultWorkspace: e.target.value || null })}
          >
            <option value="">Last used</option>
            <WorkspaceOptions />
          </select>
        </div>
        <div className="settings-row">
          <label htmlFor="pref-ccy">Portfolio base currency</label>
          <select
            id="pref-ccy"
            className="config-select"
            value={prefs.portfolioCurrency}
            onChange={(e) => update({ portfolioCurrency: e.target.value })}
          >
            {["CHF", "USD", "EUR", "GBP", "JPY", "CNY", "INR"].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="settings-row">
          <label htmlFor="pref-num">Number format</label>
          <select
            id="pref-num"
            className="config-select"
            value={prefs.numberFormat}
            onChange={(e) =>
              update({ numberFormat: e.target.value as Prefs["numberFormat"] })
            }
          >
            <option value="en-US">1,234.56 (US)</option>
            <option value="de-CH">1’234.56 (Swiss)</option>
            <option value="en-GB">1,234.56 (UK)</option>
          </select>
        </div>
      </div>

      <div className="glass settings-section">
        <h2 className="headline-sm panel-title">Local data</h2>
        <div className="settings-row">
          <span>Preferences</span>
          <button
            type="button"
            className="glass-button"
            onClick={() => {
              if (confirm("Reset all local preferences to defaults?")) {
                resetPrefs();
                setPrefs(loadPrefs());
              }
            }}
          >
            Reset preferences
          </button>
        </div>
        <div className="settings-row">
          <span>Workspace layouts</span>
          <button
            type="button"
            className="glass-button widget-btn-danger"
            onClick={() => {
              if (confirm("Delete all saved workspaces and layouts?")) {
                localStorage.removeItem("bca:workspaces:v1");
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

/** Options for the default-workspace select, from the persisted store. */
function WorkspaceOptions() {
  const [names, setNames] = useState<string[]>([]);
  useEffect(() => {
    try {
      const raw = localStorage.getItem("bca:workspaces:v1");
      if (!raw) return;
      const parsed = JSON.parse(raw);
      const order: string[] = parsed?.state?.order ?? [];
      const ws = parsed?.state?.workspaces ?? {};
      setNames(order.map((id) => ws[id]?.name ?? id));
    } catch {
      /* ignore */
    }
  }, []);
  return (
    <>
      {names.map((n) => (
        <option key={n} value={n}>{n}</option>
      ))}
    </>
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
    level_published: "Level published",
    dimension_only: "Dimension only", context_profile: "Context profile",
    deferred: "Deferred",
    approved: "approved", partial: "partial ceiling",
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
        {state.data.counts_sum_to_total
          ? ` · total ${state.data.total_forces}`
          : " · ⚠ counts do not sum to 17"}
      </p>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr><th>Force</th><th>Primary class</th><th>Approval</th><th>Dimensions</th><th>Ceiling</th></tr>
          </thead>
          <tbody>
            {state.data.forces.map((f) => (
              <tr key={f.force_code}>
                <td>{f.force_name}</td>
                <td>{labels[f.primary_classification] ?? f.primary_classification}</td>
                <td>{labels[f.approval_state] ?? f.approval_state}</td>
                <td>{f.published_dimensions.join(", ") || "—"}</td>
                <td>{f.coverage_ceiling ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
