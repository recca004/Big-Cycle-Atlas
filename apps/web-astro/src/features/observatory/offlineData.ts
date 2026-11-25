/** Isolated offline demonstration layer for the homepage observatory.
 *  Every value is synthetic, deterministic and local: no backend call,
 *  provider claim, forecast, countdown, or predictive claim. */

import type { ForceScore, ForceScoresResponse } from "@/types/api";
import type {
  DailyChanges,
  ObservatoryCountry,
  ObservatoryFreshness,
  ObservatoryHistoryPoint,
  ObservatoryOverview,
  RefreshJob,
  TransitionMeasurement,
  TransitionMonitor,
} from "@/types/observatory";
import { STAGES, type Stage } from "./stages";

export const DEMO_DISCLAIMER =
  "Offline demonstration data — synthetic observations for interface research only. No external backend, provider measurement, forecast, countdown, or predictive claim.";
export const DEMO_START_YEAR = 1950;
export const DEMO_END_YEAR = 2026;
export const OBSERVATION_PERIODS = Array.from(
  { length: DEMO_END_YEAR - DEMO_START_YEAR + 1 },
  (_, i) => String(DEMO_START_YEAR + i),
);

/* ---------- Eight power measures ---------- */

export const POWER_MEASURE_DEFINITIONS = [
  { key: "economic_output", label: "Economic output", shortLabel: "Output", unit: "usd_current", description: "Total annual production in current USD terms" },
  { key: "share_world_trade", label: "Share of world trade", shortLabel: "Trade", unit: "% of tracked trade", description: "Share of tracked imports and exports" },
  { key: "military_resources", label: "Military resources", shortLabel: "Military", unit: "usd_current", description: "Annual military expenditure in current USD terms" },
  { key: "innovation_output", label: "Innovation output", shortLabel: "Innovation", unit: "% of GDP", description: "Research and development intensity" },
  { key: "education_attainment", label: "Education attainment", shortLabel: "Education", unit: "% of adults", description: "Tertiary attainment proxy" },
  { key: "productivity_competitiveness", label: "Productivity & competitiveness", shortLabel: "Productivity", unit: "score", description: "Composite productivity demonstration index" },
  { key: "financial_center", label: "Financial-centre depth", shortLabel: "Finance", unit: "score", description: "Depth and international reach of capital markets" },
  { key: "reserve_currency_status", label: "Reserve-currency status", shortLabel: "Reserve", unit: "score", description: "International currency use in the demonstration layer" },
] as const;

export type PowerMeasureKey = (typeof POWER_MEASURE_DEFINITIONS)[number]["key"];
export interface OfflineMeasurePoint {
  current: number;
  previous: number;
  period: string;
  source: string;
}
export type OfflineMeasureProfile = Record<PowerMeasureKey, OfflineMeasurePoint>;

const point = (current: number, previous: number): OfflineMeasurePoint => ({
  current,
  previous,
  period: "2026 demo",
  source: "Offline demonstration fixture",
});
const profile = (values: Record<PowerMeasureKey, [number, number]>): OfflineMeasureProfile =>
  Object.fromEntries(
    POWER_MEASURE_DEFINITIONS.map((d) => [d.key, point(...values[d.key])]),
  ) as OfflineMeasureProfile;

