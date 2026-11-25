import { useState } from "react";
import {
  addWatchlistEntry,
  fetchMarketInstruments,
  fetchWatchlist,
  removeWatchlistEntry,
} from "@/lib/api/client";
import type { WatchlistEntry } from "@/types/strategy";
import { useAsyncState, useCountryList } from "@/features/widgets/hooks";
import { resolveAsync } from "@/features/widgets/common";

const KINDS = ["instrument", "indicator", "country", "force", "model"];

/** Mission 5 §42 — watchlist panel: pinned references across the atlas. */
export function WatchlistPanel() {
  const [tick, setTick] = useState(0);
  const entries = useAsyncState<{ entries: WatchlistEntry[] }>(
    (s) => fetchWatchlist({ signal: s }),
    [tick],
  );
  const countries = useCountryList();
  const instruments = useAsyncState(
    (s) => fetchMarketInstruments({ signal: s }),
    [],
  );

  const [kind, setKind] = useState("instrument");
  const [ref, setRef] = useState("US_SP500");
  const [label, setLabel] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const refOptions = (): { value: string; label: string }[] => {
    switch (kind) {
      case "instrument":
        return instruments.kind === "ready"
          ? instruments.data.instruments.map((i) => ({
              value: i.code, label: `${i.code} — ${i.name}`,
            }))
          : [];
      case "country":
        return countries.map((c) => ({
          value: c.iso3, label: `${c.iso3} — ${c.name}`,
        }));
      default:
        return [];
    }
  };
  const options = refOptions();

  const add = async () => {
    setMsg(null);
    try {
      const r = await addWatchlistEntry(kind, ref, label || undefined);
      setMsg(r.created ? "Added" : "Already on the watchlist");
      setTick((t) => t + 1);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    }
  };

  const remove = async (id: number) => {
    await removeWatchlistEntry(id);
    setTick((t) => t + 1);
  };

  return (
    <div className="glass">
      <h2 className="headline-sm panel-title">Watchlist</h2>
      <p className="body-sm">
        Pinned references for quick access — instruments, indicators,
        countries, forces and models.
      </p>
      <div className="research-controls glass-subtle">
        <label>
          Kind{" "}
          <select
            className="config-select" value={kind}
            onChange={(e) => setKind(e.target.value)}
          >
            {KINDS.map((k) => <option key={k}>{k}</option>)}
          </select>
        </label>
        {options.length > 0 ? (
          <label>
            Reference{" "}
            <select
              className="config-select" value={ref}
              onChange={(e) => setRef(e.target.value)}
            >
              {options.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
        ) : (
          <label>
            Reference{" "}
            <input
              className="config-select" value={ref}
              placeholder="code"
              onChange={(e) => setRef(e.target.value)}
            />
          </label>
        )}
        <label>
          Label{" "}
          <input
            className="config-select" value={label}
            placeholder="optional"
            onChange={(e) => setLabel(e.target.value)}
          />
        </label>
        <button className="glass-button" onClick={add}>Add</button>
        {msg && <span className="body-sm">{msg}</span>}
      </div>
      {resolveAsync(
        entries,
        (e) => (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr><th>Kind</th><th>Reference</th><th>Label</th><th /></tr>
              </thead>
              <tbody>
                {e.entries.map((en) => (
                  <tr key={en.id}>
                    <td><span className="badge">{en.kind}</span></td>
                    <td><code>{en.ref_code}</code></td>
                    <td>{en.label ?? "—"}</td>
                    <td>
                      <button
                        className="glass-button"
                        onClick={() => remove(en.id)}
                        aria-label={`Remove ${en.ref_code}`}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ),
        (e) => e.entries.length === 0
          ? "Nothing pinned yet — add an instrument, country or indicator above."
          : null,
      )}
    </div>
  );
}
