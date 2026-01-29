# PRD: Mobile Responsive Tables and Tabs

**Status**: Draft
**Created**: 2026-01-29
**Last Updated**: 2026-01-29
**Related Documents**:
- [Design System](../../frontend/docs/design-system.md)

---

## Executive Summary

The frontend application currently renders all data tables and tab navigation strips using desktop-oriented components that do not adapt to mobile viewport widths. Tables rely solely on horizontal scrolling, which hides columns (including action buttons) off-screen. Tab strips overflow the viewport when label counts exceed 3–4, breaking the rounded-pill visual container. This PRD defines two reusable responsive components — `<ResponsiveTable>` and `<ResponsiveTabsList>` — that transform their rendering below the `md` (768px) breakpoint to provide a mobile-friendly experience while leaving desktop behavior unchanged.

### Key Design Decisions

1. **Card layout for tables on mobile**: Each table row becomes a structured card below `md`, eliminating horizontal scroll entirely
2. **Select dropdown for tabs on mobile**: Tab strips are replaced by a `<Select>` picker below `md`, handling any number of tabs in constant width
3. **Breakpoint**: `md` (768px) is the single switch point for both components, matching the existing responsive patterns in the codebase
4. **Desktop unchanged**: Both components render the existing desktop view at `md` and above using `hidden md:block` / `md:hidden` CSS toggling
5. **Column role system**: Each table column declares a `cardRole` that controls its position and visibility in the mobile card layout
6. **Drop-in replacement**: Both components wrap existing primitives and require minimal migration per page

---

## Background

### Current State

**Tables**: All 11 tables across the application use the shadcn/ui `<Table>` component (`frontend/src/components/ui/table.tsx`). Each table is wrapped in a `<div className="rounded-md border border-border overflow-x-auto">`. The only mobile accommodation is horizontal scrolling. No column hiding, card views, or responsive breakpoint logic exists.

**Tabs**: The `<TabsList>` component (`frontend/src/components/ui/tabs.tsx`) uses `inline-flex h-9` with `whitespace-nowrap` on each `<TabsTrigger>`. There is no overflow handling — no scroll, no wrap, no collapse. When tabs exceed the viewport width, they overflow the muted pill background and break the layout.

### Problem Statement

On a mobile phone screen (~375px):

- **Tables**: A 9–10 column table needs ~720–800px of horizontal space. Users must scroll horizontally to see any column past the first 4. The primary identifier (Name) scrolls off-screen when viewing right-side columns. Action buttons (always rightmost) are hidden. There is no visual cue that more content exists.
- **Tabs**: The Settings page with 6 tabs (super admin) requires ~680px. Even with 4 tabs (regular user), the total exceeds ~500px. Labels like "Release Manifests" (17 chars) plus an "Admin" badge plus an icon cannot fit. The pill background visually breaks.

### Strategic Context

Mobile responsiveness is a prerequisite for:
- **PWA deployment** (PRD 023): Push notifications drive users to the app on their phones — they need a usable experience when they arrive
- **Agent monitoring**: Administrators checking agent status from a phone during incidents
- **Field use**: Photographers reviewing collection status on-site from a mobile device

---

## Goals

### Primary Goals

1. **Readable tables on mobile**: All table data visible without horizontal scrolling on screens ≥320px
2. **Accessible tabs on mobile**: All tab options reachable in a single interaction on any viewport width
3. **Reusable components**: A single `<ResponsiveTable>` and `<ResponsiveTabsList>` component used across all pages
4. **Zero desktop regression**: Desktop rendering is identical to current behavior

### Secondary Goals

1. **Touch-friendly actions**: Action buttons have adequate touch targets (≥44px) on mobile
2. **Design system documentation**: New components documented with usage patterns and migration guides
3. **Consistent breakpoint**: All mobile adaptations switch at `md` (768px), matching existing responsive patterns

### Non-Goals (v1)

1. **Tablet-specific layouts**: Tablets (768–1024px) continue to use the desktop table view
2. **Column sorting on mobile**: Card layout does not support column-header sort interactions
3. **Infinite scroll**: Pagination remains page-based on mobile
4. **Virtualization**: No virtual scrolling for long lists (future optimization)

---

## Affected Pages

### Tables (11 instances)

