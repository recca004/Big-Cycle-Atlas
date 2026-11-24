# Workspace Architecture

## Pieces

- `src/features/workspace/types.ts` — zod schemas: `Workspace`, `WidgetInstance`, `StoredLayoutItem`, export envelope (`version`, `kind`). `GRID_COLS lg:12/md:8/sm:4`.
- `src/features/workspace/widgetRegistry.ts` — `registerWidget`, `getWidget`, `listWidgets`, `widgetsByCategory`. A `WidgetDefinition` = `typeId`, `displayName`, `category`, `defaultSize`/`minSize`, `configFields` (with defaults), `component`.
- `src/features/widgets/index.ts` — registers all widget types (metric/chart/ranking/table/force/status/unavailable factories).
- `src/features/workspace/defaultWorkspaces.ts` — 8 preset workspace factories.
- `src/stores/workspaceStore.ts` — zustand + `persist` (localStorage `bca:workspaces`, versioned). Actions: create/rename/duplicate/delete/reset workspace; add/remove/duplicate/configure/collapse/keyboard-move widgets; `setLayouts`, export/import JSON.
- `src/features/workspace/WorkspaceApp.tsx` — tabs, toolbar (Edit/Add/Manage/export-import), `ResponsiveGridLayout` (lg/md/sm breakpoints), widget library, manage panel.
- `WidgetFrame.tsx` — header (drag handle, collapse, configure, duplicate, remove, keyboard-move cluster), config panel, body. Effective config = `configFields` defaults merged under `instance.config` (imported/older widgets missing keys still render correctly).

## Persistence

- Layouts stored per breakpoint; `deriveLayouts` regenerates md/sm from lg when widgets change.
- Export envelope: `{version:1, kind:"big-cycle-atlas-workspace", workspace}`; import validates with `workspaceExportSchema`, drops unknown widget types, back-fills missing layout entries.

## Adding a widget type

1. `registerWidget({...})` in `src/features/widgets/index.ts` (or a factory).
2. Component receives `{instanceId, config, editMode}` — use `useObservations`/`resolveAsync` for data + explicit unavailable states.
