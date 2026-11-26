import { useMemo, useState } from "react";
import {
  fetchCurrencyPowerOverview,
  fetchDebtCycleOverview,
} from "@/lib/api/client";
import { useFetch } from "@/lib/ui/shared";
import type { CrisisMarker, NamedSeries } from "@/types/research_modules";
import { SeriesChart, periodToDate } from "./SeriesChart";

const PRIMARY = ["USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND"];
const JST_EXTRA = ["EUR", "AUS", "BEL", "CAN", "DNK", "ESP", "FIN", "IRL", "ITA", "NLD", "NOR", "PRT", "SWE"];
const TABS = ["Sectoral debt", "Monetary & fiscal", "Crisis evidence", "Currency power", "Financial centres"] as const;

function chip(active: boolean) {
  return `chip ${active ? "chip-active" : ""}`;
}

function EntityPicker({
  entities, selected, onToggle, extras, showExtras, onToggleExtras,
}: {
  entities: string[]; selected: Set<string>;
  onToggle: (e: string) => void;
  extras: string[]; showExtras: boolean; onToggleExtras: () => void;
}) {
  return (
    <div className="chip-row" role="group" aria-label="countries">
      {entities.map((e) => (
        <button key={e} className={chip(selected.has(e))} onClick={() => onToggle(e)}
          aria-pressed={selected.has(e)}>{e}</button>
      ))}
      {showExtras && extras.map((e) => (
        <button key={e} className={chip(selected.has(e))} onClick={() => onToggle(e)}
          aria-pressed={selected.has(e)}>{e}</button>
      ))}
      <button className="chip chip-dim" onClick={onToggleExtras} aria-pressed={showExtras}>
        {showExtras ? "Hide extended panel" : "+ Extended (EUR/JST)"}
      </button>
    </div>
  );
}

function VariablePicker({
  options, value, onChange, label,
}: { options: [string, string][]; value: string; onChange: (v: string) => void; label: string }) {
  return (
    <label className="field-inline">
      <span className="label-md text-tertiary">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="select">
        {options.map(([k, lbl]) => <option key={k} value={k}>{lbl}</option>)}
      </select>
    </label>
  );
}

/** Build the cross-entity series map for one variable. */
function pick(section: Record<string, Record<string, NamedSeries>> | undefined,
              variable: string, entities: string[]): Record<string, NamedSeries | undefined> {
  const out: Record<string, NamedSeries | undefined> = {};
  for (const e of entities) out[e] = section?.[e]?.[variable];
  return out;
}

function unionVariables(section: Record<string, Record<string, NamedSeries>> | undefined,
                        entities: string[]): [string, string][] {
  const seen = new Map<string, string>();
  for (const e of entities) {
    for (const [k, s] of Object.entries(section?.[e] ?? {})) {
      if (!seen.has(k)) seen.set(k, s.meta.label);
    }
  }
  return [...seen.entries()];
}

function SectionChart({
  section, entities, crises, showCrises,
}: {
  section: Record<string, Record<string, NamedSeries>> | undefined;
  entities: string[]; crises?: Record<string, CrisisMarker[]> | undefined;
  showCrises: boolean;
}) {
  const options = unionVariables(section, entities);
  const [variable, setVariable] = useState("");
  const effective = variable || options[0]?.[0] || "";
  const seriesMap = pick(section, effective, entities);
  const meta = Object.values(seriesMap).find(Boolean)?.meta;
  const marks = useMemo(() => entities.flatMap((e) => crises?.[e] ?? []), [entities, crises]);
  return (
    <div className="glass-card" style={{ padding: "var(--space-4)" }}>
      <VariablePicker label="Series" options={options} value={effective} onChange={setVariable} />
      {meta && (
        <p className="caption" style={{ margin: "var(--space-2) 0" }}>
          {meta.label} — {meta.unit} · {meta.source.publisher} ({meta.source.dataset_version})
          {meta.derived_estimate && <strong> · derived estimate{meta.methodology ? ` (${meta.methodology})` : ""}</strong>}
        </p>
      )}
      <SeriesChart series={seriesMap} unit={meta?.unit} height={360}
        crisisMarks={showCrises ? marks : undefined} />
    </div>
  );
}

