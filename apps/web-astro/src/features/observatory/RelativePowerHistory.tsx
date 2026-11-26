import { useEffect, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { fetchObservatorySeries } from "@/lib/api/client";
import { EChart, baseChartOption } from "@/lib/charts/EChart";
import type { CurrencyEvidence, MeasureHistory } from "@/types/observatory";

type MeasureSpec =
  | { kind: "indicator"; code: string; label: string; worldShare: boolean }
  | { kind: "currency"; seriesKey: "cofer_reserve_share_pct" | "fx_turnover_share_200pct"; label: string; unit: string; source: string };

const MEASURES: MeasureSpec[] = [
  { kind: "indicator", code: "GDP_CURRENT_USD", label: "Nominal GDP — global share (%)", worldShare: true },
  { kind: "indicator", code: "GDP_PPP_CURRENT_INTL", label: "PPP GDP — global share (%)", worldShare: true },
  { kind: "indicator", code: "GDP_CURRENT_USD", label: "Nominal GDP (current US$)", worldShare: false },
  { kind: "indicator", code: "GDP_PPP_CURRENT_INTL", label: "PPP GDP (current international $)", worldShare: false },
  { kind: "indicator", code: "GDP_REAL_CONSTANT_USD", label: "Real GDP (2015 US$) — global share (%)", worldShare: true },
  { kind: "indicator", code: "GDP_REAL_CONSTANT_USD", label: "Real GDP (constant 2015 US$)", worldShare: false },
  { kind: "indicator", code: "GDP_PER_CAPITA", label: "GDP per capita (current US$)", worldShare: false },
  { kind: "indicator", code: "MERCHANDISE_EXPORTS_USD", label: "Goods exports — global share (%)", worldShare: true },
  { kind: "indicator", code: "MERCHANDISE_EXPORTS_USD", label: "Goods exports (current US$)", worldShare: false },
  { kind: "indicator", code: "MERCHANDISE_IMPORTS_USD", label: "Goods imports — global share (%)", worldShare: true },
  { kind: "indicator", code: "COMMERCIAL_SERVICE_EXPORTS_USD", label: "Service exports — global share (%)", worldShare: true },
  { kind: "indicator", code: "COMMERCIAL_SERVICE_EXPORTS_USD", label: "Service exports (current US$)", worldShare: false },
  { kind: "indicator", code: "EXPORTS_GDP", label: "Exports openness (% of GDP)", worldShare: false },
  { kind: "indicator", code: "MILITARY_EXPENDITURE_USD", label: "Military expenditure — global share (%)", worldShare: true },
  { kind: "indicator", code: "MILITARY_EXPENDITURE_USD", label: "Military expenditure (current US$)", worldShare: false },
  { kind: "indicator", code: "MILITARY_EXPENDITURE_GDP", label: "Military expenditure (% of GDP)", worldShare: false },
  { kind: "currency", seriesKey: "cofer_reserve_share_pct", label: "Official FX reserve share — IMF COFER (%)", unit: "% of FX reserves", source: "IMF COFER (SDMX 2.1)" },
  { kind: "currency", seriesKey: "fx_turnover_share_200pct", label: "Global FX turnover share — BIS Triennial (200% sum)", unit: "% of daily FX turnover", source: "BIS Triennial Survey" },
  { kind: "indicator", code: "RND_EXPENDITURE_GDP", label: "R&D expenditure (% of GDP)", worldShare: false },
  { kind: "indicator", code: "PATENT_APPLICATIONS_RESIDENT", label: "Resident patents — global share (%)", worldShare: true },
  { kind: "indicator", code: "PATENT_APPLICATIONS_RESIDENT", label: "Resident patent applications (count)", worldShare: false },
  { kind: "indicator", code: "RESEARCHERS_PER_MILLION", label: "Researchers in R&D (per million)", worldShare: false },
  { kind: "indicator", code: "HIGH_TECHNOLOGY_EXPORTS_USD", label: "High-tech exports — global share (%)", worldShare: true },
  { kind: "indicator", code: "HIGH_TECHNOLOGY_EXPORTS_USD", label: "High-tech exports (current US$)", worldShare: false },
  { kind: "indicator", code: "LABOUR_PRODUCTIVITY_PER_HOUR", label: "Labour productivity per hour", worldShare: false },
  { kind: "indicator", code: "STOCK_MARKET_CAP_GDP", label: "Listed market capitalisation (% of GDP)", worldShare: false },
  { kind: "indicator", code: "DOMESTIC_CREDIT_PRIVATE_GDP", label: "Domestic private credit (% of GDP)", worldShare: false },
  { kind: "indicator", code: "BROAD_MONEY_GDP", label: "Broad money (% of GDP)", worldShare: false },
  { kind: "indicator", code: "GOVERNMENT_DEBT_GDP", label: "Government debt (% of GDP)", worldShare: false },
];

const PALETTE = [
  "#c9a24e",
  "#4c96a8",
  "#7da87b",
  "#cf6b63",
  "#9b82c4",
  "#d48a54",
  "#5a7ec7",
  "#8f9ba8",
  "#b56e8a",
];

function formatAxisValue(val: number, unit: string): string {
  const abs = Math.abs(val);
  if (/usd|\$/i.test(unit) && !/%|share/i.test(unit)) {
    if (abs >= 1e12) return `$${(val / 1e12).toFixed(1)}T`;
    if (abs >= 1e9) return `$${(val / 1e9).toFixed(0)}B`;
    if (abs >= 1e6) return `$${(val / 1e6).toFixed(0)}M`;
    return `$${val.toLocaleString("en-CH", { maximumFractionDigits: 0 })}`;
  }
  if (/%|share/i.test(unit)) {
    return `${val.toLocaleString("en-CH", { maximumFractionDigits: 1 })}%`;
  }
  if (abs >= 1e6) return `${(val / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${(val / 1e3).toFixed(0)}k`;
  return val.toLocaleString("en-CH", { maximumFractionDigits: 1 });
}

interface NormalizedLine {
  code: string;
  points: Map<number, number>;
}

export function RelativePowerHistory({
  rangeStart,
  currencyEvidence,
}: {
  rangeStart: number;
  currencyEvidence?: CurrencyEvidence | null | undefined;
}) {
  const [selection, setSelection] = useState(0);
  const selected = MEASURES[selection] ?? MEASURES[0]!;
  const [payload, setPayload] = useState<MeasureHistory | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeCodes, setActiveCodes] = useState<string[] | null>(null);
  const [scaleMode, setScaleMode] = useState<"linear" | "log">("linear");
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    if (selected.kind !== "indicator") return;
    let alive = true;
    setLoading(true);
    fetchObservatorySeries({
      indicator: selected.code,
      startYear: rangeStart,
      worldShare: selected.worldShare,
    })
      .then((next) => {
        if (alive) {
          setPayload(next);
          setLoading(false);
        }
      })
      .catch(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [selected, rangeStart]);

  useEffect(() => {
    if (!fullscreen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFullscreen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [fullscreen]);

  const normalized = useMemo(() => {
    if (selected.kind === "currency") {
      const rawMap = currencyEvidence?.series?.[selected.seriesKey] ?? {};
      const preferredOrder = ["USD", "EUR", "CNY", "JPY", "GBP", "CHF", "INR", "DEM", "FRF"];
      const lines: NormalizedLine[] = preferredOrder
        .filter((ccy) => (rawMap[ccy]?.length ?? 0) > 0)
        .map((ccy) => {
          const pts = new Map<number, number>();
          for (const p of rawMap[ccy] ?? []) {
            if (p.year >= rangeStart) pts.set(p.year, p.value);
          }
          return { code: ccy, points: pts };
        })
        .filter((l) => l.points.size > 0);
      return {
        lines,
        unit: selected.unit,
        source: selected.source,
        denominator: "ALL_CURRENCIES",
      };
    }
    const countries = payload?.countries ?? [];
    const lines: NormalizedLine[] = countries
      .map((c) => {
        const pts = new Map<number, number>();
        for (const p of c.points) {
          if (p.period >= rangeStart) pts.set(p.period, p.value);
        }
        return { code: c.iso3, points: pts };
      })
      .filter((l) => l.points.size > 0);
    const unit = payload?.world_share
      ? "% of world"
      : (countries[0]?.unit ?? "source units");
    return {
      lines,
      unit,
      source: countries[0]?.source ?? "Provider latest vintage",
      denominator: payload?.world_share ? payload.denominator_entity : null,
    };
  }, [selected, currencyEvidence, payload, rangeStart]);

  const allEntityCodes = useMemo(
    () => normalized.lines.map((l) => l.code),
    [normalized.lines],
  );

  // Reset entity filter when switching between country and currency domains
  useEffect(() => {
    setActiveCodes(null);
  }, [selected.kind]);

  const visibleCodes = useMemo(() => {
    if (!activeCodes) return new Set(allEntityCodes);
    const valid = activeCodes.filter((c) => allEntityCodes.includes(c));
    return new Set(valid.length ? valid : allEntityCodes);
  }, [activeCodes, allEntityCodes]);

  const visibleValues = useMemo(() => {
    const vals: number[] = [];
    for (const line of normalized.lines) {
      if (!visibleCodes.has(line.code)) continue;
      for (const v of line.points.values()) vals.push(v);
    }
    return vals;
  }, [normalized.lines, visibleCodes]);

  const canUseLog = visibleValues.length > 0 && visibleValues.every((v) => v > 0);
  const effectiveScale = scaleMode === "log" && canUseLog ? "log" : "linear";

  const option = useMemo<EChartsOption | null>(() => {
    const activeLines = normalized.lines.filter((l) => visibleCodes.has(l.code));
    if (!activeLines.length) return null;
    const allYears = activeLines.flatMap((l) => [...l.points.keys()]);
    if (!allYears.length) return null;
    const maxYear = Math.max(...allYears);
    const minYear = Math.min(rangeStart, ...allYears);
    const calendarYears = Array.from(
      { length: maxYear - minYear + 1 },
      (_, idx) => String(minYear + idx),
    );
    const isTriennial = selected.kind === "currency" && selected.seriesKey === "fx_turnover_share_200pct";

    return {
      ...baseChartOption(),
      color: PALETTE,
      grid: { top: 38, right: 66, bottom: 64, left: 68, containLabel: false },
      legend: {
        top: 4,
        left: 0,
        textStyle: { color: "var(--text-secondary)", fontSize: 11 },
      },
      tooltip: {
        trigger: "axis",
        confine: true,
        valueFormatter: (v) =>
          typeof v === "number" ? `${formatAxisValue(v, normalized.unit)}` : "No observation",
      },
      dataZoom: [
        { type: "inside", xAxisIndex: 0, filterMode: "none" },
        {
          type: "slider",
          xAxisIndex: 0,
          height: 18,
          bottom: 12,
          borderColor: "transparent",
          filterMode: "none",
        },
      ],
      xAxis: {
        type: "category",
        data: calendarYears,
        boundaryGap: false,
        axisLabel: { fontSize: 11 },
      },
      yAxis: {
        type: effectiveScale === "log" ? ("log" as const) : ("value" as const),
        name: normalized.unit,
        nameTextStyle: { fontSize: 11, padding: [0, 0, 4, 0] },
        axisLabel: {
          fontSize: 11,
          formatter: (val: number) => formatAxisValue(val, normalized.unit),
        },
        splitLine: { lineStyle: { opacity: 0.22 } },
      },
      labelLayout: { moveOverlap: "shiftY" },
      series: activeLines.map((line, idx) => {
        const stroke = PALETTE[idx % PALETTE.length] ?? "#c9a24e";
        return {
          name: line.code,
          type: "line" as const,
          // Keep genuine historical gaps visible; only connect across non-survey
          // interim years on triennial BIS surveys while marking exact survey dots.
          connectNulls: isTriennial,
          showSymbol: isTriennial,
          symbolSize: isTriennial ? 6 : 4,
          lineStyle: { width: 2.1, color: stroke },
          itemStyle: { color: stroke },
          endLabel: {
            show: true,
            formatter: "{a}",
            fontSize: 11,
            color: stroke,
          },
          data: calendarYears.map((yr) => line.points.get(Number(yr)) ?? null),
        };
      }),
    };
  }, [normalized, visibleCodes, rangeStart, effectiveScale, selected]);

  const toggleEntity = (code: string) => {
    const next = new Set(visibleCodes);
    if (next.has(code) && next.size > 1) next.delete(code);
    else next.add(code);
    setActiveCodes([...next]);
  };

  const chartBody = (
    <div className={fullscreen ? "measure-history is-fullscreen glass" : "measure-history"}>
      <div className="measure-history-toolbar">
        <label className="obs-measure-picker">
          <span className="obs-picker-kicker">Verified measure</span>
          <select
            className="glass-button"
            value={selection}
            onChange={(event) => setSelection(Number(event.target.value))}
          >
            {MEASURES.map((m, index) => (
              <option key={`${m.label}-${index}`} value={index}>
                {m.label}
              </option>
            ))}
          </select>
        </label>

        <div className="measure-scale-controls" role="group" aria-label="Axis scale and view">
          <button
            type="button"
            className={effectiveScale === "linear" ? "glass-button active" : "glass-button"}
            aria-pressed={effectiveScale === "linear"}
            onClick={() => setScaleMode("linear")}
          >
            Linear
          </button>
          <button
            type="button"
            className={effectiveScale === "log" ? "glass-button active" : "glass-button"}
            aria-pressed={effectiveScale === "log"}
            disabled={!canUseLog}
            title={canUseLog ? "Logarithmic Y-axis" : "Log scale requires strictly positive values"}
            onClick={() => setScaleMode("log")}
          >
            Log
          </button>
          <button
            type="button"
            className="glass-button"
            onClick={() => setFullscreen((v) => !v)}
          >
            {fullscreen ? "Exit full screen" : "Full screen"}
          </button>
        </div>
      </div>

      {allEntityCodes.length > 0 && (
        <div className="measure-filter-bar" role="group" aria-label="Filter series">
          <button
            type="button"
            className={activeCodes === null ? "filter-chip active" : "filter-chip"}
            onClick={() => setActiveCodes(null)}
          >
            All ({allEntityCodes.length})
          </button>
          {selected.kind === "indicator" && (
            <button
              type="button"
              className={
                activeCodes?.length === 3 &&
                ["USA", "CHN", "IND"].every((c) => activeCodes.includes(c))
                  ? "filter-chip active"
                  : "filter-chip"
              }
              onClick={() => setActiveCodes(["USA", "CHN", "IND"])}
            >
              USA · CHN · IND
            </button>
          )}
          {allEntityCodes.map((code) => (
            <button
              key={code}
              type="button"
              className={visibleCodes.has(code) ? "filter-chip active" : "filter-chip"}
              aria-pressed={visibleCodes.has(code)}
              onClick={() => toggleEntity(code)}
            >
              {code}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="chart-skeleton" style={{ height: fullscreen ? 520 : 340 }} />
      ) : option ? (
        <div className="measure-echart-host">
          <EChart
            option={option}
            style={{ height: fullscreen ? "calc(100vh - 14rem)" : 360 }}
            ariaLabel={`${selected.label} across tracked entities`}
          />
        </div>
      ) : (
        <p className="obs-muted">No verified observations in this range.</p>
      )}

      <p className="obs-muted">
        Continuous calendar axis from {rangeStart}; latest vintages only · unit:{" "}
        <strong>{normalized.unit}</strong> · source: {normalized.source}
        {normalized.denominator ? ` · denominator: ${normalized.denominator}` : ""}. Genuine
        missing periods remain blank rather than interpolated.
      </p>
    </div>
  );

  if (fullscreen) {
    return (
      <div className="measure-fullscreen-backdrop" role="dialog" aria-modal="true" aria-label={selected.label}>
        {chartBody}
      </div>
    );
  }
  return chartBody;
}
