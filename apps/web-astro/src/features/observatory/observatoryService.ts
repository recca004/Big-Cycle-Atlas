import {
  fetchObservatoryModelComparison,
  fetchObservatoryOverview,
  fetchObservatoryRefreshStatus,
  fetchObservatoryTransition,
  postObservatoryRefresh,
} from "@/lib/api/client";
import type {
  ObservatoryOverview,
  RefreshJob,
  TransitionMonitor,
} from "@/types/observatory";

export type ObservatoryMode = "production" | "demo";

export interface ObservatoryService {
  loadOverview: (startYear?: number, model?: string) => Promise<ObservatoryOverview>;
  loadTransition: (incumbent: string, challenger: string, startYear?: number, model?: string) => Promise<TransitionMonitor>;
  loadModelComparison: (startYear?: number) => Promise<import("@/types/observatory").ObservatoryModelComparison>;
  requestRefresh: () => Promise<RefreshJob>;
  loadRefreshStatus: () => Promise<RefreshJob>;
}

export const PRODUCTION_MODEL = "model_b_domain";

const overviewCache = new Map<string, Promise<ObservatoryOverview>>();
const transitionCache = new Map<string, Promise<TransitionMonitor>>();
const comparisonCache = new Map<string, Promise<import("@/types/observatory").ObservatoryModelComparison>>();

export function invalidateObservatoryCaches(): void {
  overviewCache.clear();
  transitionCache.clear();
  comparisonCache.clear();
}

export function createObservatoryService(mode: ObservatoryMode): ObservatoryService {
  if (mode === "demo") {
    return {
      loadOverview: async () => {
        const demo = await import("./offlineData");
        return demo.createOfflineOverview();
      },
      loadTransition: async (incumbent, challenger) => {
        const demo = await import("./offlineData");
        return demo.buildOfflineTransition(incumbent, challenger);
      },
      loadModelComparison: async (startYear = 1980) => {
        const demo = await import("./offlineData");
        const overview = demo.createOfflineOverview();
        const models = overview.model.available_models;
        return {
          cycle_label: "experimental_domestic_condition_cycle",
          requested_period: null,
          active_period: overview.available_periods.at(-1) ?? null,
          start_year: startYear,
          models,
          countries: overview.countries.map((country) => ({
            iso3: country.iso3,
            name: country.name,
            models: Object.fromEntries(models.map((model) => [model.model_id, {
              stage: country.stage,
              score: country.score,
              momentum: country.momentum,
              period: country.period,
              coverage_ratio: country.coverage_ratio,
            }])),
          })),
          equivalence: {},
          note: "Demonstration model markers are synthetic interface evidence, not production model comparisons.",
        };
      },
      requestRefresh: async () => {
        const demo = await import("./offlineData");
        return demo.runningOfflineRefreshJob();
      },
      loadRefreshStatus: async () => {
        const demo = await import("./offlineData");
        return demo.offlineRefreshScenario(1).job;
      },
    };
  }

  return {
    loadOverview: (startYear = 1980, model = PRODUCTION_MODEL) => {
      const key = `overview:${model}:${startYear}`;
      let request = overviewCache.get(key);
      if (!request) {
        request = fetchObservatoryOverview({ model, startYear });
        overviewCache.set(key, request);
        request.catch(() => overviewCache.delete(key));
      }
      return request;
    },
    loadTransition: (incumbent, challenger, startYear = 1980, model = PRODUCTION_MODEL) => {
      const key = `transition:${model}:${incumbent}:${challenger}:${startYear}`;
      let request = transitionCache.get(key);
      if (!request) {
        request = fetchObservatoryTransition({
          model,
          incumbent,
          challenger,
          startYear,
        });
        transitionCache.set(key, request);
        request.catch(() => transitionCache.delete(key));
      }
      return request;
    },
    loadModelComparison: (startYear = 1980) => {
      const key = `model-comparison:${startYear}`;
      let request = comparisonCache.get(key);
      if (!request) {
        request = fetchObservatoryModelComparison({ startYear });
        comparisonCache.set(key, request);
        request.catch(() => comparisonCache.delete(key));
      }
      return request;
    },
    requestRefresh: () => postObservatoryRefresh({ model: PRODUCTION_MODEL }),
    loadRefreshStatus: fetchObservatoryRefreshStatus,
  };
}

export function formatMeasureValue(value: number | null | undefined, unit: string): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (/^usd/i.test(unit)) {
    const magnitude = Math.abs(value);
    const sign = value < 0 ? "-" : "";
    return magnitude >= 1e12
      ? `${sign}$${(magnitude / 1e12).toFixed(1)}T`
      : magnitude >= 1e9
        ? `${sign}$${(magnitude / 1e9).toFixed(0)}B`
        : `${sign}$${(magnitude / 1e6).toFixed(0)}M`;
  }
  if (/%|pct|percent/i.test(unit)) {
    return `${value.toLocaleString("en-CH", { maximumFractionDigits: 1 })}%`;
  }
  return value.toLocaleString("en-CH", { maximumFractionDigits: 1 });
}
