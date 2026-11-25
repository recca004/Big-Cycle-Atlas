/** Registers every widget type. Import once (side effect) before rendering
 *  a workspace or the widget library. */

import {
  CycleHistoryWidget,
  ForceHistoryWidget,
} from "./ResearchWidgets";
import {
  registerWidget,
  type WidgetDefinition,
  type ConfigField,
  type WidgetCategory,
} from "@/features/workspace/widgetRegistry";
import { MetricWidget } from "./MetricWidget";
import { IndicatorChartWidget } from "./IndicatorChartWidget";
import { DataTableWidget } from "./DataTableWidget";
import { RankingWidget } from "./RankingWidget";
import {
  ForceScoreWidget,
  AllForcesWidget,
  ForceCoverageWidget,
} from "./ForceWidgets";
import {
  ApiStatusWidget,
  SourceStatusWidget,
  IngestionStatusWidget,
  ModelVersionWidget,
  ResearchProgressWidget,
  CoverageMatrixWidget,
} from "./StatusWidgets";
import { UnavailableWidget } from "./UnavailableWidget";
import { BigCycleClockWidget } from "@/features/observatory/BigCycleClockWidget";
import { HistoricalValidationWidget } from "./HistoricalValidationWidget";
import { UncertaintyBandWidget } from "./UncertaintyBand";
import { INDICATOR_META } from "./indicatorMeta";
import { INITIAL_COUNTRIES, FORCES } from "@big-cycle-atlas/shared";
import { getDefaultCountry } from "@/lib/prefs";

const COUNTRY_OPTIONS = INITIAL_COUNTRIES.map((c) => ({
  value: c.iso3,
  label: c.name,
}));

const INDICATOR_OPTIONS = Object.entries(INDICATOR_META).map(
  ([value, meta]) => ({ value, label: meta.label }),
);

const FORCE_OPTIONS = FORCES.map((f) => ({
  value: f,
  label: f.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()),
}));

const countryField: ConfigField = {
  key: "country",
  label: "Country",
  type: "country",
  default: getDefaultCountry(),
  options: COUNTRY_OPTIONS,
};

const countriesField: ConfigField = {
  key: "countries",
  label: "Countries",
  type: "countries",
  default: ["USA"],
  options: COUNTRY_OPTIONS,
};

const indicatorField: ConfigField = {
  key: "indicator",
  label: "Indicator",
  type: "indicator",
  default: "GDP_GROWTH",
  options: INDICATOR_OPTIONS,
};

const forceField: ConfigField = {
  key: "force",
  label: "Force",
  type: "force",
  default: "rule_of_law",
  options: FORCE_OPTIONS,
};

const chartTypeField: ConfigField = {
  key: "chartType",
  label: "Chart type",
  type: "chart-type",
  default: "line",
  options: [
    { value: "line", label: "Line" },
    { value: "area", label: "Area" },
    { value: "bar", label: "Bar" },
  ],
};

const legendField: ConfigField = {
  key: "showLegend",
  label: "Show legend",
  type: "boolean",
  default: true,
};

const titleField: ConfigField = {
  key: "title",
  label: "Display title",
  type: "text",
};

function metricDef(
  typeId: string,
  displayName: string,
  indicator: string,
  category: WidgetCategory,
): WidgetDefinition {
  return {
    typeId,
    displayName,
    description: `Latest ${INDICATOR_META[indicator]?.label ?? indicator} value for a country.`,
    category,
    defaultSize: { w: 3, h: 3 },
    minSize: { w: 2, h: 2 },
    configFields: [
      { ...countryField },
      { ...indicatorField, default: indicator },
      titleField,
    ],
    dataRequirement: `${indicator} observations via /api/countries/{iso3}/observations`,
    configVersion: 1,
    component: MetricWidget,
  };
}