export const OFFLINE_MEASURE_PROFILES: Record<string, OfflineMeasureProfile> = {
  USA: profile({ economic_output: [28.8e12, 28.3e12], share_world_trade: [10.8, 10.9], military_resources: [916e9, 895e9], innovation_output: [3.4, 3.4], education_attainment: [48, 47], productivity_competitiveness: [78, 78], financial_center: [92, 92], reserve_currency_status: [94, 94] }),
  CHN: profile({ economic_output: [18.5e12, 17.9e12], share_world_trade: [13.4, 13.1], military_resources: [296e9, 282e9], innovation_output: [2.6, 2.5], education_attainment: [36, 35], productivity_competitiveness: [58, 57], financial_center: [54, 52], reserve_currency_status: [35, 33] }),
  DEU: profile({ economic_output: [4.7e12, 4.65e12], share_world_trade: [7.2, 7.3], military_resources: [88e9, 79e9], innovation_output: [3.1, 3.1], education_attainment: [34, 34], productivity_competitiveness: [74, 75], financial_center: [58, 58], reserve_currency_status: [56, 56] }),
  JPN: profile({ economic_output: [4.2e12, 4.25e12], share_world_trade: [4.4, 4.5], military_resources: [57e9, 54e9], innovation_output: [3.3, 3.3], education_attainment: [52, 51], productivity_competitiveness: [67, 68], financial_center: [63, 63], reserve_currency_status: [58, 59] }),
  GBR: profile({ economic_output: [3.4e12, 3.35e12], share_world_trade: [4.1, 4.2], military_resources: [74e9, 70e9], innovation_output: [2.9, 2.9], education_attainment: [46, 45], productivity_competitiveness: [65, 66], financial_center: [82, 82], reserve_currency_status: [65, 66] }),
  FRA: profile({ economic_output: [3.1e12, 3.08e12], share_world_trade: [3.8, 3.9], military_resources: [62e9, 59e9], innovation_output: [2.2, 2.2], education_attainment: [41, 40], productivity_competitiveness: [70, 70], financial_center: [57, 57], reserve_currency_status: [55, 55] }),
  IND: profile({ economic_output: [3.9e12, 3.65e12], share_world_trade: [4.8, 4.6], military_resources: [82e9, 77e9], innovation_output: [0.7, 0.7], education_attainment: [22, 21], productivity_competitiveness: [36, 35], financial_center: [34, 33], reserve_currency_status: [18, 17] }),
  CHE: profile({ economic_output: [0.94e12, 0.92e12], share_world_trade: [2.1, 2.1], military_resources: [7.5e9, 7.1e9], innovation_output: [3.4, 3.4], education_attainment: [50, 49], productivity_competitiveness: [83, 83], financial_center: [72, 72], reserve_currency_status: [52, 52] }),
};

export function formatMeasureValue(value: number, unit: string): string {
  if (/^usd/i.test(unit)) {
    const magnitude = Math.abs(value);
    const sign = value < 0 ? "-" : "";
    return magnitude >= 1e12
      ? `${sign}$${(magnitude / 1e12).toFixed(1)}T`
      : magnitude >= 1e9
        ? `${sign}$${(magnitude / 1e9).toFixed(0)}B`
        : `${sign}$${(magnitude / 1e6).toFixed(0)}M`;
  }
  if (/%/.test(unit)) return `${value.toLocaleString("en-CH", { maximumFractionDigits: 1 })}%`;
  return value.toLocaleString("en-CH", { maximumFractionDigits: 1 });
}

/* ---------- Seventeen forces ---------- */

export const FORCE_CATALOG = [
  { code: "leadership_capabilities", name: "Leadership capabilities" },
  { code: "education", name: "Education" },
  { code: "character_determination", name: "Character / determination" },
  { code: "rule_of_law", name: "Rule of law" },
  { code: "corruption", name: "Corruption" },
  { code: "resource_allocation_efficiency", name: "Resource allocation efficiency" },
  { code: "global_openness", name: "Global openness" },
  { code: "productivity_output_growth", name: "Productivity / output growth" },
  { code: "cost_competitiveness", name: "Cost competitiveness" },
  { code: "trade_capital_flows", name: "Trade and capital flows" },
  { code: "infrastructure_investment", name: "Infrastructure and investment" },
  { code: "indebtedness", name: "Indebtedness" },
  { code: "military_strength", name: "Military strength" },
  { code: "wealth_opportunity_values_gaps", name: "Wealth / opportunity / values gaps" },
  { code: "internal_conflict", name: "Internal conflict" },
  { code: "geography", name: "Geography" },
  { code: "acts_of_nature", name: "Acts of nature" },
] as const;

const FORCE_LEVELS: Record<string, number[]> = {
  USA: [74, 48, 63, 76, 72, 69, 58, 72, 52, 67, 76, 38, 92, 42, 48, 78, 64],
  CHN: [68, 36, 78, 49, 44, 73, 65, 76, 71, 82, 88, 54, 78, 51, 62, 69, 58],
  DEU: [79, 34, 61, 82, 81, 72, 82, 74, 48, 74, 71, 62, 42, 66, 74, 72, 66],
  JPN: [76, 52, 68, 81, 78, 70, 62, 69, 45, 58, 78, 35, 48, 63, 77, 65, 52],
  GBR: [78, 46, 60, 84, 83, 66, 76, 64, 44, 70, 63, 42, 58, 58, 68, 74, 62],
  FRA: [75, 41, 58, 80, 76, 68, 72, 70, 47, 68, 70, 45, 61, 61, 64, 71, 60],
  IND: [55, 22, 82, 42, 38, 66, 69, 72, 82, 61, 57, 68, 66, 35, 45, 59, 55],
  CHE: [88, 50, 66, 91, 90, 78, 86, 82, 38, 72, 76, 84, 28, 78, 86, 81, 70],
};
const SCORED_INDEXES = new Set([0, 1, 3, 4, 7, 11, 12]);
const DIMENSION_INDEXES = new Set([2, 5, 9, 13, 14]);

