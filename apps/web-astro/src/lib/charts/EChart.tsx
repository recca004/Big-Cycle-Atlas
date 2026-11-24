import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface EChartProps {
  option: echarts.EChartsOption;
  className?: string;
  style?: React.CSSProperties;
  ariaLabel?: string;
}

/** Thin ECharts wrapper — init once, update on option change, dispose on
 *  unmount (required so removed widgets don't leak chart instances). */
export function EChart({ option, className, style, ariaLabel }: EChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chartRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: true });
  }, [option]);

  return (
    <div
      ref={ref}
      className={className}
      style={{ width: "100%", height: "100%", minHeight: 120, ...style }}
      role="img"
      aria-label={ariaLabel}
    />
  );
}

const cssVar = (name: string, fallback: string) =>
  typeof window !== "undefined"
    ? getComputedStyle(document.documentElement).getPropertyValue(name).trim() ||
      fallback
    : fallback;

/** Shared chart option base themed from CSS tokens. */
export function baseChartOption(): echarts.EChartsOption {
  return {
    animation: !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches,
    grid: { left: 8, right: 12, top: 28, bottom: 24, containLabel: true },
    textStyle: {
      color: cssVar("--text-secondary", "#a8b3c7"),
      fontFamily: cssVar("--font-sans", "sans-serif"),
      fontSize: 11,
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: cssVar("--surface-solid", "#141c2e"),
      borderColor: cssVar("--border-default", "rgba(255,255,255,0.14)"),
      textStyle: { color: cssVar("--text-primary", "#eef2f9"), fontSize: 12 },
    },
    xAxis: {
      axisLine: { lineStyle: { color: cssVar("--border-subtle", "#333") } },
      axisLabel: { color: cssVar("--text-tertiary", "#6b7790") },
      splitLine: { show: false },
    },
    yAxis: {
      axisLabel: { color: cssVar("--text-tertiary", "#6b7790") },
      splitLine: {
        lineStyle: { color: cssVar("--border-subtle", "rgba(255,255,255,0.08)") },
      },
    },
    color: [
      cssVar("--chart-1", "#4d8fd1"),
      cssVar("--chart-2", "#4fbf8f"),
      cssVar("--chart-3", "#d9a441"),
      cssVar("--chart-4", "#d16a6a"),
      cssVar("--chart-5", "#8f7fd4"),
      cssVar("--chart-6", "#4fb3bf"),
      cssVar("--chart-7", "#c98fd1"),
      cssVar("--chart-8", "#9db55f"),
    ],
  };
}
