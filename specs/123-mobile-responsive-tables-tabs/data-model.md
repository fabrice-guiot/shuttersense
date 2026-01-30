# Data Model: Mobile Responsive Tables and Tabs

**Feature Branch**: `123-mobile-responsive-tables-tabs`
**Date**: 2026-01-29

## Overview

This feature introduces no new database entities or backend models. All changes are frontend-only, introducing two new TypeScript interfaces that define the component APIs for the responsive table and responsive tabs components.

## TypeScript Interfaces

### ColumnDef<T>

Defines how a single column renders in both desktop table and mobile card views.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `header` | `string` | Yes | Table header text displayed in the `<TableHead>` cell and used as the label in mobile card detail rows |
| `headerClassName` | `string` | No | Optional CSS class for `<TableHead>` element |
| `cell` | `(item: T) => React.ReactNode` | Yes | Render function for cell content, used in both table and card views |
| `cellClassName` | `string` | No | Optional CSS class for `<TableCell>` element |
| `cardRole` | `'title' \| 'subtitle' \| 'badge' \| 'detail' \| 'action' \| 'hidden'` | No | Controls rendering position in mobile card layout. Defaults to `'detail'` |

**Card Role Behavior**:

| Role | Card Position | Rendering |
|------|---------------|-----------|
| `title` | Top-left, bold text | Primary identifier (e.g., Name) |
| `subtitle` | Below title, muted text | Secondary context (e.g., Location, Hostname) |
| `badge` | Inline with title area, right-aligned | Status/type badges |
| `detail` | Key-value rows in card body | "Header: Value" label-value pairs |
| `action` | Bottom of card, full-width row | Action buttons with touch targets |
| `hidden` | Not rendered on mobile | Low-priority columns (e.g., Created date) |

### ResponsiveTableProps<T>

Props for the `<ResponsiveTable>` component.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `data` | `T[]` | Yes | Array of data items to render as rows/cards |
| `columns` | `ColumnDef<T>[]` | Yes | Column definitions with header, cell renderer, and card role |
| `keyField` | `keyof T` | Yes | Property used as React key for each row/card |
| `emptyState` | `React.ReactNode` | No | Content to render when data array is empty |
| `className` | `string` | No | Optional CSS class for the outer wrapper |

### TabOption

Defines a single tab for the mobile select picker.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `value` | `string` | Yes | Tab value matching `TabsTrigger` value and `TabsContent` value |
| `label` | `string` | Yes | Display label shown in select trigger and items |
| `icon` | `React.ComponentType<{ className?: string }>` | No | Optional icon component (Lucide icon) |
| `badge` | `React.ReactNode` | No | Optional badge content (e.g., count, "Admin" label) |

### ResponsiveTabsListProps

Props for the `<ResponsiveTabsList>` component.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tabs` | `TabOption[]` | Yes | Tab definitions for the mobile select picker |
| `value` | `string` | Yes | Currently active tab value |
| `onValueChange` | `(value: string) => void` | Yes | Change handler called when tab selection changes |
| `children` | `React.ReactNode` | Yes | `<TabsTrigger>` elements for the desktop tab strip |

## Entity Relationships

```
ResponsiveTable
  └── columns: ColumnDef<T>[]
        └── cardRole → determines card zone placement

ResponsiveTabsList
  └── tabs: TabOption[]
        └── value ↔ Tabs.value (shared controlled state)
        └── Select.value (mobile dropdown)
```

## State Management

**ResponsiveTable**: Stateless component. Receives data via props, renders both views. No internal state.

**ResponsiveTabsList**: Stateless component. Receives `value` and `onValueChange` from parent. The parent component (page) owns the tab state and synchronizes it with URL parameters where applicable.

**CollectionList migration**: Adds local `useState("all")` to manage tab state. No URL synchronization needed since CollectionList is a component within the Collections page, not a standalone route.
