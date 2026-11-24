import { useEffect, useRef, useState } from "react";
import {
  fetchCountries,
  fetchCountryObservations,
  fetchForceCoverage,
  fetchDataSources,
  fetchIngestionRuns,
  fetchHealth,
  fetchIndicators,
} from "@/lib/api/client";
import type {
  Country,
  CountryObservation,
  ForceCoverageData,
  DataSource,
  IngestionRun,
  HealthStatus,
  Indicator,
} from "@/types/api";
import { INITIAL_COUNTRIES } from "@big-cycle-atlas/shared";

export type AsyncState<T> =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "ready"; data: T };

function useAsync<T>(
  fn: (signal: AbortSignal) => Promise<T>,
  deps: unknown[],
): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ kind: "loading" });
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading" });
    fnRef
      .current(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ kind: "ready", data });
      })
      .catch(() => {
        if (!controller.signal.aborted) setState({ kind: "error" });
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}

/** Static country list (canonical, no fetch needed). */
export function useCountryList(): Country[] {
  return INITIAL_COUNTRIES.map((c) => ({
    iso3: c.iso3,
    iso2: c.iso2,
    name: c.name,
    region: c.region,
  }));
}

export function useLiveCountries(): AsyncState<Country[]> {
  return useAsync((s) => fetchCountries({ signal: s }), []);
}

export function useObservations(
  iso3: string | undefined,
  indicator?: string,
  limit = 1000,
): AsyncState<CountryObservation[]> {
  return useAsync(
    (s) =>
      fetchCountryObservations(iso3!, { indicator, limit }, { signal: s }).then(
        (p) => p.items,
      ),
    [iso3, indicator, limit],
  );
}

export function useForceCoverage(
  iso3: string | undefined,
): AsyncState<ForceCoverageData> {
  return useAsync(
    (s) => fetchForceCoverage(iso3!, { signal: s }),
    [iso3],
  );
}

export function useDataSources(): AsyncState<DataSource[]> {
  return useAsync((s) => fetchDataSources({ signal: s }), []);
}

export function useIngestionRuns(): AsyncState<IngestionRun[]> {
  return useAsync((s) => fetchIngestionRuns({ signal: s }), []);
}

export function useHealth(): AsyncState<HealthStatus> {
  return useAsync((s) => fetchHealth({ signal: s }), []);
}

export function useIndicators(): AsyncState<Indicator[]> {
  return useAsync((s) => fetchIndicators({ signal: s }), []);
}

/** Fetch observations for several countries for one indicator. */
export function useMultiCountryObservations(
  iso3s: string[],
  indicator: string | undefined,
): AsyncState<Record<string, CountryObservation[]>> {
  const key = iso3s.join(",");
  return useAsync(
    async (s) => {
      const out: Record<string, CountryObservation[]> = {};
      await Promise.all(
        iso3s.map(async (iso3) => {
          const page = await fetchCountryObservations(
            iso3,
            { indicator, limit: 1000 },
            { signal: s },
          );
          out[iso3] = page.items;
        }),
      );
      return out;
    },
    [key, indicator],
  );
}
