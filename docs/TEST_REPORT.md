# Test Report — feature/big-cycle-atlas-astro-v2

## Backend (pytest)

**670 passed** (`cd apps/api && pytest`), including Sprint 6.13 composition tests and force-scores endpoint contract tests.

## Frontend unit (Vitest)

**28 passed** (`cd apps/web-astro && npm test`):

- `registry.test.ts` — ≥35 widgets, unique ids, bounds, config-field uniqueness, category grouping (7 tests)
- `workspaceStore.test.ts` — seeding, create/rename/duplicate, addWidget default-merging, remove/duplicate/config/keyboard-move, export→import roundtrip, invalid JSON rejection, unknown-widget drop (10 tests)
- `format.test.ts` — percent/decimal/USD/quarter/year/source labels (6 tests)
- `api.test.ts` — URL construction, query params, JSON parse, error path (5 tests)

## Frontend e2e (Playwright, real dev DB)

**29 passed** (`npx playwright test`, Chromium 1440×900 + one 390×844 spec):

- 22 route-availability tests (every page loads with zero page errors)
- Live data: country metrics (real `$30.77T` GDP), force coverage pills, compare table with real scores
- Workspace: widget render + persistence across reload; edit-mode drag handles
- Theme: `bca:theme` dark/light applied to `data-theme`
- Mobile: country page usable at 390px

## Known gaps

- No widget-drag/resize e2e (RGL pointer simulation is flaky headless; covered by edit-mode assertion + keyboard-move unit test).
- No visual-regression snapshots yet.
- API-failure recovery tested at unit level only (ApiError path), not e2e.
