import { useState } from "react";
import {
  createPortfolio,
  fetchMarketInstruments,
  fetchPortfolios,
  fetchPortfolioTransactions,
  fetchPortfolioValuation,
  postTransaction,
} from "@/lib/api/client";
import type {
  PaperPortfolioSummary,
  PaperTransaction,
  PortfolioValuation,
} from "@/types/strategy";
import { useAsyncState } from "@/features/widgets/hooks";
import { resolveAsync } from "@/features/widgets/common";
import { formatPercent } from "@/lib/format";

const CCY = ["CHF", "USD", "EUR", "GBP"];

function newIdemKey() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `tx-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function TxnForm({ pid, onPosted }: { pid: number; onPosted: () => void }) {
  const instruments = useAsyncState(
    (s) => fetchMarketInstruments({ signal: s }),
    [],
  );
  const [kind, setKind] = useState<"buy" | "sell" | "deposit">("buy");
  const [code, setCode] = useState("US_SP500");
  const [qty, setQty] = useState("1");
  const [price, setPrice] = useState("");
  const [fee, setFee] = useState("0");
  const [userPrice, setUserPrice] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const r = await postTransaction(pid, {
        kind,
        ...(kind !== "deposit" ? { instrument_code: code } : {}),
        quantity: Number(qty) || 1,
        ...(price ? { price: Number(price) } : {}),
        fee: Number(fee) || 0,
        idempotency_key: newIdemKey(),
        user_entered_price: userPrice,
      });
      setMsg(r.created ? `Recorded ${r.kind} #${r.id}` : "Duplicate — already recorded");
      onPosted();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const investable =
    instruments.kind === "ready"
      ? instruments.data.instruments.filter(
          (i) => i.return_methodology === "price_index" ||
                 i.return_methodology === "spot_price",
        )
      : [];

  return (
    <div className="research-controls glass-subtle">
      <label>
        Kind{" "}
        <select
          className="config-select" value={kind}
          onChange={(e) => setKind(e.target.value as typeof kind)}
        >
          <option value="buy">buy</option>
          <option value="sell">sell</option>
          <option value="deposit">deposit</option>
        </select>
      </label>
      {kind !== "deposit" && (
        <label>
          Instrument{" "}
          <select
            className="config-select" value={code}
            onChange={(e) => setCode(e.target.value)}
          >
            {investable.map((i) => (
              <option key={i.code} value={i.code}>{i.code}</option>
            ))}
          </select>
        </label>
      )}
      <label>
        Qty{" "}
        <input className="config-select" type="number" min={0}
               value={qty} onChange={(e) => setQty(e.target.value)} />
      </label>
      <label>
        Price{" "}
        <input
          className="config-select" type="number" min={0} value={price}
          placeholder="latest stored"
          onChange={(e) => {
            setPrice(e.target.value);
            if (e.target.value) setUserPrice(true);
          }}
        />
      </label>
      <label>
        Fee{" "}
        <input className="config-select" type="number" min={0}
               value={fee} onChange={(e) => setFee(e.target.value)} />
      </label>
      {price && (
        <label className="config-check">
          <input
            type="checkbox" checked={userPrice}
            onChange={(e) => setUserPrice(e.target.checked)}
          />
          user-entered price (simulation)
        </label>
      )}
      <button className="glass-button" onClick={submit} disabled={busy}>
        {busy ? "Posting…" : "Post transaction"}
      </button>
      {msg && <span className="body-sm">{msg}</span>}
    </div>
  );
}

