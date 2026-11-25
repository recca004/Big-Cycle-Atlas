/** Global search palette (Mission 6 §8).
 *  Ctrl/Cmd+K or the header button. Merges API entity hits (countries,
 *  indicators, instruments) with static entities (pages, forces, composite
 *  models, workspaces). Keyboard: arrows navigate, Enter opens, Esc closes. */
import { useCallback, useEffect, useRef, useState } from "react";
import { INITIAL_COUNTRIES, FORCES } from "@big-cycle-atlas/shared";
import { searchEntities, type SearchHit } from "@/lib/api/client";

interface Item {
  group: string;
  key: string;
  label: string;
  detail?: string | undefined;
  href: string;
}

const PAGES: Item[] = ([
  ["Overview", "/"], ["Countries", "/countries"], ["Forces", "/forces"],
  ["Workspace", "/workspace"], ["Compare", "/compare"], ["Cycle", "/cycle"],
  ["Research Lab", "/research"], ["Forecast", "/forecast"],
  ["Markets", "/markets"], ["Strategies", "/strategies"],
  ["Portfolio", "/portfolio"], ["Watchlist", "/watchlist"],
  ["Economy", "/economy"], ["Debt", "/debt"], ["Trade", "/trade"],
  ["Data explorer", "/data"], ["Sources", "/sources"],
  ["Methodology", "/methodology"], ["Progress", "/progress"],
  ["Settings", "/settings"],
] as [string, string][]).map(([label, href]) => ({ group: "Pages", key: href, label, href }));

const MODELS: Item[] = [
  "model_a_equal", "model_b_domain",
  "model_c_overlap_adjusted", "model_d_fixed_subset",
].map((m) => ({
  group: "Cycle models",
  key: m,
  label: m.replaceAll("_", " "),
  detail: "experimental composite",
  href: `/cycle?model=${m}`,
}));

const STATIC: Item[] = [
  ...PAGES,
  ...INITIAL_COUNTRIES.map((c) => ({
    group: "Countries",
    key: c.iso3,
    label: c.name,
    detail: c.iso3,
    href: `/country/${c.iso3}`,
  })),
  ...FORCES.map((f) => ({
    group: "Forces",
    key: f,
    label: f.replaceAll("_", " "),
    detail: "force research module",
    href: `/forces?force=${f}`,
  })),
  ...MODELS,
];

function workspaceItems(query: string): Item[] {
  try {
    const raw = localStorage.getItem("bca:workspaces:v1");
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    const names: string[] = (parsed?.state?.order ?? []).map(
      (id: string) => parsed?.state?.workspaces?.[id]?.name ?? id,
    );
    return names
      .filter((n) => n.toLowerCase().includes(query))
      .map((n) => ({
        group: "Workspaces", key: n, label: n, href: "/workspace",
      }));
  } catch {
    return [];
  }
}

const WIDGET_ITEMS: Item[] = ([
  ["Force score", "force_score"], ["All forces", "all_forces"],
  ["Metric", "metric"], ["Indicator chart", "indicator_chart"],
  ["Data table", "data_table"], ["Ranking", "ranking"],
  ["Uncertainty band", "uncertainty_band"],
  ["Cycle history", "cycle_history"], ["Force history", "force_history"],
] as [string, string][]).map(([label, key]) => ({
  group: "Widgets", key, label, href: "/workspace?add=" + key,
}));

function match(items: Item[], q: string): Item[] {
  const s = q.toLowerCase();
  return items.filter(
    (i) => i.label.toLowerCase().includes(s) || i.key.toLowerCase().includes(s),
  );
}

export function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [api, setApi] = useState<SearchHit[]>([]);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      } else if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) {
      setQuery(""); setApi([]); setActive(0);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) { setApi([]); return; }
    const c = new AbortController();
    const t = setTimeout(() => {
      searchEntities(q, { signal: c.signal })
        .then((r) => setApi([...r.countries, ...r.indicators, ...r.instruments]))
        .catch(() => {});
    }, 200);
    return () => { clearTimeout(t); c.abort(); };
  }, [query]);

  const staticHits = query.trim()
    ? [...match(STATIC, query), ...workspaceItems(query.toLowerCase()), ...match(WIDGET_ITEMS, query)]
    : [];
  const apiHits: Item[] = api.map((h) => ({
    group:
      h.kind === "country" ? "Countries" :
      h.kind === "indicator" ? "Indicators" : "Instruments",
    key: `${h.kind}:${h.key}`,
    label: h.label,
    detail: h.detail ?? undefined,
    href:
      h.kind === "country" ? `/country/${h.key}` :
      h.kind === "indicator" ? `/data?indicator=${h.key}` :
      `/markets?instrument=${h.key}`,
  }));
  // API hits win for DB entities; de-dupe by destination.
  const seen = new Set(apiHits.map((h) => h.href));
  const items = [...apiHits, ...staticHits.filter((s) => !seen.has(s.href))].slice(0, 40);

  const openItem = useCallback((item: Item) => {
    setOpen(false);
    window.location.href = item.href;
  }, []);

  const onInputKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter" && items[active]) {
      e.preventDefault();
      openItem(items[active]);
    }
  };

  useEffect(() => {
    listRef.current
      ?.querySelector(`[data-idx="${active}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [active]);

  let lastGroup = "";
  return (
    <>
      <button
        type="button"
        className="glass-button search-trigger"
        onClick={() => setOpen(true)}
        aria-label="Search (Ctrl+K)"
      >
        Search <kbd className="search-kbd">Ctrl K</kbd>
      </button>
      {open && (
        <div
          className="search-overlay"
          role="presentation"
          onClick={() => setOpen(false)}
        >
          <div
            className="glass search-palette"
            role="dialog"
            aria-modal="true"
            aria-label="Search"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              ref={inputRef}
              className="search-input"
              placeholder="Search countries, indicators, instruments, forces, pages…"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setActive(0); }}
              onKeyDown={onInputKey}
              aria-label="Search query"
            />
            <div className="search-results" ref={listRef} role="listbox">
              {items.map((item, idx) => {
                const header = item.group !== lastGroup ? item.group : null;
                lastGroup = item.group;
                return (
                  <div key={`${item.group}:${item.key}`}>
                    {header && <p className="search-group label-md">{header}</p>}
                    <button
                      type="button"
                      role="option"
                      aria-selected={idx === active}
                      data-idx={idx}
                      className={`search-item ${idx === active ? "search-item-active" : ""}`}
                      onMouseEnter={() => setActive(idx)}
                      onClick={() => openItem(item)}
                    >
                      <span>{item.label}</span>
                      {item.detail && <span className="body-sm">{item.detail}</span>}
                    </button>
                  </div>
                );
              })}
              {query.trim() && items.length === 0 && (
                <p className="body-sm search-empty">
                  No entities match “{query.trim()}”.
                </p>
              )}
              {!query.trim() && (
                <p className="body-sm search-empty">
                  Type to search all application entities.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
