# Component Library

## Astro (static, zero-JS)

| Component | File | Use |
|---|---|---|
| `GlassCard` | `src/components/glass/GlassCard.astro` | base surface; `interactive` prop adds hover lift |
| `MetricCard` | `src/components/ui/MetricCard.astro` | labelled metric with unit + source |
| `CoverageIndicator` | `src/components/ui/CoverageIndicator.astro` | status dot + label |
| `MethodologyLink` | `src/components/ui/MethodologyLink.astro` | link chip → /methodology |
| `ButtonLink` | `src/components/ui/ButtonLink.astro` | styled anchor |
| `DataTable` | `src/components/tables/DataTable.astro` | dense table, `.num` right-aligned |
| `LoadingState`/`EmptyState`/`ErrorState` | `src/components/feedback/` | shared async states |

## React islands (`client:load`)

| Island | File | Used on |
|---|---|---|
| `CountryProfile` | `src/features/country/CountryProfile.tsx` | `/country/[iso3]` |
| `ForceCoveragePanel` | `src/features/forces/ForceCoveragePanel.tsx` | `/country/[iso3]/forces` |
| `SitePanels` | `src/features/site/SitePanels.tsx` | compare, economy, debt, trade, data, sources, progress panels |
| `WorkspaceApp` | `src/features/workspace/WorkspaceApp.tsx` | `/workspace` |
| `WidgetFrame` + widgets | `src/features/workspace/WidgetFrame.tsx`, `src/features/widgets/` | all ~40 widget types |

## Shared hooks/helpers

- `src/features/widgets/hooks.ts` — `useObservations`, `useCountries`, `ready()` async-state unwrap
- `src/lib/api/client.ts` — typed fetch client (`ApiError`, abort support)
- `src/lib/format.ts` — `formatPercent`, `formatUsdCompact`, `formatQuarter`, `sourceLabel`
