/** Response types matching the FastAPI contracts (docs/api.md). */

export interface Country {
  iso3: string;
  iso2: string;
  name: string;
  region: string;
  observation_count?: number;
  indicator_count?: number;
  latest_observation_year?: number;
  created_at?: string;
  updated_at?: string;
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

export interface ObservationPage {
  items: CountryObservation[];
  total: number;
  limit: number;
  offset: number;
}

export interface ForceInput {
  indicator_code: string;
  name: string | null;
  has_data: boolean;
  has_source_series: boolean;
  source: string | null;
  latest_period: string | null;
}

export type ForceCoverageStatus =
  | "available"
  | "partial"
  | "defined_not_sourced"
  | "missing";

export interface ForceCoverage {
  code: string;
  name: string;
  description: string | null;
  status: ForceCoverageStatus;
  coverage_notes: string | null;
  live_inputs: ForceInput[];
  candidate_inputs: ForceInput[];
}

export interface ForceCoverageData {
  country: string;
  forces: ForceCoverage[];
}

export interface DataSource {
  id: number;
  source_key: string;
  name: string;
  status: string;
  description?: string | null;
}

export interface Indicator {
  id: number;
  code: string;
  name: string;
  unit?: string | null;
  frequency?: string | null;
}

export interface IngestionRun {
  id: number;
  source_key?: string | null;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  observations_inserted?: number | null;
  observations_skipped?: number | null;
  observations_revised?: number | null;
}

export interface IndicatorRevision {
  id: number;
  indicator_code?: string;
  period_start?: string;
  old_value?: number;
  new_value?: number;
  vintage_from?: number;
  vintage_to?: number;
}

export interface HealthStatus {
  status: string;
  version: string;
  database: string;
  database_error: string | null;
}

/** Force-scores API (R6) — only approved dimensions are populated. */
export interface ForceScore {
  force_code: string;
  force_name: string;
  execution_status: "scored" | "deferred";
  level_score: number | null;
  relative_score: number | null;
  momentum_score: number | null;
  confidence: number | null;
  coverage_status: ForceCoverageStatus;
  period: string | null;
  model_version: string | null;
  limitations: string[];
  reasons: string[];
  backtest_safe: boolean;
}

export interface ForceScoresResponse {
  country: string;
  normalization_version: string;
  force_aggregation_version: string;
  forces: ForceScore[];
}