| Page / Component | File | Columns | Severity |
|---|---|---|---|
| Results | `components/results/ResultsTable.tsx` | 10 | Critical |
| Collections | `components/collections/CollectionList.tsx` | 9 | Critical |
| Locations | `components/directory/LocationsTab.tsx` | 8 | High |
| Organizers | `components/directory/OrganizersTab.tsx` | 8 | High |
| Performers | `components/directory/PerformersTab.tsx` | ~8 | High |
| Agents | `pages/AgentsPage.tsx` | 7 | High |
| Categories | `components/settings/CategoriesTab.tsx` | 7 | Medium |
| Connectors | `components/connectors/ConnectorList.tsx` | 6 | Medium |
| Tokens | `components/settings/TokensTab.tsx` | 6 | Medium |
| Teams | `components/settings/TeamsTab.tsx` | 5 | Low |
| Release Manifests | `components/settings/ReleaseManifestsTab.tsx` | 4 | Low |

### Tabs (5 instances)

| Page | File | Tab Count | Total Width Estimate | Severity |
|---|---|---|---|---|
| Settings (super admin) | `pages/SettingsPage.tsx` | 6 | ~680px | Critical |
| Settings (regular) | `pages/SettingsPage.tsx` | 4 | ~500px | High |
| Analytics (nested runs) | `pages/AnalyticsPage.tsx` | 4 | ~400px (with count badges) | High |
| Collections | `components/collections/CollectionList.tsx` | 3 | ~350px | Medium |
| Analytics (main) | `pages/AnalyticsPage.tsx` | 4 | ~340px (plus action buttons) | Medium |
| Directory | `pages/DirectoryPage.tsx` | 3 | ~300px | Low |

---

## Technical Approach

### 1. Responsive Table — Card Layout on Mobile

#### Component API

**File**: `frontend/src/components/ui/responsive-table.tsx`

```tsx
interface ColumnDef<T> {
  /** Table header text */
  header: string
  /** Optional className for <TableHead> */
  headerClassName?: string
  /** Render function for cell content (used in both table and card views) */
  cell: (item: T) => React.ReactNode
  /** Optional className for <TableCell> */
  cellClassName?: string
  /** Controls how this column renders in the mobile card layout */
  cardRole?: 'title' | 'subtitle' | 'badge' | 'detail' | 'action' | 'hidden'
}

interface ResponsiveTableProps<T> {
  /** Array of data items to render */
  data: T[]
  /** Column definitions */
  columns: ColumnDef<T>[]
  /** Property used as React key for each row/card */
  keyField: keyof T
  /** Optional empty state content */
  emptyState?: React.ReactNode
  /** Optional className for the outer wrapper */
  className?: string
}
```

#### Card Role System

Each column declares a `cardRole` that determines its position in the mobile card:

| `cardRole` | Card Position | Rendering |
|---|---|---|
| `title` | Top-left, bold text | Primary identifier (e.g., Name) |
| `subtitle` | Below title, muted text | Secondary context (e.g., Location, Hostname) |
| `badge` | Inline with title or in a badge row | Status/type badges |
| `detail` | Key-value rows in card body | "Header: Value" label-value pairs |
| `action` | Bottom of card, full-width row | Action buttons with adequate touch targets |
| `hidden` | Not rendered on mobile | Low-priority columns (e.g., Created date) |

Default `cardRole` if unspecified: `detail`.

#### Mobile Card Layout

```
┌──────────────────────────────────────┐
│ Collection Name            ● Active  │  ← title + badges
│ /mnt/photos/events                   │  ← subtitle
│──────────────────────────────────────│
│ Agent         studio-mac-agent       │  ← detail rows
│ Pipeline      Default v2             │
│ Inventory     1,234 files            │
│──────────────────────────────────────│
│  [View]    [Edit]    [Delete]        │  ← action row
└──────────────────────────────────────┘
```

#### Rendering Pattern

