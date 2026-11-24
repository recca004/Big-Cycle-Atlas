import { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Copy,
  GripVertical,
  Maximize2,
  Settings2,
  Trash2,
  MoveUp,
  MoveDown,
  MoveLeft,
  MoveRight,
} from "lucide-react";
import { getWidget } from "./widgetRegistry";
import type { WidgetInstance } from "./types";
import { useWorkspaceStore } from "@/stores/workspaceStore";

interface FrameProps {
  workspaceId: string;
  instance: WidgetInstance;
  editMode: boolean;
}

/** Frame chrome around a widget — drag handle, controls, title. */
export function WidgetFrame({ workspaceId, instance, editMode }: FrameProps) {
  const def = getWidget(instance.type);
  const [configOpen, setConfigOpen] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const removeWidget = useWorkspaceStore((s) => s.removeWidget);
  const duplicateWidget = useWorkspaceStore((s) => s.duplicateWidget);
  const toggleCollapsed = useWorkspaceStore((s) => s.toggleCollapsed);
  const updateWidgetConfig = useWorkspaceStore((s) => s.updateWidgetConfig);
  const moveWidgetKeyboard = useWorkspaceStore((s) => s.moveWidgetKeyboard);

  const title =
    (instance.config.title as string) || def?.displayName || instance.type;

  const body = (
    <>
      <header className="widget-header">
        {editMode && (
          <span className="widget-drag-handle" title="Drag to move">
            <GripVertical size={14} aria-hidden="true" />
          </span>
        )}
        <span className="widget-title" title={def?.description}>
          {title}
        </span>
        <span className="widget-controls">
          {editMode && (
            <>
              <span className="move-cluster" role="group" aria-label={`Move ${title} with keyboard controls`}>
                <button
                  type="button"
                  className="widget-btn"
                  title="Move up"
                  aria-label={`Move ${title} up`}
                  onClick={() => moveWidgetKeyboard(workspaceId, instance.id, 0, -1)}
                >
                  <MoveUp size={12} />
                </button>
                <button
                  type="button"
                  className="widget-btn"
                  title="Move left"
                  aria-label={`Move ${title} left`}
                  onClick={() => moveWidgetKeyboard(workspaceId, instance.id, -1, 0)}
                >
                  <MoveLeft size={12} />
                </button>
                <button
                  type="button"
                  className="widget-btn"
                  title="Move right"
                  aria-label={`Move ${title} right`}
                  onClick={() => moveWidgetKeyboard(workspaceId, instance.id, 1, 0)}
                >
                  <MoveRight size={12} />
                </button>
                <button
                  type="button"
                  className="widget-btn"
                  title="Move down"
                  aria-label={`Move ${title} down`}
                  onClick={() => moveWidgetKeyboard(workspaceId, instance.id, 0, 1)}
                >
                  <MoveDown size={12} />
                </button>
              </span>
              {def && def.configFields.length > 0 && (
                <button
                  type="button"
                  className="widget-btn"
                  title="Configure"
                  aria-label={`Configure ${title}`}
                  aria-expanded={configOpen}
                  onClick={() => setConfigOpen((v) => !v)}
                >
                  <Settings2 size={14} />
                </button>
              )}
              <button
                type="button"
                className="widget-btn"
                title="Duplicate"
                aria-label={`Duplicate ${title}`}
                onClick={() => duplicateWidget(workspaceId, instance.id)}
              >
                <Copy size={14} />
              </button>
            </>
          )}
          <button
            type="button"
            className="widget-btn"
            title={instance.collapsed ? "Expand" : "Collapse"}
            aria-label={`${instance.collapsed ? "Expand" : "Collapse"} ${title}`}
            onClick={() => toggleCollapsed(workspaceId, instance.id)}
          >
            {instance.collapsed ? (
              <ChevronDown size={14} />
            ) : (
              <ChevronUp size={14} />
            )}
          </button>
          {editMode && (
            <button
              type="button"
              className="widget-btn"
              title="Full screen"
              aria-label={`View ${title} full screen`}
              onClick={() => setFullscreen(true)}
            >
              <Maximize2 size={14} />
            </button>
          )}
          {editMode && (
            <button
              type="button"
              className="widget-btn widget-btn-danger"
              title="Remove"
              aria-label={`Remove ${title}`}
              onClick={() => removeWidget(workspaceId, instance.id)}
            >
              <Trash2 size={14} />
            </button>
          )}
        </span>
      </header>
      {configOpen && def && (
        <div className="widget-config" role="group" aria-label={`${title} settings`}>
          {def.configFields.map((field) => (
            <label key={field.key} className="widget-config-field">
              <span className="label-md text-tertiary">{field.label}</span>
              <ConfigInput
                field={field}
                value={instance.config[field.key]}
                onChange={(v) =>
                  updateWidgetConfig(workspaceId, instance.id, {
                    [field.key]: v,
                  })
                }
              />
            </label>
          ))}
        </div>
      )}
      {!instance.collapsed && (
        <div className="widget-body">
          {def ? (
            <def.component
              instanceId={instance.id}
              config={instance.config}
              editMode={editMode}
            />
          ) : (
            <div className="widget-state">
              <p className="body-sm widget-state-title">Unknown widget</p>
              <p className="widget-state-detail">
                Type &quot;{instance.type}&quot; is not registered.
              </p>
            </div>
          )}
        </div>
      )}
    </>
  );

  return (
    <>
      <section className={`widget-frame ${editMode ? "widget-frame-edit" : ""}`}>
        {body}
      </section>
      {fullscreen && (
        <div
          className="widget-fullscreen"
          role="dialog"
          aria-modal="true"
          aria-label={title}
          onClick={() => setFullscreen(false)}
        >
          <div
            className="glass widget-fullscreen-panel"
            onClick={(e) => e.stopPropagation()}
          >
            {body}
          </div>
        </div>
      )}
    </>
  );
}

function ConfigInput({
  field,
  value,
  onChange,
}: {
  field: import("./widgetRegistry").ConfigField;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  if (field.type === "boolean") {
    return (
      <input
        type="checkbox"
        checked={Boolean(value)}
        onChange={(e) => onChange(e.target.checked)}
      />
    );
  }
  if (field.type === "countries") {
    const selected = Array.isArray(value) ? (value as string[]) : [];
    return (
      <div className="config-check-list">
        {field.options?.map((opt) => (
          <label key={opt.value} className="config-check">
            <input
              type="checkbox"
              checked={selected.includes(opt.value)}
              onChange={(e) => {
                const next = e.target.checked
                  ? [...selected, opt.value]
                  : selected.filter((v) => v !== opt.value);
                onChange(next);
              }}
            />
            {opt.label}
          </label>
        ))}
      </div>
    );
  }
  if (
    field.type === "country" ||
    field.type === "indicator" ||
    field.type === "force" ||
    field.type === "chart-type"
  ) {
    return (
      <select
        className="config-select"
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">—</option>
        {field.options?.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    );
  }
  if (field.type === "number") {
    return (
      <input
        type="number"
        className="config-select"
        value={Number(value ?? field.default ?? 0)}
        min={field.min}
        max={field.max}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    );
  }
  return (
    <input
      type="text"
      className="config-select"
      value={(value as string) ?? ""}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}