function chartDef(
  typeId: string,
  displayName: string,
  indicator: string,
  category: WidgetCategory,
  countries: string[] = ["USA"],
): WidgetDefinition {
  return {
    typeId,
    displayName,
    description: `Historical ${INDICATOR_META[indicator]?.label ?? indicator} chart.`,
    category,
    defaultSize: { w: 6, h: 4 },
    minSize: { w: 4, h: 3 },
    configFields: [
      { ...countriesField, default: countries },
      { ...indicatorField, default: indicator },
      chartTypeField,
      legendField,
      titleField,
    ],
    dataRequirement: `${indicator} observations via /api/countries/{iso3}/observations`,
    configVersion: 1,
    component: IndicatorChartWidget,
  };
}

function unavailableDef(
  typeId: string,
  displayName: string,
  reason: string,
  category: WidgetCategory,
  methodologyStatus?: string,
): WidgetDefinition {
  return {
    typeId,
    displayName,
    description: reason,
    category,
    defaultSize: { w: 4, h: 3 },
    minSize: { w: 3, h: 2 },
    configFields: [
      { key: "reason", label: "Reason", type: "text", default: reason },
      {
        key: "methodologyStatus",
        label: "Methodology status",
        type: "text",
        default: methodologyStatus,
      },
    ],
    dataRequirement: "none — explicit unavailable state",
    configVersion: 1,
    component: UnavailableWidget,
  };
}

// --- Economic widgets ------------------------------------------------------
for (const [id, name, code] of [
  ["gdp", "GDP", "GDP_CURRENT_USD"],
  ["gdp-per-capita", "GDP per capita", "GDP_PER_CAPITA"],
  ["gdp-growth", "GDP growth", "GDP_GROWTH"],
  ["inflation", "Inflation", "INFLATION_CPI"],
  ["population", "Population", "POPULATION"],
  ["unemployment", "Unemployment", "UNEMPLOYMENT_RATE"],
  ["productivity", "Productivity", "LABOUR_PRODUCTIVITY_PER_HOUR"],
  ["unit-labour-costs", "Unit labour costs", "UNIT_LABOUR_COST_GROWTH"],
  ["government-debt", "Government debt", "GOVERNMENT_DEBT_GDP"],
  ["debt-service-ratio", "Debt service ratio", "DEBT_SERVICE_RATIO"],
  ["credit-gap", "Credit-to-GDP gap", "CREDIT_TO_GDP_GAP"],
  ["gross-capital-formation", "Gross capital formation", "GROSS_CAPITAL_FORMATION_GDP"],
] as const) {
  registerWidget(metricDef(id, name, code, "economic"));
}

// --- Trade widgets ---------------------------------------------------------
for (const [id, name, code] of [
  ["exports", "Exports", "EXPORTS_GDP"],
  ["imports", "Imports", "IMPORTS_GDP"],
  ["trade-balance", "Trade balance", "TRADE_BALANCE"],
  ["current-account", "Current account", "CURRENT_ACCOUNT_GDP"],
] as const) {
  registerWidget(metricDef(id, name, code, "trade"));
}
registerWidget(
  unavailableDef(
    "trade-openness",
    "Trade openness",
    "TRADE_OPENNESS_GDP exists as a derived descriptive ratio (DEC-038) but is not yet exposed via the API. It is trade intensity — not a strength score (DEC-035/039).",
    "trade",
    "Derived formula approved (trade-openness-gdp-v1); API endpoint pending.",
  ),
);
registerWidget(
  chartDef(
    "historical-trade-comparison",
    "Trade comparison",
    "EXPORTS_GDP",
    "trade",
    ["USA", "CHN", "DEU"],
  ),
);

