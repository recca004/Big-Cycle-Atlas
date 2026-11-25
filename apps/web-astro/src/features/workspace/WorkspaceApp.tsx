import { useMemo, useRef, useState } from "react";
import {
  ResponsiveGridLayout,
  useContainerWidth,
  verticalCompactor,
  type Layout,
  type ResponsiveLayouts,
} from "react-grid-layout";
import "react-grid-layout/css/styles.css";
import {
  Download,
  LayoutGrid,
  Pencil,
  Undo2,
  Redo2,
  Plus,
  RotateCcw,
  Upload,
  Copy,
  Trash2,
  Check,
} from "lucide-react";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { widgetsByCategory } from "./widgetRegistry";
import { WidgetFrame } from "./WidgetFrame";
import {
  GRID_BREAKPOINTS,
  GRID_COLS,
  type GridBreakpoint,
  type StoredLayoutItem,
} from "./types";

// Registers all widget types.
import "@/features/widgets";

const BREAKPOINTS = GRID_BREAKPOINTS as Record<GridBreakpoint, number>;
const COLS = GRID_COLS as Record<GridBreakpoint, number>;

function toStored(layout: Layout): StoredLayoutItem[] {
  return layout.map((it) => ({
    i: String(it.i),
    x: it.x,
    y: it.y,
    w: it.w,
    h: it.h,
  }));
}

