import { useState } from "react";
import { fetchHistoricalPowerOverview } from "@/lib/api/client";
import { useFetch } from "@/lib/ui/shared";
import type { NamedSeries } from "@/types/research_modules";
import { SeriesChart } from "./SeriesChart";

const DEFAULT_ENTITIES = ["NLD", "GBR", "USA", "CHN", "IND", "FRA", "DEU", "JPN"];
const VIEWS = ["GDP per capita", "Total GDP level", "Panel share", "Productivity"] as const;
const PWT_LABELS: Record<string, string> = {
  PWT_GDP_PER_WORKER_PPP2021: "Output per worker",
  PWT_GDP_PER_HOUR_PPP2021: "Output per hour",
  PWT_HUMAN_CAPITAL_INDEX: "Human capital",
  PWT_CAPITAL_STOCK_CONST2021_MN: "Capital stock",
  PWT_RTFPNA_2021_1: "TFP (2021=1)",
  PWT_CTFP_USA1: "TFP relative to USA (USA=1)",
};

function chip(active: boolean) {
  return `chip ${active ? "chip-active" : ""}`;
}

export function HistoricalPowerExplorer() {
  const state = useFetch((c) => fetchHistoricalPowerOverview({ signal: c.signal }), []);
  const [view, setView] = useState<(typeof VIEWS)[number]>(VIEWS[0]);
  const [minYear, setMinYear] = useState(1820);
  const [logScale, setLogScale] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set(DEFAULT_ENTITIES));
  const [pwtVar, setPwtVar] = useState("PWT_GDP_PER_WORKER_PPP2021");
  const data = state.kind === "ready" ? state.data : null;
  const entities = data ? Object.keys(data.maddison) : [];
  const toggle = (e: string) =>
    setSelected((s) => { const n = new Set(s); n.has(e) ? n.delete(e) : n.add(e); return n; });
  const sel = [...selected].filter((e) => entities.includes(e));

  const maddisonSeries = (key: "gdppc_2011intl" | "gdp_level_mn_2011intl") => {
    const out: Record<string, NamedSeries | undefined> = {};
    for (const e of sel) out[e] = data?.maddison[e]?.[key];
    return out;
  };
  const shareSeries: Record<string, NamedSeries | undefined> = {};
  for (const e of sel) {
    const pts = data?.panel_share_pct_of_20_entities[e];
    if (pts?.length) {
      shareSeries[e] = {
        meta: {
          label: `${e} share of 20-entity panel`, unit: "%",
          source: { source_key: "maddison", dataset_version: "2023", publisher: "Maddison Project (derived)" },
          frequency: "annual", derived_estimate: true,
        },
        points: pts,
      };
    }
  }
  const pwtSeries: Record<string, NamedSeries | undefined> = {};
  for (const e of sel) pwtSeries[e] = data?.pwt_productivity[e]?.[pwtVar];

  return (
    <div className="stack-4">
      <div className="chip-row" role="group" aria-label="research period">
        {(data?.research_periods ?? []).map((y) => (
          <button key={y} className={chip(minYear === y)} onClick={() => setMinYear(y)}
            aria-pressed={minYear === y}>{y}–present</button>
        ))}
        <label className="chip" style={{ marginLeft: "auto" }}>
          <input type="checkbox" checked={logScale}
            onChange={(e) => setLogScale(e.target.checked)} /> log scale
        </label>
      </div>
      <div className="chip-row" role="group" aria-label="entities">
        {entities.map((e) => (
          <button key={e} className={chip(selected.has(e))} onClick={() => toggle(e)}
            aria-pressed={selected.has(e)}>{e}</button>
        ))}
      </div>
      <div className="chip-row" role="tablist" aria-label="view">
        {VIEWS.map((v) => (
          <button key={v} role="tab" aria-selected={view === v}
            className={chip(view === v)} onClick={() => setView(v)}>{v}</button>
        ))}
      </div>

      {state.kind === "loading" && <p className="body-sm text-tertiary">Loading historical research panel…</p>}
      {state.kind === "error" && <p className="body-sm">Failed to load: {state.error}</p>}

      {data && view === "GDP per capita" && (
        <div className="glass-card" style={{ padding: "var(--space-4)" }}>
          <p className="caption text-tertiary">
            Maddison Project 2023, 2011 international $. Sparse benchmark years are
            shown as observations only — no interpolation across gaps.
          </p>
          <SeriesChart series={maddisonSeries("gdppc_2011intl")} unit="2011 intl $"
            height={400} logScale={logScale} minYear={minYear}
            title="GDP per capita — Maddison Project 2023" />
        </div>
      )}

      {data && view === "Total GDP level" && (
        <div className="glass-card" style={{ padding: "var(--space-4)" }}>
          <p className="caption text-tertiary">
            Derived GDP level (GDP per capita × population), millions of 2011
            international $. Modern codes do NOT represent historical empires —
            see entity definition notes below.
          </p>
          <SeriesChart series={maddisonSeries("gdp_level_mn_2011intl")} unit="mn 2011 intl $"
            height={400} logScale={logScale} minYear={minYear}
            title="Estimated total GDP — Maddison Project 2023" />
        </div>
      )}

      {data && view === "Panel share" && (
        <div className="glass-card" style={{ padding: "var(--space-4)" }}>
          <p className="caption text-tertiary">
            Share of the 20-entity imported research panel — NOT a world share.
            Panel composition is fixed to the imported entities.
          </p>
          <SeriesChart series={shareSeries} unit="%"
            height={400} minYear={minYear}
            title="Share of 20-entity Maddison panel" />
        </div>
      )}

      {data && view === "Productivity" && (
        <div className="glass-card" style={{ padding: "var(--space-4)" }}>
          <div className="chip-row" role="group" aria-label="productivity measure">
            {Object.entries(PWT_LABELS).map(([k, l]) => (
              <button key={k} className={chip(pwtVar === k)} onClick={() => setPwtVar(k)}
                aria-pressed={pwtVar === k}>{l}</button>
            ))}
          </div>
          <p className="caption text-tertiary" style={{ marginTop: "var(--space-2)" }}>
            Penn World Table 11.0 (CC-BY-4.0). Measures kept separate — this
            experimental common-universe view does not replace the approved
            OECD-relative force methodology.
          </p>
          <SeriesChart series={pwtSeries} height={400} minYear={minYear}
            title={PWT_LABELS[pwtVar]} />
        </div>
      )}

      {data && (
        <div className="glass-card" style={{ padding: "var(--space-4)" }}>
          <h3 className="label-md">Entity definition notes</h3>
          <ul className="caption text-tertiary" style={{ paddingLeft: "var(--space-5)" }}>
            {Object.entries(data.entity_definition_notes).map(([e, n]) => (
              <li key={e}><strong>{e}</strong>: {n}</li>
            ))}
            {data.methodology.map((m) => <li key={m}>{m}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}