```tsx
export function ResponsiveTable<T>({ data, columns, keyField, emptyState, className }: ResponsiveTableProps<T>) {
  if (data.length === 0 && emptyState) return <>{emptyState}</>

  const titleCols    = columns.filter(c => c.cardRole === 'title')
  const subtitleCols = columns.filter(c => c.cardRole === 'subtitle')
  const badgeCols    = columns.filter(c => c.cardRole === 'badge')
  const detailCols   = columns.filter(c => c.cardRole === 'detail' || !c.cardRole)
  const actionCols   = columns.filter(c => c.cardRole === 'action')

  return (
    <>
      {/* Desktop: standard table (md and up) */}
      <div className={cn("hidden md:block rounded-md border border-border overflow-x-auto", className)}>
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map(col => (
                <TableHead key={col.header} className={col.headerClassName}>
                  {col.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map(item => (
              <TableRow key={String(item[keyField])}>
                {columns.map(col => (
                  <TableCell key={col.header} className={col.cellClassName}>
                    {col.cell(item)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Mobile: card list (below md) */}
      <div className={cn("md:hidden flex flex-col gap-3", className)}>
        {data.map(item => (
          <div key={String(item[keyField])} className="rounded-lg border border-border bg-card p-4 space-y-3">
            {/* Title + Badge row */}
            <div className="flex items-start justify-between gap-2">
              <div>
                {titleCols.map(col => (
                  <div key={col.header} className="font-medium">{col.cell(item)}</div>
                ))}
                {subtitleCols.map(col => (
                  <div key={col.header} className="text-sm text-muted-foreground">{col.cell(item)}</div>
                ))}
              </div>
              {badgeCols.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {badgeCols.map(col => (
                    <span key={col.header}>{col.cell(item)}</span>
                  ))}
                </div>
              )}
            </div>

            {/* Detail key-value rows */}
            {detailCols.length > 0 && (
              <div className="border-t border-border pt-3 space-y-2">
                {detailCols.map(col => (
                  <div key={col.header} className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{col.header}</span>
                    <span>{col.cell(item)}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Action row */}
            {actionCols.length > 0 && (
              <div className="border-t border-border pt-3 flex justify-end gap-2">
                {actionCols.map(col => (
                  <span key={col.header}>{col.cell(item)}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  )
}
```

#### Card Role Mapping Per Table

| Table | title | subtitle | badge | detail | action | hidden |
|---|---|---|---|---|---|---|
| **Results** | Collection | Connector | Tool, Status | Pipeline, Files, Issues, Duration, Completed | View, Download, Delete | — |
| **Collections** | Name | Location | Type, State | Agent, Pipeline, Inventory, Status | Edit, Delete | — |
| **Connectors** | Name | — | Type, Status | Credentials, Created | Test, Edit, Delete | — |
| **Locations** | Name | Location | Status | Category, Rating, Instagram | Edit, Delete | Created |
| **Organizers** | Name | — | Status | Event Count, Rating, Category, Instagram | Edit, Delete | Created |
| **Performers** | Name | — | Status | Event Count, Rating, Category, Social | Edit, Delete | Created |
| **Agents** | Name | Hostname + OS | Status | Load, Version, Last Heartbeat | Menu (dropdown) | — |
| **Categories** | Name | — | Color, Icon, Status | Event Count | Edit, Delete | Created |
| **Teams** | Team | Slug | Status | Users | Edit, Delete | — |
| **Tokens** | Name | Prefix | Status | Created, Expires | Delete | — |
| **Releases** | Version | Release Date | Status | — | Actions | — |

---

### 2. Responsive Tabs List — Select Picker on Mobile

#### Component API

**File**: `frontend/src/components/ui/responsive-tabs-list.tsx`

```tsx
interface TabOption {
  /** Tab value (matches TabsTrigger value and TabsContent value) */
  value: string
  /** Display label */
  label: string
  /** Optional icon component */
  icon?: React.ComponentType<{ className?: string }>
  /** Optional badge (e.g., count, "Admin" label) */
  badge?: React.ReactNode
}

interface ResponsiveTabsListProps {
  /** Tab definitions for the mobile select */
  tabs: TabOption[]
  /** Currently active tab value */
  value: string
  /** Change handler (same as Tabs onValueChange) */
  onValueChange: (value: string) => void
  /** TabsTrigger elements for the desktop tab strip */
  children: React.ReactNode
}
```

#### Rendering Pattern

```tsx
export function ResponsiveTabsList({ tabs, value, onValueChange, children }: ResponsiveTabsListProps) {
  return (
    <>
      {/* Mobile: Select dropdown (below md) */}
      <div className="md:hidden w-full">
        <Select value={value} onValueChange={onValueChange}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {tabs.map(tab => (
              <SelectItem key={tab.value} value={tab.value}>
                <span className="flex items-center gap-2">
                  {tab.icon && <tab.icon className="h-4 w-4" />}
                  {tab.label}
                  {tab.badge}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Desktop: Standard TabsList (md and up) */}
      <TabsList className="hidden md:inline-flex">
        {children}
      </TabsList>
    </>
  )
}
```

#### Radix UI Compatibility

