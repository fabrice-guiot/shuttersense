# Quickstart: Mobile Responsive Tables and Tabs

**Feature Branch**: `123-mobile-responsive-tables-tabs`
**Date**: 2026-01-29

## Prerequisites

- Node.js 18+ and npm/pnpm
- The ShutterSense frontend dev server running (`npm run dev` from `frontend/`)

## Development Setup

```bash
# Switch to the feature branch
git checkout 123-mobile-responsive-tables-tabs

# Install dependencies (if not already)
cd frontend && npm install

# Start dev server
npm run dev
```

## Testing Responsive Behavior

### Browser DevTools (Recommended)

1. Open Chrome/Firefox DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M / Cmd+Shift+M)
3. Select a mobile preset:
   - **iPhone SE**: 375px (minimum target)
   - **iPhone 14**: 390px
   - **Pixel 7**: 412px
4. Navigate to any table or tabbed page

### Key Pages to Test

| Page | URL | What to Verify |
| ---- | --- | -------------- |
| Collections | `/collections` | Table → cards, tab strip → select |
| Settings | `/settings` | 6 tabs → select picker with admin badges |
| Analytics | `/analytics` | Tabs with action buttons, nested sub-tabs |
| Directory | `/directory` | 3 tabs, tables in each tab |
| Agents | `/agents` | Table with dropdown action menu |
| Results | (via collection) | 10-column table, pagination stacking |

### Responsive Breakpoint

- **Below 768px**: Cards + select picker (mobile)
- **768px and above**: Standard table + tab strip (desktop)

## Using the New Components

### ResponsiveTable

```typescript
import { ResponsiveTable, type ColumnDef } from '@/components/ui/responsive-table'

interface MyItem {
  guid: string
  name: string
  status: string
}

const columns: ColumnDef<MyItem>[] = [
  { header: 'Name', cell: (item) => item.name, cardRole: 'title' },
  { header: 'Status', cell: (item) => <Badge>{item.status}</Badge>, cardRole: 'badge' },
  { header: 'Actions', cell: (item) => <Button>Edit</Button>, cardRole: 'action' },
]

<ResponsiveTable data={items} columns={columns} keyField="guid" />
```

### ResponsiveTabsList

```typescript
import { ResponsiveTabsList, type TabOption } from '@/components/ui/responsive-tabs-list'

const tabs: TabOption[] = [
  { value: 'tab1', label: 'First Tab', icon: Settings },
  { value: 'tab2', label: 'Second Tab', icon: Users },
]

<Tabs value={activeTab} onValueChange={setActiveTab}>
  <ResponsiveTabsList tabs={tabs} value={activeTab} onValueChange={setActiveTab}>
    <TabsTrigger value="tab1"><Settings className="h-4 w-4" /> First Tab</TabsTrigger>
    <TabsTrigger value="tab2"><Users className="h-4 w-4" /> Second Tab</TabsTrigger>
  </ResponsiveTabsList>
  <TabsContent value="tab1">...</TabsContent>
  <TabsContent value="tab2">...</TabsContent>
</Tabs>
```

## Card Role Quick Reference

| Role | Use For | Example |
| ---- | ------- | ------- |
| `title` | Primary identifier | Name, Version |
| `subtitle` | Secondary context | Location, Hostname |
| `badge` | Status/type indicators | Active/Inactive badges, Type badges |
| `detail` | All other data (default) | Counts, dates, descriptions |
| `action` | Buttons and menus | Edit, Delete, dropdown menus |
| `hidden` | Low-priority on mobile | Created date, internal IDs |

## Verification Checklist

- [ ] New `ResponsiveTable` component renders table at >=768px and cards at <768px
- [ ] New `ResponsiveTabsList` component renders tab strip at >=768px and select at <768px
- [ ] All 13 tables migrated with correct card role mappings (AgentDetailPage, TeamPage, AgentsPage, CollectionList, ConnectorList, LocationsTab, OrganizersTab, PerformersTab, ReleaseManifestsTab, ResultsTable, CategoriesTab, TokensTab, TeamsTab)
- [ ] All 6 tab instances migrated (including nested Analytics sub-tabs)
- [ ] CollectionList tabs converted to controlled
- [ ] Pagination bar stacks vertically on mobile
- [ ] Desktop rendering unchanged (no visual regressions)
- [ ] Design system documentation updated
