import type {
  Workspace,
  WidgetInstance,
  StoredLayoutItem,
} from "./types";

let counter = 0;
function uid(): string {
  // Deterministic-ish ids fine for factory defaults — duplicates across
  // regenerated defaults are harmless since workspaces get fresh ids anyway.
  counter += 1;
  return `builtin-${counter}-${Math.random().toString(36).slice(2, 8)}`;
}

function w(
  type: string,
  config: Record<string, unknown>,
  lg: { x: number; y: number; w: number; h: number },
): { widget: WidgetInstance; item: StoredLayoutItem } {
  const id = uid();
  return {
    widget: { id, type, config, collapsed: false, locked: false },
    item: { i: id, ...lg },
  };
}

function build(
  name: string,
  defs: { widget: WidgetInstance; item: StoredLayoutItem }[],
): Workspace {
  const widgets = defs.map((d) => d.widget);
  const lg = defs.map((d) => d.item);
  const md = lg.map((it) => {
    const wdt = Math.max(1, Math.round((it.w / 12) * 8));
    const x = Math.max(0, Math.min(Math.round((it.x / 12) * 8), 8 - wdt));
    return { ...it, x, w: wdt };
  });
  const sm = lg
    .slice()
    .sort((a, b) => a.y - b.y || a.x - b.x)
    .map((it, idx) => ({ ...it, x: 0, y: idx * it.h, w: 4 }));
  return {
    id: uid(),
    name,
    widgets,
    layouts: { lg, md, sm },
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    builtin: true,
    filters: { country: null, countries: [], startYear: null, methodScope: "both" },
  };
}

