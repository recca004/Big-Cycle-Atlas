import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import {
  workspaceSchema,
  workspaceStorageSchema,
  workspaceExportSchema,
  type Workspace,
  type WorkspaceStorage,
  type StoredLayoutItem,
  type WidgetInstance,
  GRID_COLS,
  type GridBreakpoint,
} from "@/features/workspace/types";
import { getWidget } from "@/features/workspace/widgetRegistry";
import { DEFAULT_WORKSPACES } from "@/features/workspace/defaultWorkspaces";

const STORAGE_KEY = "bca:workspaces:v1";

function uid(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `w-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function now(): string {
  return new Date().toISOString();
}

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v)) as T;
}

/** Fit a stored layout item into the column count of its breakpoint. */
function clampItem(item: StoredLayoutItem, bp: GridBreakpoint): StoredLayoutItem {
  const cols = GRID_COLS[bp];
  const w = Math.max(1, Math.min(item.w, cols));
  const x = Math.max(0, Math.min(item.x, cols - w));
  return { ...item, x, w };
}

function deriveLayouts(
  _widgets: WidgetInstance[],
  lgLayout: StoredLayoutItem[],
): Workspace["layouts"] {
  // md: x/w scaled 12→8; sm: stacked single-flow on a 4-col grid.
  const md = lgLayout.map((it) => {
    const w = Math.max(1, Math.round((it.w / 12) * 8));
    const x = Math.max(0, Math.min(Math.round((it.x / 12) * 8), 8 - w));
    return { ...it, x, w };
  });
  const sm = lgLayout
    .slice()
    .sort((a, b) => a.y - b.y || a.x - b.x)
    .map((it, idx) => ({
      ...it,
      x: 0,
      y: idx * it.h,
      w: 4,
    }));
  return {
    lg: lgLayout.map((i) => clampItem(i, "lg")),
    md: md.map((i) => clampItem(i, "md")),
    sm,
  };
}

function nextFreePosition(
  layout: StoredLayoutItem[],
  _w: number,
  _h: number,
): { x: number; y: number } {
  const bottom = layout.reduce((m, i) => Math.max(m, i.y + i.h), 0);
  return { x: 0, y: bottom };
}

export interface WorkspaceState {
  workspaces: Workspace[];
  activeWorkspaceId: string | null;
  editMode: boolean;
  /** Layout-history stacks (not persisted). Entries snapshot the affected
   *  workspace BEFORE a mutating action so undo restores exactly. */
  _past: { workspaceId: string; snapshot: Workspace }[];
  _future: { workspaceId: string; snapshot: Workspace }[];

  setActiveWorkspace: (id: string) => void;
  toggleEditMode: () => void;
  setEditMode: (v: boolean) => void;

  createWorkspace: (name: string) => void;
  renameWorkspace: (id: string, name: string) => void;
  duplicateWorkspace: (id: string) => void;
  deleteWorkspace: (id: string) => void;
  resetWorkspace: (id: string) => void;

  setLayouts: (
    workspaceId: string,
    layouts: Partial<Record<GridBreakpoint, StoredLayoutItem[]>>,
  ) => void;

  addWidget: (
    workspaceId: string,
    typeId: string,
    config?: Record<string, unknown>,
  ) => void;
  removeWidget: (workspaceId: string, instanceId: string) => void;
  duplicateWidget: (workspaceId: string, instanceId: string) => void;
  toggleCollapsed: (workspaceId: string, instanceId: string) => void;
  updateWidgetConfig: (
    workspaceId: string,
    instanceId: string,
    config: Record<string, unknown>,
  ) => void;
  moveWidgetKeyboard: (
    workspaceId: string,
    instanceId: string,
    dx: number,
    dy: number,
  ) => void;
  toggleLocked: (workspaceId: string, instanceId: string) => void;
  setFilters: (
    workspaceId: string,
    filters: Partial<Workspace["filters"]>,
  ) => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  /** Record the pre-mutation snapshot — call inside every widget/layout
   *  mutation. Cheap (reference copy); capped at 50. */
  _record: (workspaceId: string) => void;

  exportWorkspace: (id: string) => string | null;
  importWorkspace: (json: string) => { ok: boolean; error?: string | undefined };
  resetAll: () => void;
}

function freshWorkspace(name: string, builtin = false): Workspace {
  return {
    id: uid(),
    name,
    widgets: [],
    layouts: { lg: [], md: [], sm: [] },
    createdAt: now(),
    updatedAt: now(),
    builtin,
    filters: {
      country: null, countries: [], startYear: null, methodScope: "both",
    },
  };
}

function initialState(): Pick<
  WorkspaceState,
  "workspaces" | "activeWorkspaceId"
> {
  const builtins = DEFAULT_WORKSPACES.map((d) => d());
  return {
    workspaces: builtins,
    activeWorkspaceId: builtins[0]?.id ?? null,
  };
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      ...initialState(),
      editMode: false,
      _past: [],
      _future: [],

      _record: (workspaceId) =>
        set((s) => {
          const ws = s.workspaces.find((w) => w.id === workspaceId);
          if (!ws) return s;
          return {
            _past: [...s._past.slice(-49),
                    { workspaceId, snapshot: ws }],
            _future: [],
          };
        }),

      undo: () =>
        set((s) => {
          const last = s._past.at(-1);
          if (!last) return s;
          const current = s.workspaces.find(
            (w) => w.id === last.workspaceId);
          if (!current) return { _past: s._past.slice(0, -1) };
          return {
            workspaces: s.workspaces.map((w) =>
              w.id === last.workspaceId
                ? { ...last.snapshot, updatedAt: now() } : w),
            _past: s._past.slice(0, -1),
            _future: [...s._future,
                      { workspaceId: last.workspaceId, snapshot: current }],
          };
        }),

      redo: () =>
        set((s) => {
          const next = s._future.at(-1);
          if (!next) return s;
          const current = s.workspaces.find(
            (w) => w.id === next.workspaceId);
          if (!current) return { _future: s._future.slice(0, -1) };
          return {
            workspaces: s.workspaces.map((w) =>
              w.id === next.workspaceId
                ? { ...next.snapshot, updatedAt: now() } : w),
            _future: s._future.slice(0, -1),
            _past: [...s._past,
                    { workspaceId: next.workspaceId, snapshot: current }],
          };
        }),

      canUndo: () => get()._past.length > 0,
      canRedo: () => get()._future.length > 0,

      toggleLocked: (workspaceId, instanceId) => {
        const ws = get().workspaces.find((w) => w.id === workspaceId);
        const wdg = ws?.widgets.find((w) => w.id === instanceId);
        if (!wdg) return;
        get()._record(workspaceId);
        set((s) => ({
          workspaces: s.workspaces.map((w) =>
            w.id !== workspaceId ? w : {
              ...w, updatedAt: now(),
              widgets: w.widgets.map((x) =>
                x.id === instanceId ? { ...x, locked: !x.locked } : x),
            }),
        }));
      },

      setFilters: (workspaceId, filters) =>
        set((s) => ({
          workspaces: s.workspaces.map((w) =>
            w.id !== workspaceId ? w : {
              ...w, updatedAt: now(),
              filters: { ...w.filters, ...filters },
            }),
        })),

      setActiveWorkspace: (id) =>
        set({ activeWorkspaceId: id, editMode: false }),

      toggleEditMode: () => set((s) => ({ editMode: !s.editMode })),
      setEditMode: (v) => set({ editMode: v }),

      createWorkspace: (name) => {
        const ws = freshWorkspace(name.trim() || "Untitled workspace");
        set((s) => ({
          workspaces: [...s.workspaces, ws],
          activeWorkspaceId: ws.id,
        }));
      },

      renameWorkspace: (id, name) =>
        set((s) => ({
          workspaces: s.workspaces.map((w) =>
            w.id === id ? { ...w, name: name.trim() || w.name, updatedAt: now() } : w,
          ),
        })),

      duplicateWorkspace: (id) =>
        set((s) => {
          const src = s.workspaces.find((w) => w.id === id);
          if (!src) return s;
          const copy = clone(src);
          copy.id = uid();
          copy.name = `${src.name} (copy)`;
          copy.builtin = false;
          copy.createdAt = now();
          copy.updatedAt = now();
          copy.widgets = copy.widgets.map((w) => ({ ...w, id: uid() }));
          const idMap = new Map(
            src.widgets.map((w, i) => [w.id, copy.widgets[i]!.id]),
          );
          (Object.keys(copy.layouts) as GridBreakpoint[]).forEach((bp) => {
            copy.layouts[bp] = copy.layouts[bp]
              .map((it) => ({ ...it, i: idMap.get(it.i) ?? it.i }))
              .filter((it) => idMap.has(it.i));
          });
          return {
            workspaces: [...s.workspaces, copy],
            activeWorkspaceId: copy.id,
          };
        }),

      deleteWorkspace: (id) =>
        set((s) => {
          const remaining = s.workspaces.filter((w) => w.id !== id);
          return {
            workspaces: remaining,
            activeWorkspaceId:
              s.activeWorkspaceId === id
                ? (remaining[0]?.id ?? null)
                : s.activeWorkspaceId,
          };
        }),

      resetWorkspace: (id) => {
        get()._record(id);
        set((s) => {
          const idx = s.workspaces.findIndex((w) => w.id === id);
          if (idx === -1) return s;
          const current = s.workspaces[idx]!;
          const defaultFactory = DEFAULT_WORKSPACES_BY_NAME.get(current.name);
          const reset = defaultFactory
            ? defaultFactory()
            : freshWorkspace(current.name, current.builtin);
          reset.id = current.id;
          reset.builtin = current.builtin;
          reset.createdAt = current.createdAt;
          const workspaces = [...s.workspaces];
          workspaces[idx] = reset;
          return { workspaces };
        });
      },

      setLayouts: (workspaceId, layouts) => {
        get()._record(workspaceId);
        set((s) => ({
          workspaces: s.workspaces.map((w) =>
            w.id === workspaceId
              ? {
                  ...w,
                  layouts: { ...w.layouts, ...layouts } as Workspace["layouts"],
                  updatedAt: now(),
                }
              : w,
          ),
        }));
      },

      addWidget: (workspaceId, typeId, config) => {
        get()._record(workspaceId);
        set((s) => {
          const def = getWidget(typeId);
          if (!def) return s;
          return {
            workspaces: s.workspaces.map((w) => {
              if (w.id !== workspaceId) return w;
              const id = uid();
              const pos = nextFreePosition(
                w.layouts.lg,
                def.defaultSize.w,
                def.defaultSize.h,
              );
              const instance: WidgetInstance = {
                id,
                type: typeId,
                config: {
                  ...Object.fromEntries(
                    def.configFields
                      .filter((f) => f.default !== undefined)
                      .map((f) => [f.key, f.default]),
                  ),
                  // Add-to-Workspace passes the chart's live configuration;
                  // only keys declared by the widget's schema are kept.
                  ...Object.fromEntries(
                    Object.entries(config ?? {}).filter(([k]) =>
                      def.configFields.some((f) => f.key === k)),
                  ),
                },
                collapsed: false,
                locked: false,
              };
              const lg = [
                ...w.layouts.lg,
                {
                  i: id,
                  x: pos.x,
                  y: pos.y,
                  w: def.defaultSize.w,
                  h: def.defaultSize.h,
                },
              ];
              return {
                ...w,
                widgets: [...w.widgets, instance],
                layouts: deriveLayouts(
                  [...w.widgets, instance],
                  lg,
                ),
                updatedAt: now(),
              };
            }),
          };
        });
      },

      removeWidget: (workspaceId, instanceId) => {
        get()._record(workspaceId);
        set((s) => ({
          workspaces: s.workspaces.map((w) => {
            if (w.id !== workspaceId) return w;
            return {
              ...w,
              widgets: w.widgets.filter((x) => x.id !== instanceId),
              layouts: {
                lg: w.layouts.lg.filter((x) => x.i !== instanceId),
                md: w.layouts.md.filter((x) => x.i !== instanceId),
                sm: w.layouts.sm.filter((x) => x.i !== instanceId),
              },
              updatedAt: now(),
            };
          }),
        }));
      },

      duplicateWidget: (workspaceId, instanceId) => {
        get()._record(workspaceId);
        set((s) => ({
          workspaces: s.workspaces.map((w) => {
            if (w.id !== workspaceId) return w;
            const src = w.widgets.find((x) => x.id === instanceId);
            const srcLayout = w.layouts.lg.find((x) => x.i === instanceId);
            if (!src || !srcLayout) return w;
            const id = uid();
            const pos = nextFreePosition(w.layouts.lg, srcLayout.w, srcLayout.h);
            const copy: WidgetInstance = { ...clone(src), id };
            const lg = [
              ...w.layouts.lg,
              { i: id, x: pos.x, y: pos.y, w: srcLayout.w, h: srcLayout.h },
            ];
            return {
              ...w,
              widgets: [...w.widgets, copy],
              layouts: deriveLayouts([...w.widgets, copy], lg),
              updatedAt: now(),
            };
          }),
        }));
      },

      toggleCollapsed: (workspaceId, instanceId) => {
        get()._record(workspaceId);
        set((s) => ({
          workspaces: s.workspaces.map((w) =>
            w.id === workspaceId
              ? {
                  ...w,
                  widgets: w.widgets.map((x) =>
                    x.id === instanceId
                      ? { ...x, collapsed: !x.collapsed }
                      : x,
                  ),
                  updatedAt: now(),
                }
              : w,
          ),
        }));
      },

      updateWidgetConfig: (workspaceId, instanceId, config) => {
        get()._record(workspaceId);
        set((s) => ({
          workspaces: s.workspaces.map((w) =>
            w.id === workspaceId
              ? {
                  ...w,
                  widgets: w.widgets.map((x) =>
                    x.id === instanceId
                      ? { ...x, config: { ...x.config, ...config } }
                      : x,
                  ),
                  updatedAt: now(),
                }
              : w,
          ),
        }));
      },

      moveWidgetKeyboard: (workspaceId, instanceId, dx, dy) => {
        get()._record(workspaceId);
        set((s) => ({
          workspaces: s.workspaces.map((w) => {
            if (w.id !== workspaceId) return w;
            const lg = w.layouts.lg.map((it) =>
              it.i === instanceId
                ? {
                    ...it,
                    x: Math.max(0, Math.min(it.x + dx, GRID_COLS.lg - it.w)),
                    y: Math.max(0, it.y + dy),
                  }
                : it,
            );
            return { ...w, layouts: deriveLayouts(w.widgets, lg), updatedAt: now() };
          }),
        }));
      },

      exportWorkspace: (id) => {
        const ws = get().workspaces.find((w) => w.id === id);
        if (!ws) return null;
        return JSON.stringify(
          { version: 1, kind: "big-cycle-atlas-workspace", workspace: ws },
          null,
          2,
        );
      },

      importWorkspace: (json) => {
        let parsed: unknown;
        try {
          parsed = JSON.parse(json);
        } catch {
          return { ok: false, error: "Not valid JSON." };
        }
        const result = workspaceExportSchema.safeParse(parsed);
        if (!result.success) {
          return {
            ok: false,
            error: "Not a valid Big Cycle Atlas workspace file.",
          };
        }
        const ws = result.data.workspace;
        // Reject unknown widget types rather than crashing.
        const unknown = ws.widgets.filter((w) => !getWidget(w.type));
        const widgets = ws.widgets.filter((w) => getWidget(w.type));
        const layoutIds = new Set(widgets.map((w) => w.id));
        const imported: Workspace = {
          ...ws,
          id: uid(),
          name: ws.name || "Imported workspace",
          builtin: false,
          widgets,
          layouts: {
            lg: ws.layouts.lg.filter((i) => layoutIds.has(i.i)),
            md: ws.layouts.md.filter((i) => layoutIds.has(i.i)),
            sm: ws.layouts.sm.filter((i) => layoutIds.has(i.i)),
          },
          createdAt: now(),
          updatedAt: now(),
        };
        // Ensure every widget has a layout entry.
        for (const wdg of imported.widgets) {
          for (const bp of ["lg", "md", "sm"] as const) {
            if (!imported.layouts[bp].some((l) => l.i === wdg.id)) {
              const def = getWidget(wdg.type)!;
              imported.layouts[bp].push({
                i: wdg.id,
                x: 0,
                y: nextFreePosition(imported.layouts[bp], def.defaultSize.w, def.defaultSize.h).y,
                w: Math.min(def.defaultSize.w, GRID_COLS[bp]),
                h: def.defaultSize.h,
              });
            }
          }
        }
        set((s) => ({
          workspaces: [...s.workspaces, imported],
          activeWorkspaceId: imported.id,
        }));
        return {
          ok: true,
          error:
            unknown.length > 0
              ? `Imported with ${unknown.length} unknown widget(s) skipped.`
              : undefined,
        };
      },

      resetAll: () => {
        set(initialState());
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({
        workspaces: s.workspaces,
        activeWorkspaceId: s.activeWorkspaceId,
      }),
      merge: (persisted, current) => {
        // Validate the persisted payload; fall back to defaults on failure.
        const parsed = workspaceStorageSchema.safeParse({
          version: 1,
          ...(persisted as object),
        });
        if (!parsed.success) return current;
        const data: WorkspaceStorage = parsed.data;
        const ids = new Set(data.workspaces.map((w) => w.id));
        // Each workspace must individually validate too.
        const workspaces = data.workspaces.filter(
          (w) => workspaceSchema.safeParse(w).success,
        );
        return {
          ...current,
          workspaces: workspaces.length > 0 ? workspaces : current.workspaces,
          activeWorkspaceId:
            data.activeWorkspaceId && ids.has(data.activeWorkspaceId)
              ? data.activeWorkspaceId
              : (workspaces[0]?.id ?? current.activeWorkspaceId),
        };
      },
    },
  ),
);

/** Name → factory lookup for resetWorkspace. */
const DEFAULT_WORKSPACES_BY_NAME = new Map(
  DEFAULT_WORKSPACES.map((f) => [f().name, f]),
);
