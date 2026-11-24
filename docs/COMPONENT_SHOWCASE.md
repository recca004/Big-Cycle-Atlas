# Component Showcase

Visual inspection: run `npm run dev` in `apps/web-astro` and open:

- **Glass surfaces & cards** — `/` (metric cards, country cards, glass panels)
- **Tables & explorer controls** — `/countries`, `/data`, `/sources`
- **Force cards + status pills** — `/forces`, `/country/USA/forces`
- **All ~40 widget types** — `/workspace` → Add (library panel lists every registered widget with description)
- **Compare table + selects** — `/compare`
- **States** — widgets show loading/empty/error/unavailable; `unavailable-*` widgets document deferred methodology
- **Theme** — header toggle or `/settings` (light/dark/system); background glows change per theme

Reference implementations: `src/components/` (Astro), `src/features/` (React islands), `src/features/widgets/` (widget bodies).