// --- Governance & society widgets ------------------------------------------
for (const [id, name, code] of [
  ["rule-of-law", "Rule of law", "RULE_OF_LAW_WGI_SCORE"],
  ["control-of-corruption", "Control of corruption", "CONTROL_OF_CORRUPTION_WGI_SCORE"],
  ["political-stability", "Political stability", "POLITICAL_STABILITY_WGI_SCORE"],
  ["education", "Education", "TERTIARY_ATTAINMENT_25_34"],
  ["wealth-inequality", "Wealth inequality", "WEALTH_SHARE_TOP_10"],
  ["gini-index", "Gini index", "GINI_INDEX"],
  ["internal-conflict-proxy", "Internal conflict proxy", "POLITICAL_STABILITY_WGI_SCORE"],
] as const) {
  registerWidget(metricDef(id, name, code, "governance"));
}
registerWidget({
  typeId: "governance-uncertainty",
  displayName: "Governance uncertainty",
  description:
    "Published WGI 90% confidence band and source counts around the score. Provider-published only — no computed confidence (DEC-022/023).",
  category: "governance",
  defaultSize: { w: 6, h: 4 },
  minSize: { w: 4, h: 3 },
  configFields: [
    { ...countryField },
    {
      ...indicatorField,
      default: "RULE_OF_LAW_WGI_SCORE",
      options: [
        { value: "RULE_OF_LAW_WGI_SCORE", label: "Rule of Law" },
        { value: "CONTROL_OF_CORRUPTION_WGI_SCORE", label: "Control of Corruption" },
        { value: "POLITICAL_STABILITY_WGI_SCORE", label: "Political Stability" },
        { value: "GOVERNMENT_EFFECTIVENESS_WGI_SCORE", label: "Government Effectiveness" },
      ],
    },
    titleField,
  ],
  dataRequirement:
    "GET /api/countries/{iso3}/indicators/{code}/uncertainty + observations",
  configVersion: 1,
  component: UncertaintyBandWidget,
});

// --- National strength widgets ---------------------------------------------
registerWidget({
  typeId: "force-score",
  displayName: "Force score",
  description: "Score dimensions for one force — approved dimensions only.",
  category: "strength",
  defaultSize: { w: 4, h: 3 },
  minSize: { w: 3, h: 2 },
  configFields: [countryField, forceField, titleField],
  dataRequirement: "GET /api/countries/{iso3}/force-scores",
  configVersion: 1,
  component: ForceScoreWidget,
});
registerWidget({
  typeId: "all-forces",
  displayName: "All 17 forces",
  description: "Every force with coverage status and executable score dimensions.",
  category: "strength",
  defaultSize: { w: 6, h: 5 },
  minSize: { w: 4, h: 3 },
  configFields: [countryField, titleField],
  dataRequirement: "force-coverage + force-scores endpoints",
  configVersion: 1,
  component: AllForcesWidget,
});
registerWidget({
  typeId: "force-coverage",
  displayName: "Force coverage",
  description: "Coverage statuses for all 17 forces.",
  category: "strength",
  defaultSize: { w: 4, h: 5 },
  minSize: { w: 3, h: 3 },
  configFields: [countryField, titleField],
  dataRequirement: "GET /api/countries/{iso3}/force-coverage",
  configVersion: 1,
  component: ForceCoverageWidget,
});
registerWidget(
  unavailableDef(
    "force-comparison",
    "Force comparison",
    "Cross-country force comparison requires the force-score API (read-only, in progress) — only 5/17 forces have executable scores, and all are proxies or single indicators.",
    "strength",
    "5/17 executable; composite methodology undecided.",
  ),
);
registerWidget(
  unavailableDef(
    "absolute-strength",
    "Absolute strength",
    "No national composite score exists — the force weighting and missing-force rules are undecided methodology questions (Milestone 6).",
    "strength",
    "Composite methodology not yet decided.",
  ),
);
registerWidget(
  unavailableDef(
    "relative-strength",
    "Relative strength",
    "Relative-vs-peers composite requires the same undecided weighting methodology as absolute strength.",
    "strength",
  ),
);
registerWidget(
  unavailableDef(
    "momentum-score",
    "Momentum (composite)",
    "Force momentum exists only for the WGI ×3; a composite momentum needs the undecided weighting methodology.",
    "strength",
  ),
);
registerWidget(
  unavailableDef(
    "confidence-score",
    "Confidence",
    "Numeric confidence is deferred (DEC-023 — no external calibration basis). Diagnostics data (CI bounds, source counts) is imported but unused.",
    "strength",
    "DEFER_NUMERIC_CONFIDENCE — qualitative diagnostics only.",
  ),
);
registerWidget(
  unavailableDef(
    "big-cycle-position",
    "Big Cycle position",
    "Phase/stage derivation is Milestone 6 — no approved composition method, weighting, or transition rules exist yet.",
    "strength",
    "Milestone 6 — methodology research not started.",
  ),
);
registerWidget(
  unavailableDef(
    "big-cycle-timeline",
    "Big Cycle timeline",
    "Historical phase/stage series requires the cycle model (Milestone 6) plus release-date discipline (Milestone 9) before any historical claim.",
    "strength",
  ),
);
registerWidget(
  unavailableDef(
    "phase-history",
    "Phase history",
    "Phase history requires an approved phase model — none exists yet.",
    "strength",
  ),
);

