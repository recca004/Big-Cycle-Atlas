import { describe, it, expect } from "vitest";
import {
  defaultInstanceConfig,
  inheritFlag,
  isInheritable,
  resolveEffectiveConfig,
} from "@/features/workspace/effectiveConfig";
import type { WidgetDefinition } from "@/features/workspace/widgetRegistry";
import type { Workspace } from "@/features/workspace/types";

const FILTERS: Workspace["filters"] = {
  country: "CHN", countries: ["CHN", "USA"],
  startYear: 2010, endYear: 2024, methodScope: "both",
};

const DEF: WidgetDefinition = {
  typeId: "t",
  displayName: "T",
  description: "",
  category: "economic",
  defaultSize: { w: 3, h: 3 },
  minSize: { w: 2, h: 2 },
  configFields: [
    { key: "country", label: "Country", type: "country", default: "USA" },
    { key: "startYear", label: "From", type: "number", default: 1996 },
    { key: "title", label: "Title", type: "text" },
  ],
  dataRequirement: "",
  configVersion: 1,
  component: () => null,
};

describe("resolveEffectiveConfig", () => {
  it("workspace filter wins when inheritance is on", () => {
    const cfg = { inherit_country: true, inherit_startYear: true };
    const eff = resolveEffectiveConfig(DEF, cfg, FILTERS);
    expect(eff.country).toBe("CHN");
    expect(eff.startYear).toBe(2010);
  });

  it("widget-specific value wins when inheritance is off", () => {
    const cfg = {
      country: "JPN", startYear: 2000,
      inherit_country: false, inherit_startYear: false,
    };
    const eff = resolveEffectiveConfig(DEF, cfg, FILTERS);
    expect(eff.country).toBe("JPN");
    expect(eff.startYear).toBe(2000);
  });

  it("falls back to widget value then default when filter unset", () => {
    const eff = resolveEffectiveConfig(
      DEF,
      { inherit_country: true },
      { ...FILTERS, country: null },
    );
    expect(eff.country).toBe("USA");
  });

  it("non-inheritable fields are untouched", () => {
    const eff = resolveEffectiveConfig(
      DEF, { title: "keep", inherit_country: true }, FILTERS);
    expect(eff.title).toBe("keep");
  });

  it("setting a value disables inheritance flag (override semantics)", () => {
    // mirrors the WidgetFrame onChange: value change writes flag=false
    const cfg = {
      country: "DEU", [inheritFlag("country")]: false,
    };
    expect(
      resolveEffectiveConfig(DEF, cfg, FILTERS).country,
    ).toBe("DEU");
  });
});

describe("defaultInstanceConfig", () => {
  it("seeds defaults and inherit flags for new widgets", () => {
    const cfg = defaultInstanceConfig(DEF);
    expect(cfg.country).toBe("USA");
    expect(cfg.inherit_country).toBe(true);
    expect(cfg.inherit_startYear).toBe(true);
    expect(cfg.inherit_title).toBeUndefined();
  });
});

describe("isInheritable", () => {
  it("covers the shared filter surface", () => {
    for (const k of ["country", "countries", "startYear", "endYear",
                     "indicator", "force", "model"]) {
      expect(isInheritable({ key: k, label: k, type: "text" })).toBe(true);
    }
    expect(isInheritable({ key: "title", label: "t", type: "text" }))
      .toBe(false);
  });
});
