import { useEffect, useState } from "react";

export const COUNTRIES = [
  "USA", "CHN", "JPN", "DEU", "FRA", "GBR", "CHE", "IND",
] as const;

export const FORCE_CODES = [
  "rule_of_law", "corruption", "leadership_capabilities",
  "internal_conflict", "education", "productivity_output_growth",
  "indebtedness", "wealth_opportunity_values_gaps",
  "character_determination", "military_strength",
  "cost_competitiveness", "trade_capital_flows", "global_openness",
  "infrastructure_investment", "resource_allocation_efficiency",
  "geography", "acts_of_nature",
] as const;

export type FetchState<T> =
  | { kind: "loading" }
  | { kind: "ready"; data: T }
  | { kind: "error"; error: string };

/** Abortable fetch hook — stale requests are cancelled on dep change. */
export function useFetch<T>(
  fn: (c: AbortController) => Promise<T>,
  deps: unknown[],
): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({ kind: "loading" });
  useEffect(() => {
    const c = new AbortController();
    setState({ kind: "loading" });
    fn(c)
      .then((data) => setState({ kind: "ready", data }))
      .catch((e) => {
        if (!c.signal.aborted)
          setState({ kind: "error", error: String(e) });
      });
    return () => c.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

export function Badge({
  children, tone,
}: { children: React.ReactNode; tone?: string }) {
  return <span className={`badge badge-${tone ?? "muted"}`}>{children}</span>;
}