/** Eight default workspaces — factories so each reset/import gets fresh ids. */
export const DEFAULT_WORKSPACES: (() => Workspace)[] = [
  () =>
    build("Global Macro Overview", [
      w("api-status", {}, { x: 0, y: 0, w: 3, h: 2 }),
      w("model-version", {}, { x: 3, y: 0, w: 3, h: 2 }),
      w("source-status", {}, { x: 6, y: 0, w: 6, h: 5 }),
      w("country-ranking", { indicator: "GDP_GROWTH" }, { x: 0, y: 2, w: 6, h: 5 }),
      w("coverage-matrix", {}, { x: 0, y: 7, w: 6, h: 5 }),
      w("research-progress", {}, { x: 6, y: 5, w: 6, h: 7 }),
      w("indicator-chart", {
        countries: ["USA", "CHN", "DEU"],
        indicator: "INFLATION_CPI",
        chartType: "line",
      }, { x: 0, y: 12, w: 12, h: 5 }),
    ]),

  () =>
    build("Country Intelligence", [
      w("all-forces", { country: "USA" }, { x: 0, y: 0, w: 6, h: 6 }),
      w("gdp", { country: "USA" }, { x: 6, y: 0, w: 3, h: 3 }),
      w("gdp-growth", { country: "USA" }, { x: 9, y: 0, w: 3, h: 3 }),
      w("inflation", { country: "USA" }, { x: 6, y: 3, w: 3, h: 3 }),
      w("government-debt", { country: "USA" }, { x: 9, y: 3, w: 3, h: 3 }),
      w("indicator-chart", {
        countries: ["USA"],
        indicator: "GDP_GROWTH",
        chartType: "bar",
      }, { x: 0, y: 6, w: 8, h: 5 }),
      w("force-coverage", { country: "USA" }, { x: 8, y: 6, w: 4, h: 5 }),
    ]),

  () =>
    build("Big Cycle Research", [
      w("research-progress", {}, { x: 0, y: 0, w: 5, h: 6 }),
      w("big-cycle-position", {}, { x: 5, y: 0, w: 4, h: 3 }),
      w("absolute-strength", {}, { x: 9, y: 0, w: 3, h: 3 }),
      w("all-forces", { country: "USA" }, { x: 5, y: 3, w: 7, h: 6 }),
      w("indicator-chart", {
        countries: ["USA", "CHN"],
        indicator: "RULE_OF_LAW_WGI_SCORE",
        chartType: "line",
      }, { x: 0, y: 6, w: 12, h: 5 }),
      w("model-version", {}, { x: 0, y: 11, w: 4, h: 3 }),
      w("confidence-score", {}, { x: 4, y: 11, w: 4, h: 3 }),
      w("big-cycle-timeline", {}, { x: 8, y: 11, w: 4, h: 3 }),
    ]),

  () =>
    build("Debt and Credit Monitor", [
      w("credit-gap", { country: "USA" }, { x: 0, y: 0, w: 3, h: 3 }),
      w("debt-service-ratio", { country: "USA" }, { x: 3, y: 0, w: 3, h: 3 }),
      w("government-debt", { country: "USA" }, { x: 6, y: 0, w: 3, h: 3 }),
      w("force-score", { country: "USA", force: "indebtedness" }, { x: 9, y: 0, w: 3, h: 3 }),
      w("indicator-chart", {
        countries: ["USA", "CHN", "JPN", "DEU"],
        indicator: "CREDIT_TO_GDP_GAP",
        chartType: "line",
      }, { x: 0, y: 3, w: 6, h: 5 }),
      w("indicator-chart", {
        countries: ["USA", "CHN", "JPN", "DEU"],
        indicator: "DEBT_SERVICE_RATIO",
        chartType: "line",
      }, { x: 6, y: 3, w: 6, h: 5 }),
      w("country-ranking", { indicator: "GOVERNMENT_DEBT_GDP" }, { x: 0, y: 8, w: 6, h: 5 }),
      w("data-table", { country: "USA", indicator: "GOVERNMENT_DEBT_GDP", limit: 12 }, { x: 6, y: 8, w: 6, h: 5 }),
    ]),

  () =>
    build("Trade and Capital Monitor", [
      w("exports", { country: "USA" }, { x: 0, y: 0, w: 3, h: 3 }),
      w("imports", { country: "USA" }, { x: 3, y: 0, w: 3, h: 3 }),
      w("trade-balance", { country: "USA" }, { x: 6, y: 0, w: 3, h: 3 }),
      w("current-account", { country: "USA" }, { x: 9, y: 0, w: 3, h: 3 }),
      w("indicator-chart", {
        countries: ["USA", "CHN", "DEU", "CHE"],
        indicator: "EXPORTS_GDP",
        chartType: "line",
      }, { x: 0, y: 3, w: 6, h: 5 }),
      w("indicator-chart", {
        countries: ["USA", "CHN", "DEU", "CHE"],
        indicator: "CURRENT_ACCOUNT_GDP",
        chartType: "line",
      }, { x: 6, y: 3, w: 6, h: 5 }),
      w("trade-openness", {}, { x: 0, y: 8, w: 4, h: 3 }),
      w("historical-trade-comparison", {}, { x: 4, y: 8, w: 8, h: 5 }),
    ]),

  () =>
    build("Country Comparison", [
      w("country-ranking", { indicator: "GDP_PER_CAPITA" }, { x: 0, y: 0, w: 6, h: 5 }),
      w("country-ranking", { indicator: "RULE_OF_LAW_WGI_SCORE" }, { x: 6, y: 0, w: 6, h: 5 }),
      w("indicator-chart", {
        countries: ["USA", "CHN", "IND", "JPN"],
        indicator: "GDP_GROWTH",
        chartType: "line",
      }, { x: 0, y: 5, w: 6, h: 5 }),
      w("indicator-chart", {
        countries: ["USA", "CHN", "IND", "JPN"],
        indicator: "INFLATION_CPI",
        chartType: "line",
      }, { x: 6, y: 5, w: 6, h: 5 }),
      w("coverage-matrix", {}, { x: 0, y: 10, w: 6, h: 4 }),
      w("country-ranking", { indicator: "INFLATION_CPI" }, { x: 6, y: 10, w: 6, h: 4 }),
    ]),

  () =>
    build("Historical Research", [
      w("indicator-chart", {
        countries: ["USA"],
        indicator: "WEALTH_SHARE_TOP_10",
        chartType: "line",
      }, { x: 0, y: 0, w: 6, h: 5 }),
      w("indicator-chart", {
        countries: ["GBR", "FRA", "DEU"],
        indicator: "GOVERNMENT_DEBT_GDP",
        chartType: "line",
      }, { x: 6, y: 0, w: 6, h: 5 }),
      w("data-table", { country: "USA", indicator: "", limit: 20 }, { x: 0, y: 5, w: 6, h: 6 }),
      w("data-table", { country: "CHN", indicator: "", limit: 20 }, { x: 6, y: 5, w: 6, h: 6 }),
    ]),

  () => build("Empty Custom Workspace", []),
];