// --- Data & research widgets ------------------------------------------------
registerWidget({
  typeId: "indicator-chart",
  displayName: "Indicator chart",
  description: "Historical chart for any indicator across 1–8 countries.",
  category: "data",
  defaultSize: { w: 6, h: 4 },
  minSize: { w: 4, h: 3 },
  configFields: [countriesField, indicatorField, chartTypeField, legendField, titleField],
  dataRequirement: "observations endpoint",
  configVersion: 1,
  component: IndicatorChartWidget,
});
registerWidget(
  unavailableDef(
    "scatter-plot",
    "Scatter plot",
    "Two-indicator scatter requires a paired-observation endpoint not yet built.",
    "data",
  ),
);
registerWidget(
  unavailableDef(
    "radar-chart",
    "Radar chart",
    "Force radar requires the force-score API plus ≥3 scored dimensions per country.",
    "data",
  ),
);
registerWidget(
  unavailableDef(
    "heatmap",
    "Heatmap",
    "Indicator × country heatmap requires a matrix endpoint not yet built.",
    "data",
  ),
);
registerWidget({
  typeId: "data-table",
  displayName: "Data table",
  description: "Latest-vintage raw observations table.",
  category: "data",
  defaultSize: { w: 6, h: 4 },
  minSize: { w: 4, h: 3 },
  configFields: [
    countryField,
    { ...indicatorField, default: "" },
    { key: "limit", label: "Rows", type: "number", default: 12, min: 4, max: 50 },
    titleField,
  ],
  dataRequirement: "observations endpoint",
  configVersion: 1,
  component: DataTableWidget,
});
registerWidget({
  typeId: "country-ranking",
  displayName: "Country ranking",
  description: "Latest indicator value across all tracked countries.",
  category: "data",
  defaultSize: { w: 5, h: 4 },
  minSize: { w: 4, h: 3 },
  configFields: [indicatorField, titleField],
  dataRequirement: "observations endpoint × 8 countries",
  configVersion: 1,
  component: RankingWidget,
});
registerWidget({
  typeId: "coverage-matrix",
  displayName: "Coverage matrix",
  description: "Per-country indicator and observation coverage.",
  category: "data",
  defaultSize: { w: 5, h: 4 },
  minSize: { w: 4, h: 3 },
  configFields: [titleField],
  dataRequirement: "GET /api/countries + observations",
  configVersion: 1,
  component: CoverageMatrixWidget,
});
registerWidget({
  typeId: "source-status",
  displayName: "Source details",
  description: "Registered providers and their pipeline status.",
  category: "data",
  defaultSize: { w: 4, h: 4 },
  minSize: { w: 3, h: 3 },
  configFields: [titleField],
  dataRequirement: "GET /api/data/sources",
  configVersion: 1,
  component: SourceStatusWidget,
});
registerWidget(
  unavailableDef(
    "observation-revisions",
    "Revision history",
    "Per-observation revision chains exist (IndicatorRevision API) but no revisions have occurred yet — all data is vintage 1.",
    "data",
  ),
);
registerWidget(
  unavailableDef(
    "data-freshness",
    "Data freshness",
    "A freshness dashboard needs per-series release-date metadata the API does not expose yet.",
    "data",
  ),
);
registerWidget({
  typeId: "ingestion-status",
  displayName: "Ingestion status",
  description: "Recent ingestion runs and outcomes.",
  category: "data",
  defaultSize: { w: 5, h: 4 },
  minSize: { w: 4, h: 3 },
  configFields: [titleField],
  dataRequirement: "GET /api/data/ingestion-runs",
  configVersion: 1,
  component: IngestionStatusWidget,
});
registerWidget({
  typeId: "api-status",
  displayName: "API status",
  description: "Backend liveness and database connectivity.",
  category: "research",
  defaultSize: { w: 3, h: 2 },
  minSize: { w: 2, h: 2 },
  configFields: [titleField],
  dataRequirement: "GET /health",
  configVersion: 1,
  component: ApiStatusWidget,
});
registerWidget({
  typeId: "model-version",
  displayName: "Model version",
  description: "Active normalization and force-aggregation versions.",
  category: "research",
  defaultSize: { w: 3, h: 3 },
  minSize: { w: 2, h: 2 },
  configFields: [titleField],
  dataRequirement: "static metadata",
  configVersion: 1,
  component: ModelVersionWidget,
});
registerWidget({
  typeId: "research-progress",
  displayName: "Research completion",
  description: "Per-force implementation status across all 17 forces.",
  category: "research",
  defaultSize: { w: 5, h: 5 },
  minSize: { w: 4, h: 3 },
  configFields: [titleField],
  dataRequirement: "static metadata synced with force_aggregation_definitions.py",
  configVersion: 1,
  component: ResearchProgressWidget,
});