The `<Select>` operates independently from Radix UI's `Tabs` primitive. All affected pages already use **controlled tabs** with `value` + `onValueChange` props synced to component state or URL search params. The select's `onValueChange` calls the same handler as `TabsTrigger`. The `TabsContent` components react to the parent `Tabs` `value` prop regardless of whether the change originated from a `TabsTrigger` click or external state update.

Confirmed controlled tab implementations:
- `SettingsPage.tsx` — `validTab` state synced to URL `?tab=` parameter
- `DirectoryPage.tsx` — `validTab` state synced to URL `?tab=` parameter
- `AnalyticsPage.tsx` — `activeTab` and `runsSubTab` state synced to URL `?tab=` and `?runsTab=` parameters
- `CollectionList.tsx` — `defaultValue="all"` (uncontrolled, but migration to controlled is straightforward)

#### Migration Example — Settings Page

```tsx
// Before (SettingsPage.tsx, lines 107-123)
<TabsList>
  {tabs.map(tab => {
    const Icon = tab.icon
    return (
      <TabsTrigger key={tab.id} value={tab.id} className="gap-2">
        <Icon className="h-4 w-4" />
        {tab.label}
        {tab.superAdminOnly && (
          <Badge variant="secondary" className="ml-1 text-xs py-0 px-1.5">Admin</Badge>
        )}
      </TabsTrigger>
    )
  })}
</TabsList>

// After
<ResponsiveTabsList
  tabs={tabs.map(t => ({
    value: t.id,
    label: t.label,
    icon: t.icon,
    badge: t.superAdminOnly
      ? <Badge variant="secondary" className="ml-1 text-xs py-0 px-1.5">Admin</Badge>
      : undefined,
  }))}
  value={validTab}
  onValueChange={handleTabChange}
>
  {tabs.map(tab => {
    const Icon = tab.icon
    return (
      <TabsTrigger key={tab.id} value={tab.id} className="gap-2">
        <Icon className="h-4 w-4" />
        {tab.label}
        {tab.superAdminOnly && (
          <Badge variant="secondary" className="ml-1 text-xs py-0 px-1.5">Admin</Badge>
        )}
      </TabsTrigger>
    )
  })}
</ResponsiveTabsList>
```

#### Edge Case — Tabs with Action Buttons (Analytics Page)

The Analytics page wraps `TabsList` and action buttons in a responsive flex container:

```tsx
<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
  <TabsList>...</TabsList>
  <div className="flex gap-2"><!-- action buttons --></div>
</div>
```

The `<ResponsiveTabsList>` replaces only the `<TabsList>`. The outer flex container continues to stack the select and buttons vertically on mobile via `flex-col`.

#### Edge Case — Nested Tabs (Analytics > Runs)

The nested sub-tabs at `AnalyticsPage.tsx:626-656` also need `<ResponsiveTabsList>`. These render inside a `TabsContent` panel, so the select picker appears naturally within the content area. Count badges (e.g., "(3)") render as inline text within `SelectItem`.

---

## Additional Responsive Fixes

### Pagination Controls

The `ResultsTable` pagination bar (`ResultsTable.tsx:344-388`) uses `flex items-center justify-between`, which squeezes on narrow viewports. It should stack vertically on mobile:

```tsx
// Current
<div className="flex items-center justify-between">

// Proposed
<div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
```

### Action Buttons on Mobile Cards

On mobile cards, action buttons should use slightly larger touch targets. Consider using a `DropdownMenu` consolidating all actions behind a single "more" button, consistent with the pattern already used in `AgentsPage.tsx:230-261`. Alternatively, render labeled icon buttons instead of icon-only buttons for improved discoverability:

```tsx
// Desktop (table): icon-only ghost buttons
<Button variant="ghost" size="icon"><Eye className="h-4 w-4" /></Button>

// Mobile (card): icon + label or DropdownMenu
<Button variant="ghost" size="sm" className="gap-1.5">
  <Eye className="h-4 w-4" /> View
</Button>
```

---

## Requirements

### Functional Requirements

#### FR-100: Responsive Table Component

- **FR-100.1**: Create `<ResponsiveTable>` component in `frontend/src/components/ui/responsive-table.tsx`
- **FR-100.2**: Accept `columns` array with `ColumnDef<T>` including `cardRole` property
- **FR-100.3**: Render standard `<Table>` at `md` (768px) and above
- **FR-100.4**: Render card list layout below `md`
- **FR-100.5**: Support all six card roles: `title`, `subtitle`, `badge`, `detail`, `action`, `hidden`
- **FR-100.6**: Default `cardRole` to `detail` when unspecified
- **FR-100.7**: Support empty state rendering
- **FR-100.8**: Preserve all existing table functionality (hover, selection states, border styles)

