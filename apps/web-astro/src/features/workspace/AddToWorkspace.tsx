import { useState } from "react";
import { LayoutGrid } from "lucide-react";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { getWidget } from "./widgetRegistry";
import "@/features/widgets"; // ensure registry is populated outside /workspace

interface Props {
  /** Widget type id — must exist in the central registry. */
  typeId: string;
  /** Live chart configuration to preserve (country, range, model…). */
  config?: Record<string, unknown>;
  label?: string;
}

/** Reusable Add-to-Workspace action (Mission 3 §10). Preserves the chart's
 *  current configuration — including experimental model ids — through the
 *  versioned workspace schema. */
export function AddToWorkspace({ typeId, config, label }: Props) {
  const workspaces = useWorkspaceStore((s) => s.workspaces);
  const addWidget = useWorkspaceStore((s) => s.addWidget);
  const createWorkspace = useWorkspaceStore((s) => s.createWorkspace);
  const [open, setOpen] = useState(false);
  const [target, setTarget] = useState("");
  const [newName, setNewName] = useState("");
  const [done, setDone] = useState<string | null>(null);

  if (!getWidget(typeId)) return null;

  const add = () => {
    let wsId = target;
    if (newName.trim()) {
      createWorkspace(newName.trim());
      wsId = useWorkspaceStore.getState().activeWorkspaceId ?? "";
    }
    if (!wsId) return;
    addWidget(wsId, typeId, config);
    const name = workspaces.find((w) => w.id === wsId)?.name ?? newName;
    setDone(name);
    setOpen(false);
    setNewName("");
  };

  return (
    <span className="add-to-ws">
      <button
        type="button"
        className="glass-button"
        onClick={() => setOpen(true)}
        title="Add this chart to a workspace"
      >
        <LayoutGrid size={13} aria-hidden="true" />{" "}
        {label ?? "Add to Workspace"}
      </button>
      {done && (
        <span className="body-sm">
          Added to {done} — <a href="/workspace">open workspace</a>
        </span>
      )}
      {open && (
        <div className="ws-dialog-backdrop" role="dialog" aria-modal="true"
             aria-label="Add to workspace" onClick={() => setOpen(false)}>
          <div className="glass ws-dialog" onClick={(e) => e.stopPropagation()}>
            <h3 className="headline-sm">Add to workspace</h3>
            <select className="config-select" value={target}
                    onChange={(e) => setTarget(e.target.value)}>
              <option value="">Select workspace…</option>
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
            <p className="body-sm text-tertiary">or create new:</p>
            <input className="config-select" placeholder="Workspace name"
                   value={newName}
                   onChange={(e) => setNewName(e.target.value)} />
            <div style={{ display: "flex", gap: 8 }}>
              <button type="button" className="btn btn-primary"
                      disabled={!target && !newName.trim()} onClick={add}>
                Add
              </button>
              <button type="button" className="glass-button"
                      onClick={() => setOpen(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </span>
  );
}
