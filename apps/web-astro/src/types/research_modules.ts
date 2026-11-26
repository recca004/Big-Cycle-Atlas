export interface SeriesMeta {
  label: string;
  unit: string;
  source: { source_key: string; dataset_version: string; publisher: string };
  frequency: string;
  derived_estimate: boolean;
  methodology?: string | null;
}

export interface NamedSeries {
  meta: SeriesMeta;
  points: [string, number][];
}

export interface CrisisMarker {
  year: number;
  event_type: string;
  source_key: string;
  dataset_version: string;
}

export interface DebtCycleOverview {
  module: string;
  entities: string[];
  entity_coverage_notes: Record<string, string>;
  sections: {
    sectoral_credit: Record<string, Record<string, NamedSeries>>;
    monetary_conditions: Record<string, Record<string, NamedSeries>>;
    fiscal_conditions: Record<string, Record<string, NamedSeries>>;
  };
  crisis_overlay: Record<string, CrisisMarker[]>;
  methodology: string[];
  sources: Record<string, unknown>;
  generated_at: string;
}

export interface CurrencyPowerOverview {
  module: string;
  reserve_currency_shares: {
    share_pct: Record<string, NamedSeries>;
    imputed_share_pct: Record<string, NamedSeries>;
    claims_usd: Record<string, NamedSeries>;
  };
  fx_turnover_shares: {
    share_200pct: Record<string, NamedSeries>;
    daily_usd_mn: Record<string, NamedSeries>;
  };
  banking_claims_by_currency: {
    share_pct: Record<string, NamedSeries>;
    usd_mn: Record<string, NamedSeries>;
  };
  financial_centres: {
    share_pct: Record<string, NamedSeries>;
    usd_mn: Record<string, NamedSeries>;
  };
  methodology: string[];
  historical_currency_support: string[];
  generated_at: string;
}

export interface HistoricalPowerOverview {
  module: string;
  maddison: Record<string, {
    gdppc_2011intl: NamedSeries;
    pop_thousands: NamedSeries;
    gdp_level_mn_2011intl: NamedSeries;
  }>;
  panel_share_pct_of_20_entities: Record<string, [string, number][]>;
  pwt_productivity: Record<string, Record<string, NamedSeries>>;
  research_periods: number[];
  entity_definition_notes: Record<string, string>;
  methodology: string[];
  generated_at: string;
}
