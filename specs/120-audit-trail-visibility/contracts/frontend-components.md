# Frontend Contract: Audit Trail Components

## TypeScript Types

**File**: `frontend/src/contracts/api/audit-api.ts`

```typescript
export interface AuditUserSummary {
  guid: string          // usr_xxx
  display_name: string | null
  email: string
}

export interface AuditInfo {
  created_at: string    // ISO 8601
  created_by: AuditUserSummary | null
  updated_at: string    // ISO 8601
  updated_by: AuditUserSummary | null
}
```

All existing entity API types gain:
```typescript
audit?: AuditInfo | null  // Optional for backward compatibility during deployment
```

## Component: AuditTrailPopover

**File**: `frontend/src/components/ui/audit-trail-popover.tsx`

### Props

```typescript
interface AuditTrailPopoverProps {
  audit: AuditInfo
}
```

### Behavior

- **Trigger**: Displays `formatRelativeTime(audit.updated_at)` (or `audit.created_at` if never modified).
- **Trigger style**: `text-sm text-muted-foreground`, dotted underline, cursor-default.
- **Popover content**: Card with created/modified details.
- **Null handling**: "—" for null `created_by`/`updated_by`.
- **Unmodified records**: If `created_at === updated_at`, only show creation row.

### Rendering

```
Trigger: "5 min ago"

Popover content:
┌─────────────────────────────────┐
│ Created   Jan 15, 2026 3:45 PM  │
│ by        John Doe               │
│─────────────────────────────────│
│ Modified  Jan 20, 2026 9:12 AM  │
│ by        Jane Smith             │
└─────────────────────────────────┘
```

## Component: AuditTrailSection

**File**: `frontend/src/components/ui/audit-trail-popover.tsx` (exported from same file)

### Props

```typescript
interface AuditTrailSectionProps {
  audit: AuditInfo
}
```

### Behavior

- Inline display for detail dialogs (no hover required).
- Renders as a `border-t` separated section at the bottom of dialogs.
- Shows created and modified rows with full timestamps and user names.
- Null users display "—".

### Rendering

```
─────────────────────────────────────────────────────────────
Created   Jan 15, 2026, 3:45 PM   by John Doe (john@example.com)
Modified  Jan 20, 2026, 9:12 AM   by Jane Smith (jane@example.com)
```

## List View Column Definition Pattern

For each of the 11 list views:

```typescript
{
  header: 'Modified',
  cell: (item) => item.audit
    ? <AuditTrailPopover audit={item.audit} />
    : <span className="text-muted-foreground">{formatRelativeTime(item.updated_at)}</span>,
  cardRole: 'detail',
}
```

**Position**: Second-to-last column (before Actions).

**Replaces**: Existing "Created" columns in ConnectorList, LocationsTab, OrganizersTab, PerformersTab, CategoriesTab, TokensTab.

## Affected List Views (11)

| Component | File | Action |
|-----------|------|--------|
| CollectionList | `CollectionList.tsx` | Add "Modified" column |
| ConnectorList | `ConnectorList.tsx` | Replace "Created" with "Modified" |
| ResultsTable | `ResultsTable.tsx` | Add "Modified" column |
| LocationsTab | `LocationsTab.tsx` | Replace "Created" with "Modified" |
| OrganizersTab | `OrganizersTab.tsx` | Replace "Created" with "Modified" |
| PerformersTab | `PerformersTab.tsx` | Replace "Created" with "Modified" |
| AgentsPage | `AgentsPage.tsx` | Add "Modified" column |
| CategoriesTab | `CategoriesTab.tsx` | Replace "Created" with "Modified" |
| TokensTab | `TokensTab.tsx` | Replace "Created" with "Modified" |
| TeamsTab | `TeamsTab.tsx` | Add "Modified" column |
| ReleaseManifestsTab | `ReleaseManifestsTab.tsx` | Add "Modified" column |

## Affected Detail Dialogs

| Component | File | Action |
|-----------|------|--------|
| AgentDetailsDialog | `AgentDetailsDialog.tsx` | Add AuditTrailSection |
| NotificationDetailDialog | `NotificationDetailDialog.tsx` | Add AuditTrailSection |

## Frontend Test Requirements

1. **AuditTrailPopover**: Renders with full data, partial data (null users), unmodified record (created_at === updated_at).
2. **AuditTrailSection**: Renders with full data, null users, same timestamps.
3. **Fallback**: List views gracefully handle missing `audit` field (transitional state).