export function WorkspaceApp() {
  const workspaces = useWorkspaceStore((s) => s.workspaces);
  const activeId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const editMode = useWorkspaceStore((s) => s.editMode);
  const setActive = useWorkspaceStore((s) => s.setActiveWorkspace);
  const toggleEdit = useWorkspaceStore((s) => s.toggleEditMode);
  const setLayouts = useWorkspaceStore((s) => s.setLayouts);
  const addWidget = useWorkspaceStore((s) => s.addWidget);
  const createWorkspace = useWorkspaceStore((s) => s.createWorkspace);
  const renameWorkspace = useWorkspaceStore((s) => s.renameWorkspace);
  const duplicateWorkspace = useWorkspaceStore((s) => s.duplicateWorkspace);
  const deleteWorkspace = useWorkspaceStore((s) => s.deleteWorkspace);
  const resetWorkspace = useWorkspaceStore((s) => s.resetWorkspace);
  const exportWorkspace = useWorkspaceStore((s) => s.exportWorkspace);
  const importWorkspace = useWorkspaceStore((s) => s.importWorkspace);
  const undo = useWorkspaceStore((s) => s.undo);
  const redo = useWorkspaceStore((s) => s.redo);
  const setFilters = useWorkspaceStore((s) => s.setFilters);
  const canUndo = useWorkspaceStore((s) => s._past.length > 0);
  const canRedo = useWorkspaceStore((s) => s._future.length > 0);

  const [libraryOpen, setLibraryOpen] = useState(false);
  const [manageOpen, setManageOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const importRef = useRef<HTMLInputElement>(null);
  const { width, containerRef, mounted } = useContainerWidth();

  const workspace = workspaces.find((w) => w.id === activeId) ?? workspaces[0];

  const layouts: ResponsiveLayouts<string> | undefined = useMemo(() => {
    if (!workspace) return undefined;
    return {
      lg: workspace.layouts.lg,
      md: workspace.layouts.md,
      sm: workspace.layouts.sm,
    };
  }, [workspace]);

  if (!workspace) {
    return (
      <div className="glass-subtle state-box">
        <p className="headline-sm">No workspaces</p>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => createWorkspace("My workspace")}
        >
          Create a workspace
        </button>
      </div>
    );
  }

  const ws = workspace;

  const onLayoutChange = (_layout: Layout, all: ResponsiveLayouts<string>) => {
    if (!editMode) return;
    const stored: Partial<Record<GridBreakpoint, StoredLayoutItem[]>> = {};
    for (const bp of ["lg", "md", "sm"] as const) {
      if (all[bp]) stored[bp] = toStored(all[bp]);
    }
    setLayouts(ws.id, stored);
  };

  const doExport = () => {
    const json = exportWorkspace(ws.id);
    if (!json) return;
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${ws.name.replaceAll(/[^a-z0-9]+/gi, "-").toLowerCase()}.workspace.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const doImport = async (file: File) => {
    const text = await file.text();
    const result = importWorkspace(text);
    setNotice(
      result.ok
        ? result.error ?? `Imported "${file.name}".`
        : `Import failed: ${result.error}`,
    );
    setTimeout(() => setNotice(null), 6000);
  };

  return (
    <div className="workspace-app">
      <div className="workspace-toolbar glass">
        <div className="workspace-tabs" role="tablist" aria-label="Workspaces">
          {workspaces.map((w) => (
            <button
              key={w.id}
              type="button"
              role="tab"
              aria-selected={w.id === ws.id}
              className={`ws-tab ${w.id === ws.id ? "ws-tab-active" : ""}`}
              onClick={() => setActive(w.id)}
            >
              {w.name}
            </button>
          ))}
        </div>
        <div className="workspace-actions">
          <button
            type="button"
            className={`glass-button ${editMode ? "btn-active" : ""}`}
            onClick={toggleEdit}
            aria-pressed={editMode}
            title={editMode ? "Exit edit mode" : "Edit layout"}
          >
            <Pencil size={14} aria-hidden="true" />
            <span className="btn-label">{editMode ? "Done" : "Edit"}</span>
          </button>
          <button
            type="button"
            className="glass-button"
            onClick={undo}
            disabled={!canUndo}
            title="Undo layout change"
            aria-label="Undo layout change"
          >
            <Undo2 size={14} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="glass-button"
            onClick={redo}
            disabled={!canRedo}
            title="Redo layout change"
            aria-label="Redo layout change"
          >
            <Redo2 size={14} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="glass-button"
            onClick={() => setLibraryOpen((v) => !v)}
            aria-expanded={libraryOpen}
            title="Add widget"
          >
            <Plus size={14} aria-hidden="true" />
            <span className="btn-label">Add</span>
          </button>
          <button
            type="button"
            className="glass-button"
            onClick={() => setManageOpen((v) => !v)}
            aria-expanded={manageOpen}
            title="Manage workspaces"
          >
            <LayoutGrid size={14} aria-hidden="true" />
            <span className="btn-label">Manage</span>
          </button>
          <button
            type="button"
            className="glass-button"
            onClick={doExport}
            title="Export workspace JSON"
          >
            <Download size={14} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="glass-button"
            onClick={() => importRef.current?.click()}
            title="Import workspace JSON"
          >
            <Upload size={14} aria-hidden="true" />
          </button>
          <input
            ref={importRef}
            type="file"
            accept="application/json,.json"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void doImport(f);
              e.target.value = "";
            }}
          />
        </div>
      </div>

      {notice && (
        <div className="glass-subtle ws-notice" role="status">
          {notice}
        </div>
      )}

      {manageOpen && (
        <div className="glass ws-manage">
          <div className="ws-manage-row">
            <strong>{ws.name}</strong>
            <span className="pill-row">
              <button
                type="button"
                className="glass-button"
                onClick={() => {
                  const name = prompt("Rename workspace", ws.name);
                  if (name) renameWorkspace(ws.id, name);
                }}
              >
                <Pencil size={12} /> Rename
              </button>
              <button
                type="button"
                className="glass-button"
                onClick={() => duplicateWorkspace(ws.id)}
              >
                <Copy size={12} /> Duplicate
              </button>
              <button
                type="button"
                className="glass-button"
                onClick={() => {
                  if (confirm(`Reset "${ws.name}" to its default layout?`))
                    resetWorkspace(ws.id);
                }}
              >
                <RotateCcw size={12} /> Reset
              </button>
              {!ws.builtin && (
                <button
                  type="button"
                  className="glass-button widget-btn-danger"
                  onClick={() => {
                    if (confirm(`Delete workspace "${ws.name}"?`))
                      deleteWorkspace(ws.id);
                  }}
                >
                  <Trash2 size={12} /> Delete
                </button>
              )}
            </span>
          </div>
          <button
            type="button"
            className="glass-button"
            onClick={() => {
              const name = prompt("New workspace name", "My workspace");
              if (name) createWorkspace(name);
            }}
          >
            <Plus size={12} /> New workspace
          </button>
        </div>
      )}

      <div className="workspace-filters" role="group" aria-label="Workspace filters">
        <label className="body-sm">
          Country{" "}
          <select
            className="config-select"
            value={ws.filters.country ?? ""}
            onChange={(e) =>
              setFilters(ws.id, { country: e.target.value || null })
            }
          >
            <option value="">All</option>
            {["USA","CHN","JPN","DEU","FRA","GBR","CHE","IND"].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="body-sm">
          From{" "}
          <select
            className="config-select"
            value={ws.filters.startYear ?? ""}
            onChange={(e) =>
              setFilters(ws.id, {
                startYear: e.target.value ? Number(e.target.value) : null,
              })
            }
          >
            <option value="">Default</option>
            {[1996, 2000, 2005, 2010, 2015, 2020].map((y) => (
              <option key={y}>{y}</option>
            ))}
          </select>
        </label>
        <span className="body-sm text-tertiary">
          Widgets inherit these filters unless overridden in their settings.
        </span>
      </div>

      {libraryOpen && (
        <div className="glass ws-library">
          <div className="ws-library-head">
            <strong>Widget library</strong>
            <button
              type="button"
              className="glass-button"
              onClick={() => setLibraryOpen(false)}
              aria-label="Close widget library"
            >
              <Check size={14} />
            </button>
          </div>
          <div className="ws-library-groups">
            {widgetsByCategory().map(([category, defs]) => (
              <div key={category} className="ws-library-group">
                <p className="label-md text-tertiary ws-library-cat">
                  {category}
                </p>
                {defs.map((def) => (
                  <div key={def.typeId} className="ws-library-item">
                    <div>
                      <p className="ws-library-name">{def.displayName}</p>
                      <p className="ws-library-desc">{def.description}</p>
                    </div>
                    <button
                      type="button"
                      className="glass-button"
                      title={`Add ${def.displayName}`}
                      onClick={() => addWidget(ws.id, def.typeId)}
                    >
                      <Plus size={14} />
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      <div ref={containerRef} className="workspace-grid">
        {mounted && (
          <ResponsiveGridLayout
            width={width}
            breakpoints={BREAKPOINTS}
            cols={COLS}
            layouts={layouts ?? {}}
            rowHeight={56}
            margin={[12, 12] as const}
            dragConfig={{
              enabled: editMode,
              handle: ".widget-drag-handle",
            }}
            resizeConfig={{ enabled: editMode }}
            compactor={verticalCompactor}
            onLayoutChange={onLayoutChange}
          >
            {ws.widgets.map((instance) => (
              <div key={instance.id} className="grid-cell"
                   data-grid={instance.locked ? { static: true } : undefined}>
                <WidgetFrame
                  workspaceId={ws.id}
                  instance={instance}
                  editMode={editMode}
                />
              </div>
            ))}
          </ResponsiveGridLayout>
        )}
        {ws.widgets.length === 0 && (
          <div className="glass-subtle state-box">
            <p className="headline-sm">Empty workspace</p>
            <p className="body-sm">
              Open the widget library and add components to build your
              dashboard.
            </p>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setLibraryOpen(true)}
            >
              <Plus size={14} /> Add a widget
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
