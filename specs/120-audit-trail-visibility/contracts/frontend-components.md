# Frontend Contract: Audit Trail Components

## TypeScript Types

**File**: `frontend/src/contracts/api/audit-api.ts`

```typescript
/**
 * Minimal user representation for audit attribution display.
 * Does NOT include email by default to avoid unconditional PII exposure.
 * Use AuditUserDetail for contexts where full email is authorized.
 */
export interface AuditUserSummary {
  guid: string              // usr_xxx
  display_name: string | null
  email?: string | null     // Optional — only populated when requester is authorized
}

/**
 * Extended user representation with full PII, returned only when
 * the requester has permission to view email (e.g., team admins,
 * detail-dialog endpoints with explicit permission checks).
 */
export interface AuditUserDetail extends AuditUserSummary {
  email: string             // Always present in the detail variant
}

export interface AuditInfo {
  created_at: string    // ISO 8601
  created_by: AuditUserSummary | null
  updated_at: string    // ISO 8601
  updated_by: AuditUserSummary | null
}
```

### PII Protection

- **API layer**: Backend audit serialization populates `AuditUserSummary.email` only when the requester is authorized (e.g., same team admin or the user themselves). Unauthorized responses omit or null-out the `email` field.
- **Frontend rendering**: The audit detail dialog component (AuditTrailSection in detail views) reads `email` only when a `showEmail` prop is `true` or a permission check (`hasPermission('view_email')`) passes. Otherwise it displays a masked value via a `maskEmail(email)` helper (e.g., `j***@example.com`) or omits the email entirely.
- **List view popover**: AuditTrailPopover displays `display_name` with fallback to `email` only if `email` is present; otherwise shows `display_name` alone or "—".

### maskEmail Helper

```typescript
// frontend/src/utils/mask-email.ts
export function maskEmail(email: string | null | undefined): string {
  if (!email) return '—'
  const [local, domain] = email.split('@')
  if (!domain) return '—'
  return `${local[0]}***@${domain}`
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
  audit?: AuditInfo | null
}
```

### Behavior

- **Null/undefined audit**: If `audit` is null or undefined, the component returns a fallback `<span className="text-muted-foreground">—</span>` (early return, no popover rendered).
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
  audit?: AuditInfo | null
}
```

### Behavior

- **Null/undefined audit**: If `audit` is null or undefined, the component returns `null` (renders nothing). Consumers (detail dialogs) conditionally render: `{entity.audit && <AuditTrailSection audit={entity.audit} />}`.
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

### Core Tests

1. **AuditTrailPopover**: Renders with full data, partial data (null users), unmodified record (created_at === updated_at).
2. **AuditTrailSection**: Renders with full data, null users, same timestamps.
3. **Fallback**: List views gracefully handle missing `audit` field (transitional state).

### Edge-Case Tests

4. **Deleted user scenario** (AuditTrailPopover + AuditTrailSection): Simulate `created_by` and/or `updated_by` as `null` (representing FK SET NULL after user deletion). Assert the UI renders the "—" placeholder for the user name and does not throw errors. Test both components independently.

5. **API token attribution** (AuditTrailPopover + AuditTrailSection): Supply `AuditUserSummary` records with synthetic system-user data (e.g., `{ guid: "usr_xxx", display_name: "API Token: CI Pipeline", email: "tok_ci@system.shuttersense" }`). Assert the popover/section displays the full `display_name` "API Token: CI Pipeline". When `email` is present and `display_name` is null, assert the email or masked email is shown as fallback.

6. **Agent attribution** (AuditTrailPopover + AuditTrailSection): Supply `AuditUserSummary` with `display_name: "Agent: Home Mac"` and `email: "agt_home_mac@system.shuttersense"`. Assert the popover/section renders the full display_name "Agent: Home Mac".

7. **List-view missing audit field** (list view integration): Render a list-view row where `item.audit` is `undefined` or `null`. Assert the fallback `<span>` with `formatRelativeTime(item.updated_at)` renders correctly and no AuditTrailPopover is mounted. Verify no console errors or thrown exceptions.