export function buildOfflineForceScores(iso3: string): ForceScoresResponse {
  const levels = FORCE_LEVELS[iso3] ?? FORCE_LEVELS.USA!;
  const forces: ForceScore[] = FORCE_CATALOG.map((force, index) => {
    const level = levels[index] ?? 50;
    const scored = SCORED_INDEXES.has(index);
    const dimension = DIMENSION_INDEXES.has(index);
    const status: ForceScore["execution_status"] = scored ? "scored" : dimension ? "dimension_only" : "context";
    return {
      force_code: force.code,
      force_name: force.name,
      execution_status: status,
      level_score: scored ? level : null,
      relative_score: dimension || scored ? level : null,
      momentum_score: ((iso3.charCodeAt(0) + index * 7) % 9) - 4,
      confidence: scored ? 0.58 : dimension ? 0.34 : null,
      coverage_status: scored || dimension ? "partial" : "defined_not_sourced",
      period: "2026 demo",
      model_version: "offline-demo-v1",
      limitations: ["Synthetic demonstration value; not an observed provider measurement"],
      reasons: ["offline demonstration layer"],
      backtest_safe: false,
      comparison_semantics: scored ? "comparable" : dimension ? "own_history" : "not_scored",
    };
  });
  return { country: iso3, normalization_version: "offline-demo-normalization", force_aggregation_version: "offline-demo-forces", forces };
}

/* ---------- Country histories, 1950–2026 ---------- */

interface StageEra { from: number; to: number; stage: Stage; phase: string }
interface DemoCountrySpec {
  iso3: string; name: string; region: string; latitude: number; longitude: number;
  domestic2026: number; coverage: number; eras: StageEra[];
}
const era = (from: number, to: number, stage: Stage, phase: string): StageEra => ({ from, to, stage, phase });

const DEMO_COUNTRY_SPECS: DemoCountrySpec[] = [
  { iso3: "USA", name: "United States", region: "North America", latitude: 39, longitude: -98, domestic2026: 67.5, coverage: 0.86, eras: [era(1950, 1963, "PEAK", "post-war consolidation"), era(1964, 1975, "LATE_PEAK", "institutional strain"), era(1976, 1982, "EARLY_DECLINE", "adjustment"), era(1983, 1999, "RISE", "renewal demonstration"), era(2000, 2007, "LATE_PEAK", "financial expansion"), era(2008, 2016, "EARLY_DECLINE", "balance-sheet stress"), era(2017, 2026, "LATE_PEAK", "contested primacy")] },
  { iso3: "CHN", name: "China", region: "East Asia", latitude: 35, longitude: 104, domestic2026: 63.8, coverage: 0.78, eras: [era(1950, 1957, "RESET", "state formation"), era(1958, 1977, "EARLY_RISE", "mobilisation"), era(1978, 1999, "RISE", "opening demonstration"), era(2000, 2026, "LATE_RISE", "scale and constraint")] },
  { iso3: "DEU", name: "Germany", region: "Europe", latitude: 51, longitude: 10, domestic2026: 61.7, coverage: 0.84, eras: [era(1950, 1966, "EARLY_RISE", "reconstruction"), era(1967, 1989, "RISE", "export consolidation"), era(1990, 2004, "PEAK", "reunification adjustment"), era(2005, 2018, "LATE_PEAK", "industrial surplus"), era(2019, 2026, "EARLY_DECLINE", "energy and investment pressure")] },
  { iso3: "JPN", name: "Japan", region: "East Asia", latitude: 36, longitude: 138, domestic2026: 58.2, coverage: 0.83, eras: [era(1950, 1969, "EARLY_RISE", "reconstruction"), era(1970, 1989, "RISE", "industrial ascent"), era(1990, 1994, "PEAK", "asset-cycle crest"), era(1995, 2012, "LATE_PEAK", "balance-sheet adjustment"), era(2013, 2026, "EARLY_DECLINE", "demographic constraint")] },
  { iso3: "GBR", name: "United Kingdom", region: "Europe", latitude: 54, longitude: -2, domestic2026: 56.1, coverage: 0.85, eras: [era(1950, 1964, "LATE_PEAK", "post-imperial adjustment"), era(1965, 1979, "EARLY_DECLINE", "industrial stress"), era(1980, 1999, "RESET", "structural reset"), era(2000, 2007, "LATE_PEAK", "financial expansion"), era(2008, 2026, "DECLINE", "productivity and cohesion strain")] },
  { iso3: "FRA", name: "France", region: "Europe", latitude: 47, longitude: 2, domestic2026: 57.4, coverage: 0.84, eras: [era(1950, 1973, "RISE", "trente glorieuses demonstration"), era(1974, 1994, "LATE_PEAK", "welfare-state consolidation"), era(1995, 2011, "PEAK", "European integration"), era(2012, 2026, "EARLY_DECLINE", "fiscal and cohesion pressure")] },
  { iso3: "IND", name: "India", region: "South Asia", latitude: 21, longitude: 78, domestic2026: 55.9, coverage: 0.72, eras: [era(1950, 1965, "RESET", "state formation"), era(1966, 1990, "EARLY_RISE", "institutional build-out"), era(1991, 2026, "RISE", "liberalisation and scale-up demonstration")] },
  { iso3: "CHE", name: "Switzerland", region: "Europe", latitude: 47, longitude: 8, domestic2026: 82.6, coverage: 0.88, eras: [era(1950, 1979, "RISE", "institutional consolidation"), era(1980, 2007, "PEAK", "financial and industrial strength"), era(2008, 2026, "LATE_PEAK", "high-condition plateau")] },
];

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const eraForYear = (spec: DemoCountrySpec, year: number) =>
  spec.eras.find((entry) => year >= entry.from && year <= entry.to) ?? spec.eras[spec.eras.length - 1]!;

