/** Observatory overview payload — /api/observatory/overview.
 *  All fields are EXPERIMENTAL model outputs unless noted. */

export interface ObservatoryHistoryPoint {
  period: string;
  score: number | null;
  momentum: number | null;
  stage: string | null;
  phase: string | null;
  reason?: string;
}

export interface ObservatoryTransition {
  period: string;
  to: string;
  reason: string;
}

export interface TopForce {
  force_code: string;
  force_name: string;
  execution_status: string;
  level_score: number | null;
  relative_score: number | null;
  momentum_score: number | null;
}

export interface ForceRecord extends TopForce {
  coverage_status?: string;
  period?: string | null;
}

export interface ForceSummary {
  scored_count: number;
  dimension_only_count: number;
  context_only_count: number;
  top_forces: TopForce[];
  weakest_forces?: TopForce[];
  forces: ForceRecord[];
}

export interface IndicatorSnapshot {
  year: number;
  period: string;
  value: number;
  vintage: number;
  source: string;
}

export interface TradePower {
  trade_volume_usd?: number | null;
  tracked_share_pct?: number | null;
  exports_pct_gdp?: number | null;
  imports_pct_gdp?: number | null;
  current_account_pct_gdp?: number | null;
  period?: string | null;
  source?: string | null;
}

export interface InnovationPower {
  rnd_pct_gdp?: number | null;
  implied_rnd_usd?: number | null;
  tracked_share_pct?: number | null;
  period?: string | null;
  source?: string | null;
}

export interface MonetaryPower {
  currency_code?: string;
  reserve_anchor_role?: string;
  reer_index?: number | null;
  reer_period?: string | null;
  gov_10y_yield?: number | null;
  gov_10y_period?: string | null;
  source?: string | null;
  scope_note?: string;
}

export interface InternationalPower {
  economic_size?: {
    value_usd: number;
    tracked_share_pct: number;
    period: string;
    source: string;
  };
  military_resources?: {
    expenditure_usd: number;
    tracked_share_pct: number;
    pct_gdp: number;
    period: string;
    source: string;
  };
  international_trade?: TradePower;
  innovation_scale?: InnovationPower;
  monetary_influence?: MonetaryPower;
  [key: string]: unknown;
}

export interface ObservatoryCountry {
  iso3: string;
  name: string;
  region: string;
  stage: string | null;
  phase: string | null;
  domestic_condition_score: number | null;
  score: number | null;
  momentum: number | null;
  coverage_ratio: number | null;
  period: string | null;
  direction: string | null;
  classified: boolean;
  recent_transition: ObservatoryTransition | null;
  transitions: ObservatoryTransition[];
  history: ObservatoryHistoryPoint[];
  force_summary: ForceSummary;
  international_power: InternationalPower;
  indicator_snapshots: Record<
    string,
    { latest: IndicatorSnapshot; prior_5y?: IndicatorSnapshot }
  >;
  domestic_condition_rank: number | null;
}

export interface PowerSummary {
  largest_economy_iso3: string;
  second_economy_iso3: string;
  highest_domestic_condition_iso3: string;
  separation_note: string;
}

export interface TransitionMeasurement {
  key: string;
  label: string;
  category: string;
  unit: string;
  incumbent_value: number | null;
  challenger_value: number | null;
  challenger_to_incumbent_ratio: number | null;
  absolute_gap: number | null;
  direction?: string;
  relationship?: "convergence" | "divergence" | "stable" | "insufficient_data";
  trend_note?: string | null;
  period?: string | null;
  source?: string | null;
}

export interface ForecastHorizon {
  horizon: string;
  horizon_label: string;
  horizon_quarters: number;
  available: boolean;
  status_label: string;
  blockers?: string[];
}

export interface ForecastReadiness {
  methodology_status: string;
  overall_available: boolean;
  estimated_transition_window: string;
  blockers: string[];
  total_scored_periods: number;
  total_genuine_transitions: number;
  strict_eligible_periods: number;
  horizons: ForecastHorizon[];
}

export interface HistoricalTransition {
  period: string;
  from: string;
  to: string;
  reason: string;
}

export interface HistoricalEvidence {
  incumbent_transitions?: HistoricalTransition[];
  challenger_transitions?: HistoricalTransition[];
  [key: string]: unknown;
}

export interface TransitionMonitor {
  incumbent_iso3: string;
  incumbent_name: string;
  incumbent_stage: string | null;
  incumbent_direction: string | null;
  challenger_iso3: string;
  challenger_name: string;
  challenger_stage: string | null;
  challenger_direction: string | null;
  measurements: TransitionMeasurement[];
  areas_of_convergence: TransitionMeasurement[];
  areas_of_divergence: TransitionMeasurement[];
  historical_evidence: HistoricalEvidence;
  forecast_readiness: ForecastReadiness;
}

export interface ProviderFailure {
  provider: string;
  provider_name: string;
  latest_status: string;
  error_count: number;
  last_run_at: string;
  message: string;
}

export interface ObservatoryFreshness {
  status:
    | "updated"
    | "no_new_observations"
    | "partial_provider_failure"
    | "update_failed"
    | "historical_view";
  status_label: string;
  latest_collection_at: string | null;
  latest_collection_zurich: string | null;
  latest_calculation_at: string | null;
  latest_calculation_zurich: string | null;
  latest_observation_period: string | null;
  scoring_period: string | null;
  timezone: string;
  new_observations_count: number;
  revisions_count: number;
  changed_classifications_count: number;
  provider_failures: ProviderFailure[];
  total_observations: number;
  total_revisions: number;
}

export interface DailyChange {
  kind: string;
  iso3?: string;
  country_name?: string;
  measurement: string;
  previous: number | string | null;
  current: number | string | null;
  difference?: number | null;
  period?: string | null;
  source?: string | null;
}

export interface DailyChanges {
  has_previous_snapshot: boolean;
  previous_snapshot_at: string | null;
  previous_snapshot_zurich: string | null;
  current_snapshot_at: string | null;
  current_snapshot_zurich: string | null;
  summary_message: string;
  changes: DailyChange[];
}

export interface RefreshJob {
  running: boolean;
  mode: string | null;
  started_at: string | null;
  completed_at: string | null;
  current_provider: string | null;
  completed_steps: number;
  total_steps: number;
  inserted: number;
  revised: number;
  failed: number;
  status: "idle" | "running" | "succeeded" | "failed" | string;
  error: string | null;
}

export interface ObservatoryOverview {
  methodology_status: string;
  normalization_version: string;
  model: {
    model_id: string;
    model_version: string;
    available_models: {
      model_id: string;
      model_version: string;
      kind: string;
      notes: string;
    }[];
  };
  scoring_period: string | null;
  available_periods: string[];
  countries: ObservatoryCountry[];
  power_summary: PowerSummary;
  transition_monitor: TransitionMonitor;
  freshness: ObservatoryFreshness;
  daily_changes: DailyChanges;
  refresh_job: RefreshJob;
}
