import { useMemo, useState } from "react";
import {
  fetchCountryObservations,
  fetchIndicatorRevisions,
} from "@/lib/api/client";
import type { CountryObservation } from "@/types/api";
import {
  useLiveCountries,
  useIndicators,
  useDataSources,
  type AsyncState,
} from "@/features/widgets/hooks";
import { useFetch } from "@/lib/ui/shared";

function ready<T>(s: AsyncState<T>): T | undefined {
  return s.kind === "ready" ? s.data : undefined;
}
import { formatDate, formatQuarter } from "@/lib/format";
import { indicatorLabel, indicatorFormat, formatValue } from "@/features/widgets/indicatorMeta";
import { EChart, baseChartOption } from "@/lib/charts/EChart";
import { toCsv, downloadText } from "@/lib/export";
import { AddToWorkspace } from "@/features/workspace/AddToWorkspace";

const PAGE_SIZE = 100;
const EXPORT_CAP = 10_000;

type SortKey = "period" | "value" | "source" | "vintage";

/** Bounded data explorer — server-side filters + pagination; the browser
 *  never loads more than one page or one bounded export (Mission 4 §12). */
export function DataExplorer() {
  const countries = ready(useLiveCountries());
  const indicators = ready(useIndicators());
  const sources = ready(useDataSources());
  const iso3s = countries?.map((c) => c.iso3) ?? [];

  const [iso3, setIso3] = useState("USA");
  const [code, setCode] = useState("");
  const [source, setSource] = useState("");
  const [startYear, setStartYear] = useState("");
  const [endYear, setEndYear] = useState("");
  const [search, setSearch] = useState("");
  const [view, setView] = useState<"chart" | "table">("table");
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<SortKey>("period");
  const [exporting, setExporting] = useState(false);

  const filteredIndicators = useMemo(() => {
    const all = indicators ?? [];
    const q = search.trim().toLowerCase();
    return q ? all.filter((i) => i.code.toLowerCase().includes(q)) : all;
  }, [indicators, search]);

  const params = useMemo(
    () => ({
      indicator: code || undefined,
      source: source || undefined,
      start: startYear || undefined,
      end: endYear || undefined,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }),
    [code, source, startYear, endYear, page],
  );

  const state = useFetch(
    (c) =>
      code
        ? fetchCountryObservations(iso3, params, { signal: c.signal })
        : Promise.resolve(null),
    [iso3, params.indicator, params.source, params.start, params.end, page],
  );

  const revisionsState = useFetch(
    (c) => (code ? fetchIndicatorRevisions(code, { signal: c.signal }) : Promise.resolve(null)),
    [code],
  );

  const page_items = state.kind === "ready" ? state.data?.items ?? [] : [];
  const total = state.kind === "ready" ? state.data?.total ?? 0 : 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const sorted = useMemo(() => {
    const items = [...page_items];
    items.sort((a, b) => {
      switch (sort) {
        case "value": return b.value - a.value;
        case "source": return (a.source_key ?? "").localeCompare(b.source_key ?? "");
        case "vintage": return b.vintage_number - a.vintage_number;
        default: return b.period_start.localeCompare(a.period_start);
      }
    });
    return items;
  }, [page_items, sort]);

  const option = useMemo(() => {
    const items = [...page_items].sort((a, b) =>
      a.period_start.localeCompare(b.period_start),
    );
    if (items.length === 0) return null;
    const base = baseChartOption();
    return {
      ...base,
      xAxis: { ...base.xAxis, type: "time" as const },
      yAxis: { type: "value" as const, scale: true },
      series: [
        { type: "line" as const, showSymbol: false,
          data: items.map((o) => [o.period_start.slice(0, 10), o.value]) },
      ],
      tooltip: {
        ...base.tooltip,
        valueFormatter: (v: unknown) =>
          formatValue(indicatorFormat(code), Number(v)),
      },
    } as import("echarts").EChartsOption;
  }, [page_items, code]);

  const setFilter = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v);
    setPage(0);
  };

  async function exportAll(format: "csv" | "json") {
    if (!code) return;
    setExporting(true);
    try {
      const all: CountryObservation[] = [];
      let offset = 0;
      // Bounded: stops at EXPORT_CAP or the reported total.
      while (offset < EXPORT_CAP) {
        const r = await fetchCountryObservations(iso3, {
          ...params, limit: 1000, offset,
        });
        all.push(...r.items);
        if (r.items.length < 1000 || all.length >= r.total) break;
        offset += 1000;
      }
      const stamp = `${iso3}_${code}_${new Date().toISOString().slice(0, 10)}`;
      if (format === "csv") {
        downloadText(
          `${stamp}.csv`,
          toCsv(
            ["period_start", "value", "unit", "source", "vintage", "retrieved_at"],
            all.map((o) => [
              o.period_start.slice(0, 10), o.value, o.unit, o.source_key,
              o.vintage_number, o.retrieved_at,
            ]),
          ),
          "text/csv",
        );
      } else {
        downloadText(
          `${stamp}.json`,
          JSON.stringify(
            { country: iso3, indicator: code, filters: params,
              exported: all.length, observations: all },
            null, 1,
          ),
          "application/json",
        );
      }
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="section-stack">
      <div className="glass compare-controls" style={{ flexWrap: "wrap" }}>
        <select className="config-select" value={iso3}
                onChange={(e) => setFilter(setIso3)(e.target.value)}
                aria-label="Country">
          {iso3s.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input className="config-select" placeholder="Search indicators…"
               value={search} onChange={(e) => setSearch(e.target.value)}
               aria-label="Search indicators" style={{ maxWidth: 170 }} />
        <select className="config-select" value={code}
                onChange={(e) => setFilter(setCode)(e.target.value)}
                aria-label="Indicator">
          <option value="">Select indicator…</option>
          {filteredIndicators.map((i) => (
            <option key={i.code} value={i.code}>{i.code}</option>
          ))}
        </select>
        <select className="config-select" value={source}
                onChange={(e) => setFilter(setSource)(e.target.value)}
                aria-label="Source">
          <option value="">All sources</option>
          {(sources ?? []).map((s) => (
            <option key={s.source_key} value={s.source_key}>{s.source_key}</option>
          ))}
        </select>
        <input className="config-select" placeholder="From year" value={startYear}
               onChange={(e) => setFilter(setStartYear)(e.target.value)}
               aria-label="From year" style={{ maxWidth: 90 }} />
        <input className="config-select" placeholder="To year" value={endYear}
               onChange={(e) => setFilter(setEndYear)(e.target.value)}
               aria-label="To year" style={{ maxWidth: 90 }} />
        <button type="button" className="glass-button"
                onClick={() => setView(view === "table" ? "chart" : "table")}>
          {view === "table" ? "Chart view" : "Table view"}
        </button>
        <button type="button" className="glass-button" disabled={!code || exporting}
                onClick={() => exportAll("csv")}>Export CSV</button>
        <button type="button" className="glass-button" disabled={!code || exporting}
                onClick={() => exportAll("json")}>Export JSON</button>
        {code && (
          <AddToWorkspace typeId="indicator-chart"
                          config={{ countries: [iso3], indicator: code }} />
        )}
      </div>

      {!code ? (
        <div className="glass-subtle state-box">
          <p className="body-sm">Choose a country and indicator to inspect observations.</p>
        </div>
      ) : state.kind === "loading" ? (
        <div className="glass-subtle state-box"><p className="body-sm">Loading observations…</p></div>
      ) : state.kind === "error" ? (
        <div className="glass-subtle state-box" role="alert">
          <p className="body-sm">Observations are currently unavailable.</p>
        </div>
      ) : sorted.length === 0 ? (
        <div className="glass-subtle state-box">
          <p className="body-sm">No observations match the current filters.</p>
        </div>
      ) : (
        <>
          <div className="glass table-wrap">
            {view === "chart" && option ? (
              <div style={{ padding: "var(--space-4)" }}>
                <EChart option={option} style={{ height: 280 }}
                        ariaLabel={`${indicatorLabel(code)} history for ${iso3}`} />
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th onClick={() => setSort("period")} style={{ cursor: "pointer" }}>Period</th>
                    <th className="num" onClick={() => setSort("value")} style={{ cursor: "pointer" }}>Value</th>
                    <th>Unit</th>
                    <th onClick={() => setSort("source")} style={{ cursor: "pointer" }}>Source</th>
                    <th className="num" onClick={() => setSort("vintage")} style={{ cursor: "pointer" }}>Vintage</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((o) => (
                    <tr key={o.id}>
                      <td title={formatDate(o.period_start)}>
                        {formatQuarter(o.period_start)}
                      </td>
                      <td className="num">
                        {formatValue(indicatorFormat(code), o.value)}
                      </td>
                      <td>{o.unit ?? "—"}</td>
                      <td>{o.source_key ?? "—"}</td>
                      <td className="num">{o.vintage_number}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div className="glass" style={{ padding: "var(--space-3)" }}>
            <p className="body-sm">
              {total.toLocaleString()} matching observations · page{" "}
              {page + 1} of {pages}
            </p>
            <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
              <button type="button" className="glass-button" disabled={page === 0}
                      onClick={() => setPage(page - 1)}>Previous</button>
              <button type="button" className="glass-button" disabled={page >= pages - 1}
                      onClick={() => setPage(page + 1)}>Next</button>
            </div>
            {revisionsState.kind === "ready" && revisionsState.data && (
              <p className="section-note">
                {revisionsState.data.length === 0
                  ? "No recorded revisions for this indicator."
                  : `${revisionsState.data.length} recorded revision(s) — see /api/indicators/${code}/revisions.`}
              </p>
            )}
            <p className="section-note">
              Exports include units, periods and source identities. Formula-like
              cell values are quoted to prevent spreadsheet injection.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