function buildHistory(spec: DemoCountrySpec, countryIndex: number): ObservatoryHistoryPoint[] {
  let previousScore: number | null = null;
  return OBSERVATION_PERIODS.map((period) => {
    const year = Number(period);
    const currentEra = eraForYear(spec, year);
    const eraLength = Math.max(1, currentEra.to - currentEra.from + 1);
    const score = clamp(
      spec.domestic2026 + (year - DEMO_END_YEAR) * 0.11 + Math.sin((year + countryIndex * 7) * 0.53) * 1.35 + ((year - currentEra.from) / eraLength) * 1.1,
      18,
      94,
    );
    const momentum = previousScore === null ? 0 : score - previousScore;
    previousScore = score;
    return { period, score: Number(score.toFixed(2)), momentum: Number(momentum.toFixed(2)), stage: currentEra.stage, phase: currentEra.phase, reason: "offline demonstration classification" };
  });
}

function transitionsFromHistory(history: ObservatoryHistoryPoint[]) {
  const transitions: { period: string; to: string; reason: string }[] = [];
  for (let i = 1; i < history.length; i++) {
    const previous = history[i - 1], current = history[i];
    if (previous?.stage && current?.stage && previous.stage !== current.stage)
      transitions.push({ period: current.period, to: current.stage, reason: current.reason ?? "offline demonstration classification" });
  }
  return transitions;
}

function forceSummaryFor(iso3: string) {
  const response = buildOfflineForceScores(iso3);
  return {
    scored_count: response.forces.filter((force) => force.execution_status === "scored").length,
    dimension_only_count: response.forces.filter((force) => force.execution_status === "dimension_only").length,
    context_only_count: response.forces.filter((force) => force.execution_status === "context").length,
    top_forces: response.forces.slice(0, 5).map((force) => ({ force_code: force.force_code, force_name: force.force_name, execution_status: force.execution_status, level_score: force.level_score, relative_score: force.relative_score, momentum_score: force.momentum_score })),
    forces: response.forces.map((force) => ({ force_code: force.force_code, force_name: force.force_name, execution_status: force.execution_status, level_score: force.level_score, relative_score: force.relative_score, momentum_score: force.momentum_score, coverage_status: force.coverage_status, period: force.period })),
  };
}

