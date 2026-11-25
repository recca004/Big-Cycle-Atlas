/** Strategy + paper portfolio API contracts (Mission 5 §26-§36). */

export interface BenchmarkStrategy {
  strategy_id: string;
  version: string;
  kind: string;
  allocations: Record<string, number>;
  rebalance: string;
  category: string;
  description: string;
}

export interface StrategiesResponse {
  benchmarks: BenchmarkStrategy[];
  custom_kinds: string[];
  categories: string[];
  note: string;
}

export interface SimulateRequest {
  strategy: string;
  kind?: string;
  allocations?: Record<string, number>;
  instruments?: string[];
  start: string;
  end: string;
  initial_capital: number;
  base_currency: string;
  rebalance: string;
  cost_bps: number;
  slippage_bps: number;
  benchmark: boolean;
}

export interface SimulationTrade {
  date: string;
  code: string;
  side: string;
  qty: number;
  price: number;
  value: number;
  cost: number;
}

export interface SimulateResponse {
  available: boolean;
  unavailable_reason?: string;
  strategy_id: string;
  strategy_version?: string;
  model_version: string;
  engine_version?: string;
  category: string;
  methodology_status?: string;
  date_range?: [string, string];
  initial_capital?: number;
  base_currency?: string;
  final_value?: number | null;
  cumulative_return?: number | null;
  annualised_return?: number | null;
  volatility?: number | null;
  max_drawdown?: number | null;
  turnover?: number;
  transaction_costs?: number;
  n_trades?: number;
  trades?: SimulationTrade[];
  path?: { date: string; value: number; cash: number }[];
  missing_valuations?: string[];
  data_sources?: Record<
    string,
    {
      external_code: string | false;
      observations: number;
      first: string | null;
      last: string | null;
    }
  >;
  execution_assumptions?: Record<string, unknown>;
  execution_mode?: string;
  backtest_safe?: boolean;
  benchmark?: {
    strategy_id: string;
    cumulative_return: number | null;
    final_value: number | null;
  } | null;
  run_manifest?: Record<string, unknown>;
  warnings?: string[];
}

/* ---------- Paper portfolio (§32-§36) ---------- */

export interface PaperPortfolioSummary {
  id: number;
  name: string;
  base_currency: string;
  starting_capital: number;
  archived?: boolean;
  simulation: true;
}

export interface PortfolioHolding {
  instrument: string;
  asset_class: string;
  currency: string;
  quantity: number;
  cost_basis_base: number;
  price_base: number | null;
  price_date: string | null;
  market_value_base: number | null;
}

export interface PortfolioValuation {
  portfolio_id: number;
  name: string;
  base_currency: string;
  calc_version: string;
  cash: number;
  market_value: number;
  total_value: number;
  cost_basis_method: string;
  realised_result: number;
  unrealised_result: number;
  total_return: number | null;
  holdings: PortfolioHolding[];
  missing_prices: string[];
  n_transactions: number;
  simulation: true;
}

export interface PaperTransaction {
  id: number;
  kind: string;
  instrument_id: number | null;
  quantity: number;
  price: number;
  currency: string;
  base_value: number;
  fee: number;
  user_entered_price: boolean;
  executed_at: string;
  idempotency_key: string;
}

export interface WatchlistEntry {
  id: number;
  kind: string;
  ref_code: string;
  label: string | null;
}