#### FR-200: Responsive Tabs Component

- **FR-200.1**: Create `<ResponsiveTabsList>` component in `frontend/src/components/ui/responsive-tabs-list.tsx`
- **FR-200.2**: Accept `tabs` array with `TabOption` (value, label, icon, badge)
- **FR-200.3**: Render standard `<TabsList>` with `<TabsTrigger>` children at `md` and above
- **FR-200.4**: Render `<Select>` dropdown below `md`
- **FR-200.5**: Support icons and badges in select items
- **FR-200.6**: Compatible with Radix UI controlled `Tabs` (value + onValueChange)
- **FR-200.7**: Work alongside action buttons in flex containers (Analytics page pattern)

#### FR-300: Page Migrations

- **FR-300.1**: Migrate all 11 table instances to `<ResponsiveTable>`
- **FR-300.2**: Migrate all 5 tab instances (plus 1 nested) to `<ResponsiveTabsList>`
- **FR-300.3**: Convert `CollectionList` tabs from uncontrolled to controlled (required for select picker)
- **FR-300.4**: Update pagination controls to stack vertically on mobile
- **FR-300.5**: Desktop rendering of all pages is visually identical before and after migration

#### FR-400: Design System Documentation

- **FR-400.1**: Add "Table Responsiveness" section to `frontend/docs/design-system.md`
- **FR-400.2**: Add "Tab Responsiveness" section to `frontend/docs/design-system.md`
- **FR-400.3**: Document `cardRole` conventions and recommended mappings
- **FR-400.4**: Document that all new tables MUST use `<ResponsiveTable>`
- **FR-400.5**: Document that all new tab sets MUST use `<ResponsiveTabsList>`

### Non-Functional Requirements

#### NFR-100: Performance

- **NFR-100.1**: No additional API calls — mobile and desktop render from the same data
- **NFR-100.2**: Both table and card views render from a single pass over the data array
- **NFR-100.3**: CSS class toggling (`hidden md:block` / `md:hidden`) handled by Tailwind — no JavaScript viewport detection

#### NFR-200: Accessibility

- **NFR-200.1**: Mobile cards maintain semantic structure (headings, labels)
- **NFR-200.2**: Select picker is keyboard-navigable (provided by Radix UI Select)
- **NFR-200.3**: Touch targets for action buttons are ≥44px on mobile
- **NFR-200.4**: Screen readers can access all data in both table and card views

#### NFR-300: Testing

- **NFR-300.1**: Visual regression tests at 375px (iPhone SE), 390px (iPhone 14), 412px (Pixel) viewports
- **NFR-300.2**: Unit tests for `<ResponsiveTable>` rendering both views based on viewport
- **NFR-300.3**: Unit tests for `<ResponsiveTabsList>` rendering select vs tab strip
- **NFR-300.4**: Integration tests confirming tab changes via select update the active content panel
- **NFR-300.5**: Verify desktop rendering is pixel-identical before and after migration

---

## Implementation Plan

### Phase 1: Core Components

**Tasks:**

1. Create `<ResponsiveTable>` component with card rendering logic
2. Create `<ResponsiveTabsList>` component with select rendering logic
3. Unit tests for both components

**Checkpoint**: Both components render correctly in isolation

---

### Phase 2: High-Severity Table Migrations

**Tasks:**

1. Migrate `ResultsTable` (10 columns — most complex)
2. Migrate `CollectionList` (9 columns — includes tabs conversion)
3. Migrate `LocationsTab`, `OrganizersTab`, `PerformersTab` (8 columns each)
4. Migrate `AgentsPage` (7 columns — uses dropdown actions)

**Checkpoint**: The 6 most complex tables render as cards on mobile

---

### Phase 3: Tab Migrations

**Tasks:**

1. Migrate `SettingsPage` tabs (6 tabs with admin badges — worst case)
2. Migrate `AnalyticsPage` main tabs (with action buttons)
3. Migrate `AnalyticsPage` nested runs sub-tabs (with count badges)
4. Migrate `DirectoryPage` tabs
5. Migrate `CollectionList` tabs (convert to controlled)