function buildCountries(): ObservatoryCountry[] {
  const countries = DEMO_COUNTRY_SPECS.map((spec, countryIndex) => {
    const history = buildHistory(spec, countryIndex);
    const latest = history[history.length - 1]!;
    const transitions = transitionsFromHistory(history);
    const measures = OFFLINE_MEASURE_PROFILES[spec.iso3]!;
    const military = measures.military_resources.current;
    const gdp = measures.economic_output.current;
    return {
      iso3: spec.iso3, name: spec.name, region: spec.region, stage: latest.stage, phase: latest.phase,
      domestic_condition_score: latest.score, score: latest.score, momentum: latest.momentum, coverage_ratio: spec.coverage,
      period: latest.period, direction: (latest.momentum ?? 0) >= 0 ? "improving" : "softening", classified: true,
      recent_transition: transitions[transitions.length - 1] ?? null, transitions, history, force_summary: forceSummaryFor(spec.iso3),
      international_power: {
        economic_size: { value_usd: gdp, tracked_share_pct: (gdp / 67.58e12) * 100, period: "2026 demo", source: "Offline demonstration fixture" },
        military_resources: { expenditure_usd: military, tracked_share_pct: (military / 1.5925e12) * 100, pct_gdp: (military / gdp) * 100, period: "2026 demo", source: "Offline demonstration fixture" },
      },
      indicator_snapshots: {
        GDP_CURRENT_USD: { latest: { year: 2026, period: "2026 demo", value: gdp, vintage: 1, source: "Offline demonstration fixture" } },
        MILITARY_EXPENDITURE_USD: { latest: { year: 2026, period: "2026 demo", value: military, vintage: 1, source: "Offline demonstration fixture" } },
        GOVERNMENT_DEBT_GDP: { latest: { year: 2026, period: "2026 demo", value: ({ USA: 121, CHN: 83, DEU: 63, JPN: 236, GBR: 101, FRA: 112, IND: 82, CHE: 38 } as Record<string, number>)[spec.iso3] ?? 70, vintage: 1, source: "Offline demonstration fixture" } },
      },
      domestic_condition_rank: null as number | null,
    } satisfies ObservatoryCountry;
  });
  const ranked = [...countries].sort((a, b) => (b.domestic_condition_score ?? 0) - (a.domestic_condition_score ?? 0));
  for (const country of countries) country.domestic_condition_rank = ranked.findIndex((entry) => entry.iso3 === country.iso3) + 1;
  return countries;
}

/* ---------- Freshness and simulated daily comparisons ---------- */

const baseFreshness: ObservatoryFreshness = {
  status: "updated", status_label: "Simulated snapshot current",
  latest_collection_at: "2026-11-25T04:30:00Z", latest_collection_zurich: "2026-11-25 05:30 CET",
  latest_calculation_at: "2026-11-25T04:42:00Z", latest_calculation_zurich: "2026-11-25 05:42 CET",
  latest_observation_period: "2026 demo", scoring_period: "2026 demo", timezone: "Europe/Zurich",
  new_observations_count: 18, revisions_count: 4, changed_classifications_count: 1,
  provider_failures: [], total_observations: 612, total_revisions: 29,
};
const baseDailyChanges: DailyChanges = {
  has_previous_snapshot: true,
  previous_snapshot_at: "2026-11-24T04:30:00Z", previous_snapshot_zurich: "2026-11-24 05:30 CET",
  current_snapshot_at: "2026-11-25T04:30:00Z", current_snapshot_zurich: "2026-11-25 05:30 CET",
  summary_message: "18 simulated observations changed across 5 demonstration series.",
  changes: [
    { kind: "observation", iso3: "CHN", country_name: "China", measurement: "Economic output", previous: 17.9e12, current: 18.5e12, difference: 0.6e12, period: "2026 demo", source: "Offline demonstration fixture" },
    { kind: "revision", iso3: "IND", country_name: "India", measurement: "Share of world trade", previous: 4.6, current: 4.8, difference: 0.2, period: "2026 demo", source: "Offline demonstration fixture" },
    { kind: "classification", iso3: "JPN", country_name: "Japan", measurement: "Cycle stage", previous: "Late peak", current: "Early decline", difference: null, period: "2026 demo", source: "Offline demonstration fixture" },
    { kind: "observation", iso3: "USA", country_name: "United States", measurement: "Military resources", previous: 895e9, current: 916e9, difference: 21e9, period: "2026 demo", source: "Offline demonstration fixture" },
  ],
};

