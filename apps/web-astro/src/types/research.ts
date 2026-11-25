/** Research API contracts (Mission 2). Everything here is experimental. */

export interface MethodInfo {
  method_id: string;
  force_code: string;
  formula_id: string;
  version: string;
  state:
    | "approved_production"
    | "validated_candidate"
    | "experimental"
    | "context_only"
    | "deferred";
  dimension: string;
  inputs: string[];
  interpretation: string;
  reference_universe: string | null;
  units: string;
  parameters: Record<string, unknown>;
  coverage_ceiling: string | null;
  approval_decision: string | null;
  limitations: string[];
}

export interface CompositeModelInfo {
  model_id: string;
  version: string;
  kind: string;
  eligible_forces: string[];
  missing_policy: string;
  min_coverage: number;
  methodology_status: string;
  notes: string;
}

export interface CompositeResult {
  methodology_status: string;
  composite: {
    model_id: string;
    model_version: string;
    score: number | null;
    included_forces: string[];
    missing_forces: string[];
    excluded_forces: string[];
    weights: Record<string, number>;
    coverage_ratio: number;
    warnings: string[];
    limitations: string[];
  };
  period: string;
  backtest_safe: boolean;
  execution_mode?: string;
  info_cutoff?: string | null;
}

export interface CyclePoint {
  period: string;
  score: number | null;
  momentum: number | null;
  stage: string | null;
  phase: string | null;
  reason: string;
}

export interface CycleHistoryResponse {
  methodology_status: string;
  retrospective: boolean;
  execution_mode?: string;
  info_cutoff?: string | null;
  model: string;
  engine_version: string;
  country_iso3: string;
  coverage_ratio: number;
  points: CyclePoint[];
  transitions: Record<string, string>[];
  warnings: string[];
  backtest_safe: boolean;
}

export interface ExecutionModeInfo {
  mode: string;
  description: string;
  requires_info_cutoff: boolean;
  backtest_safe_by_construction: boolean;
}

export interface ExecutionModesResponse {
  modes: ExecutionModeInfo[];
  backtest_safe_rule: string;
}

export interface ProviderReleaseEvidence {
  source_key: string;
  provider: string;
  has_release_dates: boolean;
  has_revision_dates: boolean;
  has_vintage_history: boolean;
  publication_calendar: string | null;
  historical_archive: string | null;
  assumed_lag_days: number | null;
  notes: string;
}

export interface ReleaseEvidenceResponse {
  providers: ProviderReleaseEvidence[];
  disclaimer: string;
}

export interface IndicatorAvailability {
  indicator_code: string;
  source_key: string;
  observation_count: number;
  earliest_period: string | null;
  latest_period: string | null;
  with_release_evidence: number;
  max_vintage: number;
  strict_eligible: boolean;
}

export interface AvailabilityResponse {
  country: string;
  indicators: IndicatorAvailability[];
  note: string;
}

export interface ModelDiagnosticsManifest {
  generated_at: string;
  normalization_version: string;
  execution_mode: string;
  retrospective: boolean;
  backtest_safe: boolean;
  period_range: [string, string];
  methodology_status: string;
  models: Record<string, {
    model_id: string;
    model_version: string;
    kind: string;
    countries: Record<string, {
      earliest_usable_period: string | null;
      valid_periods: number;
      unavailable_periods: number;
      included_forces: string[];
      missing_forces: string[];
      mean_coverage: number | null;
      score_mean: number | null;
      score_volatility: number | null;
      stage_transitions: number;
      stages_seen: string[];
      coverage_ratio_path: number;
    }>;
  }>;
  countries_evaluated: string[];
  model_disagreement?: Record<string, {
    periods_compared: number;
    mean_spread: number | null;
    max_spread: number | null;
  }>;
  disclaimer: string;
}

export type PrimaryClassification =
  | "level_published"
  | "dimension_only"
  | "context_profile"
  | "deferred";

export interface ForceMethodProgress {
  force_code: string;
  force_name: string;
  /** Mutually-exclusive primary implementation type (Mission 3 §3). */
  primary_classification: PrimaryClassification;
  /** Independent attributes — may overlap across forces. */
  approval_state: "approved" | "partial" | "none";
  published_dimensions: string[];
  has_context_profile: boolean;
  experimental_methods: string[];
  methods: string[];
  coverage_ceiling: string | null;
  live_inputs: string[];
}

export interface ResearchProgress {
  as_of_period: string;
  total_forces: number;
  counts: Record<PrimaryClassification, number>;
  counts_sum_to_total: boolean;
  forces: ForceMethodProgress[];
}

export interface ForceHistoryPoint {
  period: string;
  execution_status: string;
  level_score: number | null;
  relative_score: number | null;
  momentum_score: number | null;
  coverage_status: string;
}

export interface ForceHistoryResponse {
  country_iso3: string;
  force_code: string;
  points: ForceHistoryPoint[];
  backtest_safe: boolean;
}
