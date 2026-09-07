import type { Country } from "@/types/country";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchCountries(): Promise<Country[]> {
  const response = await fetch(`${API_URL}/api/countries`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }
  return response.json();
}