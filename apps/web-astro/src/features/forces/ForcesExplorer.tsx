/** The 17 Forces — complete research interface (v1.1 §5–7).
 *
 *  Grid/list of all 17 forces in canonical order, live engine-level
 *  classification counts (research/progress) kept distinct from
 *  country-level availability (force-scores), plus a per-force research
 *  view with history chart, underlying measurements (incl. context
 *  profiles), methodology, sources and limitations.
 *
 *  URL state: ?force=<code>&country=<iso3> — stable, shareable.
 *  No economic calculation is duplicated client-side: every number is an
 *  API value. */
import { useMemo, useState } from "react";
import {
  fetchForceScores,
  fetchForceCoverage,
  fetchForceHistory,
  fetchResearchProgress,
  fetchCountryObservations,
} from "@/lib/api/client";
import type {
  ForceScoresResponse,
  ForceScore,
  ForceCoverageData,
  ForceCoverage,
} from "@/types/api";
import { EChart } from "@/lib/charts/EChart";
import { COUNTRIES, useFetch } from "@/lib/ui/shared";
import { AddToWorkspace } from "@/features/workspace/AddToWorkspace";

const STATUS_LABELS: Record<string, string> = {
  scored: "level",
  dimension_only: "dimension",
  context: "context",
  deferred: "unavailable",
};

const CLASS_LABELS: Record<string, string> = {
  level_published: "published level",
  dimension_only: "dimension-only",
  context_profile: "context profile",
  deferred: "deferred",
};

const FORCE_ICONS: Record<string, string> = {
  leadership_capabilities: "◈",
  education: "✦",
  character_determination: "◆",
  rule_of_law: "§",
  corruption: "◇",
  resource_allocation_efficiency: "⚙",
  global_openness: "◍",
  productivity_output_growth: "▲",
  cost_competitiveness: "≈",
  trade_capital_flows: "⇄",
  infrastructure_investment: "⌂",
  indebtedness: "⚠",
  military_strength: "✚",
  wealth_values_gaps: "≠",
  internal_conflict: "⚡",
  geography: "◎",
  acts_of_nature: "☈",
};

interface GeoProfile {
  methodology_status: string;
  landlocked: boolean;
  coastline_km: number | null;
  island_state: boolean;
  land_area_km2: number | null;
  maritime_access: string | null;
  terrain_notes: string | null;
  limitations: string[];
}

async function fetchGeography(iso3: string): Promise<GeoProfile> {
  const res = await fetch(
    `/api/research/countries/${encodeURIComponent(iso3)}/geography`,
  );
  if (!res.ok) throw new Error(`geography ${res.status}`);
  return res.json();
}

interface ForceMethod {
  method_id: string;
  formula_id: string;
  state: string;
  dimension: string;
  inputs: string[];
  interpretation: string | null;
  units: string | null;
  limitations: string[];
}

async function fetchForceMethods(forceCode: string): Promise<ForceMethod[]> {
  const res = await fetch(
    `/api/research/forces/${encodeURIComponent(forceCode)}/methods`,
  );
  if (!res.ok) throw new Error(`methods ${res.status}`);
  return res.json();
}

function useUrlState() {
  const read = () => {
    if (typeof window === "undefined")
      return { force: null as string | null, country: "USA" };
    const q = new URLSearchParams(window.location.search);
    return { force: q.get("force"), country: q.get("country") ?? "USA" };
  };
  const [state, setState] = useState(read);
  const update = (patch: Partial<{ force: string | null; country: string }>) => {
    setState((prev) => {
      const next = { ...prev, ...patch };
      const q = new URLSearchParams();
      if (next.force) q.set("force", next.force);
      q.set("country", next.country);
      window.history.replaceState(null, "", `?${q.toString()}`);
      return next;
    });
  };
  return { ...state, update };
}

