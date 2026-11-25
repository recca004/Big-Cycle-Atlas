/** Typed API client — single point of access to the FastAPI backend.
 *  Cancellable, retry-limited (network errors only), timeout-guarded. */

import type {
  Country,
  ObservationPage,
  ForceCoverageData,
  DataSource,
  Indicator,
  IngestionRun,
  IndicatorRevision,
  HealthStatus,
  ForceScoresResponse,
  IndicatorUncertaintyHistory,
} from "@/types/api";

export const API_URL: string =
  (import.meta.env.PUBLIC_API_URL as string | undefined) ??
  "http://localhost:8000";

const DEFAULT_TIMEOUT_MS = 15_000;
const MAX_RETRIES = 1; // one retry for network-level failures only

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface FetchOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
}

async function request<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { signal, timeoutMs = DEFAULT_TIMEOUT_MS, method, body } = opts;
  let lastError: unknown;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    const timeout = AbortSignal.timeout(timeoutMs);
    const combined = signal
      ? AbortSignal.any([signal, timeout])
      : timeout;
    try {
      const response = await fetch(`${API_URL}${path}`, {
        method: method ?? "GET",
        signal: combined,
        headers: {
          Accept: "application/json",
          ...(body !== undefined
            ? { "Content-Type": "application/json" }
            : {}),
        },
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
      if (!response.ok) {
        // 4xx/5xx are definitive answers — never retried.
        throw new ApiError(
          `API request failed: ${response.status}`,
          response.status,
        );
      }
      return (await response.json()) as T;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      if (signal?.aborted) throw err;
      lastError = err;
      // Retry only on network-level failure / timeout.
    }
  }
  throw lastError instanceof Error
    ? lastError
    : new ApiError("API request failed");
}

export function fetchHealth(opts?: FetchOptions): Promise<HealthStatus> {
  return request<HealthStatus>("/health", opts);
}

export function fetchCountries(opts?: FetchOptions): Promise<Country[]> {
  return request<Country[]>("/api/countries", opts);
}

