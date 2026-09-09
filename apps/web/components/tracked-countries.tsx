"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchCountries } from "@/lib/api";
import type { Country } from "@/types/country";

export function TrackedCountries() {
  const [countries, setCountries] = useState<Country[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchCountries()
      .then((data) => {
        if (!cancelled) setCountries(data);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="headline-sm">Country data is currently unavailable.</p>
        <p className="mt-2 text-sm text-tertiary">
          The Atlas could not reach the API. Start the backend with{" "}
          <code>uv run python run.py</code> from apps/api, then reload.
        </p>
      </div>
    );
  }

  if (countries === null) {
    return <p className="text-sm text-tertiary">Loading countries…</p>;
  }

  if (countries.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="headline-sm">No countries found.</p>
        <p className="mt-2 text-sm text-tertiary">
          Run the seed script: <code>python -m app.db.seed</code> from apps/api.
        </p>
      </div>
    );
  }

  const regions = [...new Set(countries.map((c) => c.region))];

  return (
    <>
      <div className="mb-8 flex items-baseline justify-between">
        <h2 className="headline-lg">Tracked countries</h2>
        <span className="label-md text-tertiary">
          {countries.length} countries · {regions.length} regions
        </span>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {countries.map((country) => (
          <Link
            key={country.iso3}
            href={`/country/${country.iso3}`}
            className="block rounded-lg border border-border bg-surface p-4 transition-colors hover:border-tertiary"
          >
            <div className="flex items-baseline justify-between">
              <span className="headline-sm">{country.name}</span>
              <span className="label-md text-tertiary">{country.iso3}</span>
            </div>
            <p className="mt-1 text-[13px] text-tertiary">{country.region}</p>
            <p className="mt-1 text-[13px] text-tertiary">
              {country.indicator_count
                ? `Economic data / ${country.indicator_count} indicator${country.indicator_count === 1 ? "" : "s"}`
                : "No data yet"}
            </p>
            <div className="mt-4">
              <span className="inline-flex items-center rounded-full bg-neutral px-2.5 py-1 text-xs font-medium text-tertiary">
                Phase — not yet calculated
              </span>
            </div>
          </Link>
        ))}
      </div>
      <p className="mt-8 text-sm text-tertiary">
        Scoring and phase calculation arrive with the force engine (Milestone 5).
        No live or simulated scores are shown on this page.
      </p>
    </>
  );
}