export function DebtCycleExplorer() {
  const [selected, setSelected] = useState<Set<string>>(new Set(PRIMARY));
  const [showExtras, setShowExtras] = useState(false);
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);
  const [showCrises, setShowCrises] = useState(true);
  const [currencyTab, setCurrencyTab] = useState(0);
  const entities = [...selected].filter((e) => PRIMARY.includes(e) || JST_EXTRA.includes(e));

  const toggle = (e: string) =>
    setSelected((s) => {
      const n = new Set(s);
      n.has(e) ? n.delete(e) : n.add(e);
      return n;
    });

  const debt = useFetch((c) => fetchDebtCycleOverview([...entities], { signal: c.signal }), [entities.join(",")]);
  const currency = useFetch((c) => fetchCurrencyPowerOverview({ signal: c.signal }), []);
  const data = debt.kind === "ready" ? debt.data : null;

  return (
    <div className="stack-4">
      <EntityPicker entities={PRIMARY} extras={JST_EXTRA} selected={selected}
        onToggle={toggle} showExtras={showExtras} onToggleExtras={() => setShowExtras(!showExtras)} />
      <div className="chip-row" role="tablist" aria-label="research section">
        {TABS.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t}
            className={chip(tab === t)} onClick={() => setTab(t)}>{t}</button>
        ))}
        <label className="chip" style={{ marginLeft: "auto" }}>
          <input type="checkbox" checked={showCrises}
            onChange={(e) => setShowCrises(e.target.checked)} /> crisis markers
        </label>
      </div>

      {debt.kind === "loading" && <p className="body-sm text-tertiary">Loading research series…</p>}
      {debt.kind === "error" && <p className="body-sm">Failed to load: {debt.error}</p>}

      {data && tab === "Sectoral debt" && (
        <SectionChart section={data.sections.sectoral_credit} entities={entities}
          crises={data.crisis_overlay} showCrises={showCrises} />
      )}

      {data && tab === "Monetary & fiscal" && (
        <div className="stack-4">
          <SectionChart section={data.sections.monetary_conditions} entities={entities}
            crises={data.crisis_overlay} showCrises={showCrises} />
          <SectionChart section={data.sections.fiscal_conditions} entities={entities}
            crises={data.crisis_overlay} showCrises={showCrises} />
          <p className="caption text-tertiary">
            Nominal and real rates are separate series. Real rate = JST long rate minus
            contemporaneous CPI inflation (derived). JST fiscal aggregates are nominal
            local currency converted to GDP ratios; the interest-burden series is a
            modelled estimate (debt/GDP × long rate), not an official expenditure series.
          </p>
        </div>
      )}

      {data && tab === "Crisis evidence" && (
        <div className="glass-card" style={{ padding: "var(--space-4)" }}>
          <p className="caption text-tertiary">
            Independently dated JST systemic banking-crisis onsets. Dashed markers on
            other tabs show these events; overlap with credit series is evidence
            display only — it does not imply causation. Registered evaluations:
            H01-P1.0 (public debt change — failed, AUC 0.363/0.381/0.296),
            H01B-P1.0 (private credit — exploratory retrospective diagnostic,
            1y AUC 0.719, bootstrap CI 0.52–0.85), H01T-P1.0 (level thresholds —
            no reproducible universal cutoff).
          </p>
          <table className="table" style={{ marginTop: "var(--space-3)" }}>
            <thead><tr><th>Entity</th><th>Crisis onset years</th><th>Source</th><th>Pre-crisis series available</th></tr></thead>
            <tbody>
              {entities.map((e) => {
                const crises = data.crisis_overlay[e] ?? [];
                const sect = data.sections.sectoral_credit[e] ?? {};
                const mon = data.sections.monetary_conditions[e] ?? {};
                const preAvailability = crises.length
                  ? [...new Set([...Object.entries(sect), ...Object.entries(mon)]
                      .filter(([, s]) => s?.points?.some(([p]) => {
                        const y = periodToDate(p)?.getUTCFullYear();
                        return y !== undefined && crises.some((c) => y >= c.year - 5 && y < c.year);
                      })).map(([k]) => k))].slice(0, 6)
                  : [];
                return (
                  <tr key={e}>
                    <td><strong>{e}</strong></td>
                    <td>{crises.length ? crises.map((c) => c.year).join(", ") : "—"}</td>
                    <td>{crises[0]?.source_key ?? "—"} {crises[0]?.dataset_version ?? ""}</td>
                    <td>{preAvailability.length ? preAvailability.join(", ") : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {tab === "Currency power" && currency.kind === "ready" && (
        <div className="stack-4">
          <div className="chip-row" role="tablist" aria-label="currency view">
            {["Reserve shares (COFER)", "FX turnover (BIS, 200% legs)", "Cross-border claims by currency"].map((t, i) => (
              <button key={t} role="tab" aria-selected={currencyTab === i}
                className={chip(currencyTab === i)} onClick={() => setCurrencyTab(i)}>{t}</button>
            ))}
          </div>
          <div className="glass-card" style={{ padding: "var(--space-4)" }}>
            {currencyTab === 0 && (
              <>
                <p className="caption text-tertiary">
                  IMF COFER shares of allocated official reserves. EUR is the shared
                  euro-area currency — never attributed nationally. INR is not reported
                  by COFER. TFXRA_IMPUTED reallocation shown as the separate
                  "imputed" view only on demand.
                </p>
                <SeriesChart series={currency.data.reserve_currency_shares.share_pct}
                  unit="%" title="Official FX reserve shares (allocated)" height={380} />
              </>
            )}
            {currencyTab === 1 && (
              <>
                <p className="caption text-tertiary">
                  BIS Triennial Survey. Shares are per currency leg and sum to 200%
                  (two sides per transaction) — not normalised to 100%.
                </p>
                <SeriesChart series={currency.data.fx_turnover_shares.share_200pct}
                  unit="% of 200%" title="FX turnover shares (200% convention)" height={380} />
              </>
            )}
            {currencyTab === 2 && (
              <>
                <p className="caption text-tertiary">
                  BIS Locational Banking Statistics — cross-border claims by
                  denomination currency (banking office location, not nationality).
                </p>
                <SeriesChart series={currency.data.banking_claims_by_currency.share_pct}
                  unit="%" title="Cross-border bank claims share by currency" height={380} />
              </>
            )}
          </div>
          <ul className="caption text-tertiary" style={{ paddingLeft: "var(--space-5)" }}>
            {currency.data.methodology.map((m) => <li key={m}>{m}</li>)}
          </ul>
        </div>
      )}

      {tab === "Financial centres" && currency.kind === "ready" && (
        <div className="stack-4">
          <div className="glass-card" style={{ padding: "var(--space-4)" }}>
            <p className="caption text-tertiary">
              BIS LBS reporting-centre shares measure where cross-border claims are
              BOOKED (banking office location) — not ultimate ownership and not total
              national financial influence. Kept separate from reserve-currency measures.
            </p>
            <SeriesChart series={currency.data.financial_centres.share_pct}
              unit="%" title="Reporting-centre cross-border claims share" height={400} />
          </div>
        </div>
      )}

      {data && (
        <ul className="caption text-tertiary" style={{ paddingLeft: "var(--space-5)" }}>
          {data.methodology.map((m) => <li key={m}>{m}</li>)}
        </ul>
      )}
    </div>
  );
}