**Checkpoint**: All tab strips use select picker on mobile

---

### Phase 4: Remaining Tables and Polish

**Tasks:**

1. Migrate `CategoriesTab`, `ConnectorList`, `TokensTab`, `TeamsTab`, `ReleaseManifestsTab`
2. Fix pagination stacking on mobile
3. Verify action button touch targets
4. Visual QA at target viewports (375px, 390px, 412px)

**Checkpoint**: All pages are mobile-responsive

---

### Phase 5: Documentation

**Tasks:**

1. Add responsive table and tab sections to design system docs
2. Document `cardRole` mapping conventions
3. Add migration guide for future tables/tabs

**Checkpoint**: Design system updated, all future development guided

---

## Alternatives Considered

### Tables

| Approach | Pros | Cons | Decision |
|---|---|---|---|
| **Card layout (chosen)** | All data visible; touch-friendly; clean UX | Requires column config per table | Chosen — best mobile UX |
| Column hiding | Minimal code change | Users lose access to data; doesn't scale to 9+ columns | Rejected |
| Horizontal scroll (current) | Already implemented | Poor mobile UX; action buttons hidden; no discoverability | Rejected (status quo) |
| TanStack Table | Built-in column visibility, sorting, filtering | Heavy dependency; full rewrite of 11 tables; overkill | Rejected |

### Tabs

| Approach | Pros | Cons | Decision |
|---|---|---|---|
| **Select picker (chosen)** | Works for any tab count; constant width; familiar UX | Loses at-a-glance visibility | Chosen — most scalable |
| Horizontally scrollable strip | Preserves visual style | Hidden tabs need scrolling; no cue for overflow | Rejected |
| Multi-row wrapping | Shows all tabs | Breaks pill aesthetic; inconsistent heights | Rejected |
| Hamburger/overflow menu | Common in toolbars | Unfamiliar for tab navigation | Rejected |

---

## Risks and Mitigation

### Risk 1: Card Layout Information Density

- **Impact**: Medium — Cards may feel verbose for simple tables (4–5 columns)
- **Probability**: Low — Most tables have 6+ columns
- **Mitigation**: Tables with fewer columns (Teams, Release Manifests) can use fewer detail rows; `hidden` role reduces noise

### Risk 2: Action Button Discoverability on Cards

- **Impact**: Medium — Users may not see actions at the bottom of cards
- **Probability**: Medium — Card bottom is below the fold for tall cards
- **Mitigation**: Keep action row visually distinct with border-top separator; consider sticky action row for very tall cards

### Risk 3: Select Picker Loses Tab Context

- **Impact**: Low — Users cannot see all tab options at once on mobile
- **Probability**: Certain — By design, only the active tab label is visible
- **Mitigation**: Select trigger shows the active tab with icon; dropdown reveals all options. This is an accepted trade-off for mobile.

### Risk 4: Migration Effort

- **Impact**: Medium — 11 tables and 6 tab instances require column/tab definitions
- **Probability**: Certain — Each page needs a `cardRole` mapping
- **Mitigation**: Phase the work (highest severity first); the mapping is mechanical once the component is built

### Risk 5: Uncontrolled Tabs (CollectionList)

- **Impact**: Low — CollectionList uses uncontrolled `Tabs` with `defaultValue`
- **Probability**: Certain — Needs conversion to controlled
- **Mitigation**: Convert to controlled with `useState` — minimal change, well-understood pattern

---

## Open Questions

1. **Dual rendering DOM size**: Both the table and card views are in the DOM (hidden via CSS). For pages with very large datasets (50+ rows with pagination), should we conditionally render based on a `useMediaQuery` hook instead of CSS hiding to reduce DOM nodes?

2. **Card action pattern**: Should all mobile card action rows use a consolidated `DropdownMenu` (single button), or individual labeled buttons? The Agents page already uses a dropdown — should this become the standard?

3. **Nested tabs depth**: If the application introduces deeper tab nesting in the future, should `<ResponsiveTabsList>` support indented/grouped select items?

4. **Animation**: Should the card list have enter/exit animations (e.g., fade-in on filter changes) to match the table's row transition effects?

---

## Revision History

- **2026-01-29 (v1.0)**: Initial draft
  - Defined responsive table card layout component
  - Defined responsive tabs select picker component
  - Catalogued all 11 affected tables and 6 affected tab instances
  - Created 5-phase implementation plan
  - Documented alternatives considered and risks
