import type {
  ConfigField,
  WidgetConfig,
  WidgetDefinition,
} from "./widgetRegistry";
import type { Workspace } from "./types";

/** Fields that can inherit a shared workspace filter value. */
const INHERITABLE_KEYS = new Set([
  "country", "countries", "startYear", "endYear", "indicator",
  "force", "model",
]);

/** Per-widget opt-out flag stored in config as `inherit_<key>` (boolean).
 *  true (default for new widgets on inheritable fields) → workspace
 *  filter wins over the widget's stored default; false → widget keeps
 *  its own configured value. */
export function inheritFlag(key: string): string {
  return `inherit_${key}`;
}

export function isInheritable(field: ConfigField): boolean {
  return field.inheritable === true || INHERITABLE_KEYS.has(field.key);
}

/** Resolve the effective widget config:
 *    widget-specific value (when inheritance off)
 *    → workspace filter (when inheritance on)
 *    → widget default.
 *  Shared resolver — widgets never implement this themselves. */
export function resolveEffectiveConfig(
  def: WidgetDefinition,
  instanceConfig: WidgetConfig,
  filters: Workspace["filters"],
): WidgetConfig {
  const out: WidgetConfig = { ...instanceConfig };
  for (const field of def.configFields) {
    if (!isInheritable(field)) continue;
    const flag = inheritFlag(field.key);
    const inherits = instanceConfig[flag] === true;
    const filterValue =
      field.key === "country"
        ? filters.country
        : field.key === "countries"
          ? filters.countries?.length
            ? filters.countries
            : null
          : field.key === "startYear"
            ? filters.startYear
            : field.key === "endYear"
              ? filters.endYear ?? null
              : null;
    if (inherits && filterValue != null) {
      out[field.key] = filterValue;
    } else if (out[field.key] === undefined) {
      out[field.key] = field.default;
    }
  }
  return out;
}

/** Which config fields currently inherit from the workspace — used to
 *  show the inheritance state in each widget's settings (§9). */
export function inheritedKeys(
  def: WidgetDefinition,
  instanceConfig: WidgetConfig,
): string[] {
  return def.configFields
    .filter((f) => isInheritable(f) && instanceConfig[inheritFlag(f.key)] === true)
    .map((f) => f.key);
}

/** Default config payload for a new widget instance: fields' declared
 *  defaults + inherit flags ON for inheritable fields. */
export function defaultInstanceConfig(def: WidgetDefinition): WidgetConfig {
  const cfg: WidgetConfig = {};
  for (const f of def.configFields) {
    if (f.default !== undefined) cfg[f.key] = f.default;
    if (isInheritable(f)) cfg[inheritFlag(f.key)] = true;
  }
  return cfg;
}