export interface OfflineRefreshScenario { freshness: ObservatoryFreshness; dailyChanges: DailyChanges; job: RefreshJob }
const refreshScenarios: OfflineRefreshScenario[] = [
  { freshness: baseFreshness, dailyChanges: baseDailyChanges, job: { running: false, mode: "offline-demo", started_at: null, completed_at: "2026-11-25T04:42:00Z", current_provider: null, completed_steps: 5, total_steps: 5, inserted: 18, revised: 4, failed: 0, status: "succeeded", error: null } },
  { freshness: { ...baseFreshness, latest_collection_zurich: "2026-11-25 06:10 CET", latest_calculation_zurich: "2026-11-25 06:18 CET", new_observations_count: 7, revisions_count: 2, changed_classifications_count: 0 },
    dailyChanges: { ...baseDailyChanges, previous_snapshot_zurich: "2026-11-25 05:30 CET", current_snapshot_zurich: "2026-11-25 06:10 CET", summary_message: "7 simulated observations changed; no classification moved.", changes: [
      { kind: "observation", iso3: "DEU", country_name: "Germany", measurement: "Innovation output", previous: 3.0, current: 3.1, difference: 0.1, period: "2026 demo", source: "Offline demonstration fixture" },
      { kind: "revision", iso3: "CHE", country_name: "Switzerland", measurement: "Education attainment", previous: 49, current: 50, difference: 1, period: "2026 demo", source: "Offline demonstration fixture" },
    ] },
    job: { running: false, mode: "offline-demo", started_at: "2026-11-25T05:10:00Z", completed_at: "2026-11-25T05:18:00Z", current_provider: null, completed_steps: 5, total_steps: 5, inserted: 7, revised: 2, failed: 0, status: "succeeded", error: null } },
  { freshness: { ...baseFreshness, status: "no_new_observations", status_label: "No new simulated observations", latest_collection_zurich: "2026-11-25 06:40 CET", latest_calculation_zurich: "2026-11-25 06:44 CET", new_observations_count: 0, revisions_count: 1, changed_classifications_count: 0 },
    dailyChanges: { ...baseDailyChanges, previous_snapshot_zurich: "2026-11-25 06:10 CET", current_snapshot_zurich: "2026-11-25 06:40 CET", summary_message: "No new simulated observations; one prior series was revised.", changes: [
      { kind: "revision", iso3: "GBR", country_name: "United Kingdom", measurement: "Productivity & competitiveness", previous: 66, current: 65, difference: -1, period: "2026 demo", source: "Offline demonstration fixture" },
    ] },
    job: { running: false, mode: "offline-demo", started_at: "2026-11-25T05:40:00Z", completed_at: "2026-11-25T05:44:00Z", current_provider: null, completed_steps: 5, total_steps: 5, inserted: 0, revised: 1, failed: 0, status: "succeeded", error: null } },
];

export const offlineRefreshScenario = (step: number): OfflineRefreshScenario => refreshScenarios[step % refreshScenarios.length]!;
export const runningOfflineRefreshJob = (): RefreshJob => ({
  running: true, mode: "offline-demo", started_at: "2026-11-25T05:00:00Z", completed_at: null,
  current_provider: "offline demonstration simulator", completed_steps: 2, total_steps: 5,
  inserted: 0, revised: 0, failed: 0, status: "running", error: null,
});

/* ---------- Offline transition diagnostics ---------- */

function transitionMeasurement(incumbentIso3: string, challengerIso3: string, key: PowerMeasureKey): TransitionMeasurement {
  const definition = POWER_MEASURE_DEFINITIONS.find((entry) => entry.key === key)!;
  const incumbent = OFFLINE_MEASURE_PROFILES[incumbentIso3]![key];
  const challenger = OFFLINE_MEASURE_PROFILES[challengerIso3]![key];
  const ratio = incumbent.current === 0 ? null : challenger.current / incumbent.current;
  const previousRatio = incumbent.previous === 0 ? null : challenger.previous / incumbent.previous;
  let relationship: TransitionMeasurement["relationship"] = "insufficient_data";
  let trendNote: string | null = null;
  if (ratio !== null && previousRatio !== null) {
    const delta = Math.abs(1 - previousRatio) - Math.abs(1 - ratio);
    relationship = delta > 0.015 ? "convergence" : delta < -0.015 ? "divergence" : "stable";
    trendNote = `demonstration ratio moved from ${(previousRatio * 100).toFixed(0)}% to ${(ratio * 100).toFixed(0)}% of the incumbent`;
  }
  return {
    key, label: definition.label, category: "power measure", unit: definition.unit,
    incumbent_value: incumbent.current, challenger_value: challenger.current,
    challenger_to_incumbent_ratio: ratio, absolute_gap: incumbent.current - challenger.current,
    direction: ratio !== null && previousRatio !== null ? (ratio > previousRatio ? "challenger rising" : ratio < previousRatio ? "challenger softening" : "stable") : "unknown",
    relationship, trend_note: trendNote, period: "2026 demo", source: "Offline demonstration fixture",
  };
}

