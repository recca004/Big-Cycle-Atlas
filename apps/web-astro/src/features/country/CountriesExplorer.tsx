import { useEffect, useMemo, useState } from "react";
import { fetchCountries } from "@/lib/api/client";
import type { Country } from "@/types/api";

type View = "cards" | "table";

export function CountriesExplorer() {
  const [countries, setCountries] = useState<Country[] | null>(null);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [view, setView] = useState<View>("cards");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    const controller = new AbortController();
    fetchCountries({ signal: controller.signal })
      .then(setCountries)
      .catch(() => setError(true));
    return () => controller.abort();
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return countries ?? [];
    return (countries ?? []).filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.iso3.toLowerCase().includes(q) ||
        c.region.toLowerCase().includes(q),
    );
  }, [countries, query]);

  const toggleSelect = (iso3: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(iso3)) next.delete(iso3);
      else next.add(iso3);
      return next;
    });
  };

  if (error) {
    return (
      <div className="glass-subtle state-box" role="alert">
        <p className="headline-sm">Country data is currently unavailable.</p>
        <p className="body-sm">
          The Atlas could not reach the API. Start the backend with{" "}
          <code>uv run python run.py</code> from <code>apps/api</code>, then
          reload.
        </p>
      </div>
    );
  }

  const compareHref =
    selected.size >= 2 ? `/compare?countries=${[...selected].join(",")}` : null;

  return (
    <div className="section-stack" style={{ gap: "var(--space-5)" }}>
      <div className="explorer-toolbar">
        <input
          type="search"
          className="search-input"
          placeholder="Search countries…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search countries"
        />
        <div className="view-toggle" role="group" aria-label="View mode">
          <button
            type="button"
            className={view === "cards" ? "toggle-btn toggle-active" : "toggle-btn"}
            onClick={() => setView("cards")}
          >
            Cards
          </button>
          <button
            type="button"
            className={view === "table" ? "toggle-btn toggle-active" : "toggle-btn"}
            onClick={() => setView("table")}
          >
            Table
          </button>
        </div>
        {compareHref && (
          <a href={compareHref} className="btn btn-primary">
            Compare {selected.size} countries
          </a>
        )}
      </div>

      {!countries ? (
        <p className="body-sm">Loading countries…</p>
      ) : filtered.length === 0 ? (
        <div className="glass-subtle state-box">
          <p className="headline-sm">No countries match</p>
          <p className="body-sm">Try a different search term.</p>
        </div>
      ) : view === "cards" ? (
        <div className="country-grid">
          {filtered.map((c) => (
            <div key={c.iso3} className="glass country-card-wrap">
              <a href={`/country/${c.iso3}`} className="country-card country-card-plain">
                <p className="country-name">{c.name}</p>
                <p className="label-md text-tertiary">
                  {c.iso3} · {c.region}
                </p>
                <p className="body-sm country-coverage">
                  {c.indicator_count
                    ? `${c.indicator_count} indicators · through ${c.latest_observation_year ?? "—"}`
                    : "No data yet"}
                </p>
              </a>
              <label className="compare-check">
                <input
                  type="checkbox"
                  checked={selected.has(c.iso3)}
                  onChange={() => toggleSelect(c.iso3)}
                />
                Compare
              </label>
            </div>
          ))}
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col"></th>
                <th scope="col">Country</th>
                <th scope="col">ISO3</th>
                <th scope="col">Region</th>
                <th scope="col" className="num">Indicators</th>
                <th scope="col" className="num">Observations</th>
                <th scope="col" className="num">Latest</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.iso3}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(c.iso3)}
                      onChange={() => toggleSelect(c.iso3)}
                      aria-label={`Select ${c.name} for comparison`}
                    />
                  </td>
                  <td>
                    <a href={`/country/${c.iso3}`} className="country-link">
                      {c.name}
                    </a>
                  </td>
                  <td>{c.iso3}</td>
                  <td>{c.region}</td>
                  <td className="num">{c.indicator_count ?? "—"}</td>
                  <td className="num">{c.observation_count ?? "—"}</td>
                  <td className="num">{c.latest_observation_year ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
