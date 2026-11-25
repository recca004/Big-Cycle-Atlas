import {
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
  loadOverview: () => Promise<ObservatoryOverview>;
  loadTransition: (incumbent: string, challenger: string) => Promise<TransitionMonitor>;
  requestRefresh: () => Promise<RefreshJob>;
  loadRefreshStatus: () => Promise<RefreshJob>;
}

export const PRODUCTION_MODEL = "model_b_domain";

const overviewCache = new Map<string, Promise<ObservatoryOverview>>();
const transitionCache = new Map<string, Promise<TransitionMonitor>>();

export function invalidateObservatoryCaches(): void {
  overviewCache.clear();
  transitionCache.clear();
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
    loadOverview: () => {
      const key = `overview:${PRODUCTION_MODEL}`;
      let request = overviewCache.get(key);
      if (!request) {
        request = fetchObservatoryOverview({ model: PRODUCTION_MODEL });
        overviewCache.set(key, request);
        request.catch(() => overviewCache.delete(key));
      }
      return request;
    },
    loadTransition: (incumbent, challenger) => {
      const key = `transition:${PRODUCTION_MODEL}:${incumbent}:${challenger}`;
      let request = transitionCache.get(key);
      if (!request) {
        request = fetchObservatoryTransition({
          model: PRODUCTION_MODEL,
          incumbent,
          challenger,
        });
        transitionCache.set(key, request);
        request.catch(() => transitionCache.delete(key));
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
