import { useState } from "react";
import * as echarts from "echarts";
import { fetchStrategies, postSimulate } from "@/lib/api/client";
import type {
  SimulateRequest,
  SimulateResponse,
  StrategiesResponse,
} from "@/types/strategy";
import { useAsyncState } from "@/features/widgets/hooks";
import { resolveAsync } from "@/features/widgets/common";
import { EChart, baseChartOption } from "@/lib/charts/EChart";
import { formatPercent } from "@/lib/format";

const CURRENCIES = ["CHF", "USD", "EUR", "GBP"];
const REBALANCES = ["annual", "quarterly", "monthly", "none"];

/** §37 preset scenarios — one click, honest defaults. */
const PRESETS: { label: string; patch: Partial<SimulateRequest> }[] = [
  {
    label: "US equity 2000–today",
    patch: {
      strategy: "buy_and_hold_us_equity",
      start: "2000-01-01",
      end: new Date().toISOString().slice(0, 10),
    },
  },
  {
    label: "Global equities, annual rebalance",
    patch: {
      strategy: "custom",
      kind: "equal_weight",
      instruments: [
        "USA_EQUITY_PRICE_INDEX", "DEU_EQUITY_PRICE_INDEX",
        "GBR_EQUITY_PRICE_INDEX", "JPN_EQUITY_PRICE_INDEX",
        "CHE_EQUITY_PRICE_INDEX", "CHN_EQUITY_PRICE_INDEX",
        "IND_EQUITY_PRICE_INDEX", "BRA_EQUITY_PRICE_INDEX",
      ],
      rebalance: "annual",
      start: "2000-01-01",
      end: new Date().toISOString().slice(0, 10),
      benchmark: true,
    },
  },
  {
    label: "Zero-cost sensitivity",
    patch: { cost_bps: 0, slippage_bps: 0 },
  },
];

function equityChart(
  path: { date: string; value: number }[],
  name: string,
): echarts.EChartsOption {
  return {
    ...baseChartOption(),
    xAxis: { type: "time" },
    yAxis: { type: "value", scale: true },
    series: [
      {
        type: "line", name, showSymbol: false,
        data: path.map((p) => [p.date, p.value]),
        areaStyle: { opacity: 0.08 },
      },
    ],
    tooltip: { trigger: "axis" },
  };
}

