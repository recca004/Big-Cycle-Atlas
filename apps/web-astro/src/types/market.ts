/** Market research API contracts (Mission 5 §14-§25). All experimental. */

export interface MarketInstrument {
  code: string;
  name: string;
  asset_class: string;
  return_methodology: string;
  country_id: number | null;
  currency: string;
  unit: string;
  frequency: string;
  external_code: string;
  quote_convention: string | null;
  notes: string | null;
  active: boolean;
}

export interface InstrumentsResponse {
  instruments: MarketInstrument[];
  count: number;
  note: string;
}

export interface InstrumentCoverage {
  code: string;
  asset_class: string;
  frequency: string;
  observations: number;
  earliest: string | null;
  latest: string | null;
  last_retrieved: string | null;
}

export interface MarketCoverageResponse {
  instruments: InstrumentCoverage[];
  note: string;
}

export interface DatedPoint {
  date: string;
  value: number;
}

export interface InstrumentHistoryResponse {
  instrument: MarketInstrument;
  observations: DatedPoint[];
  count: number;
  bounded: boolean;
}

export interface PerformanceStats {
  cumulative_return: number | null;
  annualised_return: number | null;
  volatility: number | null;
  max_drawdown: number | null;
  observations?: number;
  [k: string]: number | null | undefined;
}

export interface InstrumentReturnsResponse {
  instrument: MarketInstrument;
  calc_version: string;
  return_methodology: string;
  returns: DatedPoint[];
  statistics: PerformanceStats;
  warning: string;
}

export interface RollingResponse {
  instrument: MarketInstrument;
  window: number;
  kind: "volatility" | "return";
  points: DatedPoint[];
}

export interface CorrelationResponse {
  methodology: string;
  pairs: Record<
    string,
    { shared_obs: number; correlation: number | null }
  >;
}

export interface FxConvertResponse {
  value: number | null;
  from: string;
  to: string;
  as_of: string;
  fx_used: {
    instrument: string;
    rate_date: string;
    rate: number;
    convention: string;
  }[];
  reason?: string | null;
}

/* ---------- Market regimes (§19-§25) ---------- */

export interface RegimeModelInfo {
  engine_version: string;
  model_id: string;
  methodology_status: string;
  framework: string;
  categories: string[];
  separate_measurements: string[];
  disclaimer: string;
}

export interface RegimeYear {
  year: number;
  regime: string;
  growth_direction: string;
  inflation_direction: string;
  gdp_growth: number | null;
  inflation_cpi: number | null;
  missing_inputs: string[];
  reason: string;
}

export interface FinancialConditionsYear {
  year: number;
  policy_rate: number | null;
  long_yield: number | null;
  real_rate_proxy: number | null;
  currency_return: number | null;
  missing: string[];
}

export interface RegimeHistoryResponse {
  country: string;
  model_id: string;
  model_version: string;
  methodology_status: string;
  execution_mode: string;
  backtest_safe: boolean;
  assumptions: Record<string, unknown>;
  regimes: RegimeYear[];
  financial_conditions: FinancialConditionsYear[];
  coverage: Record<string, number>;
  limitations: string[];
}

export interface RegimeAssetReturnsResponse {
  country: string;
  instrument: string;
  model_version: string;
  methodology_status: string;
  by_regime: Record<
    string,
    {
      episodes: number;
      mean_annual_return: number;
      min: number;
      max: number;
    }
  >;
  warning: string;
}
