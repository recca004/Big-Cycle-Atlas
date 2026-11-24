import type { ComponentType } from "react";

/** Widget type contract. Each widget declares everything the workspace
 *  engine needs: identity, grid bounds, config fields, and renderer. */

export type WidgetCategory =
  | "economic"
  | "trade"
  | "governance"
  | "strength"
  | "data"
  | "research";

export type ConfigFieldType =
  | "country"
  | "countries"
  | "indicator"
  | "force"
  | "chart-type"
  | "text"
  | "boolean"
  | "number";

export interface ConfigField {
  key: string;
  label: string;
  type: ConfigFieldType;
  default?: unknown;
  options?: { value: string; label: string }[];
  min?: number;
  max?: number;
}

export interface WidgetConfig {
  [key: string]: unknown;
}

export interface WidgetProps {
  instanceId: string;
  config: WidgetConfig;
  editMode: boolean;
}

export interface WidgetDefinition {
  /** Stable type id — stored in saved layouts, never rename. */
  typeId: string;
  displayName: string;
  description: string;
  category: WidgetCategory;
  defaultSize: { w: number; h: number };
  minSize: { w: number; h: number };
  maxSize?: { w: number; h: number };
  configFields: ConfigField[];
  /** What data this widget needs — drives "unavailable" messaging. */
  dataRequirement: string;
  /** Schema version for this widget's config payload. */
  configVersion: number;
  component: ComponentType<WidgetProps>;
}

const registry = new Map<string, WidgetDefinition>();

export function registerWidget(def: WidgetDefinition): void {
  registry.set(def.typeId, def);
}

export function getWidget(typeId: string): WidgetDefinition | undefined {
  return registry.get(typeId);
}

export function listWidgets(): WidgetDefinition[] {
  return [...registry.values()];
}

export function widgetsByCategory(): [WidgetCategory, WidgetDefinition[]][] {
  const groups = new Map<WidgetCategory, WidgetDefinition[]>();
  for (const def of registry.values()) {
    const list = groups.get(def.category) ?? [];
    list.push(def);
    groups.set(def.category, list);
  }
  return [...groups.entries()];
}
