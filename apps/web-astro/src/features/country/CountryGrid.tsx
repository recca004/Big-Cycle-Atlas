import { useEffect, useState } from "react";
import { fetchCountries } from "@/lib/api/client";
import type { Country } from "@/types/api";

type State =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "ready"; countries: Country[] };

export function CountryGrid() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetchCountries({ signal: controller.signal })
      .then((countries) => setState({ kind: "ready", countries }))
      .catch((err) => {
        if (!controller.signal.aborted) setState({ kind: "error" });
        void err;
      });
    return () => controller.abort();
  }, []);

  if (state.kind === "loading") {
    return (
      <div className="country-grid" aria-busy="true">
        {Array.from({ length: 8 }, (_, i) => (
          <div key={i} className="glass country-card country-card-skeleton" />
        ))}
      </div>
    );
  }

  if (state.kind === "error") {
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

  return (
    <div className="country-grid">
      {state.countries.map((c) => (
        <a
          key={c.iso3}
          href={`/country/${c.iso3}`}
          className="glass glass-interactive country-card"
        >
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
      ))}
    </div>
  );
}
