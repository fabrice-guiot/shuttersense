# Implementation Plan: Page Layout Cleanup

**Branch**: `015-page-layout-cleanup` | **Date**: 2026-01-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/015-page-layout-cleanup/spec.md`

## Summary

Remove duplicate page titles across all frontend pages, consolidating to a single title in the TopHeader. Add an optional help tooltip mechanism for pages with descriptive context. Reposition action buttons consistently across all page types (tabbed and non-tabbed).

**Technical Approach**: Extend TopHeader with optional `pageHelp` prop, update route configuration to include help descriptions, modify page components to remove redundant h1 elements and reposition action buttons.

## Technical Context

**Language/Version**: TypeScript 5.9.3 (Frontend)
**Primary Dependencies**: React 18.3.1, shadcn/ui, Tailwind CSS 4.x, Radix UI Tooltip
**Storage**: N/A (frontend-only, no data persistence changes)
**Testing**: Vitest (frontend unit tests), Playwright (E2E visual testing)
**Target Platform**: Web browsers (desktop/tablet/mobile)
**Project Type**: Web application (frontend-only changes)
**Performance Goals**: No measurable impact (UI restructure only)
**Constraints**: Maintain accessibility (WCAG 2.1 AA), maintain responsive behavior
**Scale/Scope**: ~10 pages affected, ~6 components modified

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: N/A - This is a frontend-only feature, no CLI tools involved.
- [x] **Testing & Quality**: Visual regression tests planned. Component unit tests for TopHeader changes.
- [x] **User-Centric Design**:
  - For analysis tools: N/A - Not an analysis tool.
  - Are error messages clear and actionable? N/A - No new error states.
  - Is the implementation simple (YAGNI)? Yes - Using existing Tooltip component, minimal new code.
  - Is structured logging included for observability? N/A - Frontend UI change only.
- [x] **Shared Infrastructure**: N/A - No backend changes, no config schema changes.
- [x] **Simplicity**: Yes - Leveraging existing shadcn/ui Tooltip, extending existing route config pattern.
- [x] **Frontend UI Standards (TopHeader KPI Pattern)**: Existing pattern preserved. Stats display unchanged.

**Violations/Exceptions**: None. This feature complies with all applicable principles.

## Project Structure

### Documentation (this feature)

```text
specs/015-page-layout-cleanup/
├── plan.md              # This file
├── research.md          # Current page analysis, design decisions
├── data-model.md        # Interface changes (TypeScript)
├── quickstart.md        # Implementation guide
├── contracts/           # No API changes (README only)
│   └── README.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── TopHeader.tsx      # Add pageHelp prop and tooltip
│   │   │   └── MainLayout.tsx     # Pass pageHelp to TopHeader
│   │   └── ui/
│   │       └── tooltip.tsx        # Existing (no changes)
│   ├── pages/
│   │   ├── CollectionsPage.tsx    # Remove h1, reposition button
│   │   ├── ConnectorsPage.tsx     # Remove h1, reposition button
│   │   ├── AnalyticsPage.tsx      # Remove h1, integrate actions with tabs
│   │   ├── EventsPage.tsx         # Remove h1
│   │   ├── SettingsPage.tsx       # Remove h1 + description
│   │   ├── DirectoryPage.tsx      # Remove h1 + description
│   │   └── PipelinesPage.tsx      # Minor adjustments if needed
│   └── App.tsx                    # Extend RouteConfig with pageHelp
└── tests/
    └── components/
        └── TopHeader.test.tsx     # New tests for help tooltip
```

**Structure Decision**: Frontend-only changes. Modifications confined to `frontend/src/` directory. No backend changes required.

## Complexity Tracking

> No violations. Feature is simple UI restructure using existing patterns.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | - | - |

## Implementation Phases

### Phase 1: TopHeader Help Mechanism

**Goal**: Add optional help tooltip to TopHeader

**Files**:
- `frontend/src/components/layout/TopHeader.tsx`
- `frontend/src/components/layout/MainLayout.tsx`
- `frontend/src/App.tsx`

**Changes**:
1. Add `pageHelp?: string` to `TopHeaderProps` interface
2. Add `pageHelp?: string` to `RouteConfig` interface in App.tsx
3. Add `pageHelp` to MainLayout props and pass to TopHeader
4. Render HelpCircle icon with Tooltip when `pageHelp` is provided
5. Add help descriptions to routes that need them (Settings primarily)

### Phase 2: Remove Secondary Titles

**Goal**: Remove duplicate h1 elements from page content areas

**Files**:
- `frontend/src/pages/CollectionsPage.tsx`
- `frontend/src/pages/ConnectorsPage.tsx`
- `frontend/src/pages/AnalyticsPage.tsx`
- `frontend/src/pages/EventsPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`

**Changes**:
1. Remove `<h1>` elements from each page
2. Remove associated wrapper divs if they become empty
3. Preserve action buttons (repositioned in Phase 3)

### Phase 3: Reposition Action Buttons

**Goal**: Create consistent action button placement across pages

**Pattern A - Non-tabbed pages** (Collections, Connectors):
- Action buttons in a row immediately below TopHeader
- Right-aligned, flex container

**Pattern B - Tabbed pages** (Analytics, Settings):
- Action buttons integrated with TabsList
- TabsList left, actions right, same row

**Pattern C - Calendar page** (Events):
- Action button remains in calendar component header
- No change needed (already good position)

### Phase 4: Testing & Verification

**Goal**: Ensure all pages work correctly at all viewport sizes

**Tests**:
1. Unit tests for TopHeader help tooltip rendering
2. Visual regression tests for each page at 375px, 768px, 1024px
3. Accessibility testing (keyboard navigation to help icon)

## Dependencies

- shadcn/ui Tooltip component (already installed)
- Lucide icons (HelpCircle - already available)
- No new npm packages required

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Mobile layout breaks | Low | Medium | Test at breakpoints before merge |
| Action buttons harder to discover | Low | Low | Consistent placement, maintain existing styling |
| Help icon not noticed | Medium | Low | Use standard HelpCircle icon, familiar pattern |

## Success Metrics

- [ ] Zero duplicate titles on any page
- [ ] All action buttons remain accessible
- [ ] Help tooltip displays on Settings page
- [ ] No visual regression at mobile/tablet/desktop breakpoints
- [ ] Keyboard accessible help tooltip (Tab + Enter)
