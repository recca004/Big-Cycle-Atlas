/** Versioned local preferences (Mission 6 §8).
 *  Single JSON blob at bca:prefs:v1. Theme and transparency are also
 *  mirrored to the standalone keys the BaseLayout boot script reads
 *  before first paint — the blob is the source of truth. */

export interface Prefs {
  version: 1;
  theme: "light" | "dark" | "system";
  reducedMotion: boolean;
  reducedTransparency: boolean;
  defaultCountry: string;
  defaultDateRange: "5y" | "10y" | "25y" | "max";
  defaultWorkspace: string | null;
  portfolioCurrency: string;
  numberFormat: "en-US" | "de-CH" | "en-GB";
  fullResearch: boolean;
}

export const DEFAULT_PREFS: Prefs = {
  version: 1,
  theme: "system",
  reducedMotion: false,
  reducedTransparency: false,
  defaultCountry: "USA",
  defaultDateRange: "25y",
  defaultWorkspace: null,
  portfolioCurrency: "CHF",
  numberFormat: "en-US",
  fullResearch: false,
};

const KEY = "bca:prefs:v1";
const listeners = new Set<(p: Prefs) => void>();

export function loadPrefs(): Prefs {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed?.version === 1) return { ...DEFAULT_PREFS, ...parsed };
    }
    // Migrate the legacy standalone theme key, if present.
    const legacyTheme = localStorage.getItem("bca:theme");
    if (legacyTheme === "light" || legacyTheme === "dark") {
      return { ...DEFAULT_PREFS, theme: legacyTheme };
    }
  } catch {
    /* private mode / corrupt blob */
  }
  return { ...DEFAULT_PREFS };
}

function mirrorBootKeys(p: Prefs) {
  try {
    // Boot script reads these before first paint; keep them in sync.
    if (p.theme === "system") localStorage.removeItem("bca:theme");
    else localStorage.setItem("bca:theme", p.theme);
    if (p.reducedTransparency)
      localStorage.setItem("bca:transparency", "reduced");
    else localStorage.removeItem("bca:transparency");
  } catch {
    /* ignore */
  }
}

export function savePrefs(next: Partial<Prefs>): Prefs {
  const merged = { ...loadPrefs(), ...next, version: 1 as const };
  try {
    localStorage.setItem(KEY, JSON.stringify(merged));
    mirrorBootKeys(merged);
  } catch {
    /* private mode */
  }
  applyPrefsToDom(merged);
  listeners.forEach((fn) => fn(merged));
  return merged;
}

export function resetPrefs(): void {
  try {
    localStorage.removeItem(KEY);
    localStorage.removeItem("bca:theme");
    localStorage.removeItem("bca:transparency");
  } catch {
    /* ignore */
  }
  applyPrefsToDom(DEFAULT_PREFS);
  listeners.forEach((fn) => fn({ ...DEFAULT_PREFS }));
}

export function subscribePrefs(fn: (p: Prefs) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function getPref<K extends keyof Prefs>(key: K): Prefs[K] {
  return loadPrefs()[key];
}

export function getDefaultCountry(): string {
  return loadPrefs().defaultCountry;
}

export function getPortfolioCurrency(): string {
  return loadPrefs().portfolioCurrency;
}

/** Applies DOM-side prefs (theme resolution + transparency + motion attrs). */
export function applyPrefsToDom(p: Prefs = loadPrefs()): void {
  const el = document.documentElement;
  const resolved =
    p.theme === "system"
      ? matchMedia("(prefers-color-scheme: light)").matches
        ? "light"
        : "dark"
      : p.theme;
  el.dataset.theme = resolved;
  if (p.reducedTransparency) el.dataset.transparency = "reduced";
  else delete el.dataset.transparency;
  if (p.reducedMotion) el.dataset.motion = "reduced";
  else delete el.dataset.motion;
  if (p.fullResearch) el.dataset.fullResearch = "true";
  else delete el.dataset.fullResearch;
}

/** Number formatter honouring the locale preference. */
export function formatNumberPref(value: number, digits = 2): string {
  return value.toLocaleString(loadPrefs().numberFormat, {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}
