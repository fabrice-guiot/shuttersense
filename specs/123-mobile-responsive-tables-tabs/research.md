# Research: Mobile Responsive Tables and Tabs

**Feature Branch**: `123-mobile-responsive-tables-tabs`
**Date**: 2026-01-29

## R1: Responsive Table Pattern — Card Layout on Mobile

**Decision**: Use CSS-toggled dual rendering (table + card list) with a `cardRole` column role system.

**Rationale**:
- All 11 tables use the same `Table/TableHeader/TableBody/TableRow/TableCell` component primitives from `frontend/src/components/ui/table.tsx`. A single `<ResponsiveTable>` wrapper can serve all cases.
- CSS toggling via `hidden md:block` / `md:hidden` is the simplest approach — no JavaScript viewport detection, no `useMediaQuery` hook, no conditional rendering logic. Both views are in the DOM but only one is visible.
- The card layout with structured zones (title, subtitle, badge, detail, action) handles all column counts from 4 (Release Manifests) to 10 (Results) without per-table layout code.
- The `cardRole` system allows declarative column→card mapping without runtime logic. Default to `detail` means most columns just work.

**Alternatives Considered**:
1. **Column hiding (CSS visibility)**: Rejected — hides data from users; doesn't scale to 9-10 column tables.
2. **TanStack Table**: Rejected — heavy dependency requiring full rewrite of 11 tables. The existing table primitives are adequate for desktop.
3. **JavaScript `useMediaQuery` hook with conditional rendering**: Rejected — adds complexity (resize listeners, hydration concerns) for no UX benefit. CSS toggling is sufficient for the `md` breakpoint.
4. **Single responsive component with CSS Grid**: Rejected — card layout provides better mobile UX than a grid that still requires horizontal scanning.

## R2: Responsive Tabs Pattern — Select Picker on Mobile

**Decision**: Replace `<TabsList>` with a `<ResponsiveTabsList>` that renders a `<Select>` dropdown below `md` and passes through `<TabsList>` children at `md` and above.

**Rationale**:
- The existing `<Select>` component from shadcn/ui provides keyboard navigation, ARIA attributes, and portal-based rendering out of the box.
- All tabbed pages except CollectionList already use controlled tabs with `value` + `onValueChange`. The select's `onValueChange` directly calls the same handler.
- The select operates independently from Radix UI's `Tabs` primitive — it updates external state, which flows back to `Tabs` via the `value` prop. No Radix internals are bypassed.
- Confirmed controlled tab implementations: SettingsPage (URL sync), DirectoryPage (URL sync), AnalyticsPage (URL + useState). CollectionList uses `defaultValue="all"` (uncontrolled) and needs conversion.

**Alternatives Considered**:
1. **Horizontally scrollable tab strip**: Rejected — hides tabs without visual cue; users must guess to scroll.
2. **Multi-row wrapping**: Rejected — breaks the pill/inline aesthetic; inconsistent heights.
3. **Hamburger/overflow menu**: Rejected — unfamiliar pattern for tab navigation.

## R3: CollectionList Tabs — Uncontrolled to Controlled Migration

**Decision**: Convert `CollectionList` from `defaultValue="all"` to `useState("all")` with `value` and `onValueChange` props.

**Rationale**:
- The `<ResponsiveTabsList>` select picker requires `value` and `onValueChange` to synchronize the dropdown with the active content panel.
- Uncontrolled tabs do not expose the current value, so the select cannot know which tab is active.
- The conversion is straightforward: add `const [activeTab, setActiveTab] = useState("all")` and pass to `<Tabs value={activeTab} onValueChange={setActiveTab}>`.
- No URL sync is needed for CollectionList since it's a component within a page, not a top-level page.

**Alternatives Considered**:
1. **Keep uncontrolled and use ref**: Rejected — Radix Tabs don't expose an imperative API for reading current value.
2. **Lift state to parent**: Rejected — over-engineering; the state is local to this component.

## R4: DOM Size Impact of Dual Rendering

**Decision**: Accept dual rendering (both table and card in DOM, one hidden via CSS) for v1.

**Rationale**:
- Typical page sizes are 10-50 rows per paginated page. With 10 columns, that's 100-500 table cells plus 10-50 cards. Modern browsers handle this without measurable performance impact.
- CSS `display: none` (via Tailwind's `hidden`) prevents layout computation and paint for the hidden view.
- Avoiding `useMediaQuery` eliminates JavaScript complexity, resize listeners, and potential hydration mismatches.
- If performance becomes an issue for future tables with hundreds of rows, a `useMediaQuery`-based conditional rendering can be added later as an optimization.

**Alternatives Considered**:
1. **`useMediaQuery` conditional rendering**: Rejected for v1 — adds JS complexity for no measurable benefit at current scale. Can be added later if needed.

## R5: Mobile Action Button Pattern

**Decision**: Preserve each table's existing action pattern on mobile cards. Tables with individual buttons keep individual buttons; AgentsPage with DropdownMenu keeps DropdownMenu.

**Rationale**:
- The `cardRole: 'action'` system renders the same `cell()` output in both desktop and mobile views. No special mobile-only action rendering is needed.
- The Agents table already uses a `DropdownMenu` pattern — this naturally works in the card action row.
- Other tables use 2-5 icon buttons with tooltips. On mobile cards, these render in a flex row with `gap-2`. Touch targets are adequate when buttons use `size="sm"` (36px) or larger.
- Standardizing all tables to dropdown menus would require changing 10 existing table implementations for minimal UX benefit.

**Alternatives Considered**:
1. **Consolidate all actions into DropdownMenu on mobile**: Rejected — requires mobile-specific action rendering, increasing component complexity. Can be revisited in future iteration.

## R6: Pagination Stacking

**Decision**: Update the ResultsTable pagination bar to use `flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between` for mobile stacking.

**Rationale**:
- Only ResultsTable has full pagination controls. Other tables rely on API-level pagination or display all items.
- The current `flex items-center justify-between` squeezes on narrow viewports. The responsive stacking pattern is already used elsewhere in the codebase (search + action rows).
- This is a one-line CSS class change, consistent with the existing responsive flex pattern documented in the design system.

## R7: Existing Codebase Patterns Confirmed

**Findings**:
- **Table wrapper**: All tables use `<div className="rounded-md border border-border overflow-x-auto">` — `ResponsiveTable` will replace this wrapper with dual rendering.
- **Empty states**: Icon + message pattern, centered with `py-8` or `py-12`. `ResponsiveTable` passes through the `emptyState` prop.
- **Action buttons**: Consistently use `variant="ghost" size="icon"` with `Tooltip` wrappers. Some tables use `DropdownMenu`.
- **Status badges**: Consistent use of `Badge` component with domain-specific variants.
- **`cn()` utility**: Available at `frontend/src/lib/utils.ts` for class merging — used throughout all components.
- **Tailwind breakpoints**: `sm:` (640px) used for action row stacking, `md:` (768px) appropriate for table/card and tab/select switch.
