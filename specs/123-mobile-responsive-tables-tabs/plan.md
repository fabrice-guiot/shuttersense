# Implementation Plan: Mobile Responsive Tables and Tabs

**Branch**: `123-mobile-responsive-tables-tabs` | **Date**: 2026-01-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/123-mobile-responsive-tables-tabs/spec.md`

## Summary

Create two reusable frontend components — `<ResponsiveTable>` and `<ResponsiveTabsList>` — that transform their rendering below the `md` (768px) breakpoint. Tables switch from standard rows to structured cards with a `cardRole` column system. Tab strips switch from inline triggers to a `<Select>` dropdown. Migrate all 11 existing tables and 6 tab instances across the application. Desktop rendering remains unchanged.

## Technical Context

**Language/Version**: TypeScript 5.9.3, React 18.3.1
**Primary Dependencies**: shadcn/ui (Table, Tabs, Select, Badge), Tailwind CSS 4.x, Radix UI primitives, class-variance-authority, Lucide React icons
**Storage**: N/A (frontend-only, no backend changes)
**Testing**: Vitest + React Testing Library (frontend unit tests)
**Target Platform**: Web browser (mobile and desktop viewports)
**Project Type**: Web application (frontend-only changes)
**Performance Goals**: No measurable performance regression; CSS toggling only (no JS viewport detection)
**Constraints**: Both DOM views rendered simultaneously (hidden via CSS); acceptable for paginated tables up to 50 rows
**Scale/Scope**: 11 table migrations, 6 tab migrations, 2 new UI components, 1 design system documentation update

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Agent-Only Tool Execution**: N/A — this feature is frontend-only UI components, not analysis tool execution.
- [x] **Testing & Quality**: Unit tests planned for both new components using Vitest + React Testing Library. Integration testing via manual verification at target viewports (375px, 390px, 412px).
- [x] **User-Centric Design**:
  - For analysis tools: N/A — no analysis tool changes.
  - Are error messages clear and actionable? N/A — no new error states introduced.
  - Is the implementation simple (YAGNI)? Yes — two focused components with minimal API surface. No unnecessary abstractions.
  - Is structured logging included? N/A — frontend UI components do not require logging.
- [x] **Shared Infrastructure**: N/A — no shared Python config or backend infrastructure involved. Frontend components follow existing shadcn/ui patterns.
- [x] **Simplicity**: Yes — CSS class toggling (`hidden md:block` / `md:hidden`) is the simplest possible approach. No JavaScript viewport detection, no conditional rendering, no resize observers.
- [x] **GUIDs**: N/A — no new entities or API endpoints. Existing GUID usage in table data is preserved.
- [x] **Multi-Tenancy**: N/A — no backend changes. Frontend authentication/authorization unchanged.
- [x] **Agent-Only Execution**: N/A — no job processing changes.
- [x] **TopHeader KPI Pattern**: N/A — no changes to header stats. Existing KPI implementations preserved.
- [x] **Single Title Pattern**: Preserved — no new page titles or h1 elements added. Tab content continues without h2 titles.

**Violations/Exceptions**: None. All constitution principles are satisfied or not applicable.

## Project Structure

### Documentation (this feature)

```text
specs/123-mobile-responsive-tables-tabs/
├── plan.md              # This file
├── research.md          # Phase 0 output - technology decisions
├── data-model.md        # Phase 1 output - TypeScript interfaces
├── quickstart.md        # Phase 1 output - development guide
├── contracts/           # Phase 1 output - component API contracts
│   └── component-api.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── components/
│   │   ├── ui/
│   │   │   ├── responsive-table.tsx          # NEW - ResponsiveTable component
│   │   │   └── responsive-tabs-list.tsx      # NEW - ResponsiveTabsList component
│   │   ├── collections/
│   │   │   └── CollectionList.tsx            # MODIFIED - migrate table + tabs
│   │   ├── connectors/
│   │   │   └── ConnectorList.tsx             # MODIFIED - migrate table
│   │   ├── directory/
│   │   │   ├── LocationsTab.tsx              # MODIFIED - migrate table
│   │   │   ├── OrganizersTab.tsx             # MODIFIED - migrate table
│   │   │   └── PerformersTab.tsx             # MODIFIED - migrate table
│   │   ├── results/
│   │   │   └── ResultsTable.tsx              # MODIFIED - migrate table + pagination
│   │   └── settings/
│   │       ├── CategoriesTab.tsx             # MODIFIED - migrate table
│   │       ├── TokensTab.tsx                 # MODIFIED - migrate table
│   │       ├── TeamsTab.tsx                  # MODIFIED - migrate table
│   │       └── ReleaseManifestsTab.tsx       # MODIFIED - migrate table
│   └── pages/
│       ├── AgentsPage.tsx                    # MODIFIED - migrate table
│       ├── SettingsPage.tsx                  # MODIFIED - migrate tabs
│       ├── AnalyticsPage.tsx                 # MODIFIED - migrate tabs (main + nested)
│       └── DirectoryPage.tsx                 # MODIFIED - migrate tabs
├── docs/
│   └── design-system.md                      # MODIFIED - add responsive sections
└── tests/                                     # Tests for new components
```

**Structure Decision**: Frontend-only changes. Two new UI components in `frontend/src/components/ui/`, modifications to 11 table components and 4 page/component files for tab migrations, plus design system documentation update.

## Complexity Tracking

No violations. All approaches use the simplest available technique (CSS class toggling, existing shadcn/ui primitives, declarative card role system).
