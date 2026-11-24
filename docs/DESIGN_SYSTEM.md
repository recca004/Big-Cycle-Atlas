# Design System — Liquid Glass

Single system in `src/styles/`. Every page and island consumes the same tokens — no page-specific palettes.

## Layers

| File | Role |
|---|---|
| `tokens.css` | spacing, radius, type scale, motion, z-order, chart palette (theme-independent) |
| `themes.css` | `[data-theme="dark"|"light"]` surfaces, text, borders, accent, status, glass, shadows, background glows |
| `liquid-glass.css` | `.glass`, `.glass-subtle`, `.glass-interactive`, `.glass-button` surfaces |
| `typography.css` | `headline-*`, `body-*`, `label-md`, `num` (tabular numerals) |
| `components.css` | cards, tables, pills, states, buttons, forms, workspace chrome |
| `global.css` | reset, body background (per-theme radial glows + `--bg-app`), utility helpers |

## Principles

- **Glass over glow.** Translucency only reads against depth; each theme defines `--bg-glow-1/2` radial washes under `body`. Cards use `backdrop-filter: blur(var(--glass-blur))`.
- **Honest surfaces.** `prefers-reduced-transparency` and `bca:transparency=reduced` swap glass for `--surface-solid`.
- **Theme-safe colour.** Never hardcode hex in components — use tokens (`--text-secondary`, `--border-subtle`, `--status-good`). Charts pull `--chart-*` series colours.
- **Density first.** Financial tables use `--text-sm` + tabular nums; scores are `num`-classed right-aligned.

## States

`LoadingState`/`EmptyState`/`ErrorState` (Astro) and `resolveAsync`/`PanelState` (React) share `.state-box`, `.widget-state`, `.status-*` classes.
