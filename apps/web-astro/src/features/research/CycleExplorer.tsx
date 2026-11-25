import { useState } from "react";
import {
  fetchCompositeModels,
  fetchCountryCycle,
  fetchCycleHistory,
} from "@/lib/api/client";
import type {
  CompositeModelInfo,
  CompositeResult,
  CycleHistoryResponse,
} from "@/types/research";
import { EChart } from "@/lib/charts/EChart";
import { cycleHistoryOption } from "@/lib/charts/cycleChart";
import { Badge, COUNTRIES, useFetch } from "@/lib/ui/shared";
import { AddToWorkspace } from "@/features/workspace/AddToWorkspace";

const START_YEARS = [1996, 2000, 2005, 2010, 2015];

/** Big Cycle explorer — experimental composite + stage classification,
 *  computed in Python through /api/research/*. No production cycle score
 *  exists; every number shown is labelled experimental + retrospective. */
export function CycleExplorer() {
  const [iso3, setIso3] = useState("USA");
  const [model, setModel] = useState("model_b_domain");
  const [startYear, setStartYear] = useState(2000);

  const models = useFetch<CompositeModelInfo[]>(fetchCompositeModels, []);
  const cycle = useFetch<CompositeResult>(
    (c) => fetchCountryCycle(iso3, model, { signal: c.signal }),
    [iso3, model],
  );
  const history = useFetch<CycleHistoryResponse>(
    (c) =>
      fetchCycleHistory(iso3, model, startYear, { signal: c.signal }),
    [iso3, model, startYear],
  );

  const composite = cycle.kind === "ready" ? cycle.data : null;
  const hist = history.kind === "ready" ? history.data : null;
  const latestStage =
    hist?.points?.filter((p) => p.stage).at(-1)?.stage ?? null;
  const latestPhase =
    hist?.points?.filter((p) => p.phase).at(-1)?.phase ?? null;

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
          Composite model{" "}
          <select className="config-select" value={model}
                  onChange={(e) => setModel(e.target.value)}>
            {(models.kind === "ready" ? models.data : []).map((m) => (
              <option key={m.model_id} value={m.model_id}>
                {m.model_id} ({m.kind})
              </option>
            ))}
            {models.kind !== "ready" && <option value={model}>{model}</option>}
          </select>
        </label>
        <label>
          From{" "}
          <select className="config-select" value={startYear}
                  onChange={(e) => setStartYear(Number(e.target.value))}>
            {START_YEARS.map((y) => <option key={y}>{y}</option>)}
          </select>
        </label>
        <Badge tone="warn">EXPERIMENTAL — not a production classification</Badge>
      </div>

      {/* Latest experimental result */}
      <div className="glass">
        <h2 className="headline-sm panel-title">
          National conditions — {iso3} <Badge tone="warn">experimental</Badge>
        </h2>
        {cycle.kind === "loading" && <p className="body-sm">Loading…</p>}
        {cycle.kind === "error" && (
          <p className="body-sm">Unavailable: {cycle.error}</p>
        )}
        {composite && (
          <div className="research-grid">
            <div className="metric-card glass-subtle">
              <p className="label-md text-tertiary">
                Conditions ({composite.period})
              </p>
              <p className="metric-value">
                {composite.composite.score?.toFixed(1) ?? "unavailable"}
              </p>
              <p className="body-sm">
                {latestStage ? `stage ${latestStage}` : "no stage"}
                {latestPhase ? ` · phase ${latestPhase}` : ""}
                {` · coverage ${(composite.composite.coverage_ratio * 100).toFixed(0)}%`}
              </p>
            </div>
            <div>
              <p className="label-md text-tertiary">Weights</p>
              <ul className="body-sm weight-list">
                {Object.entries(composite.composite.weights).map(([f, w]) => (
                  <li key={f}>{f} — {(w * 100).toFixed(1)}%</li>
                ))}
              </ul>
              {composite.composite.excluded_forces.length > 0 && (
                <p className="body-sm">
                  Excluded — {composite.composite.excluded_forces.join(", ")}
                </p>
              )}
              {composite.composite.warnings.map((w) => (
                <p key={w} className="body-sm">⚠ {w}</p>
              ))}
              {composite.composite.limitations.map((w) => (
                <p key={w} className="body-sm">⚠ {w}</p>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Historical cycle */}
      <div className="glass">
        <h2 className="headline-sm panel-title">
          Experimental cycle history — {iso3}{" "}
          <Badge tone="warn">retrospective</Badge>
        </h2>
        <AddToWorkspace typeId="cycle-history"
          config={{ country: iso3, model, startYear }} />
        {history.kind === "loading" && <p className="body-sm">Loading…</p>}
        {history.kind === "error" && (
          <p className="body-sm">Unavailable: {history.error}</p>
        )}
        {hist && (
          <>
            <EChart option={cycleHistoryOption(hist)} style={{ height: 320 }}
                  ariaLabel={`Experimental composite history for ${iso3}`} />
            <p className="body-sm">
              {hist.transitions.length} stage transitions · coverage{" "}
              {(hist.coverage_ratio * 100).toFixed(0)}% · engine{" "}
              {hist.engine_version} · retrospective, backtest_safe=false
            </p>
            {hist.warnings.map((w) => (
              <p key={w} className="body-sm">⚠ {w}</p>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
