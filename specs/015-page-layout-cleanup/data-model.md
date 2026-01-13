# Data Model: Page Layout Cleanup

**Feature Branch**: `015-page-layout-cleanup`
**Created**: 2026-01-13

## Overview

This feature is a **frontend-only UI change**. No database entities or backend APIs are affected.

## Data Changes

**None required.** This feature:
- Removes redundant UI elements (duplicate titles)
- Repositions existing UI elements (action buttons)
- Adds static help content to route configuration

## Frontend Configuration Changes

### Route Configuration Extension

The existing `RouteConfig` interface in `App.tsx` will be extended:

```typescript
interface RouteConfig {
  path: string
  element: ReactElement
  pageTitle: string
  pageIcon?: LucideIcon
  pageHelp?: string  // NEW: Optional help description for the page
}
```

### TopHeader Props Extension

The `TopHeaderProps` interface will be extended:

```typescript
interface TopHeaderProps {
  pageTitle: string
  pageIcon?: LucideIcon
  stats?: HeaderStat[]
  className?: string
  onOpenMobileMenu?: () => void
  isSidebarCollapsed?: boolean
  pageHelp?: string  // NEW: Optional help text for tooltip
}
```

## No Backend Changes

- No new database tables
- No schema migrations
- No new API endpoints
- No changes to existing API responses

## State Management

No new state management required. The help content is:
- Static (defined at route configuration time)
- Passed through existing component props
- Rendered conditionally based on presence
