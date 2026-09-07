import countriesData from "../data/initial-countries.json";

export interface CountryRef {
  iso3: string;
  iso2: string;
  name: string;
  region: string;
}

/** Canonical initial country set (DEC-004). Same file the backend seed reads. */
export const INITIAL_COUNTRIES: CountryRef[] = countriesData.countries;

export const BIG_CYCLE_PHASES = ["RISE", "PEAK", "DECLINE"] as const;
export type BigCyclePhase = (typeof BIG_CYCLE_PHASES)[number];

export const BIG_CYCLE_STAGES = [
  "EARLY_RISE",
  "RISE",
  "LATE_RISE",
  "PEAK",
  "LATE_PEAK",
  "EARLY_DECLINE",
  "DECLINE",
  "RESET",
] as const;
export type BigCycleStage = (typeof BIG_CYCLE_STAGES)[number];

export const TREND_VALUES = [
  "strongly rising",
  "rising",
  "stable",
  "falling",
  "strongly falling",
] as const;
export type TrendValue = (typeof TREND_VALUES)[number];

export const FORCES = [
  "leadership_capabilities",
  "education",
  "character_determination",
  "rule_of_law",
  "corruption",
  "resource_allocation_efficiency",
  "global_openness",
  "productivity_output_growth",
  "cost_competitiveness",
  "trade_capital_flows",
  "infrastructure_investment",
  "indebtedness",
  "military_strength",
  "wealth_opportunity_values_gaps",
  "internal_conflict",
  "geography",
  "acts_of_nature",
] as const;
export type ForceKey = (typeof FORCES)[number];