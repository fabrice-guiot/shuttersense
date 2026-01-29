# Component API Contracts: Mobile Responsive Tables and Tabs

**Feature Branch**: `123-mobile-responsive-tables-tabs`
**Date**: 2026-01-29

## Overview

This feature is frontend-only and introduces no new backend API endpoints. The "contracts" are the public component APIs — the props interfaces that each consuming page/component must satisfy.

## Contract 1: ResponsiveTable<T>

**File**: `frontend/src/components/ui/responsive-table.tsx`

### Import

```typescript
import { ResponsiveTable } from '@/components/ui/responsive-table'
import type { ColumnDef } from '@/components/ui/responsive-table'
```

### Usage Contract

```typescript
// Consumer MUST provide:
// 1. A typed data array
// 2. Column definitions with cardRole for mobile layout
// 3. A keyField that uniquely identifies each row

interface CollectionRow {
  guid: string
  name: string
  type: string
  // ...
}

const columns: ColumnDef<CollectionRow>[] = [
  { header: 'Name', cell: (item) => item.name, cardRole: 'title' },
  { header: 'Type', cell: (item) => <Badge>{item.type}</Badge>, cardRole: 'badge' },
  { header: 'Agent', cell: (item) => item.agent_name, cardRole: 'detail' },
  { header: 'Actions', cell: (item) => <ActionButtons item={item} />, cardRole: 'action' },
  { header: 'Created', cell: (item) => formatDate(item.created), cardRole: 'hidden' },
]

<ResponsiveTable
  data={collections}
  columns={columns}
  keyField="guid"
  emptyState={<EmptyCollections />}
/>
```

### Behavioral Contract

| Viewport | Rendering | DOM |
|----------|-----------|-----|
| >= 768px (md) | Standard `<Table>` with `<TableHeader>`/`<TableBody>` | `hidden md:block` wrapper |
| < 768px | Card list with role-based zones | `md:hidden` wrapper |

| cardRole | Required | Default | Mobile Behavior |
|----------|----------|---------|-----------------|
| `title` | At least 1 recommended | — | Bold text, top-left of card |
| `subtitle` | No | — | Muted text below title |
| `badge` | No | — | Right-aligned inline with title |
| `detail` | No | Yes (default) | Key-value row: "Header: Value" |
| `action` | No | — | Bottom row with border separator |
| `hidden` | No | — | Not rendered on mobile |

### Edge Case Contract

- If `data` is empty and `emptyState` is provided → render `emptyState`
- If `data` is empty and no `emptyState` → render nothing
- If no columns have `cardRole: 'action'` → no action row separator rendered
- If no columns have `cardRole: 'badge'` → no badge area rendered
- If all columns lack `cardRole` → all render as `detail` key-value rows

---

## Contract 2: ResponsiveTabsList

**File**: `frontend/src/components/ui/responsive-tabs-list.tsx`

### Import

```typescript
import { ResponsiveTabsList } from '@/components/ui/responsive-tabs-list'
import type { TabOption } from '@/components/ui/responsive-tabs-list'
```

### Usage Contract

```typescript
// Consumer MUST provide:
// 1. Tab definitions array with value, label, optional icon/badge
// 2. Current value (controlled)
// 3. onValueChange handler
// 4. Desktop TabsTrigger children

const tabOptions: TabOption[] = [
  { value: 'config', label: 'Configuration', icon: Settings },
  { value: 'categories', label: 'Categories', icon: Tag },
  { value: 'tokens', label: 'API Tokens', icon: Key, badge: <Badge>Admin</Badge> },
]

<Tabs value={activeTab} onValueChange={setActiveTab}>
  <ResponsiveTabsList
    tabs={tabOptions}
    value={activeTab}
    onValueChange={setActiveTab}
  >
    {tabOptions.map(tab => (
      <TabsTrigger key={tab.value} value={tab.value}>
        {tab.icon && <tab.icon className="h-4 w-4" />}
        {tab.label}
        {tab.badge}
      </TabsTrigger>
    ))}
  </ResponsiveTabsList>
  <TabsContent value="config">...</TabsContent>
  <TabsContent value="categories">...</TabsContent>
</Tabs>
```

### Behavioral Contract

| Viewport | Rendering | DOM |
|----------|-----------|-----|
| >= 768px (md) | Standard `<TabsList>` wrapping children | `hidden md:inline-flex` wrapper |
| < 768px | `<Select>` dropdown with `TabOption` items | `md:hidden` wrapper |

### Integration Contract

- `ResponsiveTabsList` MUST be placed inside a `<Tabs>` component.
- The `value` and `onValueChange` props MUST match the parent `<Tabs>` props.
- The mobile `<Select>` calls the same `onValueChange` handler, so `Tabs` receives state updates from both sources.
- `TabsContent` components react to the parent `Tabs` `value` prop regardless of whether the change came from a `TabsTrigger` click or `Select` change.

### Flex Container Compatibility

When `ResponsiveTabsList` is placed alongside action buttons in a flex row (e.g., Analytics page), the outer flex container handles the stacking:

```typescript
// The outer flex container controls layout — ResponsiveTabsList does not need to know about siblings
<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
  <ResponsiveTabsList tabs={tabs} value={value} onValueChange={onChange}>
    {children}
  </ResponsiveTabsList>
  <div className="flex gap-2">
    <Button>Refresh</Button>
    <Button>Run Tool</Button>
  </div>
</div>
```

---

## Migration Contract: Per-Table Card Role Mappings

Each table migration MUST define card roles according to these mappings (from PRD):

| Table | title | subtitle | badge | detail | action | hidden |
|-------|-------|----------|-------|--------|--------|--------|
| Results | Collection | Connector | Tool, Status | Pipeline, Files, Issues, Duration, Completed | View, Download, Delete | — |
| Collections | Name | Location | Type, State | Agent, Pipeline, Inventory, Status | Edit, Delete | — |
| Connectors | Name | — | Type, Status | Credentials, Created | Test, Edit, Delete | — |
| Locations | Name | Location | Status | Category, Rating, Instagram | Edit, Delete | Created |
| Organizers | Name | — | Status | Event Count, Rating, Category, Instagram | Edit, Delete | Created |
| Performers | Name | — | Status | Event Count, Rating, Category, Social | Edit, Delete | Created |
| Agents | Name | Hostname + OS | Status | Load, Version, Last Heartbeat | Menu (dropdown) | — |
| Categories | Name | — | Color, Icon, Status | Event Count | Edit, Delete | Created |
| Teams | Team | Slug | Status | Users | Edit, Delete | — |
| Tokens | Name | Prefix | Status | Created, Expires | Delete | — |
| Releases | Version | Release Date | Status | — | Actions | — |
