# Quickstart: Page Layout Cleanup

**Feature Branch**: `015-page-layout-cleanup`
**Created**: 2026-01-13

## Overview

Remove duplicate page titles and add help tooltips to create a cleaner UI.

## Prerequisites

- Node.js (for frontend development)
- Running frontend dev server: `npm run dev`

## Key Files to Modify

### 1. TopHeader Component

**File**: `frontend/src/components/layout/TopHeader.tsx`

Add optional help tooltip:
```tsx
import { HelpCircle } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

interface TopHeaderProps {
  // ... existing props
  pageHelp?: string  // Add this
}

// In component, next to title:
{pageHelp && (
  <TooltipProvider>
    <Tooltip>
      <TooltipTrigger asChild>
        <button className="p-1 rounded-md hover:bg-accent">
          <HelpCircle className="h-4 w-4 text-muted-foreground" />
        </button>
      </TooltipTrigger>
      <TooltipContent>
        <p>{pageHelp}</p>
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
)}
```

### 2. Route Configuration

**File**: `frontend/src/App.tsx`

Add `pageHelp` to routes:
```tsx
interface RouteConfig {
  path: string
  element: ReactElement
  pageTitle: string
  pageIcon?: LucideIcon
  pageHelp?: string  // Add this
}

const routes: RouteConfig[] = [
  {
    path: '/settings',
    element: <SettingsPage />,
    pageTitle: 'Settings',
    pageIcon: Settings,
    pageHelp: 'Configure tools, event categories, and storage connectors',
  },
  // ... other routes
]
```

### 3. Page Components

**Remove h1 elements** from:
- `frontend/src/pages/CollectionsPage.tsx` (line ~134)
- `frontend/src/pages/ConnectorsPage.tsx` (line ~104)
- `frontend/src/pages/AnalyticsPage.tsx` (line ~395)
- `frontend/src/pages/EventsPage.tsx` (line ~285)
- `frontend/src/pages/SettingsPage.tsx` (line ~68)

**Reposition action buttons** in each page to be in a consistent location below the TopHeader.

## Testing

```bash
# Run frontend dev server
cd frontend
npm run dev

# Open browser at localhost:5173
# Navigate to each page and verify:
# 1. Only one title visible (in TopHeader)
# 2. Action buttons accessible
# 3. Help icon shows tooltip on hover (where applicable)
```

## Verification Checklist

- [ ] Collections page: Single title, "New Collection" button accessible
- [ ] Connectors page: Single title, "New Connector" button accessible
- [ ] Analytics page: Single title, tabs + action buttons on same row
- [ ] Events page: Single title, "New Event" button accessible
- [ ] Settings page: Single title, help tooltip shows description
- [ ] Mobile: All pages work at 375px width
- [ ] Tablet: All pages work at 768px width
- [ ] Desktop: All pages work at 1024px+ width
