import { describe, it, expect } from "vitest";
import {
  formatPercent,
  formatDecimal,
  formatUsdCompact,
  formatQuarter,
  yearOf,
  sourceLabel,
} from "@/lib/format";

describe("format", () => {
  it("formats percentages", () => {
    expect(formatPercent(2.156)).toBe("2.16%");
    expect(formatPercent(-3.072)).toBe("-3.07%");
  });
  it("formats decimals", () => {
    expect(formatDecimal(87.333)).toBe("87.33");
  });
  it("formats compact USD", () => {
    expect(formatUsdCompact(30_770_000_000_000)).toBe("$30.77T");
    expect(formatUsdCompact(4_500_000_000)).toBe("$4.50B");
  });
  it("derives quarter labels", () => {
    expect(formatQuarter("2025-04-01")).toBe("2025 Q2");
    expect(formatQuarter("2025-10-01")).toBe("2025 Q4");
  });
  it("derives year", () => {
    expect(yearOf("2024-07-01")).toBe(2024);
  });
  it("labels sources", () => {
    expect(sourceLabel("world_bank")).toBe("World Bank");
    expect(sourceLabel(null)).toBe("Unknown source");
  });
});
