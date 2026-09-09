import type { Country } from "@/types/country";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchCountries(): Promise<Country[]> {
  const response = await fetch(`${API_URL}/api/countries`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }
  return response.json();
}

export async function fetchCountry(iso3: string): Promise<Country | null> {
  const response = await fetch(`${API_URL}/api/countries/${iso3}`, {
    cache: "no-store",
  });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }
  return response.json();
}

export interface CountryObservation {
  id: number;
  indicator_code: string | null;
  value: number;
  period_start: string;
  retrieved_at: string;
  vintage_number: number;
  unit: string | null;
  source_key: string | null;
}

export async function fetchCountryObservations(
  iso3: string,
): Promise<CountryObservation[]> {
  const response = await fetch(
    `${API_URL}/api/countries/${iso3}/observations?limit=1000`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }
  const data = (await response.json()) as { items: CountryObservation[] };
  return data.items;
}

export interface ForceInput {
  indicator_code: string;
  name: string | null;
  has_data: boolean;
  has_source_series: boolean;
  source: string | null;
  latest_period: string | null;
}

export interface ForceCoverage {
  code: string;
  name: string;
  description: string | null;
  status: "available" | "partial" | "defined_not_sourced" | "missing";
  coverage_notes: string | null;
  live_inputs: ForceInput[];
  candidate_inputs: ForceInput[];
}

export interface ForceCoverageData {
  country: string;
  forces: ForceCoverage[];
}

export async function fetchForceCoverage(
  iso3: string,
): Promise<ForceCoverageData> {
  const response = await fetch(
    `${API_URL}/api/countries/${iso3}/force-coverage`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }
  return response.json();
}