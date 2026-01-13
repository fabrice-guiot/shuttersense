# Research: Page Layout Cleanup

**Feature Branch**: `015-page-layout-cleanup`
**Created**: 2026-01-13

## Research Summary

This feature is a frontend-only UI cleanup that removes duplicate page titles and repositions action buttons. No backend changes required.

## Current Page Layout Analysis

### Pages Affected

| Page | Current Title Pattern | Action Buttons | Has Description |
|------|----------------------|----------------|-----------------|
| CollectionsPage | "Photo Collections" (text-3xl) | + New Collection | No |
| ConnectorsPage | "Remote Storage Connectors" (text-3xl) | + New Connector | No |
| AnalyticsPage | "Analytics" (text-3xl) | Refresh, Run Tool | No |
| EventsPage | "Events" (text-2xl) | + New Event | No |
| SettingsPage | "Settings" (text-3xl) with icon + description | None (tabs only) | Yes |
| DirectoryPage | "Directory" (text-3xl) with icon + description | None (tabs only) | Yes |
| PipelinesPage | No secondary title (uses PipelineList) | New, Import (in PipelineList) | No (beta banner only) |

### TopHeader Component (TopHeader.tsx)

- Located at: `frontend/src/components/layout/TopHeader.tsx`
- Displays page title in h1 (text-xl, font-semibold)
- Stats displayed in right section (hidden on mobile)
- Accepts `pageTitle`, `pageIcon`, and `stats` props
- Title set via route config in App.tsx

### Route Configuration (App.tsx)

- Routes defined with `pageTitle` and `pageIcon`
- MainLayout receives these and passes to TopHeader
- Current titles: "Dashboard", "Events", "Workflows", "Collections", "Assets", "Analytics", "Team", "Pipelines", "Directory", "Settings"

### Current Pattern (Double Title)

```tsx
// TopHeader (text-xl)
<h1 className="text-xl font-semibold text-foreground">{pageTitle}</h1>

// Page content (text-3xl)
<h1 className="text-3xl font-bold tracking-tight">Photo Collections</h1>
```

## Design Decisions

### Decision 1: Help Mechanism Component

**Decision**: Use shadcn/ui Tooltip component (Radix-based)

**Rationale**:
- Already available in the project (`frontend/src/components/ui/tooltip.tsx`)
- Consistent with existing design system
- Supports both hover (desktop) and click interactions
- Accessible by default (Radix primitives)

**Alternatives Considered**:
- Popover: More complex, better for interactive content (not needed here)
- Custom tooltip: Would duplicate existing functionality

### Decision 2: Help Content Storage

**Decision**: Store help content in route configuration (App.tsx)

**Rationale**:
- Help content is static and page-specific
- Already centralized page metadata (title, icon) in route config
- No backend storage needed
- Simple to maintain alongside route definitions

**Alternatives Considered**:
- Separate help content file: Adds complexity without benefit
- Backend API: Overkill for static help text
- Context provider: Unnecessary state management

### Decision 3: Action Button Positioning

**Decision**: Create a page-level action slot in TopHeader OR use new PageToolbar component

**Rationale**:
- TopHeader is the single title location now
- Action buttons should be near the title/page context
- Non-tabbed pages: Actions in a toolbar row below TopHeader
- Tabbed pages: Actions integrated with TabsList row

**Alternatives Considered**:
- Keep actions in page content: Still requires consistent placement pattern
- Move all actions to TopHeader: Overcrowds header, poor mobile UX

### Decision 4: Title Styling After Cleanup

**Decision**: Keep TopHeader title styling (text-xl, font-semibold)

**Rationale**:
- Consistent across all pages
- Appropriate size for header context
- Already tested for responsive behavior

**Alternatives Considered**:
- Increase to text-2xl: Might crowd header space
- Keep page content title: Defeats purpose of cleanup

## Implementation Approach

### Phase 1: Remove Secondary Titles

1. Remove `<h1>` elements from page content areas:
   - CollectionsPage (line 134)
   - ConnectorsPage (line 104)
   - AnalyticsPage (line 395)
   - EventsPage (line 285)
   - SettingsPage (line 68)

### Phase 2: Add Help Mechanism

1. Extend route config with optional `pageHelp` description
2. Add help icon to TopHeader (conditionally rendered)
3. Use Tooltip to display help content

### Phase 3: Reposition Action Buttons

1. **Non-tabbed pages** (Collections, Connectors):
   - Create action button row below TopHeader
   - Align buttons to right side

2. **Tabbed pages** (Analytics, Settings):
   - Integrate action buttons with TabsList row
   - Tabs left, actions right

3. **Calendar page** (Events):
   - Action button in calendar header area (existing EventCalendar component handles this well)

### Phase 4: Mobile Responsiveness

1. Test all pages at mobile breakpoints
2. Ensure action buttons remain accessible
3. Verify help tooltips work with tap interaction

## Technical Notes

### Existing Components to Modify

- `TopHeader.tsx`: Add optional help tooltip
- `MainLayout.tsx`: Pass help content to TopHeader
- `App.tsx`: Extend RouteConfig with `pageHelp`

### Pages to Modify

- `CollectionsPage.tsx`: Remove h1, reposition button
- `ConnectorsPage.tsx`: Remove h1, reposition button
- `AnalyticsPage.tsx`: Remove h1, integrate actions with tabs
- `EventsPage.tsx`: Remove h1 (button position may stay in calendar)
- `SettingsPage.tsx`: Remove h1 and description, add to help
- `DirectoryPage.tsx`: Remove h1 and description, add to help
- `PipelinesPage.tsx`: Minimal changes (no secondary title currently)

### New Components Needed

None required. Changes are to existing components only.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Mobile layout breaks | Low | Medium | Test at all breakpoints before merge |
| Tooltip accessibility issues | Low | Medium | Use Radix Tooltip (accessible by default) |
| Action buttons hard to find | Low | Low | Consistent placement across all pages |
| Help content not discovered | Medium | Low | Standard help icon (HelpCircle) is recognizable |

## Dependencies

- No backend changes
- No new npm packages
- Uses existing shadcn/ui components (Tooltip)

## Testing Strategy

1. Visual regression testing at multiple viewport widths
2. Keyboard navigation testing (Tab to help icon, Enter to activate)
3. Screen reader testing for help content
4. E2E tests for action button functionality (ensure buttons still work)
