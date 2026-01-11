# Implementation Plan: User Timezone Display

**Branch**: `010-user-timezone-display` | **Date**: 2026-01-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-user-timezone-display/spec.md`

## Summary

Create a centralized date formatting utility for the React frontend that displays all timestamps in the user's local timezone using native browser Intl APIs. The utility will support both absolute formatting (e.g., "Jan 7, 2026, 3:45 PM") and relative time display (e.g., "2 hours ago"). This is a frontend-only change with no backend modifications required.

## Technical Context

**Language/Version**: TypeScript 5.9.3
**Primary Dependencies**: React 18.3.1, Vite 6.0.5, native browser Intl APIs (no external date libraries)
**Storage**: N/A (frontend-only feature, backend continues storing UTC timestamps)
**Testing**: Vitest 4.0.16, @testing-library/react 16.1.0, jsdom 25.0.1
**Target Platform**: Modern browsers (Chrome 71+, Firefox 65+, Safari 14+, Edge 79+)
**Project Type**: Web application (frontend-only changes)
**Performance Goals**: No visible UI lag from date formatting operations
**Constraints**: No external date libraries, must use native Intl APIs
**Scale/Scope**: 8 components currently display dates, all must be migrated to centralized utility

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: N/A - This feature is frontend-only, not a CLI tool.
- [x] **Testing & Quality**: Tests are planned with Vitest. Target is 90%+ coverage for the date formatting utility per NFR-004.
- [x] **User-Centric Design**:
  - For analysis tools: N/A - not an analysis tool
  - Are error messages clear and actionable? Yes - graceful fallback for null/invalid dates with "Never" or fallback text
  - Is the implementation simple (YAGNI)? Yes - using native Intl APIs, no external libraries
  - Is structured logging included for observability? N/A - frontend display utility, no logging needed
- [x] **Shared Infrastructure**: N/A - frontend utility, not using PhotoAdminConfig
- [x] **Simplicity**: Yes - minimal utility functions, native browser APIs, no over-abstraction

**Violations/Exceptions**: None - all applicable constitution principles are satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/010-user-timezone-display/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal - no data model changes)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (empty - no API changes)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── utils/
│   │   ├── dateFormat.ts         # NEW: Centralized date formatting utility
│   │   └── index.ts              # MODIFY: Export date formatting functions
│   └── components/
│       ├── connectors/
│       │   └── ConnectorList.tsx # MODIFY: Replace inline formatDate()
│       ├── results/
│       │   ├── ResultsTable.tsx         # MODIFY: Replace inline formatDate()
│       │   └── ResultDetailPanel.tsx    # MODIFY: Replace inline formatDate()
│       ├── pipelines/
│       │   └── PipelineCard.tsx         # MODIFY: Replace inline formatDate()
│       ├── tools/
│       │   └── JobProgressCard.tsx      # MODIFY: Replace inline formatDate()
│       └── trends/
│           ├── TrendChart.tsx                # MODIFY: Replace inline formatting
│           ├── TrendSummaryCard.tsx          # MODIFY: Replace inline formatting
│           └── PipelineValidationTrend.tsx   # MODIFY: Replace inline formatting
└── tests/
    └── utils/
        └── dateFormat.test.ts    # NEW: Comprehensive unit tests
```

**Structure Decision**: Frontend-only changes in the existing web application structure. New utility file in `frontend/src/utils/` following existing patterns (like `guid.ts`).

## Complexity Tracking

No complexity tracking needed - all constitution principles satisfied without exceptions.
