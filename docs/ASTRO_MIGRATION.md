# Astro Migration (Atlas 2.0)

**Status:** complete scaffold, production build green. The Next.js app (`apps/web`) remains untouched; `apps/web-astro` is the new frontend on branch `feature/big-cycle-atlas-astro-v2`.

## Stack

- Astro 5 + `@astrojs/react` (React 19 islands for interactive components)
- Tailwind CSS v4 via `@tailwindcss/vite` (utility escape-hatches; the design system is plain CSS tokens, not Tailwind)
- react-grid-layout v2 (dashboard grid), zustand (workspace store), echarts (charts), zod (import validation)
- Vitest + Playwright for tests

## Architecture

- `.astro` pages and layout = server-rendered shell (no JS shipped for static content)
- `client:load` React islands in `src/features/**` fetch `/api/*` at runtime (API_URL from `src/lib/api/client.ts`, default `http://localhost:8000`)
- Workspace engine: `src/features/workspace/` + `src/stores/workspaceStore.ts` (persisted, versioned localStorage)

## Routes

30 pages — see `src/pages/`. Dynamic route: `/country/[iso3]` and `/country/[iso3]/forces` prerendered for the 8 tracked countries.

## Commands

```
cd apps/web-astro
npm install
npm run dev      # http://localhost:3000 (needs API on :8000)
npm run build    # static build → dist/
npm test         # vitest unit tests
npx playwright test   # e2e (needs dev servers running)
```
