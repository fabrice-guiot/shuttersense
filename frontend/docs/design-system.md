# Photo Admin Design System

This document establishes UI/UX guidelines to ensure consistency across all screens, components, and interactions in the Photo Admin application.

## Table of Contents

- [Color System](#color-system)
- [Semantic Colors](#semantic-colors)
- [Button Guidelines](#button-guidelines)
- [Message & Feedback Patterns](#message--feedback-patterns)
- [Status Indicators](#status-indicators)
- [Domain Model Display](#domain-model-display)
- [Notification System](#notification-system)
- [Icons](#icons)
- [Dark Theme Compliance](#dark-theme-compliance)

---

## Color System

### Design Tokens

Always use CSS custom properties (design tokens) instead of hardcoded colors. This ensures theme consistency and makes future theming possible.

```tsx
// CORRECT - Uses design tokens
<div className="bg-background text-foreground" />
<div className="bg-card border-border" />
<div className="text-muted-foreground" />

// INCORRECT - Hardcoded colors
<div className="bg-gray-900 text-white" />
<div className="bg-slate-800 border-slate-700" />
```

### Available Design Tokens

| Token | Purpose | Dark Mode Value |
|-------|---------|-----------------|
| `background` | Page/app background | Very dark blue-gray |
| `foreground` | Primary text | Near white |
| `card` | Card/panel backgrounds | Same as background |
| `primary` | Primary brand color | Blue (#3B82F6) |
| `secondary` | Secondary backgrounds | Muted blue-gray |
| `muted` | Subtle backgrounds | Same as secondary |
| `muted-foreground` | Secondary text | Light gray |
| `accent` | Interactive hover states | Same as secondary |
| `destructive` | Errors/danger | Red |
| `border` | Default borders | Muted blue-gray |
| `ring` | Focus rings | Blue |

---

## Semantic Colors

Use these semantic color patterns consistently across the application.

### Status Colors

| Status | Badge Variant | Use Case |
|--------|---------------|----------|
| **Success/Positive** | `success` | Accessible, Active, Valid, Complete, Live |
| **Error/Negative** | `destructive` | Not Accessible, Invalid, Failed, Error |
| **Warning/Caution** | `warning` (to be added) | Pending validation, Needs attention |
| **Info/Neutral** | `info` | Archived, Read-only, Reference |
| **Inactive/Disabled** | `muted` or `outline` | Inactive, Disabled, Closed |
| **Default/Standard** | `secondary` | Normal state, Type labels |

### Feature State Colors

| State | Visual Treatment | Example |
|-------|-----------------|---------|
| **Enabled/Active** | Green dot or `success` badge | Pipeline enabled |
| **Disabled/Inactive** | Gray dot or `muted`/`outline` badge | Pipeline disabled |
| **Default Record** | Star icon or subtle highlight | Default connector |

### Collection State Mapping

```typescript
// CANONICAL MAPPING - Use consistently
const COLLECTION_STATE_BADGE_VARIANT = {
  live: 'success',      // Green - actively used
  closed: 'muted',      // Gray - not accepting new items
  archived: 'info'      // Blue - historical/read-only
}
```

### Accessibility Status Mapping

```typescript
// CANONICAL MAPPING - Use consistently
const ACCESSIBILITY_STATUS = {
  accessible: {
    variant: 'success',
    label: 'Accessible',
    description: 'Collection can be read'
  },
  notAccessible: {
    variant: 'destructive',
    label: 'Not Accessible',
    description: 'Connection or permission error'
  }
}
```

---

## Button Guidelines

### Primary Actions

Use the **default** (primary) button variant for main actions.

```tsx
// Main form submit actions
<Button>Create Collection</Button>
<Button>Save Changes</Button>
<Button>Submit</Button>

// Page primary actions
<Button className="gap-2">
  <Plus className="h-4 w-4" />
  New Collection
</Button>
```

### Secondary/Cancel Actions

Use **outline** variant for secondary actions and cancel buttons.

```tsx
<Button variant="outline">Cancel</Button>
<Button variant="outline">Back</Button>
<Button variant="outline">Skip</Button>
```

### Destructive Actions

Use **destructive** variant ONLY for delete/remove operations.

```tsx
<Button variant="destructive">Delete</Button>
<Button variant="destructive">Remove</Button>
```

### Toolbar/Icon Actions

Use **ghost** variant for icon-only buttons in toolbars and table rows.

```tsx
<Button variant="ghost" size="icon" aria-label="Edit">
  <Edit className="h-4 w-4" />
</Button>
```

### Button Placement in Dialogs

```tsx
// Standard dialog footer layout
<DialogFooter>
  <Button variant="outline" onClick={onCancel}>Cancel</Button>
  <Button onClick={onConfirm}>Confirm</Button>
</DialogFooter>

// Delete confirmation dialog
<DialogFooter>
  <Button variant="outline" onClick={onCancel}>Cancel</Button>
  <Button variant="destructive" onClick={onDelete}>Delete</Button>
</DialogFooter>
```

### Button Placement in Forms

```tsx
// Standard form actions - right-aligned
<div className="flex justify-end gap-2 pt-4">
  <Button type="button" variant="outline" onClick={onCancel}>
    Cancel
  </Button>
  <Button type="submit">
    {isEdit ? 'Update' : 'Create'}
  </Button>
</div>

// Form with test action - split layout
<div className="flex justify-between gap-2 pt-4">
  <div>
    <Button type="button" variant="outline" onClick={onTest}>
      <TestTube className="h-4 w-4 mr-2" />
      Test Connection
    </Button>
  </div>
  <div className="flex gap-2">
    <Button type="button" variant="outline" onClick={onCancel}>
      Cancel
    </Button>
    <Button type="submit">Save</Button>
  </div>
</div>
```

---

## Message & Feedback Patterns

### Alert Variants

| Variant | Use Case | Visual |
|---------|----------|--------|
| `default` | Informational messages | Default styling |
| `destructive` | Errors, failures | Red border, red text |
| `success` (to be added) | Success confirmations | Green styling |
| `warning` (to be added) | Warnings, cautions | Yellow/amber styling |

### Page-Level Errors

Display API errors and page-level issues at the top of the content area.

```tsx
// Page-level error pattern
{error && (
  <Alert variant="destructive">
    <AlertCircle className="h-4 w-4" />
    <AlertTitle>Error</AlertTitle>
    <AlertDescription>{error}</AlertDescription>
  </Alert>
)}
```

### Form-Level Errors

Display form submission errors inside the form, above the action buttons.

```tsx
// Form-level error pattern
{formError && (
  <Alert variant="destructive" className="mb-4">
    <AlertDescription>{formError}</AlertDescription>
  </Alert>
)}
```

### Field-Level Errors

Use FormMessage component for field validation errors.

```tsx
<FormField
  control={form.control}
  name="fieldName"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Field Label</FormLabel>
      <FormControl>
        <Input {...field} />
      </FormControl>
      <FormMessage /> {/* Shows Zod validation errors */}
    </FormItem>
  )}
/>
```

### API Error Handling

All API errors should be transformed into user-friendly messages:

```typescript
// Service layer error handling pattern
try {
  const response = await fetch(url)
  if (!response.ok) {
    const errorData = await response.json()
    const error = new Error(errorData.error?.message || 'Operation failed')
    error.userMessage = getUserFriendlyMessage(response.status, errorData)
    throw error
  }
} catch (err) {
  // Network errors
  if (err.name === 'TypeError') {
    const error = new Error('Unable to connect to server')
    error.userMessage = 'Unable to connect to the server. Please check your connection.'
    throw error
  }
  throw err
}

// Hook layer - display userMessage if available
catch (err: any) {
  const errorMessage = err.userMessage || 'Operation failed'
  setError(errorMessage)
}
```

### Connection/Backend Unavailable

When the backend is unavailable, display a clear message:

```tsx
// Backend unavailable pattern
<Alert variant="destructive">
  <AlertCircle className="h-4 w-4" />
  <AlertTitle>Connection Error</AlertTitle>
  <AlertDescription>
    Unable to connect to the server. Please check your connection and try again.
  </AlertDescription>
</Alert>
```

### Empty States

Use consistent empty state messaging:

```tsx
// No data empty state
<div className="flex flex-col items-center justify-center py-12 text-center">
  <FolderOpen className="h-10 w-10 text-muted-foreground mb-3" />
  <p className="text-muted-foreground">No collections found</p>
  <p className="text-sm text-muted-foreground mt-1">
    Create a collection to get started
  </p>
</div>

// No search results empty state
<div className="flex flex-col items-center justify-center py-12 text-center">
  <Search className="h-10 w-10 text-muted-foreground mb-3" />
  <p className="text-muted-foreground">No results for "{searchTerm}"</p>
  <p className="text-sm text-muted-foreground mt-1">
    Try a different search term
  </p>
</div>
```

---

## Status Indicators

### Badge Usage

```tsx
// Type labels - always secondary
<Badge variant="secondary">{typeLabel}</Badge>

// Active/Inactive status
<Badge variant={isActive ? 'default' : 'outline'}>
  {isActive ? 'Active' : 'Inactive'}
</Badge>

// Accessibility status
<Badge variant={isAccessible ? 'success' : 'destructive'}>
  {isAccessible ? 'Accessible' : 'Not Accessible'}
</Badge>

// Collection state
<Badge variant={COLLECTION_STATE_BADGE_VARIANT[state]}>
  {COLLECTION_STATE_LABELS[state]}
</Badge>
```

### Loading States

```tsx
// Table/list loading
<div className="flex justify-center py-8">
  <div
    role="status"
    className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"
  />
</div>

// Button loading
<Button disabled>
  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
  Loading...
</Button>
```

---

## Domain Model Display

### Centralized Label Registry

All domain model labels MUST be defined in a single location and reused throughout the application.

**Location**: `src/contracts/domain-labels.ts` (to be created)

```typescript
// src/contracts/domain-labels.ts

// ============================================================================
// Connector Types
// ============================================================================

export const CONNECTOR_TYPE_LABELS: Record<ConnectorType, string> = {
  s3: 'Amazon S3',
  gcs: 'Google Cloud Storage',
  smb: 'SMB/CIFS'
}

export const CONNECTOR_TYPE_ICONS: Record<ConnectorType, LucideIcon> = {
  s3: Cloud,      // or a specific S3 icon
  gcs: Cloud,     // or a specific GCS icon
  smb: HardDrive
}

// ============================================================================
// Collection Types
// ============================================================================

export const COLLECTION_TYPE_LABELS: Record<CollectionType, string> = {
  local: 'Local',
  s3: 'Amazon S3',
  gcs: 'Google Cloud Storage',
  smb: 'SMB/CIFS'
}

// ============================================================================
// Collection States
// ============================================================================

export const COLLECTION_STATE_LABELS: Record<CollectionState, string> = {
  live: 'Live',
  closed: 'Closed',
  archived: 'Archived'
}

// ============================================================================
// Domain Icons (for navigation and references)
// ============================================================================

export const DOMAIN_ICONS = {
  collection: FolderOpen,
  connector: Plug,
  pipeline: Workflow,
  asset: Archive,
  // ... add more as domains are created
} as const
```

### Using Domain Labels

```tsx
// CORRECT - Import from centralized location
import { CONNECTOR_TYPE_LABELS } from '@/contracts/domain-labels'

<Badge variant="secondary">
  {CONNECTOR_TYPE_LABELS[connector.type]}
</Badge>

// INCORRECT - Defining labels locally
const TYPE_LABELS = { s3: 'Amazon S3', ... } // Don't do this!
```

### Foreign Key Reference Display

When displaying a reference to another domain object:

```tsx
// FK reference pattern - show icon + label
import { DOMAIN_ICONS, CONNECTOR_TYPE_LABELS } from '@/contracts/domain-labels'

const ConnectorIcon = DOMAIN_ICONS.connector

<div className="flex items-center gap-2">
  <ConnectorIcon className="h-4 w-4 text-muted-foreground" />
  <span>{connector.name}</span>
  <Badge variant="secondary" className="text-xs">
    {CONNECTOR_TYPE_LABELS[connector.type]}
  </Badge>
</div>
```

---

## Notification System

### Toast Notifications (To Be Implemented)

Toast notifications should be used for:
- Success confirmations (created, updated, deleted)
- Transient errors that don't block the UI
- Background operation completion

```tsx
// Proposed toast usage
import { useToast } from '@/hooks/useToast'

const { toast } = useToast()

// Success toast
toast({
  title: 'Collection Created',
  description: 'Your new collection has been created successfully.',
  variant: 'success'
})

// Error toast
toast({
  title: 'Operation Failed',
  description: error.userMessage,
  variant: 'destructive'
})
```

### Header Notification Bell

The notification bell in the TopHeader should:
1. Show count of unread notifications
2. Open a dropdown/panel showing recent notifications
3. Link to a dedicated notifications page (if needed)

**Integration Pattern:**
- Toast = ephemeral feedback (disappears after ~5 seconds)
- Bell notifications = persistent items requiring user attention
- Toasts do NOT add to bell count unless they represent important events

### Notification Categories

| Category | Toast | Bell | Examples |
|----------|-------|------|----------|
| CRUD Success | Yes | No | "Collection created" |
| Validation Error | No (inline) | No | Form field errors |
| API Error | Yes (transient) | Yes (if critical) | "Server unavailable" |
| Background Task | Yes | Yes | "Scan complete", "Export ready" |
| System Alert | No | Yes | "License expiring" |

---

## Icons

### Icon Sizing

| Context | Size | Class |
|---------|------|-------|
| Inline with text | 16px | `h-4 w-4` |
| Standalone small | 20px | `h-5 w-5` |
| Page header | 24px | `h-6 w-6` |
| Empty state | 40px | `h-10 w-10` |

### Domain Object Icons

Each domain object type should have a consistent icon:

| Domain | Icon | Usage |
|--------|------|-------|
| Collection | `FolderOpen` | Sidebar, headers, FK refs |
| Connector | `Plug` | Sidebar, headers, FK refs |
| Pipeline | `Workflow` | Sidebar, headers, FK refs |
| Asset | `Archive` | Sidebar, headers, FK refs |
| Analytics | `BarChart3` | Sidebar only |
| Settings | `Settings` | Sidebar only |

### Action Icons

| Action | Icon |
|--------|------|
| Create/Add | `Plus` |
| Edit | `Edit` |
| Delete | `Trash2` |
| Test/Check | `CloudCheck`, `FolderCheck` |
| Refresh/Sync | `RefreshCw`, `FolderSync` |
| Info | `Info` |
| Search | `Search` |
| Filter | `Filter` |

---

## Dark Theme Compliance

### Required Practices

1. **Never use hardcoded colors** - Always use design tokens
2. **Test in dark mode** - All components must be verified in dark mode
3. **Use semantic color classes** - `text-foreground` not `text-white`
4. **Contrast ratios** - Ensure WCAG AA compliance (4.5:1 for text, 3:1 for UI)

### Scrollbar Styling

Scrollbars are styled globally to match the dark theme. The styles are defined in `globals.css` and apply to all scrollable elements.

**Design Tokens:**

| Token | Purpose | Dark Mode |
|-------|---------|-----------|
| `--scrollbar-thumb` | Scrollbar handle | Muted gray |
| `--scrollbar-thumb-hover` | Handle on hover | Lighter gray |
| `--scrollbar-track` | Scrollbar track | Matches background |

**Browser Support:**

| Browser | Implementation | Notes |
|---------|----------------|-------|
| Chrome/Edge/Safari | WebKit pseudo-elements | Full styling (rounded corners, hover states) |
| Firefox | Standard CSS properties | `scrollbar-color`, `scrollbar-width: thin` |

**CSS Pattern (already implemented in globals.css):**

```css
/* Firefox */
* {
  scrollbar-color: hsl(var(--scrollbar-thumb)) hsl(var(--scrollbar-track));
  scrollbar-width: thin;
}

/* WebKit (Chrome, Safari, Edge) */
*::-webkit-scrollbar { width: 8px; height: 8px; }
*::-webkit-scrollbar-track { background: hsl(var(--scrollbar-track)); }
*::-webkit-scrollbar-thumb {
  background: hsl(var(--scrollbar-thumb));
  border-radius: 4px;
}
*::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--scrollbar-thumb-hover));
}
```

### Known Exceptions

Some elements cannot be fully themed due to browser/OS limitations:

| Element | Limitation | Mitigation |
|---------|------------|------------|
| **Native `<select>` dropdown** | OS-controlled appearance | Use shadcn/ui `Select` component instead |
| **Date/time inputs** | Browser-native picker | Consider custom date picker for full theming |
| **File input button** | Limited styling support | Use custom file upload UI |
| **Color picker** | Browser-native | Consider custom color picker |
| **Autocomplete dropdowns** | Browser-controlled | Disable or style where possible |

**Acceptable Contextual Colors:**

Some hardcoded colors are acceptable when they serve specific semantic purposes AND have proper dark mode variants:

```tsx
// ACCEPTABLE - Amber for "Beta" labels with dark mode variant
<span className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
  Beta
</span>

// ACCEPTABLE - Amber for "Required" field indicators
<span className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
  Required
</span>

// NOT ACCEPTABLE - Hardcoded without dark mode variant
<span className="bg-green-500 text-white">Status</span>
```

### Common Dark Theme Issues

```tsx
// ISSUE: White text on light background in light mode
// FIX: Use foreground token
<span className="text-foreground">Text</span>

// ISSUE: Hardcoded dark background
// FIX: Use background token
<div className="bg-background">Content</div>

// ISSUE: Border not visible in dark mode
// FIX: Use border token
<div className="border border-border">Content</div>
```

### Charts and Visualizations

Use the chart color tokens for data visualizations:

```tsx
// Chart colors
--chart-1: Blue
--chart-2: Green
--chart-3: Orange
--chart-4: Purple
--chart-5: Pink
```

---

## Checklist for New Features

Before submitting a PR for a new UI feature, verify:

### Colors & Theme
- [ ] No hardcoded colors - all use design tokens
- [ ] Tested in dark mode
- [ ] Status colors follow semantic mapping

### Buttons & Actions
- [ ] Primary action uses default variant
- [ ] Cancel/secondary uses outline variant
- [ ] Delete uses destructive variant
- [ ] Icon buttons use ghost variant with aria-label

### Messages & Errors
- [ ] Page errors displayed in Alert at top
- [ ] Form errors displayed above action buttons
- [ ] Field errors use FormMessage
- [ ] Empty states have appropriate messaging

### Domain Consistency
- [ ] Labels imported from domain-labels registry
- [ ] Icons match domain definitions
- [ ] FK references show icon + name + type badge

### Accessibility
- [ ] All icon buttons have aria-label
- [ ] Loading states have role="status"
- [ ] Form fields have associated labels
- [ ] Color is not the only indicator of state

---

## Migration Notes

### Immediate Actions Needed

1. **Create `src/contracts/domain-labels.ts`**
   - Consolidate all type labels from various components
   - Define domain icons

2. **Extend Alert component**
   - Add `success` variant
   - Add `warning` variant

3. **Update Badge component**
   - Use CSS variables instead of hardcoded colors
   - Add `warning` variant

4. **Implement Toast system**
   - Add sonner or similar toast library
   - Create useToast hook
   - Define toast variants

5. **Implement Header Notifications**
   - Create notification context/store
   - Connect bell icon to notification dropdown
   - Define notification types and persistence

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-01-10 | Added scrollbar styling guidelines, known exceptions, error handling patterns (Issue #55) |
| 1.0 | 2026-01-07 | Initial design system documentation |