function PortfolioDetail({ pid }: { pid: number }) {
  const [tick, setTick] = useState(0);
  const valuation = useAsyncState<PortfolioValuation>(
    (s) => fetchPortfolioValuation(pid, { signal: s }),
    [pid, tick],
  );
  const txns = useAsyncState<{ transactions: PaperTransaction[] }>(
    (s) => fetchPortfolioTransactions(pid, { signal: s }),
    [pid, tick],
  );

  return (
    <>
      {resolveAsync(valuation, (v) => (
        <>
          <div className="metric-grid">
            {(
              [
                ["Total value", v.total_value.toLocaleString(undefined, {
                  maximumFractionDigits: 0,
                }) + " " + v.base_currency],
                ["Cash", v.cash.toLocaleString(undefined, {
                  maximumFractionDigits: 0,
                })],
                ["Market value", v.market_value.toLocaleString(undefined, {
                  maximumFractionDigits: 0,
                })],
                ["Total return", v.total_return == null
                  ? "—" : formatPercent(v.total_return * 100)],
                ["Realised", v.realised_result.toLocaleString(undefined, {
                  maximumFractionDigits: 0,
                })],
                ["Unrealised", v.unrealised_result.toLocaleString(undefined, {
                  maximumFractionDigits: 0,
                })],
              ] as const
            ).map(([label, val]) => (
              <div key={label} className="metric-card glass-subtle">
                <p className="label-md text-tertiary">{label}</p>
                <p className="metric-value">{val}</p>
              </div>
            ))}
          </div>
          <p className="body-sm text-tertiary">
            {v.cost_basis_method} · {v.calc_version} ·{" "}
            {v.n_transactions} transactions
          </p>
          {v.missing_prices.length > 0 && (
            <p className="body-sm">
              <span className="badge badge-warn">no stored price</span>{" "}
              {v.missing_prices.join(", ")} — positions held at cost
            </p>
          )}
          {v.holdings.length > 0 && (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Instrument</th><th>Class</th>
                    <th className="num">Qty</th>
                    <th className="num">Cost basis</th>
                    <th className="num">Price ({v.base_currency})</th>
                    <th className="num">Market value</th>
                  </tr>
                </thead>
                <tbody>
                  {v.holdings.map((h) => (
                    <tr key={h.instrument}>
                      <td><code>{h.instrument}</code></td>
                      <td>{h.asset_class}</td>
                      <td className="num tabular-nums">
                        {h.quantity.toFixed(2)}
                      </td>
                      <td className="num tabular-nums">
                        {h.cost_basis_base.toFixed(0)}
                      </td>
                      <td className="num tabular-nums">
                        {h.price_base?.toFixed(2) ?? "—"}
                        {h.price_date && (
                          <span className="text-tertiary">
                            {" "}({h.price_date})
                          </span>
                        )}
                      </td>
                      <td className="num tabular-nums">
                        {h.market_value_base?.toFixed(0) ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ))}

      <h3 className="headline-sm panel-title">Post transaction</h3>
      <TxnForm pid={pid} onPosted={() => setTick((t) => t + 1)} />

      {resolveAsync(txns, (t) =>
        t.transactions.length === 0 ? null : (
          <details>
            <summary className="body-sm">
              {t.transactions.length} transactions
            </summary>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th><th>Kind</th><th className="num">Qty</th>
                    <th className="num">Price</th><th>Ccy</th>
                    <th className="num">Base value</th>
                    <th className="num">Fee</th><th>Price src</th>
                    <th>Executed</th>
                  </tr>
                </thead>
                <tbody>
                  {t.transactions.map((x) => (
                    <tr key={x.id}>
                      <td className="tabular-nums">{x.id}</td>
                      <td>{x.kind}</td>
                      <td className="num tabular-nums">
                        {x.quantity.toFixed(2)}
                      </td>
                      <td className="num tabular-nums">
                        {x.price.toFixed(2)}
                      </td>
                      <td>{x.currency}</td>
                      <td className="num tabular-nums">
                        {x.base_value.toFixed(0)}
                      </td>
                      <td className="num tabular-nums">
                        {x.fee.toFixed(2)}
                      </td>
                      <td>
                        {x.user_entered_price
                          ? <span className="badge badge-warn">manual</span>
                          : <span className="badge">stored</span>}
                      </td>
                      <td className="tabular-nums">
                        {x.executed_at.slice(0, 10)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        ),
      )}
    </>
  );
}

/** Mission 5 §42 — paper portfolio panel. SIMULATION ONLY: the banner
 *  is part of the contract, not decoration. */
export function PortfolioPanel() {
  const [tick, setTick] = useState(0);
  const portfolios = useAsyncState<{ portfolios: PaperPortfolioSummary[] }>(
    (s) => fetchPortfolios({ signal: s }),
    [tick],
  );
  const [selected, setSelected] = useState<number | null>(null);
  const [name, setName] = useState("Paper portfolio");
  const [ccy, setCcy] = useState("CHF");
  const [capital, setCapital] = useState("100000");
  const [msg, setMsg] = useState<string | null>(null);

  const create = async () => {
    setMsg(null);
    try {
      const p = await createPortfolio(name, ccy, Number(capital) || 0);
      setSelected(p.id);
      setTick((t) => t + 1);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    }
  };

  const active =
    selected ??
    (portfolios.kind === "ready"
      ? portfolios.data.portfolios[0]?.id ?? null
      : null);

  return (
    <>
      <div className="glass">
        <h2 className="headline-sm panel-title">Paper portfolios</h2>
        <p className="body-sm">
          <span className="badge badge-warn">simulation only</span>{" "}
          Deterministic ledger over stored prices — no real money, no
          brokerage connection, no order routing.
        </p>
        {resolveAsync(portfolios, (p) => (
          <>
            {p.portfolios.length > 0 && (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>#</th><th>Name</th><th>Ccy</th>
                      <th className="num">Starting capital</th><th />
                    </tr>
                  </thead>
                  <tbody>
                    {p.portfolios.map((pp) => (
                      <tr
                        key={pp.id}
                        onClick={() => setSelected(pp.id)}
                        style={{
                          cursor: "pointer",
                          background:
                            active === pp.id
                              ? "var(--accent-soft)"
                              : undefined,
                        }}
                      >
                        <td className="tabular-nums">{pp.id}</td>
                        <td>{pp.name}</td>
                        <td>{pp.base_currency}</td>
                        <td className="num tabular-nums">
                          {pp.starting_capital.toLocaleString()}
                        </td>
                        <td>{pp.archived ? "archived" : ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="research-controls glass-subtle">
              <label>
                Name{" "}
                <input className="config-select" value={name}
                       onChange={(e) => setName(e.target.value)} />
              </label>
              <label>
                Currency{" "}
                <select className="config-select" value={ccy}
                        onChange={(e) => setCcy(e.target.value)}>
                  {CCY.map((c) => <option key={c}>{c}</option>)}
                </select>
              </label>
              <label>
                Capital{" "}
                <input className="config-select" type="number" min={1}
                       value={capital}
                       onChange={(e) => setCapital(e.target.value)} />
              </label>
              <button className="glass-button" onClick={create}>
                Create portfolio
              </button>
              {msg && <span className="body-sm">{msg}</span>}
            </div>
          </>
        ))}
      </div>

      {active != null && (
        <div className="glass">
          <h2 className="headline-sm panel-title">
            Portfolio #{active} — valuation
          </h2>
          <PortfolioDetail pid={active} />
        </div>
      )}
    </>
  );
}
