import { describe, it, expect, beforeEach } from "vitest";
import "@/features/widgets";
import { useWorkspaceStore } from "@/stores/workspaceStore";

const S = () => useWorkspaceStore.getState();

function firstWs() {
  return S().workspaces[0]!;
}

beforeEach(() => {
  localStorage.clear();
  S().resetAll();
});

describe("workspace store", () => {
  it("seeds default workspaces", () => {
    expect(S().workspaces.length).toBeGreaterThanOrEqual(6);
    expect(S().activeWorkspaceId).toBe(firstWs().id);
  });

  it("creates and renames workspaces", () => {
    const before = S().workspaces.length;
    S().createWorkspace("Research desk");
    expect(S().workspaces.length).toBe(before + 1);
    const ws = S().workspaces.at(-1)!;
    expect(ws.name).toBe("Research desk");
    S().renameWorkspace(ws.id, "Renamed");
    expect(S().workspaces.find((w) => w.id === ws.id)!.name).toBe("Renamed");
  });

  it("duplicates a workspace with fresh ids", () => {
    const src = firstWs();
    S().duplicateWorkspace(src.id);
    const copy = S().workspaces.at(-1)!;
    expect(copy.id).not.toBe(src.id);
    expect(copy.name).toContain(src.name);
    expect(copy.widgets.length).toBe(src.widgets.length);
    for (const w of copy.widgets) {
      expect(src.widgets.some((x) => x.id === w.id)).toBe(false);
    }
  });

  it("addWidget merges definition config defaults", () => {
    S().createWorkspace("T");
    const ws = S().workspaces.at(-1)!;
    S().addWidget(ws.id, "credit-gap");
    const w = S().workspaces.at(-1)!.widgets[0]!;
    expect(w.config.indicator).toBe("CREDIT_TO_GDP_GAP");
    expect(w.config.country).toBe("USA");
  });

  it("removes and duplicates widgets", () => {
    const ws = firstWs();
    const wid = ws.widgets[0]!.id;
    S().duplicateWidget(ws.id, wid);
    const after = S().workspaces.find((w) => w.id === ws.id)!;
    expect(after.widgets.length).toBe(ws.widgets.length + 1);
    S().removeWidget(ws.id, wid);
    const afterRm = S().workspaces.find((w) => w.id === ws.id)!;
    expect(afterRm.widgets.some((x) => x.id === wid)).toBe(false);
    expect(afterRm.layouts.lg.some((l) => l.i === wid)).toBe(false);
  });

  it("updateWidgetConfig merges keys", () => {
    const ws = firstWs();
    const wid = ws.widgets[0]!.id;
    S().updateWidgetConfig(ws.id, wid, { country: "DEU" });
    const w = S().workspaces.find((x) => x.id === ws.id)!.widgets[0]!;
    expect(w.config.country).toBe("DEU");
  });

  it("moveWidgetKeyboard shifts layout position within bounds", () => {
    const ws = firstWs();
    const wid = ws.widgets[0]!.id;
    const x0 = ws.layouts.lg.find((l) => l.i === wid)!.x;
    S().moveWidgetKeyboard(ws.id, wid, 1, 0);
    const x1 = S().workspaces.find((w) => w.id === ws.id)!.layouts.lg.find((l) => l.i === wid)!.x;
    expect(x1).toBe(x0 + 1);
  });

  it("export/import roundtrips a workspace", () => {
    const ws = firstWs();
    const json = S().exportWorkspace(ws.id)!;
    expect(JSON.parse(json).version).toBe(1);
    const before = S().workspaces.length;
    const res = S().importWorkspace(json);
    expect(res.ok).toBe(true);
    expect(S().workspaces.length).toBe(before + 1);
  });

  it("rejects invalid JSON and wrong payload shape", () => {
    expect(S().importWorkspace("not json{{").ok).toBe(false);
    expect(S().importWorkspace('{"version":1}').ok).toBe(false);
    expect(S().importWorkspace('{"version":99,"kind":"big-cycle-atlas-workspace","workspace":{}}').ok).toBe(false);
  });

  it("drops unknown widget types on import without crashing", () => {
    const ws = firstWs();
    const json = S().exportWorkspace(ws.id)!;
    const obj = JSON.parse(json);
    obj.workspace.widgets.push({ id: "x1", type: "bogus-widget", config: {}, collapsed: false });
    obj.workspace.layouts.lg.push({ i: "x1", x: 0, y: 0, w: 3, h: 3 });
    const res = S().importWorkspace(JSON.stringify(obj));
    expect(res.ok).toBe(true);
    const imported = S().workspaces.at(-1)!;
    expect(imported.widgets.some((w) => w.type === "bogus-widget")).toBe(false);
  });
});
