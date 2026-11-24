import { z } from "zod";

/** Persisted workspace schema — versioned for safe import/export. */

export const GRID_COLS = { lg: 12, md: 8, sm: 4 } as const;
export const GRID_BREAKPOINTS = { lg: 1200, md: 768, sm: 0 } as const;
export type GridBreakpoint = keyof typeof GRID_COLS;

export const layoutItemSchema = z.object({
  i: z.string(),
  x: z.number().int().min(0),
  y: z.number().int().min(0),
  w: z.number().int().min(1),
  h: z.number().int().min(1),
});
export type StoredLayoutItem = z.infer<typeof layoutItemSchema>;

export const widgetInstanceSchema = z.object({
  id: z.string().min(1),
  type: z.string().min(1),
  config: z.record(z.string(), z.unknown()).default({}),
  collapsed: z.boolean().default(false),
});
export type WidgetInstance = z.infer<typeof widgetInstanceSchema>;

export const workspaceSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1).max(80),
  widgets: z.array(widgetInstanceSchema),
  layouts: z.object({
    lg: z.array(layoutItemSchema),
    md: z.array(layoutItemSchema),
    sm: z.array(layoutItemSchema),
  }),
  createdAt: z.string(),
  updatedAt: z.string(),
  builtin: z.boolean().default(false),
});
export type Workspace = z.infer<typeof workspaceSchema>;

export const workspaceStorageSchema = z.object({
  version: z.literal(1),
  workspaces: z.array(workspaceSchema),
  activeWorkspaceId: z.string().nullable(),
});
export type WorkspaceStorage = z.infer<typeof workspaceStorageSchema>;

/** Single-workspace export payload (also versioned). */
export const workspaceExportSchema = z.object({
  version: z.literal(1),
  kind: z.literal("big-cycle-atlas-workspace"),
  workspace: workspaceSchema,
});
export type WorkspaceExport = z.infer<typeof workspaceExportSchema>;