/* Mission 3 §11 — research widgets */

const modelField: ConfigField = {
  key: "model",
  label: "Composite model",
  type: "text",
  default: "model_b_domain",
};
const startYearField: ConfigField = {
  key: "startYear",
  label: "Start year",
  type: "number",
  default: 2000,
  min: 1996,
  max: 2100,
};

registerWidget({
  typeId: "cycle-history",
  displayName: "Big Cycle history (experimental)",
  description:
    "Experimental composite conditions + stage markers from the research API. Retrospective; backtest_safe=false.",
  category: "research",
  defaultSize: { w: 8, h: 4 },
  minSize: { w: 5, h: 3 },
  configFields: [{ ...countryField }, modelField, startYearField, titleField],
  dataRequirement: "GET /api/research/countries/{iso3}/cycle/history",
  configVersion: 1,
  component: CycleHistoryWidget,
});
registerWidget({
  typeId: "force-history",
  displayName: "Force history",
  description:
    "Historical force level / relative / momentum dimensions — retrospective latest-vintage view.",
  category: "research",
  defaultSize: { w: 6, h: 4 },
  minSize: { w: 4, h: 3 },
  configFields: [
    { ...countryField },
    { ...forceField },
    { ...startYearField, default: 1996 },
    titleField,
  ],
  dataRequirement: "GET /api/countries/{iso3}/forces/{force}/history",
  configVersion: 1,
  component: ForceHistoryWidget,
});

/* Mission 6 §8 — historical validation widget */
registerWidget({
  typeId: "historical-validation",
  displayName: "Historical validation",
  description:
    "Availability evidence per country: strict eligibility, provider publication and atlas retrieval evidence, missing evidence, latest period.",
  category: "research",
  defaultSize: { w: 5, h: 4 },
  minSize: { w: 4, h: 3 },
  configFields: [countryField, titleField],
  dataRequirement:
    "GET /api/research/countries/{iso3}/availability + /api/research/execution-modes",
  configVersion: 1,
  component: HistoricalValidationWidget,
});

/* Great Power Observatory — Big Cycle clock widget */
registerWidget({
  typeId: "big-cycle-clock",
  displayName: "Big Cycle clock",
  description:
    "Observatory dial — all eight powers placed by experimental cycle stage. Model output, not a prediction.",
  category: "research",
  defaultSize: { w: 6, h: 5 },
  minSize: { w: 4, h: 4 },
  configFields: [{ ...countryField, label: "Focus country" }, titleField],
  dataRequirement: "GET /api/observatory/overview",
  configVersion: 1,
  component: BigCycleClockWidget,
});