export function buildOfflineTransition(incumbentIso3: string, challengerIso3: string): TransitionMonitor {
  const incumbent = offlineCountries.find((country) => country.iso3 === incumbentIso3) ?? offlineCountries[0]!;
  const challenger = offlineCountries.find((country) => country.iso3 === challengerIso3) ?? offlineCountries[1]!;
  const measurements = POWER_MEASURE_DEFINITIONS.map((definition) => transitionMeasurement(incumbent.iso3, challenger.iso3, definition.key));
  return {
    incumbent_iso3: incumbent.iso3, incumbent_name: incumbent.name, incumbent_stage: incumbent.stage, incumbent_direction: incumbent.direction,
    challenger_iso3: challenger.iso3, challenger_name: challenger.name, challenger_stage: challenger.stage, challenger_direction: challenger.direction,
    measurements,
    areas_of_convergence: measurements.filter((m) => m.relationship === "convergence"),
    areas_of_divergence: measurements.filter((m) => m.relationship === "divergence"),
    historical_evidence: {
      incumbent_transitions: incumbent.transitions.map((t) => ({ period: t.period, from: "previous demonstration stage", to: t.to, reason: t.reason })),
      challenger_transitions: challenger.transitions.map((t) => ({ period: t.period, from: "previous demonstration stage", to: t.to, reason: t.reason })),
    },
    forecast_readiness: {
      methodology_status: "offline demonstration — predictive output disabled",
      overall_available: false,
      estimated_transition_window: "No window issued — offline evidence demonstration",
      blockers: ["offline fixture has no provider provenance", "predictive claims are explicitly disabled", "demonstration diagnostics are descriptive only"],
      total_scored_periods: OBSERVATION_PERIODS.length,
      total_genuine_transitions: incumbent.transitions.length + challenger.transitions.length,
      strict_eligible_periods: 0,
      horizons: [
        { horizon: "1y", horizon_label: "1 year", horizon_quarters: 4, available: false, status_label: "disabled in offline demonstration", blockers: ["no predictive layer"] },
        { horizon: "5y", horizon_label: "5 years", horizon_quarters: 20, available: false, status_label: "disabled in offline demonstration", blockers: ["no predictive layer"] },
      ],
    },
  };
}

/* ---------- Overview assembly ---------- */

export const offlineCountries = buildCountries();
const largestEconomy = [...offlineCountries].sort((a, b) => (b.international_power.economic_size?.value_usd ?? 0) - (a.international_power.economic_size?.value_usd ?? 0));

export function createOfflineOverview(): ObservatoryOverview {
  return {
    methodology_status: "offline demonstration — no predictive claims",
    normalization_version: "offline-demo-normalization-v1",
    model: { model_id: "offline_observatory_demo", model_version: "offline-demo-v1", available_models: [{ model_id: "offline_observatory_demo", model_version: "offline-demo-v1", kind: "demonstration", notes: DEMO_DISCLAIMER }] },
    scoring_period: "2026 demo",
    available_periods: OBSERVATION_PERIODS,
    countries: offlineCountries,
    power_summary: {
      largest_economy_iso3: largestEconomy[0]?.iso3 ?? "USA",
      second_economy_iso3: largestEconomy[1]?.iso3 ?? "CHN",
      highest_domestic_condition_iso3: [...offlineCountries].sort((a, b) => (b.domestic_condition_score ?? 0) - (a.domestic_condition_score ?? 0))[0]?.iso3 ?? "CHE",
      separation_note: "Domestic condition and international power are deliberately separated: internal cohesion, productivity and governance are not the same thing as external scale, finance or military resources.",
    },
    transition_monitor: buildOfflineTransition("USA", "CHN"),
    freshness: baseFreshness,
    daily_changes: baseDailyChanges,
    refresh_job: refreshScenarios[0]!.job,
  };
}

export const OFFLINE_STAGE_ORDER = STAGES;
