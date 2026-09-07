"use client";

import { useEffect, useState } from "react";
import { fetchCountries } from "@/lib/api";
import type { Country } from "@/types/country";

export function CountryList() {
  const [countries, setCountries] = useState<Country[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchCountries()
      .then((data) => {
        if (!cancelled) setCountries(data);
      })
      .catch(() => {
        if (!cancelled) {
          setError("Could not load countries from the API. Is the backend running on port 8000?");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="headline-sm">{error}</p>
        <p className="mt-2 text-sm text-tertiary">
          Start it with <code>uv run python run.py</code> from apps/api, then reload.
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

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border">
            <th className="px-4 py-3 text-xs font-medium text-tertiary">Country</th>
            <th className="px-4 py-3 text-xs font-medium text-tertiary">ISO3</th>
            <th className="px-4 py-3 text-xs font-medium text-tertiary">Region</th>
          </tr>
        </thead>
        <tbody>
          {countries.map((country) => (
            <tr key={country.iso3} className="border-b border-border last:border-none">
              <td className="px-4 py-3 text-[15px]">{country.name}</td>
              <td className="px-4 py-3 text-[13px] text-tertiary">{country.iso3}</td>
              <td className="px-4 py-3 text-[13px] text-tertiary">{country.region}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}