export function ForcesExplorer() {
  const url = useUrlState();
  const iso3 = url.country;
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [view, setView] = useState<"grid" | "list">("grid");

  const scores = useFetch<ForceScoresResponse>(
    (c) => fetchForceScores(iso3, undefined, { signal: c.signal }),
    [iso3],
  );
  const coverage = useFetch<ForceCoverageData>(
    (c) => fetchForceCoverage(iso3, { signal: c.signal }),
    [iso3],
  );
  const progress = useFetch<any>(
    (c) => fetchResearchProgress({ signal: c.signal }),
    [],
  );

  const engineByCode = useMemo(() => {
    const map: Record<string, any> = {};
    if (progress.kind === "ready") {
      for (const f of progress.data.forces) map[f.force_code] = f;
    }
    return map;
  }, [progress]);

  const coverageByCode = useMemo(() => {
    const map: Record<string, ForceCoverage> = {};
    if (coverage.kind === "ready") {
      for (const f of coverage.data.forces) map[f.code] = f;
    }
    return map;
  }, [coverage]);

  const forces = scores.kind === "ready" ? scores.data.forces : [];
  const filtered = forces.filter((f) => {
    if (search) {
      const hay = `${f.force_name} ${f.force_code}`.toLowerCase();
      if (!hay.includes(search.toLowerCase())) return false;
    }
    if (statusFilter) {
      if (statusFilter === "scored" && f.execution_status !== "scored") return false;
      if (statusFilter === "dimension_only" && f.execution_status !== "dimension_only") return false;
      if (statusFilter === "context" && f.execution_status !== "context") return false;
      if (statusFilter === "unavailable" && f.execution_status === "scored") return false;
    }
    return true;
  });

  if (url.force) {
    return (
      <ForceResearch
        iso3={iso3}
        forceCode={url.force}
        forces={forces}
        engineMeta={engineByCode[url.force]}
        coverage={coverageByCode[url.force]}
        onBack={() => url.update({ force: null })}
        onSelectForce={(code) => url.update({ force: code })}
        onCountryChange={(c) => url.update({ country: c })}
      />
    );
  }

  return (
    <div className="forces-explorer">
      <div className="glass-subtle research-toolbar">
        <label>
          Country{" "}
          <select
            className="config-select"
            value={iso3}
            onChange={(e) => url.update({ country: e.target.value })}
          >
            {COUNTRIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="toolbar-search">
          Search{" "}
          <input
            className="config-select"
            type="search"
            placeholder="force name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <div className="toolbar-filters" role="group" aria-label="Status filter">
          {[null, "scored", "dimension_only", "context", "unavailable"].map((s) => (
            <button
              key={s ?? "all"}
              className={`filter-chip ${statusFilter === s ? "active" : ""}`}
              onClick={() => setStatusFilter(s)}
            >
              {s === null ? "All" : s === "unavailable" ? "unavailable" : STATUS_LABELS[s]}
            </button>
          ))}
        </div>
        <div className="toolbar-view" role="group" aria-label="View">
          <button
            className={`filter-chip ${view === "grid" ? "active" : ""}`}
            onClick={() => setView("grid")}
          >
            Grid
          </button>
          <button
            className={`filter-chip ${view === "list" ? "active" : ""}`}
            onClick={() => setView("list")}
          >
            List
          </button>
        </div>
      </div>

      {progress.kind === "ready" && (
        <p className="body-sm forces-counts">
          Engine-level:{" "}
          <strong>{progress.data.counts.level_published}</strong> published levels ·{" "}
          <strong>{progress.data.counts.dimension_only}</strong> dimension-only ·{" "}
          <strong>{progress.data.counts.context_profile}</strong> context profiles ·{" "}
          <strong>{progress.data.counts.deferred}</strong> fully deferred{" "}
          <span className="text-tertiary">
            (as of {progress.data.as_of_period} — engine implementation, not{" "}
            {iso3} availability)
          </span>
          {scores.kind === "ready" && (
            <>
              {" · "}
              {iso3}:{" "}
              <strong>
                {
                  scores.data.forces.filter((f) => f.execution_status === "scored")
                    .length
                }
              </strong>{" "}
              with numerical levels
            </>
          )}
        </p>
      )}

      {scores.kind === "loading" && <div className="clock-skeleton" aria-busy="true" />}
      {scores.kind === "error" && (
        <p className="body-sm" role="alert">
          Force scores unavailable — {scores.error}
        </p>
      )}

      <div className={view === "grid" ? "forces-grid" : "forces-list"} role="list">
        {filtered.map((f) => (
          <ForceCard
            key={f.force_code}
            index={forces.indexOf(f)}
            force={f}
            engineMeta={engineByCode[f.force_code]}
            compact={view === "list"}
            onOpen={() => url.update({ force: f.force_code })}
          />
        ))}
      </div>
      {filtered.length === 0 && scores.kind === "ready" && (
        <p className="body-sm text-tertiary">No forces match the current filter.</p>
      )}
    </div>
  );
}

function ForceCard({
  index,
  force,
  engineMeta,
  compact,
  onOpen,
}: {
  index: number;
  force: ForceScore;
  engineMeta?: any;
  compact: boolean;
  onOpen: () => void;
}) {
  const hasLevel = force.execution_status === "scored" && force.level_score !== null;
  const engineClass = engineMeta?.primary_classification;
  return (
    <button
      className={`force-card glass-subtle ${compact ? "compact" : ""}`}
      onClick={onOpen}
      role="listitem"
    >
      <span className="force-card-head">
        <span className="force-num">{String(index + 1).padStart(2, "0")}</span>
        <span className="force-icon" aria-hidden>
          {FORCE_ICONS[force.force_code] ?? "◌"}
        </span>
        <span className="force-name">{force.force_name}</span>
      </span>
      <span className="force-card-measure">
        {hasLevel ? (
          <>
            <strong className="force-value-lg">{force.level_score!.toFixed(1)}</strong>
            {force.momentum_score !== null && (
              <span className={`force-mom ${force.momentum_score >= 0 ? "up" : "down"}`}>
                {force.momentum_score >= 0 ? "▲" : "▼"}
                {Math.abs(force.momentum_score).toFixed(1)}
              </span>
            )}
          </>
        ) : (
          <span
            className={`status-pill status-${
              force.execution_status === "scored"
                ? "good"
                : force.execution_status === "deferred"
                  ? "warn"
                  : "neutral"
            }`}
          >
            {STATUS_LABELS[force.execution_status] ?? force.execution_status}
          </span>
        )}
      </span>
      {!compact && (
        <span className="force-card-meta">
          {force.period && <span>period {force.period}</span>}
          {force.comparison_semantics === "own_history" && (
            <span className="force-semantics">
              own-history — not internationally ranked
            </span>
          )}
          {engineClass && engineClass !== "level_published" && (
            <span className="text-tertiary">
              {CLASS_LABELS[engineClass] ?? engineClass}
            </span>
          )}
        </span>
      )}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* Individual force research view                                      */
/* ------------------------------------------------------------------ */

function ForceResearch({
  iso3,
  forceCode,
  forces,
  engineMeta,
  coverage,
  onBack,
  onSelectForce,
  onCountryChange,
}: {
  iso3: string;
  forceCode: string;
  forces: ForceScore[];
  engineMeta?: any;
  coverage?: ForceCoverage | undefined;
  onBack: () => void;
  onSelectForce: (code: string) => void;
  onCountryChange: (c: string) => void;
}) {
  const force = forces.find((f) => f.force_code === forceCode);
  const index = forces.findIndex((f) => f.force_code === forceCode);
  const methods = useFetch<ForceMethod[]>(
    () => fetchForceMethods(forceCode),
    [forceCode],
  );
  const history = useFetch<any>(
    (c) => fetchForceHistory(iso3, forceCode, 1990, { signal: c.signal }),
    [iso3, forceCode],
  );
  const geography = useFetch<GeoProfile | null>(
    () =>
      forceCode === "geography" ? fetchGeography(iso3) : Promise.resolve(null),
    [iso3, forceCode],
  );

  const inputCodes = useMemo(() => {
    const codes = new Set<string>();
    if (methods.kind === "ready") {
      for (const m of methods.data) for (const i of m.inputs) codes.add(i);
    }
    for (const li of coverage?.live_inputs ?? []) codes.add(li.indicator_code);
    return [...codes];
  }, [methods, coverage]);

  return (
    <div className="force-research">
      <div className="force-research-nav glass-subtle">
        <button className="filter-chip" onClick={onBack}>
          ← All forces
        </button>
        <label>
          Force{" "}
          <select
            className="config-select"
            value={forceCode}
            onChange={(e) => onSelectForce(e.target.value)}
          >
            {forces.map((f, i) => (
              <option key={f.force_code} value={f.force_code}>
                {String(i + 1).padStart(2, "0")} · {f.force_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Country{" "}
          <select
            className="config-select"
            value={iso3}
            onChange={(e) => onCountryChange(e.target.value)}
          >
            {COUNTRIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <AddToWorkspace
          typeId="force-history"
          config={{ iso3, force_code: forceCode }}
          label="Add to Workspace"
        />
      </div>

      <header className="force-research-header">
        <h2 className="headline-sm">
          <span className="force-num">{String(index + 1).padStart(2, "0")}</span>{" "}
          <span className="force-icon" aria-hidden>
            {FORCE_ICONS[forceCode] ?? "◌"}
          </span>{" "}
          {force?.force_name ?? forceCode.replace(/_/g, " ")}
        </h2>
        {coverage?.description && <p className="body-sm">{coverage.description}</p>}
        <div className="force-research-pills">
          {engineMeta && (
            <span className="status-pill status-neutral">
              engine: {CLASS_LABELS[engineMeta.primary_classification] ?? engineMeta.primary_classification}
            </span>
          )}
          {force && (
            <span className="status-pill status-neutral">
              {iso3}:{" "}
              {force.execution_status === "scored"
                ? "level"
                : engineMeta?.primary_classification === "context_profile"
                  ? "context profile — structural measurements, no numerical level"
                  : engineMeta?.primary_classification === "dimension_only"
                    ? "independent dimension"
                    : (STATUS_LABELS[force.execution_status] ?? force.execution_status)}
            </span>
          )}
          {force?.comparison_semantics === "own_history" && (
            <span className="status-pill status-warn">
              own-history — positions {iso3} against its own past; not an
              international strength ranking
            </span>
          )}
        </div>
      </header>

      <div className="force-research-body">
        <section className="glass force-panel">
          <h3 className="label-md text-tertiary">Current measurement</h3>
          {force?.execution_status === "scored" && force.level_score !== null ? (
            <div className="force-measures">
              <div>
                <p className="metric-value">{force.level_score.toFixed(1)}</p>
                <p className="body-sm text-tertiary">
                  level 0–100 · period {force.period} · {force.coverage_status} coverage
                </p>
              </div>
              {force.relative_score !== null && (
                <div>
                  <p className="metric-value" style={{ fontSize: "var(--text-xl)" }}>
                    {force.relative_score.toFixed(1)}
                  </p>
                  <p className="body-sm text-tertiary">relative — share/position vs reference</p>
                </div>
              )}
              {force.momentum_score !== null && (
                <div>
                  <p className="metric-value" style={{ fontSize: "var(--text-xl)" }}>
                    {force.momentum_score >= 0 ? "+" : ""}
                    {force.momentum_score.toFixed(1)}
                  </p>
                  <p className="body-sm text-tertiary">momentum — own-history direction</p>
                </div>
              )}
            </div>
          ) : (
            <p className="body-sm">
              No approved numerical level for {iso3}.{" "}
              {engineMeta?.primary_classification === "context_profile"
                ? "This force is a context profile — its actual underlying measurements are shown below."
                : engineMeta?.primary_classification === "dimension_only"
                  ? "This force publishes an independent dimension, not a composed level."
                  : "Underlying measurements are shown where available."}
            </p>
          )}
          {force?.limitations?.map((l) => (
            <p key={l} className="body-sm text-tertiary">
              ⚠ {l}
            </p>
          ))}
        </section>

        {/* History chart */}
        <section className="glass force-panel">
          <h3 className="label-md text-tertiary">
            Historical measurements — {iso3}{" "}
            <span className="status-pill status-warn">retrospective</span>
          </h3>
          {history.kind === "loading" && (
            <div className="chart-skeleton" aria-busy="true" style={{ height: 280 }} />
          )}
          {history.kind === "error" && (
            <p className="body-sm">History unavailable — {history.error}</p>
          )}
          {history.kind === "ready" && (
            <ForceHistoryChart data={history.data} />
          )}
        </section>

        {/* Underlying measurements — the actual context content */}
        <section className="glass force-panel">
          <h3 className="label-md text-tertiary">
            Underlying measurements ({inputCodes.length})
          </h3>
          {inputCodes.length === 0 && methods.kind === "ready" && (
            <p className="body-sm text-tertiary">
              No sourced inputs for this force in {iso3}.
            </p>
          )}
          {inputCodes.map((code) => (
            <InputMeasurement key={code} iso3={iso3} code={code} />
          ))}
          {coverage?.coverage_notes && (
            <details className="force-details">
              <summary className="body-sm">Coverage notes</summary>
              <p className="body-sm">{coverage.coverage_notes}</p>
            </details>
          )}
        </section>

        {/* Geography structural profile */}
        {forceCode === "geography" && geography.kind === "ready" && geography.data && (
          <section className="glass force-panel">
            <h3 className="label-md text-tertiary">
              Structural geography profile — {iso3}
            </h3>
            <table className="data-table">
              <tbody>
                <tr>
                  <td>Landlocked</td>
                  <td className="num">{geography.data.landlocked ? "yes" : "no"}</td>
                </tr>
                <tr>
                  <td>Coastline</td>
                  <td className="num">
                    {geography.data.coastline_km?.toLocaleString() ?? "—"} km
                  </td>
                </tr>
                <tr>
                  <td>Island state</td>
                  <td className="num">{geography.data.island_state ? "yes" : "no"}</td>
                </tr>
                <tr>
                  <td>Land area</td>
                  <td className="num">
                    {geography.data.land_area_km2?.toLocaleString() ?? "—"} km²
                  </td>
                </tr>
                <tr>
                  <td>Maritime access</td>
                  <td className="num">{geography.data.maritime_access ?? "—"}</td>
                </tr>
              </tbody>
            </table>
            {geography.data.terrain_notes && (
              <p className="body-sm">{geography.data.terrain_notes}</p>
            )}
            {geography.data.limitations.map((l) => (
              <p key={l} className="body-sm text-tertiary">
                ⚠ {l}
              </p>
            ))}
          </section>
        )}

        {/* Methodology */}
        <section className="glass force-panel">
          <h3 className="label-md text-tertiary">Methodology</h3>
          {methods.kind === "loading" && (
            <div className="clock-skeleton" aria-busy="true" style={{ height: 80 }} />
          )}
          {methods.kind === "ready" && methods.data.length === 0 && (
            <p className="body-sm text-tertiary">
              No registered methodology — implementation deferred.
            </p>
          )}
          {methods.kind === "ready" &&
            methods.data.map((m) => (
              <details key={m.method_id} className="force-details">
                <summary className="body-sm">
                  <strong>{m.interpretation ?? m.formula_id}</strong>{" "}
                  <span className="text-tertiary">
                    {m.dimension} · {m.state.replace(/_/g, " ")}
                    {m.units ? ` · ${m.units}` : ""}
                  </span>
                </summary>
                <p className="body-sm text-tertiary">id: {m.method_id}</p>
                <p className="body-sm">inputs: {m.inputs.join(", ") || "—"}</p>
                {m.limitations.map((l) => (
                  <p key={l} className="body-sm text-tertiary">
                    ⚠ {l}
                  </p>
                ))}
              </details>
            ))}
        </section>
      </div>
    </div>
  );
}

function ForceHistoryChart({ data }: { data: any }) {
  const points: any[] = data.points ?? [];
  const seriesPoints = points.filter(
    (p: any) => p.level_score !== null || p.relative_score !== null || p.momentum_score !== null,
  );
  if (seriesPoints.length === 0) {
    return (
      <p className="body-sm text-tertiary">
        No numerical history — this force has no approved numeric series. Missing
        records are not zero events.
      </p>
    );
  }
  const option = {
    grid: { left: 40, right: 16, top: 30, bottom: 24 },
    tooltip: { trigger: "axis" },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    xAxis: {
      type: "category",
      data: seriesPoints.map((p: any) => p.period),
      axisLabel: { fontSize: 10 },
    },
    yAxis: { type: "value", scale: true, axisLabel: { fontSize: 10 } },
    series: [
      {
        name: "level",
        type: "line",
        data: seriesPoints.map((p: any) => p.level_score),
        connectNulls: false,
        showSymbol: false,
        lineStyle: { width: 2 },
      },
      {
        name: "momentum",
        type: "line",
        data: seriesPoints.map((p: any) => p.momentum_score),
        connectNulls: false,
        showSymbol: false,
        lineStyle: { width: 1, type: "dashed" },
      },
    ],
  };
  return <EChart option={option as any} style={{ height: 280 }} />;
}

function InputMeasurement({ iso3, code }: { iso3: string; code: string }) {
  const obs = useFetch<any>(
    (c) =>
      fetchCountryObservations(iso3, { indicator: code, limit: 100 }, { signal: c.signal }),
    [iso3, code],
  );

  if (obs.kind === "loading") {
    return <div className="clock-skeleton" aria-busy="true" style={{ height: 40 }} />;
  }
  if (obs.kind === "error") {
    return (
      <p className="body-sm text-tertiary">
        {code} — unavailable ({obs.error})
      </p>
    );
  }
  const items = [...(obs.data.items ?? [])].sort(
    (a: any, b: any) =>
      new Date(b.period_start).getTime() - new Date(a.period_start).getTime(),
  );
  if (items.length === 0) {
    return (
      <p className="body-sm text-tertiary">{code} — no observations for {iso3}</p>
    );
  }
  const latest = items[0];
  const prior = items.length > 5 ? items[Math.min(5, items.length - 1)] : null;
  const change =
    prior && prior.value !== 0
      ? ((latest.value - prior.value) / Math.abs(prior.value)) * 100
      : null;
  const year = new Date(latest.period_start).getFullYear();
  return (
    <div className="input-measure">
      <div className="input-measure-head">
        <span className="body-sm">
          <strong>{code.replace(/_/g, " ").toLowerCase()}</strong>
        </span>
        <span className="num force-value-lg">
          {formatMeasure(latest.value)}
          {latest.unit ? ` ${latest.unit}` : ""}
        </span>
      </div>
      <p className="body-sm text-tertiary">
        {year}
        {change !== null && (
          <>
            {" · "}
            {change >= 0 ? "+" : ""}
            {change.toFixed(1)}% vs {new Date(prior!.period_start).getFullYear()}
            {" — direction only, not inherently positive or negative"}
          </>
        )}
        {latest.release_date && ` · published ${latest.release_date.slice(0, 10)}`}
        {" · atlas retrieval evidence"}
      </p>
    </div>
  );
}

function formatMeasure(v: number): string {
  // Fixed en-US formatting — never locale-dependent decimal separators.
  const abs = Math.abs(v);
  const fmt = (n: number, digits: number) =>
    n.toLocaleString("en-US", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  if (abs >= 1e12) return `$${fmt(v / 1e12, 2)}T`;
  if (abs >= 1e9) return `$${fmt(v / 1e9, 1)}B`;
  if (abs >= 1e6) return fmt(v / 1e6, 1) + "M";
  if (abs >= 1000) return fmt(v, 0);
  return fmt(v, 2);
}
