# Implementation Plan: Mobile Calendar View

**Branch**: `016-mobile-calendar-view` | **Date**: 2026-01-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/016-mobile-calendar-view/spec.md`

## Summary

Implement a compact calendar view for mobile devices (viewport < 640px) that replaces full event cards with category icon badges showing event counts. Users tap on day numbers to reveal the full event list in the existing Day Detail popup. The implementation uses Tailwind CSS responsive classes and follows existing patterns from TopHeader and MainLayout. No backend changes required - this is a frontend-only feature.

## Technical Context

**Language/Version**: TypeScript 5.9.3 + React 18.3.1
**Primary Dependencies**: Tailwind CSS 4.x, shadcn/ui, Radix UI, Lucide React icons
**Storage**: N/A (frontend-only feature, uses existing event data from backend)
**Testing**: Vitest + @testing-library/react + MSW
**Target Platform**: Web browsers (responsive design for mobile/tablet/desktop)
**Project Type**: Web application (frontend only)
**Performance Goals**: 60fps scroll/interaction, <100ms layout switch
**Constraints**: Touch targets minimum 44x44 pixels, accessible (ARIA, keyboard nav)
**Scale/Scope**: Single page modification (EventsPage/EventCalendar), ~3 new components

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: N/A - This is a frontend-only feature, no CLI tools involved.
- [x] **Testing & Quality**: Tests planned using Vitest + React Testing Library. Coverage for new components (CategoryBadge, CompactCalendarCell) and viewport hook.
- [x] **User-Centric Design**:
  - N/A - Not an analysis tool, no HTML report generation.
  - Error states handled via existing loading/error patterns in EventCalendar.
  - Implementation is simple - uses existing Tailwind responsive patterns, minimal new code.
  - N/A - Frontend-only, no backend logging changes needed.
- [x] **Shared Infrastructure**: N/A - Frontend-only feature using existing component patterns.
- [x] **Simplicity**: Yes - uses pure CSS-based responsive design (Tailwind breakpoints), no complex state management or viewport detection hooks needed.
- [x] **Single Title Pattern**: N/A - No changes to page titles; EventsPage already follows this pattern.
- [x] **TopHeader KPI Pattern**: N/A - No changes to KPI display; existing stats behavior preserved.
- [x] **GUID Pattern**: N/A - No new entities, uses existing event GUIDs.

**Violations/Exceptions**: None - all principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/016-mobile-calendar-view/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 component design
├── quickstart.md        # Phase 1 implementation guide
├── contracts/           # Phase 1 component interfaces
│   └── components.ts    # TypeScript interfaces
├── checklists/          # Quality validation
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── components/
│   │   └── events/
│   │       ├── EventCalendar.tsx      # Modified: add responsive compact mode
│   │       ├── EventCard.tsx          # Existing: already has compact mode
│   │       ├── CategoryBadge.tsx      # New: category icon with count badge
│   │       └── CompactCalendarCell.tsx # New: mobile day cell with badges
│   ├── hooks/
│   │   └── useMediaQuery.ts           # New: responsive breakpoint hook
│   └── pages/
│       └── EventsPage.tsx             # Minor: ensure dialogs work on mobile
└── tests/
    ├── components/
    │   └── events/
    │       ├── CategoryBadge.test.tsx     # New: badge rendering tests
    │       ├── CompactCalendarCell.test.tsx # New: cell composition tests
    │       └── EventCalendar.test.tsx     # Extended: responsive behavior tests
    └── hooks/
        └── useMediaQuery.test.ts      # New: hook behavior tests
```

**Structure Decision**: Frontend-only modification using existing web application structure. New components follow established patterns in `frontend/src/components/events/`. New hook follows existing hook patterns in `frontend/src/hooks/`.

## Complexity Tracking

> No violations - table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none)    | -          | -                                   |
