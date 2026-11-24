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
}

async function request<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { signal, timeoutMs = DEFAULT_TIMEOUT_MS } = opts;
  let lastError: unknown;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    const timeout = AbortSignal.timeout(timeoutMs);
    const combined = signal
      ? AbortSignal.any([signal, timeout])
      : timeout;
    try {
      const response = await fetch(`${API_URL}${path}`, {
        signal: combined,
        headers: { Accept: "application/json" },
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
  params: { indicator?: string | undefined; limit?: number; offset?: number } = {},
  opts?: FetchOptions,
): Promise<ObservationPage> {
  const query = new URLSearchParams();
  if (params.indicator) query.set("indicator", params.indicator);
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