export async function fetchCountry(
  iso3: string,
  opts?: FetchOptions,
): Promise<Country | null> {
  try {
    return await request<Country>(
      `/api/countries/${encodeURIComponent(iso3)}`,
      opts,
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export function fetchCountryObservations(
  iso3: string,
  params: {
    indicator?: string | undefined;
    source?: string | undefined;
    start?: string | undefined;
    end?: string | undefined;
    limit?: number;
    offset?: number;
  } = {},
  opts?: FetchOptions,
): Promise<ObservationPage> {
  const query = new URLSearchParams();
  if (params.indicator) query.set("indicator", params.indicator);
  if (params.source) query.set("source", params.source);
  if (params.start) query.set("start", params.start);
  if (params.end) query.set("end", params.end);
  query.set("limit", String(params.limit ?? 100));
  query.set("offset", String(params.offset ?? 0));
  return request<ObservationPage>(
    `/api/countries/${encodeURIComponent(iso3)}/observations?${query}`,
    opts,
  );
}

export function fetchForceCoverage(
  iso3: string,
  opts?: FetchOptions,
): Promise<ForceCoverageData> {
  return request<ForceCoverageData>(
    `/api/countries/${encodeURIComponent(iso3)}/force-coverage`,
    opts,
  );
}

export function fetchDataSources(opts?: FetchOptions): Promise<DataSource[]> {
  return request<DataSource[]>("/api/data/sources", opts);
}

export function fetchIngestionRuns(
  opts?: FetchOptions,
): Promise<IngestionRun[]> {
  return request<IngestionRun[]>("/api/data/ingestion-runs", opts);
}

export function fetchIndicators(opts?: FetchOptions): Promise<Indicator[]> {
  return request<Indicator[]>("/api/indicators", opts);
}

export function fetchForceScores(
  iso3: string,
  period?: string,
  opts?: FetchOptions,
): Promise<ForceScoresResponse> {
  const query = period ? `?period=${encodeURIComponent(period)}` : "";
  return request<ForceScoresResponse>(
    `/api/countries/${encodeURIComponent(iso3)}/force-scores${query}`,
    opts,
  );
}

export function fetchIndicatorRevisions(
  code: string,
  opts?: FetchOptions,
): Promise<IndicatorRevision[]> {
  return request<IndicatorRevision[]>(
    `/api/indicators/${encodeURIComponent(code)}/revisions`,
    opts,
  );
}

/* ---------- Research API (experimental — Mission 2) ---------- */

import type {
  MethodInfo,
  CompositeModelInfo,
  CompositeResult,
  CycleHistoryResponse,
  ResearchProgress,
  ForceHistoryResponse,
  ExecutionModesResponse,
  ReleaseEvidenceResponse,
  AvailabilityResponse,
  ModelDiagnosticsManifest,
} from "@/types/research";

export function fetchResearchMethods(
  opts?: FetchOptions,
): Promise<MethodInfo[]> {
  return request<MethodInfo[]>("/api/research/methods", opts);
}

export function fetchCompositeModels(
  opts?: FetchOptions,
): Promise<CompositeModelInfo[]> {
  return request<CompositeModelInfo[]>("/api/research/models", opts);
}

export function fetchCountryCycle(
  iso3: string,
  model: string,
  opts?: FetchOptions & { executionMode?: string; infoCutoff?: string },
): Promise<CompositeResult> {
  const { executionMode, infoCutoff, ...rest } = opts ?? {};
  const q = new URLSearchParams({ model });
  if (executionMode) q.set("execution_mode", executionMode);
  if (infoCutoff) q.set("info_cutoff", infoCutoff);
  return request<CompositeResult>(
    `/api/research/countries/${encodeURIComponent(iso3)}/cycle?${q}`,
    rest,
  );
}

export function fetchCycleHistory(
  iso3: string,
  model: string,
  startYear = 2000,
  opts?: FetchOptions & { executionMode?: string; infoCutoff?: string },
): Promise<CycleHistoryResponse> {
  const { executionMode, infoCutoff, ...rest } = opts ?? {};
  const q = new URLSearchParams({ model, start_year: String(startYear) });
  if (executionMode) q.set("execution_mode", executionMode);
  if (infoCutoff) q.set("info_cutoff", infoCutoff);
  return request<CycleHistoryResponse>(
    `/api/research/countries/${encodeURIComponent(iso3)}/cycle/history?${q}`,
    rest,
  );
}

export function fetchExecutionModes(
  opts?: FetchOptions,
): Promise<ExecutionModesResponse> {
  return request<ExecutionModesResponse>(
    "/api/research/execution-modes", opts,
  );
}

export function fetchReleaseEvidence(
  opts?: FetchOptions,
): Promise<ReleaseEvidenceResponse> {
  return request<ReleaseEvidenceResponse>(
    "/api/research/release-evidence", opts,
  );
}

export function fetchCountryAvailability(
  iso3: string,
  opts?: FetchOptions,
): Promise<AvailabilityResponse> {
  return request<AvailabilityResponse>(
    `/api/research/countries/${encodeURIComponent(iso3)}/availability`,
    opts,
  );
}

export function fetchModelDiagnostics(
  opts?: FetchOptions,
): Promise<ModelDiagnosticsManifest> {
  return request<ModelDiagnosticsManifest>(
    "/api/research/diagnostics", opts,
  );
}

export function fetchResearchProgress(
  opts?: FetchOptions,
): Promise<ResearchProgress> {
  return request<ResearchProgress>("/api/research/progress", opts);
}

export function fetchIndicatorUncertaintyHistory(
  iso3: string,
  indicatorCode: string,
  opts?: FetchOptions,
): Promise<IndicatorUncertaintyHistory> {
  return request<IndicatorUncertaintyHistory>(
    `/api/countries/${encodeURIComponent(iso3)}/indicators/${encodeURIComponent(indicatorCode)}/uncertainty`,
    opts,
  );
}

export function fetchForceHistory(
  iso3: string,
  forceCode: string,
  startYear = 1996,
  opts?: FetchOptions,
): Promise<ForceHistoryResponse> {
  return request<ForceHistoryResponse>(
    `/api/countries/${encodeURIComponent(iso3)}/forces/${encodeURIComponent(forceCode)}/history?start_year=${startYear}`,
    opts,
  );
}

/* ---------- Forecast research (Mission 5 §10-§13) ---------- */

import type {
  ForecastReadinessResponse,
  CountryForecastResponse,
} from "@/types/research";

export function fetchForecastReadiness(
  opts?: FetchOptions,
): Promise<ForecastReadinessResponse> {
  return request<ForecastReadinessResponse>(
    "/api/research/forecast/readiness", opts,
  );
}

export function fetchCountryForecast(
  iso3: string,
  model: string,
  horizon: string,
  opts?: FetchOptions,
): Promise<CountryForecastResponse> {
  const q = new URLSearchParams({ model, horizon });
  return request<CountryForecastResponse>(
    `/api/research/forecast/${encodeURIComponent(iso3)}?${q}`, opts,
  );
}

/* ---------- Market research (Mission 5 §14-§25) ---------- */

import type {
  InstrumentsResponse,
  MarketCoverageResponse,
  InstrumentHistoryResponse,
  InstrumentReturnsResponse,
  CorrelationResponse,
  FxConvertResponse,
  RegimeModelInfo,
  RegimeHistoryResponse,
  RegimeAssetReturnsResponse,
} from "@/types/market";

export function fetchMarketInstruments(
  opts?: FetchOptions,
): Promise<InstrumentsResponse> {
  return request<InstrumentsResponse>("/api/markets/instruments", opts);
}

export function fetchMarketCoverage(
  opts?: FetchOptions,
): Promise<MarketCoverageResponse> {
  return request<MarketCoverageResponse>("/api/markets/coverage", opts);
}

export function fetchInstrumentHistory(
  code: string,
  params: { start?: string; end?: string; limit?: number } = {},
  opts?: FetchOptions,
): Promise<InstrumentHistoryResponse> {
  const q = new URLSearchParams();
  if (params.start) q.set("start", params.start);
  if (params.end) q.set("end", params.end);
  if (params.limit) q.set("limit", String(params.limit));
  const suffix = q.size ? `?${q}` : "";
  return request<InstrumentHistoryResponse>(
    `/api/markets/instruments/${encodeURIComponent(code)}/history${suffix}`,
    opts,
  );
}

export function fetchInstrumentReturns(
  code: string,
  params: { start?: string; end?: string } = {},
  opts?: FetchOptions,
): Promise<InstrumentReturnsResponse> {
  const q = new URLSearchParams();
  if (params.start) q.set("start", params.start);
  if (params.end) q.set("end", params.end);
  const suffix = q.size ? `?${q}` : "";
  return request<InstrumentReturnsResponse>(
    `/api/markets/instruments/${encodeURIComponent(code)}/returns${suffix}`,
    opts,
  );
}

export function fetchCorrelations(
  codes: string[],
  params: { start?: string; end?: string } = {},
  opts?: FetchOptions,
): Promise<CorrelationResponse> {
  const q = new URLSearchParams({ codes: codes.join(",") });
  if (params.start) q.set("start", params.start);
  if (params.end) q.set("end", params.end);
  return request<CorrelationResponse>(`/api/markets/correlations?${q}`, opts);
}

export function fetchFxConvert(
  amount: number,
  from: string,
  to: string,
  asOf?: string,
  opts?: FetchOptions,
): Promise<FxConvertResponse> {
  const q = new URLSearchParams({
    amount: String(amount), from, to,
  });
  if (asOf) q.set("as_of", asOf);
  return request<FxConvertResponse>(`/api/markets/fx/convert?${q}`, opts);
}

export function fetchRegimeModel(
  opts?: FetchOptions,
): Promise<RegimeModelInfo> {
  return request<RegimeModelInfo>("/api/regimes/model", opts);
}

export function fetchRegimeHistory(
  iso3: string,
  opts?: FetchOptions,
): Promise<RegimeHistoryResponse> {
  return request<RegimeHistoryResponse>(
    `/api/regimes/countries/${encodeURIComponent(iso3)}/history`, opts,
  );
}

export function fetchRegimeAssetReturns(
  iso3: string,
  opts?: FetchOptions,
): Promise<RegimeAssetReturnsResponse> {
  return request<RegimeAssetReturnsResponse>(
    `/api/regimes/countries/${encodeURIComponent(iso3)}/asset-returns`, opts,
  );
}

/* ---------- Strategies (Mission 5 §26-§31) ---------- */

import type {
  StrategiesResponse,
  SimulateRequest,
  SimulateResponse,
  PaperPortfolioSummary,
  PortfolioValuation,
  PaperTransaction,
  WatchlistEntry,
} from "@/types/strategy";

export function fetchStrategies(
  opts?: FetchOptions,
): Promise<StrategiesResponse> {
  return request<StrategiesResponse>("/api/strategies", opts);
}

export function postSimulate(
  req: SimulateRequest,
  opts?: FetchOptions,
): Promise<SimulateResponse> {
  return request<SimulateResponse>("/api/strategies/simulate", {
    ...opts, method: "POST", body: req,
  });
}

/* ---------- Paper portfolio + watchlist (Mission 5 §32-§36) ---------- */

export function fetchPortfolios(
  opts?: FetchOptions,
): Promise<{ portfolios: PaperPortfolioSummary[] }> {
  return request("/api/portfolio", opts);
}

export function createPortfolio(
  name: string,
  baseCurrency: string,
  startingCapital: number,
  opts?: FetchOptions,
): Promise<PaperPortfolioSummary> {
  return request("/api/portfolio", {
    ...opts, method: "POST",
    body: {
      name, base_currency: baseCurrency,
      starting_capital: startingCapital,
    },
  });
}

export function fetchPortfolioValuation(
  pid: number,
  opts?: FetchOptions,
): Promise<PortfolioValuation> {
  return request<PortfolioValuation>(`/api/portfolio/${pid}`, opts);
}

export function fetchPortfolioTransactions(
  pid: number,
  opts?: FetchOptions,
): Promise<{ transactions: PaperTransaction[]; simulation: true }> {
  return request(`/api/portfolio/${pid}/transactions`, opts);
}

export interface TransactionRequest {
  kind: "buy" | "sell" | "deposit";
  instrument_code?: string;
  quantity?: number;
  price?: number;
  currency?: string;
  fee?: number;
  idempotency_key: string;
  user_entered_price?: boolean;
}

export function postTransaction(
  pid: number,
  req: TransactionRequest,
  opts?: FetchOptions,
): Promise<{ id: number; created: boolean; kind: string }> {
  return request(`/api/portfolio/${pid}/transactions`, {
    ...opts, method: "POST", body: req,
  });
}

export function fetchWatchlist(
  opts?: FetchOptions,
): Promise<{ entries: WatchlistEntry[] }> {
  return request("/api/portfolio/watchlist/all", opts);
}

export function addWatchlistEntry(
  kind: string,
  refCode: string,
  label?: string,
  opts?: FetchOptions,
): Promise<{ id: number; created: boolean }> {
  return request("/api/portfolio/watchlist", {
    ...opts, method: "POST",
    body: { kind, ref_code: refCode, label: label ?? null },
  });
}

export function removeWatchlistEntry(
  eid: number,
  opts?: FetchOptions,
): Promise<{ removed: boolean }> {
  return request(`/api/portfolio/watchlist/${eid}`, {
    ...opts, method: "DELETE",
  });
}
