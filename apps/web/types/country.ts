export interface Country {
  iso3: string;
  iso2: string;
  name: string;
  region: string;
  created_at: string;
  updated_at: string;
  observation_count?: number | null;
  indicator_count?: number | null;
  latest_observation_year?: number | null;
}