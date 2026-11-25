import { useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import {
  fetchCorrelations,
  fetchFxConvert,
  fetchInstrumentHistory,
  fetchInstrumentReturns,
  fetchMarketCoverage,
  fetchMarketInstruments,
  fetchRegimeAssetReturns,
  fetchRegimeHistory,
  fetchRegimeModel,
} from "@/lib/api/client";
import type {
  CorrelationResponse,
  FxConvertResponse,
  InstrumentHistoryResponse,
  InstrumentReturnsResponse,
  MarketCoverageResponse,
  MarketInstrument,
  RegimeAssetReturnsResponse,
  RegimeHistoryResponse,
} from "@/types/market";
import { useAsyncState, useCountryList } from "@/features/widgets/hooks";
import { resolveAsync, WidgetError, WidgetLoading } from "@/features/widgets/common";
import { EChart, baseChartOption } from "@/lib/charts/EChart";
import { formatPercent } from "@/lib/format";

const ASSET_CLASSES = [
  "all",
  "equity_index",
  "gov_bond_yield",
  "policy_rate",
  "cash_rate",
  "corporate_bond_yield",
  "fx_rate",
  "commodity_index",
] as const;

const REGIME_BADGE: Record<string, string> = {
  REFLATION: "badge-info",
  GOLDILOCKS: "badge-ok",
  STAGFLATION: "badge-err",
  DISINFLATION_SLOWDOWN: "badge-warn",
  UNCLASSIFIED: "",
};

function lineChart(
  points: { date: string; value: number }[],
  name: string,
): EChartsOption {
  return {
    ...baseChartOption(),
    xAxis: {
      type: "time",
      axisLabel: { color: "inherit" },
    },
    yAxis: { type: "value", scale: true },
    series: [
      {
        type: "line",
        name,
        showSymbol: false,
        data: points.map((p) => [p.date, p.value]),
      },
    ],
    tooltip: { trigger: "axis" },
  };
}

function InstrumentDetail({ code }: { code: string }) {
  const history = useAsyncState<InstrumentHistoryResponse>(
    (s) => fetchInstrumentHistory(code, {}, { signal: s }),
    [code],
  );
  const returns = useAsyncState<InstrumentReturnsResponse>(
    (s) => fetchInstrumentReturns(code, {}, { signal: s }),
    [code],
  );

  if (history.kind === "loading" || returns.kind === "loading") {
    return <WidgetLoading />;
  }
  if (history.kind === "error") return <WidgetError />;

  const inst = history.data.instrument;
  const stats = returns.kind === "ready" ? returns.data.statistics : null;
  // Price-like series chart cumulative growth; yields/rates chart levels.
  const chartPoints =
    inst.return_methodology === "price_index" ||
    inst.return_methodology === "spot_price"
      ? history.data.observations
      : history.data.observations;

  return (
    <>
      <p className="body-sm">
        <strong>{inst.name}</strong>{" "}
        <span className="badge badge-info">{inst.asset_class}</span>{" "}
        <span className="badge">{inst.return_methodology}</span>{" "}
        <span className="text-tertiary">
          {inst.currency} · {inst.frequency} · {inst.external_code}
        </span>
      </p>
      {inst.notes && <p className="body-sm text-tertiary">{inst.notes}</p>}
      <div className="chart-card" style={{ minHeight: "16rem" }}>
        <EChart
          option={lineChart(chartPoints, inst.unit)}
          ariaLabel={`${inst.name} history`}
        />
      </div>
      {stats &&
        (inst.return_methodology === "price_index" ||
          inst.return_methodology === "spot_price" ? (
          <div className="metric-grid">
            {(
              [
                ["Cumulative", stats.cumulative_return],
                ["Annualised", stats.annualised_return],
                ["Volatility", stats.volatility],
                ["Max drawdown", stats.max_drawdown],
              ] as const
            ).map(([label, v]) => (
              <div key={label} className="metric-card glass-subtle">
                <p className="label-md text-tertiary">{label}</p>
                <p className="metric-value">
                  {v == null ? "—" : formatPercent(v * 100)}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="body-sm text-tertiary">
            Level series — return-style statistics are not meaningful for a{" "}
            {inst.return_methodology} and are intentionally not displayed.
          </p>
        ))}
      {returns.kind === "ready" && (
        <p className="body-sm text-tertiary">{returns.data.warning}</p>
      )}
    </>
  );
}

function CorrelationPanel({ instruments }: { instruments: MarketInstrument[] }) {
  const equities = instruments.filter((i) => i.asset_class === "equity_index");
  const [selected, setSelected] = useState<string[]>(
    equities.slice(0, 4).map((i) => i.code),
  );
  const corr = useAsyncState<CorrelationResponse>(
    (s) =>
      selected.length >= 2
        ? fetchCorrelations(selected, {}, { signal: s })
        : Promise.resolve({ methodology: "", pairs: {} }),
    [selected.join(",")],
  );

  return (
    <div className="glass">
      <h2 className="headline-sm panel-title">Return correlations</h2>
      <p className="body-sm">
        Pairwise correlations on shared observation dates only.
      </p>
      <div className="config-check-list" style={{ padding: "0 var(--space-4)" }}>
        {equities.map((i) => (
          <label key={i.code} className="config-check">
            <input
              type="checkbox"
              checked={selected.includes(i.code)}
              onChange={(e) =>
                setSelected((prev) =>
                  e.target.checked
                    ? [...prev, i.code].slice(-12)
                    : prev.filter((c) => c !== i.code),
                )
              }
            />
            {i.code}
          </label>
        ))}
      </div>
      {selected.length < 2 ? (
        <p className="body-sm">Select at least two instruments.</p>
      ) : (
        resolveAsync(corr, (c) => {
          const codes = [...selected].sort();
          const pair = (a: string, b: string) =>
            c.pairs[`${a}|${b}`] ?? c.pairs[`${b}|${a}`];
          return (
            <>
              <p className="body-sm text-tertiary">{c.methodology}</p>
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th />
                      {codes.map((code) => (
                        <th key={code} className="num">{code}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {codes.map((row) => (
                      <tr key={row}>
                        <th>{row}</th>
                        {codes.map((col) => (
                          <td key={col} className="num tabular-nums">
                            {row === col
                              ? "1.00"
                              : pair(row, col)?.correlation == null
                                ? "—"
                                : pair(row, col)!.correlation!.toFixed(2)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          );
        })
      )}
    </div>
  );
}

function FxPanel() {
  const [amount, setAmount] = useState("1000");
  const [from, setFrom] = useState("EUR");
  const [to, setTo] = useState("CHF");
  const [asOf, setAsOf] = useState("");
  const result = useAsyncState<FxConvertResponse>(
    (s) =>
      fetchFxConvert(
        Number(amount) || 0, from, to, asOf || undefined, { signal: s },
      ),
    [amount, from, to, asOf],
  );
  return (
    <div className="glass">
      <h2 className="headline-sm panel-title">FX conversion</h2>
      <p className="body-sm">
        As-of conversion through stored USD legs — never uses a rate from
        after the requested date.
      </p>
      <div className="research-controls glass-subtle">
        <label>
          Amount{" "}
          <input
            className="config-select" value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </label>
        <label>
          From{" "}
          <select className="config-select" value={from}
                  onChange={(e) => setFrom(e.target.value)}>
            {["USD", "EUR", "GBP", "CHF", "JPY", "CNY", "INR", "BRL"].map(
              (c) => <option key={c}>{c}</option>,
            )}
          </select>
        </label>
        <label>
          To{" "}
          <select className="config-select" value={to}
                  onChange={(e) => setTo(e.target.value)}>
            {["CHF", "USD", "EUR", "GBP", "JPY", "CNY", "INR", "BRL"].map(
              (c) => <option key={c}>{c}</option>,
            )}
          </select>
        </label>
        <label>
          As of{" "}
          <input className="config-select" type="date" value={asOf}
                 onChange={(e) => setAsOf(e.target.value)} />
        </label>
      </div>
      {resolveAsync(result, (r) =>
        r.value == null ? (
          <p className="body-sm">Unavailable: {r.reason ?? "no stored rate"}</p>
        ) : (
          <p className="body-sm">
            <strong className="tabular-nums">
              {amount} {r.from} ={" "}
              {r.value.toLocaleString(undefined, {
                maximumFractionDigits: 2,
              })}{" "}
              {r.to}
            </strong>{" "}
            as of {r.as_of}
            {r.fx_used.length > 0 && (
              <span className="text-tertiary">
                {" "}
                via{" "}
                {r.fx_used
                  .map((f) => `${f.instrument} @ ${f.rate} (${f.rate_date})`)
                  .join(" + ")}
              </span>
            )}
          </p>
        ),
      )}
    </div>
  );
}

function RegimePanel() {
  const countries = useCountryList();
  const [iso3, setIso3] = useState("USA");
  const model = useAsyncState((s) => fetchRegimeModel({ signal: s }), []);
  const history = useAsyncState<RegimeHistoryResponse>(
    (s) => fetchRegimeHistory(iso3, { signal: s }),
    [iso3],
  );
  const assetReturns = useAsyncState<RegimeAssetReturnsResponse>(
    (s) => fetchRegimeAssetReturns(iso3, { signal: s }),
    [iso3],
  );

  return (
    <div className="glass">
      <h2 className="headline-sm panel-title">Market regimes</h2>
      {model.kind === "ready" && (
        <p className="body-sm">
          <span className="badge badge-info">
            {model.data.methodology_status}
          </span>{" "}
          {model.data.framework} — {model.data.disclaimer}
        </p>
      )}
      <div className="research-controls glass-subtle">
        <label>
          Country{" "}
          <select
            className="config-select" value={iso3}
            onChange={(e) => setIso3(e.target.value)}
          >
            {countries.map((c) => (
              <option key={c.iso3} value={c.iso3}>
                {c.iso3} — {c.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {resolveAsync(history, (h) => (
        <>
          <p className="body-sm">
            {h.coverage["classified"]} of {h.regimes.length} years classified
            · {h.execution_mode} · backtest_safe={String(h.backtest_safe)}
          </p>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Year</th><th>Regime</th><th>Growth</th>
                  <th>Inflation</th><th className="num">GDP %</th>
                  <th className="num">CPI %</th>
                </tr>
              </thead>
              <tbody>
                {h.regimes.map((r) => (
                  <tr key={r.year}>
                    <td className="tabular-nums">{r.year}</td>
                    <td>
                      <span className={`badge ${REGIME_BADGE[r.regime] ?? ""}`}>
                        {r.regime}
                      </span>
                    </td>
                    <td>{r.growth_direction}</td>
                    <td>{r.inflation_direction}</td>
                    <td className="num tabular-nums">
                      {r.gdp_growth?.toFixed(1) ?? "—"}
                    </td>
                    <td className="num tabular-nums">
                      {r.inflation_cpi?.toFixed(1) ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {h.limitations.map((l) => (
            <p key={l} className="body-sm text-tertiary">· {l}</p>
          ))}
        </>
      ))}
      {resolveAsync(assetReturns, (a) =>
        Object.keys(a.by_regime).length === 0 ? null : (
          <>
            <h3 className="headline-sm panel-title">
              Equity returns by regime ({a.instrument})
            </h3>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Regime</th><th className="num">Episodes</th>
                    <th className="num">Mean</th><th className="num">Min</th>
                    <th className="num">Max</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(a.by_regime).map(([regime, v]) => (
                    <tr key={regime}>
                      <td>{regime}</td>
                      <td className="num tabular-nums">{v.episodes}</td>
                      <td className="num tabular-nums">
                        {formatPercent(v.mean_annual_return * 100)}
                      </td>
                      <td className="num tabular-nums">
                        {formatPercent(v.min * 100)}
                      </td>
                      <td className="num tabular-nums">
                        {formatPercent(v.max * 100)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="body-sm text-tertiary">{a.warning}</p>
          </>
        ),
      )}
    </div>
  );
}

/** Mission 5 §38-§39 — markets explorer: instruments, history, returns,
 * correlations, FX and experimental regime view. */
export function MarketsExplorer() {
  const [assetClass, setAssetClass] = useState<string>("all");
  const [selected, setSelected] = useState<string | null>(null);

  const instruments = useAsyncState(
    (s) => fetchMarketInstruments({ signal: s }),
    [],
  );
  const coverage = useAsyncState<MarketCoverageResponse>(
    (s) => fetchMarketCoverage({ signal: s }),
    [],
  );

  const filtered = useMemo(() => {
    if (instruments.kind !== "ready") return [];
    return instruments.data.instruments.filter(
      (i) => assetClass === "all" || i.asset_class === assetClass,
    );
  }, [instruments, assetClass]);

  const coverageByCode = useMemo(() => {
    const map: Record<string, MarketCoverageResponse["instruments"][0]> = {};
    if (coverage.kind === "ready") {
      for (const c of coverage.data.instruments) map[c.code] = c;
    }
    return map;
  }, [coverage]);

  const active =
    selected ??
    filtered.find((i) => i.asset_class === "equity_index")?.code ??
    filtered[0]?.code ??
    null;

  return (
    <>
      <div className="glass">
        <h2 className="headline-sm panel-title">Instruments</h2>
        <div className="research-controls glass-subtle">
          <label>
            Asset class{" "}
            <select
              className="config-select" value={assetClass}
              onChange={(e) => setAssetClass(e.target.value)}
            >
              {ASSET_CLASSES.map((a) => <option key={a}>{a}</option>)}
            </select>
          </label>
          {instruments.kind === "ready" && (
            <span className="body-sm text-tertiary">
              {filtered.length} instruments
            </span>
          )}
        </div>
        {resolveAsync(instruments, () => (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Code</th><th>Name</th><th>Class</th><th>Ccy</th>
                  <th>Methodology</th>
                  <th className="num">Obs</th><th>Range</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((i) => {
                  const cov = coverageByCode[i.code];
                  return (
                    <tr
                      key={i.code}
                      onClick={() => setSelected(i.code)}
                      style={{
                        cursor: "pointer",
                        background:
                          active === i.code
                            ? "var(--accent-soft)"
                            : undefined,
                      }}
                    >
                      <td><code>{i.code}</code></td>
                      <td>{i.name}</td>
                      <td>{i.asset_class}</td>
                      <td>{i.currency}</td>
                      <td>{i.return_methodology}</td>
                      <td className="num tabular-nums">
                        {cov?.observations ?? "—"}
                      </td>
                      <td className="tabular-nums">
                        {cov?.earliest?.slice(0, 4) ?? "—"}–
                        {cov?.latest?.slice(0, 4) ?? "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ))}
      </div>

      {active && (
        <div className="glass">
          <h2 className="headline-sm panel-title">{active}</h2>
          <InstrumentDetail code={active} />
        </div>
      )}

      {instruments.kind === "ready" && (
        <CorrelationPanel instruments={instruments.data.instruments} />
      )}
      <FxPanel />
      <RegimePanel />
    </>
  );
}
