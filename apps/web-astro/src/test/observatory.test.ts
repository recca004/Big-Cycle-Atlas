import { describe, it, expect } from "vitest";
import {
  STAGES,
  STAGE_HOURS,
  STAGE_LABELS,
  layoutMarkers,
  hourToDeg,
  hourToRad,
  polar,
  stageLabel,
} from "@/features/observatory/stages";

describe("cycle stage geometry", () => {
  it("defines all eight cycle stages", () => {
    expect(STAGES).toHaveLength(8);
    for (const s of STAGES) {
      expect(STAGE_HOURS[s]).toBeTypeOf("number");
      expect(STAGE_LABELS[s]).toBeTruthy();
    }
  });

  it("places PEAK at 12 o'clock and RESET at 6", () => {
    expect(hourToDeg(STAGE_HOURS.PEAK)).toBe(360);
    expect(hourToDeg(STAGE_HOURS.RESET)).toBe(180);
  });

  it("polar(12h) is straight up", () => {
    const p = polar(12, 100);
    expect(p.x).toBeCloseTo(320);
    expect(p.y).toBeCloseTo(200);
  });

  it("hourToRad converts hours to trig radians", () => {
    expect(hourToRad(3)).toBeCloseTo(0); // 3 o'clock = +x axis
  });
});

describe("layoutMarkers", () => {
  it("keeps a single marker exactly on its stage anchor", () => {
    const [m] = layoutMarkers([{ iso3: "USA", stage: "RISE" }]);
    expect(m?.hour).toBe(STAGE_HOURS.RISE);
    expect(m?.groupSize).toBe(1);
  });

  it("fans same-stage markers symmetrically around the anchor", () => {
    const out = layoutMarkers([
      { iso3: "CHE", stage: "DECLINE" },
      { iso3: "DEU", stage: "DECLINE" },
      { iso3: "FRA", stage: "DECLINE" },
      { iso3: "GBR", stage: "DECLINE" },
    ]);
    expect(out).toHaveLength(4);
    const hours = out.map((m) => m.hour).sort((a, b) => a - b);
    const mean = hours.reduce((a, b) => a + b, 0) / hours.length;
    expect(mean).toBeCloseTo(STAGE_HOURS.DECLINE);
    // No two markers share the exact same hour — labels can't stack.
    expect(new Set(hours).size).toBe(4);
  });

  it("drops unclassified or unknown-stage markers", () => {
    const out = layoutMarkers([
      { iso3: "USA", stage: "RISE" },
      { iso3: "XXX", stage: null },
      { iso3: "YYY", stage: "BOGUS" },
    ]);
    expect(out.map((m) => m.iso3)).toEqual(["USA"]);
  });

  it("does not spread markers across different stages", () => {
    const out = layoutMarkers([
      { iso3: "USA", stage: "RISE" },
      { iso3: "CHN", stage: "DECLINE" },
    ]);
    expect(out.find((m) => m.iso3 === "USA")!.hour).toBe(STAGE_HOURS.RISE);
    expect(out.find((m) => m.iso3 === "CHN")!.hour).toBe(
      STAGE_HOURS.DECLINE,
    );
  });
});

describe("stageLabel", () => {
  it("maps known stages and is honest about missing ones", () => {
    expect(stageLabel("EARLY_DECLINE")).toBe("Early decline");
    expect(stageLabel(null)).toBe("Unclassified");
    expect(stageLabel("UNKNOWN")).toBe("UNKNOWN");
  });
});

describe("big-cycle-clock widget registration", () => {
  it("is registered in the workspace widget registry", async () => {
    const { getWidget } = await import(
      "@/features/workspace/widgetRegistry"
    );
    await import("@/features/widgets");
    const w = getWidget("big-cycle-clock");
    expect(w).toBeDefined();
    expect(w!.category).toBe("research");
    expect(w!.dataRequirement).toContain("/api/observatory/overview");
  });
});
