import { describe, it, expect } from "vitest";
import { buildUncertaintyOption } from "@/lib/charts/uncertaintyChart";

const scores = [
  { period_start: "2020-01-01", value: 82.3 },
  { period_start: "2021-01-01", value: 83.1 },
  { period_start: "2022-01-01", value: 81.9 },
];
const diags = [
  { period_start: "2020-01-01", ci_lower_bound: 76.0, ci_upper_bound: 88.0, source_count: 8 },
  // 2021 diagnostics absent — must surface as a gap, not interpolation
  { period_start: "2022-01-01", ci_lower_bound: 75.0, ci_upper_bound: 87.5, source_count: 9 },
];

describe("buildUncertaintyOption", () => {
  it("aligns score and diagnostics by exact period", () => {
    const built = buildUncertaintyOption(scores, diags, "Rule of Law");
    expect(built.kind).toBe("chart");
    if (built.kind !== "chart") return;
    const series = built.option.series as { name: string; data: unknown[] }[];
    const band = series.find((s) => s.name === "90% CI (published)")!;
    // UB-LB stacked band; 2021 has no diagnostics → null (gap)
    expect(band.data).toEqual([12, null, 12.5]);
    const score = series.find((s) => s.name === "Score")!;
    expect(score.data).toEqual([82.3, 83.1, 81.9]);
    expect(built.diagnosticsPresent).toBe(true);
  });

  it("shows diagnostic-only periods on the axis", () => {
    const built = buildUncertaintyOption(
      scores.slice(0, 1),
      diags,
      "Rule of Law",
    );
    if (built.kind !== "chart") throw new Error("expected chart");
    const x = built.option.xAxis as { data: string[] };
    expect(x.data).toEqual(["2020", "2022"]);
  });

  it("flags missing bounds without fabricating them", () => {
    const built = buildUncertaintyOption(
      scores,
      [{ period_start: "2020-01-01", source_count: 8 }],
      "Rule of Law",
    );
    if (built.kind !== "chart") throw new Error("expected chart");
    expect(built.diagnosticsPresent).toBe(false);
    const series = built.option.series as { name: string }[];
    expect(series.some((s) => s.name === "90% CI (published)")).toBe(false);
  });

  it("returns an explicit empty state with no data", () => {
    const built = buildUncertaintyOption([], [], "Rule of Law");
    expect(built.kind).toBe("empty");
  });
});
