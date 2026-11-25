import { useMemo, useState } from "react";
import {
  fetchForceScores,
  fetchCountryObservations,
} from "@/lib/api/client";
import type { CountryObservation, ForceScore } from "@/types/api";
import { useLiveCountries, useIndicators, type AsyncState } from "@/features/widgets/hooks";
import { useFetch } from "@/lib/ui/shared";
import { indicatorLabel, indicatorFormat, formatValue } from "@/features/widgets/indicatorMeta";
import { EChart, baseChartOption } from "@/lib/charts/EChart";
import { toCsv, downloadText } from "@/lib/export";
import { AddToWorkspace } from "@/features/workspace/AddToWorkspace";

function ready<T>(s: AsyncState<T>): T | undefined {
  return s.kind === "ready" ? s.data : undefined;
}

function periodKey(o: CountryObservation): string {
  return o.period_start.slice(0, 10);
}

/* ---------- forces tab ---------- */

function ForcesCompare({ iso3s }: { iso3s: string[] }) {
  const state = useFetch(
    async (c) => {
      const out: Record<string, ForceScore[]> = {};
      await Promise.all(
        iso3s.map(async (iso3) => {
          out[iso3] = (await fetchForceScores(iso3, undefined, { signal: c.signal })).forces;
        }),
      );
      return out;
    },
    [iso3s.join(",")],
  );

  if (iso3s.length === 0)
    return <p className="body-sm">Select at least one country.</p>;
  if (state.kind === "loading")
    return <p className="body-sm">Loading force scores…</p>;
  if (state.kind === "error")
    return <p className="body-sm">Force scores are currently unavailable.</p>;

  const forces = state.data[iso3s[0] ?? ""] ?? [];
  const exportCsv = () => {
    downloadText(
      `forces_${iso3s.join("-")}.csv`,
      toCsv(
        ["force", ...iso3s],
        forces.map((fa: ForceScore) => [
          fa.force_name,
          ...iso3s.map((c) => state.data[c]?.find((x) => x.force_code === fa.force_code)?.level_score ?? null),
        ]),
      ),
      "text/csv",
    );
  };

  return (
    <div className="section-stack">
      <div className="glass table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Force</th>
              {iso3s.map((c) => (
                <th key={c} className="num">
                  {c}{" "}
                  <AddToWorkspace typeId="all-forces"
                                  config={{ country: c }} label="＋" />
                </th>
              ))}
              <th className="num">Δ max−min</th>
            </tr>
          </thead>
          <tbody>
            {forces.map((fa: ForceScore) => {
              const vals = iso3s.map(
                (c) => state.data[c]?.find((x) => x.force_code === fa.force_code) ?? null,
              );
              const nums = vals.map((v) => v?.level_score).filter((v): v is number => v != null);
              // Own-history levels position each country against its own past —
              // a cross-country spread is not a meaningful international difference.
              const ownHistory = vals.some(
                (v) => v?.comparison_semantics === "own_history",
              );
              const spread =
                !ownHistory && nums.length >= 2
                  ? Math.max(...nums) - Math.min(...nums)
                  : null;
              const coverageWarn = vals.some(
                (v) => v && v.coverage_status !== "available",
              );
              return (
                <tr key={fa.force_code}>
                  <td>
                    {fa.force_name}
                    {coverageWarn && (
                      <span className="badge badge-warn" title="Coverage is partial or missing for at least one country">partial</span>
                    )}
                  </td>
                  {vals.map((v, i) => (
                    <td key={i} className="num"
                        title={v?.limitations.join("; ") ?? undefined}>
                      {v?.execution_status === "deferred"
                        ? <span className="text-tertiary" title={v.reasons.join("; ")}>deferred</span>
                        : v?.level_score != null
                          ? v.level_score.toFixed(1)
                          : "—"}
                    </td>
                  ))}
                  <td className="num">
                    {ownHistory ? (
                      <span className="text-tertiary" title="Own-history condition — positions each country against its own past. Not internationally comparable.">
                        n/a · own-history
                      </span>
                    ) : spread != null ? (
                      spread.toFixed(1)
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="glass" style={{ padding: "var(--space-3)" }}>
        <button type="button" className="glass-button" onClick={exportCsv}>Export CSV</button>
        <p className="section-note">
          Approved force levels only; “deferred” forces have no executable
          score. Rows marked “n/a · own-history” (e.g. indebtedness) position
          each country against its own past — no cross-country difference is
          computed for them. Compare raw debt indicators (e.g. government
          debt % of GDP in the indicators tab) for international levels.
        </p>
      </div>
    </div>
  );
}

/* ---------- indicators tab ---------- */

function IndicatorCompare({ iso3s, code, startYear }: { iso3s: string[]; code: string; startYear: string }) {
  const state = useFetch(
    async (c) => {
      const out: Record<string, CountryObservation[]> = {};
      await Promise.all(
        iso3s.map(async (iso3) => {
          out[iso3] = (
            await fetchCountryObservations(
              iso3,
              { indicator: code, start: startYear || undefined, limit: 1000 },
              { signal: c.signal },
            )
          ).items;
        }),
      );
      return out;
    },
    [iso3s.join(","), code, startYear],
  );

  const option = useMemo(() => {
    if (state.kind !== "ready" || !code) return null;
    const base = baseChartOption();
    const series = iso3s
      .map((iso3) => ({
        name: iso3,
        type: "line" as const,
        showSymbol: false,
        data: (state.data[iso3] ?? [])
          .slice()
          .sort((a, b) => a.period_start.localeCompare(b.period_start))
          .map((o) => [periodKey(o), o.value]),
      }))
      .filter((s) => s.data.length > 0);
    if (series.length === 0) return null;
    return {
      ...base,
      legend: { top: 0, textStyle: base.textStyle },
      xAxis: { ...base.xAxis, type: "time" as const },
      yAxis: {
        type: "value" as const, scale: true,
        axisLabel: { formatter: (v: number) => formatValue(indicatorFormat(code), v) },
      },
      tooltip: {
        ...base.tooltip,
        valueFormatter: (v: unknown) => formatValue(indicatorFormat(code), Number(v)),
      },
      series,
    } as import("echarts").EChartsOption;
  }, [state, iso3s, code]);

  const summary = useMemo(() => {
    if (state.kind !== "ready") return [];
    return iso3s.map((iso3) => {
      const items = (state.data[iso3] ?? [])
        .slice()
        .sort((a, b) => b.period_start.localeCompare(a.period_start));
      const latest = items[0];
      return {
        iso3,
        latest,
        count: items.length,
        first: items[items.length - 1],
        sources: [...new Set(items.map((o) => o.source_key).filter(Boolean))],
        units: [...new Set(items.map((o) => o.unit).filter(Boolean))],
      };
    });
  }, [state, iso3s]);

  if (!code) return <p className="body-sm">Select an indicator.</p>;
  if (state.kind === "loading") return <p className="body-sm">Loading…</p>;
  if (state.kind === "error")
    return <p className="body-sm">Observations are currently unavailable.</p>;

  const unitSet = new Set(summary.flatMap((s) => s.units));
  const sourceSet = new Set(summary.flatMap((s) => s.sources));

  const exportCsv = () => {
    const rows: (string | number | null)[][] = [];
    for (const iso3 of iso3s) {
      for (const o of state.data[iso3] ?? []) {
        rows.push([iso3, periodKey(o), o.value, o.unit, o.source_key, o.vintage_number]);
      }
    }
    downloadText(
      `${code}_${iso3s.join("-")}.csv`,
      toCsv(["country", "period_start", "value", "unit", "source", "vintage"], rows),
      "text/csv",
    );
  };

  return (
    <div className="section-stack">
      {option ? (
        <div className="glass" style={{ padding: "var(--space-4)" }}>
          <EChart option={option} style={{ height: 300 }}
                  ariaLabel={`${indicatorLabel(code)} comparison`} />
        </div>
      ) : (
        <div className="glass-subtle state-box">
          <p className="body-sm">No observations for {indicatorLabel(code)} in the selected countries.</p>
        </div>
      )}
      <div className="glass table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Country</th>
              <th className="num">Latest</th>
              <th>Period</th>
              <th className="num">Obs</th>
              <th>Coverage</th>
              <th>Sources</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {summary.map((s) => (
              <tr key={s.iso3}>
                <td>{s.iso3}</td>
                <td className="num">
                  {s.latest ? formatValue(indicatorFormat(code), s.latest.value) : "—"}
                </td>
                <td>
                  {s.latest
                    ? `${periodKey(s.first!).slice(0, 7)} → ${periodKey(s.latest).slice(0, 7)}`
                    : "—"}
                </td>
                <td className="num">{s.count}</td>
                <td>{s.count === 0 ? <span className="badge badge-warn">none</span> : "ok"}</td>
                <td>{s.sources.join(", ") || "—"}</td>
                <td>
                  <AddToWorkspace typeId="indicator-chart"
                                  config={{ countries: [s.iso3], indicator: code }}
                                  label="＋" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="glass" style={{ padding: "var(--space-3)" }}>
        <div style={{ display: "flex", gap: 8 }}>
          <button type="button" className="glass-button" onClick={exportCsv}>Export CSV</button>
          <button type="button" className="glass-button"
                  onClick={() => downloadText(
                    `${code}_${iso3s.join("-")}.json`,
                    JSON.stringify({ indicator: code, countries: state.data }, null, 1),
                    "application/json")}>Export JSON</button>
          <AddToWorkspace typeId="indicator-chart"
                          config={{ countries: iso3s, indicator: code }} />
        </div>
        {unitSet.size > 1 && (
          <p className="section-note" role="alert">
            Different units across countries ({[...unitSet].join(", ")}) —
            values are not directly comparable.
          </p>
        )}
        {sourceSet.size > 1 && (
          <p className="section-note">
            Sources differ across countries ({[...sourceSet].join(", ")} —
            check provider definitions before comparing levels.
          </p>
        )}
      </div>
    </div>
  );
}

/* ---------- panel ---------- */

export function ComparePanel() {
  const countries = ready(useLiveCountries());
  const indicators = ready(useIndicators());
  const all = countries?.map((c) => c.iso3) ?? [];
  const [selected, setSelected] = useState<string[]>(["USA", "CHN"]);
  const [mode, setMode] = useState<"forces" | "indicators">("forces");
  const [code, setCode] = useState("GDP_GROWTH");
  const [startYear, setStartYear] = useState("");

  const toggle = (c: string) =>
    setSelected((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c],
    );

  const iso3s = selected.filter((c) => all.includes(c));

  return (
    <div className="section-stack">
      <div className="glass compare-controls" style={{ flexWrap: "wrap" }}>
        <div role="group" aria-label="Countries" style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {all.map((c) => (
            <button
              key={c}
              type="button"
              className={`glass-button${selected.includes(c) ? " btn-active" : ""}`}
              aria-pressed={selected.includes(c)}
              onClick={() => toggle(c)}
            >
              {c}
            </button>
          ))}
        </div>
        <div role="group" aria-label="Comparison mode">
          <button type="button" className={`glass-button${mode === "forces" ? " btn-active" : ""}`}
                  onClick={() => setMode("forces")}>Forces</button>
          <button type="button" className={`glass-button${mode === "indicators" ? " btn-active" : ""}`}
                  onClick={() => setMode("indicators")}>Indicators</button>
        </div>
        {mode === "indicators" && (
          <>
            <select className="config-select" value={code}
                    onChange={(e) => setCode(e.target.value)} aria-label="Indicator">
              {(indicators ?? []).map((i) => (
                <option key={i.code} value={i.code}>{i.code}</option>
              ))}
            </select>
            <input className="config-select" placeholder="From year" value={startYear}
                   onChange={(e) => setStartYear(e.target.value)}
                   aria-label="From year" style={{ maxWidth: 90 }} />
          </>
        )}
      </div>
      {mode === "forces" ? (
        <ForcesCompare iso3s={iso3s} />
      ) : (
        <IndicatorCompare iso3s={iso3s} code={code} startYear={startYear} />
      )}
    </div>
  );
}