function ResultPanel({ result }: { result: SimulateResponse }) {
  if (!result.available) {
    return (
      <p className="body-sm">
        <span className="badge badge-warn">unavailable</span>{" "}
        {result.unavailable_reason}
      </p>
    );
  }
  const pct = (v: number | null | undefined) =>
    v == null ? "—" : formatPercent(v * 100);
  return (
    <>
      <p className="body-sm">
        <span className="badge badge-info">{result.category}</span>{" "}
        <span className={`badge badge-${result.backtest_safe ? "ok" : "warn"}`}>
          backtest_safe={String(result.backtest_safe)}
        </span>{" "}
        <span className="text-tertiary">
          {result.strategy_id} · {result.model_version} ·{" "}
          {result.date_range?.join(" → ")}
        </span>
      </p>
      <div className="metric-grid">
        {(
          [
            ["Final value", result.final_value != null
              ? result.final_value.toLocaleString(undefined, {
                  maximumFractionDigits: 0,
                }) + " " + result.base_currency
              : "—"],
            ["Cumulative", pct(result.cumulative_return)],
            ["Annualised", pct(result.annualised_return)],
            ["Volatility", pct(result.volatility)],
            ["Max drawdown", pct(result.max_drawdown)],
            ["Trades", String(result.n_trades ?? 0)],
          ] as const
        ).map(([label, v]) => (
          <div key={label} className="metric-card glass-subtle">
            <p className="label-md text-tertiary">{label}</p>
            <p className="metric-value">{v}</p>
          </div>
        ))}
      </div>
      {result.benchmark && (
        <p className="body-sm">
          Benchmark {result.benchmark.strategy_id}: cumulative{" "}
          {pct(result.benchmark.cumulative_return)} · final{" "}
          {result.benchmark.final_value?.toLocaleString(undefined, {
            maximumFractionDigits: 0,
          }) ?? "—"}
        </p>
      )}
      {result.path && result.path.length > 1 && (
        <div className="chart-card" style={{ minHeight: "16rem" }}>
          <EChart
            option={equityChart(result.path, "portfolio value")}
            ariaLabel="Simulated portfolio value"
          />
        </div>
      )}
      <p className="body-sm">
        Turnover {result.turnover?.toFixed(2) ?? "—"} · costs{" "}
        {result.transaction_costs?.toFixed(0) ?? "—"}{" "}
        {result.base_currency}.{" "}
        {String(result.execution_assumptions?.timing ?? "")}
      </p>
      {result.missing_valuations && result.missing_valuations.length > 0 && (
        <p className="body-sm">
          <span className="badge badge-warn">missing valuations</span>{" "}
          {result.missing_valuations.slice(0, 10).join(", ")}
          {result.missing_valuations.length > 10 && " …"}
        </p>
      )}
      {result.warnings?.map((w) => (
        <p key={w} className="body-sm text-tertiary">· {w}</p>
      ))}
      {result.trades && result.trades.length > 0 && (
        <details>
          <summary className="body-sm">
            {result.trades.length} trades
          </summary>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th><th>Code</th><th>Side</th>
                  <th className="num">Qty</th><th className="num">Price</th>
                  <th className="num">Value</th><th className="num">Cost</th>
                </tr>
              </thead>
              <tbody>
                {result.trades.slice(0, 100).map((t, i) => (
                  <tr key={i}>
                    <td className="tabular-nums">{t.date}</td>
                    <td><code>{t.code}</code></td>
                    <td>{t.side}</td>
                    <td className="num tabular-nums">{t.qty.toFixed(2)}</td>
                    <td className="num tabular-nums">{t.price.toFixed(2)}</td>
                    <td className="num tabular-nums">{t.value.toFixed(0)}</td>
                    <td className="num tabular-nums">{t.cost.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </>
  );
}

/** Mission 5 §40 — strategy lab: benchmark definitions + bounded
 *  simulations rendered only from backend-calculated results. */
export function StrategyLab() {
  const strategies = useAsyncState<StrategiesResponse>(
    (s) => fetchStrategies({ signal: s }),
    [],
  );

  const [form, setForm] = useState<SimulateRequest>({
    strategy: "buy_and_hold_us_equity",
    start: "2000-01-01",
    end: new Date().toISOString().slice(0, 10),
    initial_capital: 100_000,
    base_currency: "CHF",
    rebalance: "annual",
    cost_bps: 10,
    slippage_bps: 5,
    benchmark: false,
  });
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const patch = (p: Partial<SimulateRequest>) =>
    setForm((f) => ({ ...f, ...p }));

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await postSimulate(form));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="glass">
        <h2 className="headline-sm panel-title">Benchmark strategies</h2>
        {resolveAsync(strategies, (s) => (
          <>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Strategy</th><th>Category</th><th>Rebalance</th>
                    <th>Allocations</th>
                  </tr>
                </thead>
                <tbody>
                  {s.benchmarks.map((b) => (
                    <tr key={b.strategy_id}>
                      <td>
                        <code>{b.strategy_id}</code>
                        <div className="body-sm text-tertiary">
                          {b.description}
                        </div>
                      </td>
                      <td>
                        <span className="badge badge-info">{b.category}</span>
                      </td>
                      <td>{b.rebalance}</td>
                      <td className="body-sm">
                        {Object.entries(b.allocations)
                          .map(([k, w]) => `${k} ${(w * 100).toFixed(0)}%`)
                          .join(" · ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="body-sm text-tertiary">{s.note}</p>
          </>
        ))}
      </div>

      <div className="glass">
        <h2 className="headline-sm panel-title">Simulate</h2>
        <p className="body-sm">
          Monthly-grid, long-only, unleveraged simulation. Rebalance
          decisions execute at the first price <em>after</em> the schedule
          date — the engine never trades on the same observation it used
          to decide.
        </p>
        <div className="research-controls glass-subtle">
          <label>
            Preset{" "}
            <select
              className="config-select" value=""
              onChange={(e) => {
                const p = PRESETS[Number(e.target.value)];
                if (p) patch(p.patch);
              }}
            >
              <option value="">choose…</option>
              {PRESETS.map((p, i) => (
                <option key={p.label} value={i}>{p.label}</option>
              ))}
            </select>
          </label>
          <label>
            Strategy{" "}
            <select
              className="config-select" value={form.strategy}
              onChange={(e) => {
                const v = e.target.value;
                if (v === "custom") {
                  patch({
                    strategy: "custom",
                    kind: "equal_weight",
                    instruments: [
                      "USA_EQUITY_PRICE_INDEX",
                      "DEU_EQUITY_PRICE_INDEX",
                      "GBR_EQUITY_PRICE_INDEX",
                      "JPN_EQUITY_PRICE_INDEX",
                      "CHE_EQUITY_PRICE_INDEX",
                      "CHN_EQUITY_PRICE_INDEX",
                      "IND_EQUITY_PRICE_INDEX",
                      "BRA_EQUITY_PRICE_INDEX",
                    ],
                  });
                } else {
                  setForm((f) => {
                    const { kind, instruments, allocations, ...rest } = f;
                    return { ...rest, strategy: v };
                  });
                }
              }}
            >
              {(strategies.kind === "ready"
                ? strategies.data.benchmarks.map((b) => b.strategy_id)
                : [form.strategy]
              ).map((id) => <option key={id}>{id}</option>)}
              <option value="custom">custom — equal-weight 8 equities</option>
            </select>
          </label>
          <label>
            Start{" "}
            <input className="config-select" type="date" value={form.start}
                   onChange={(e) => patch({ start: e.target.value })} />
          </label>
          <label>
            End{" "}
            <input className="config-select" type="date" value={form.end}
                   onChange={(e) => patch({ end: e.target.value })} />
          </label>
          <label>
            Capital{" "}
            <input
              className="config-select" type="number" min={1}
              value={form.initial_capital}
              onChange={(e) =>
                patch({ initial_capital: Number(e.target.value) })}
            />
          </label>
          <label>
            Currency{" "}
            <select
              className="config-select" value={form.base_currency}
              onChange={(e) => patch({ base_currency: e.target.value })}
            >
              {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <label>
            Cost bps{" "}
            <input
              className="config-select" type="number" min={0} max={1000}
              value={form.cost_bps}
              onChange={(e) => patch({ cost_bps: Number(e.target.value) })}
            />
          </label>
          <label>
            Slippage bps{" "}
            <input
              className="config-select" type="number" min={0} max={1000}
              value={form.slippage_bps}
              onChange={(e) =>
                patch({ slippage_bps: Number(e.target.value) })}
            />
          </label>
          <label>
            Rebalance{" "}
            <select
              className="config-select" value={form.rebalance}
              onChange={(e) => patch({ rebalance: e.target.value })}
            >
              {REBALANCES.map((r) => <option key={r}>{r}</option>)}
            </select>
          </label>
          <label className="config-check">
            <input
              type="checkbox" checked={form.benchmark}
              onChange={(e) => patch({ benchmark: e.target.checked })}
            />
            vs buy &amp; hold US equity
          </label>
          <button className="glass-button" onClick={run} disabled={busy}>
            {busy ? "Simulating…" : "Run simulation"}
          </button>
        </div>
        {error && <p className="body-sm">Simulation failed: {error}</p>}
        {result && <ResultPanel result={result} />}
      </div>
    </>
  );
}
