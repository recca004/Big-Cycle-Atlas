import { describe, it, expect } from "vitest";
import "@/features/widgets";
import {
  listWidgets,
  getWidget,
  widgetsByCategory,
} from "@/features/workspace/widgetRegistry";

const ALL = listWidgets();

describe("widget registry", () => {
  it("registers the full widget inventory", () => {
    expect(ALL.length).toBeGreaterThanOrEqual(35);
  });

  it("has unique typeIds", () => {
    const ids = ALL.map((d) => d.typeId);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("every widget has valid bounds", () => {
    for (const d of ALL) {
      expect(d.defaultSize.w).toBeGreaterThanOrEqual(d.minSize.w);
      expect(d.defaultSize.h).toBeGreaterThanOrEqual(d.minSize.h);
      expect(d.minSize.w).toBeGreaterThanOrEqual(1);
      expect(d.defaultSize.w).toBeLessThanOrEqual(12);
    }
  });

  it("every widget has display name, description, category, component", () => {
    for (const d of ALL) {
      expect(d.displayName.length).toBeGreaterThan(0);
      expect(d.description.length).toBeGreaterThan(0);
      expect(d.category.length).toBeGreaterThan(0);
      expect(d.component).toBeTypeOf("function");
      expect(d.dataRequirement.length).toBeGreaterThan(0);
    }
  });

  it("config field keys are unique per widget", () => {
    for (const d of ALL) {
      const keys = d.configFields.map((f) => f.key);
      expect(new Set(keys).size).toBe(keys.length);
    }
  });

  it("getWidget resolves registered ids", () => {
    expect(getWidget("gdp")?.displayName).toBe("GDP");
    expect(getWidget("nonexistent-widget")).toBeUndefined();
  });

  it("groups into non-empty categories", () => {
    for (const [cat, defs] of widgetsByCategory()) {
      expect(defs.length).toBeGreaterThan(0);
      for (const d of defs) expect(d.category).toBe(cat);
    }
  });
});
