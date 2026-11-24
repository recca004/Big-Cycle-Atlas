import {
  formatDecimal,
  formatPercent,
  formatUsdCompact,
  formatUsdWhole,
} from "@/lib/format";

export type ValueFormat =
  | "percent"
  | "decimal"
  | "usd-compact"
  | "usd-whole"
  | "share-percent"
  | "score";

export function formatValue(format: ValueFormat, value: number): string {
  switch (format) {
    case "percent":
      return formatPercent(value);
    case "decimal":
      return formatDecimal(value);
    case "usd-compact":
      return formatUsdCompact(value);
    case "usd-whole":
      return formatUsdWhole(value);
    case "share-percent":
      return formatPercent(value * 100);
    case "score":
      return `${formatDecimal(value)} / 100`;
  }
}

export interface IndicatorMeta {
  label: string;
  format: ValueFormat;
  unit?: string;
}

export const INDICATOR_META: Record<string, IndicatorMeta> = {
  GDP_GROWTH: { label: "GDP growth", format: "percent", unit: "annual %" },
  GDP_CURRENT_USD: { label: "GDP", format: "usd-compact", unit: "current US$" },
  GDP_PER_CAPITA: {
    label: "GDP per capita",
    format: "usd-whole",
    unit: "current US$",
  },
  EXPORTS_GDP: { label: "Exports", format: "percent", unit: "% of GDP" },
  IMPORTS_GDP: { label: "Imports", format: "percent", unit: "% of GDP" },
  TRADE_BALANCE: {
    label: "Trade balance",
    format: "percent",
    unit: "% of GDP",
  },
  CURRENT_ACCOUNT_GDP: {
    label: "Current account",
    format: "percent",
    unit: "% of GDP",
  },
  GROSS_CAPITAL_FORMATION_GDP: {
    label: "Gross capital formation",
    format: "percent",
    unit: "% of GDP",
  },
  GINI_INDEX: { label: "Gini index", format: "decimal", unit: "index 0–100" },
  INFLATION_CPI: { label: "Inflation (CPI)", format: "percent", unit: "annual %" },
  MILITARY_EXPENDITURE_USD: {
    label: "Military expenditure",
    format: "usd-compact",
    unit: "current US$",
  },
  MILITARY_EXPENDITURE_GDP: {
    label: "Military expenditure (% GDP)",
    format: "percent",
    unit: "% of GDP",
  },
  RULE_OF_LAW_WGI_SCORE: {
    label: "Rule of law",
    format: "score",
    unit: "WGI 0–100",
  },
  CONTROL_OF_CORRUPTION_WGI_SCORE: {
    label: "Control of corruption",
    format: "score",
    unit: "WGI 0–100",
  },
  POLITICAL_STABILITY_WGI_SCORE: {
    label: "Political stability",
    format: "score",
    unit: "WGI 0–100",
  },
  CREDIT_TO_GDP_GAP: {
    label: "Credit-to-GDP gap",
    format: "decimal",
    unit: "% of GDP",
  },
  DEBT_SERVICE_RATIO: {
    label: "Debt service ratio",
    format: "percent",
    unit: "per cent",
  },
  LABOUR_PRODUCTIVITY_PER_HOUR: {
    label: "Labour productivity",
    format: "decimal",
    unit: "USD PPP/hour",
  },
  UNIT_LABOUR_COST_GROWTH: {
    label: "Unit labour cost growth",
    format: "percent",
    unit: "% p.a.",
  },
  GOVERNMENT_DEBT_GDP: {
    label: "Government debt",
    format: "percent",
    unit: "% of GDP",
  },
  TERTIARY_ATTAINMENT_25_34: {
    label: "Tertiary attainment (25–34)",
    format: "percent",
    unit: "% of cohort",
  },
  WEALTH_SHARE_TOP_10: {
    label: "Top 10% wealth share",
    format: "share-percent",
    unit: "share of net wealth",
  },
  POPULATION: { label: "Population", format: "decimal" },
  RND_EXPENDITURE_GDP: {
    label: "R&D expenditure",
    format: "percent",
    unit: "% of GDP",
  },
  SECONDARY_ENROLLMENT: {
    label: "Secondary enrollment",
    format: "percent",
  },
  TERTIARY_ENROLLMENT: { label: "Tertiary enrollment", format: "percent" },
  UNEMPLOYMENT_RATE: { label: "Unemployment", format: "percent" },
};

export function indicatorLabel(code: string): string {
  return INDICATOR_META[code]?.label ?? code;
}

export function indicatorFormat(code: string): ValueFormat {
  return INDICATOR_META[code]?.format ?? "decimal";
}
