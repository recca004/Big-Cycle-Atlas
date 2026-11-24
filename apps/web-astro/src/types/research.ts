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
  model: string;
  engine_version: string;
  country_iso3: string;
  coverage_ratio: number;
  points: CyclePoint[];
  transitions: Record<string, string>[];
  warnings: string[];
  backtest_safe: boolean;
}

export interface ForceMethodProgress {
  force_code: string;
  force_name: string;
  implementation_status:
    | "approved_level"
    | "partial"
    | "dimension_only"
    | "context_only"
    | "deferred";
  dimensions: string[];
  methods: string[];
  coverage_ceiling: string | null;
  live_inputs: string[];
}

export interface ResearchProgress {
  as_of_period: string;
  counts: Record<string, number>;
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
