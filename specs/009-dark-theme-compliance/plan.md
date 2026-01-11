# Implementation Plan: Dark Theme Compliance

**Branch**: `009-dark-theme-compliance` | **Date**: 2026-01-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-dark-theme-compliance/spec.md`
**Related Issue**: [GitHub Issue #55](https://github.com/fabrice-guiot/photo-admin/issues/55)

## Summary

Audit and remediate all dark theme violations in the Photo Admin frontend to ensure a cohesive, accessible, and visually consistent user experience. Primary focus areas:

1. **Scrollbar styling** - Add cross-browser dark-themed scrollbars using CSS custom properties
2. **Design token compliance** - Replace any hardcoded colors with design tokens
3. **Accessibility contrast** - Ensure all text/UI meets WCAG 2.1 AA requirements
4. **Error state handling** - Implement styled error boundaries, 404 page, and consistent error messages
5. **Form control styling** - Verify all form elements use proper dark theme tokens

Technical approach: CSS-first solution using existing Tailwind/shadcn infrastructure with design tokens already defined in `globals.css`.

## Technical Context

**Language/Version**: TypeScript 5.x (Frontend), React 18.3.1
**Primary Dependencies**: Tailwind CSS 4.x, shadcn/ui components, Radix UI primitives, class-variance-authority (cva)
**Storage**: N/A (styling-only feature, no data persistence changes)
**Testing**: Vitest for unit tests, manual visual verification, Lighthouse/axe for accessibility audits
**Target Platform**: Modern browsers (Chrome, Firefox, Safari, Edge - latest 2 major versions)
**Project Type**: Web application (frontend-only changes for this feature)
**Performance Goals**: No performance regression; CSS changes should have negligible impact
**Constraints**: Must maintain WCAG 2.1 AA compliance (4.5:1 text contrast, 3:1 UI contrast)
**Scale/Scope**: ~30 component files to audit, ~10 pages to verify, global CSS changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Pre-Phase 0 Check**: ✅ Passed (2026-01-10)
**Post-Phase 1 Re-check**: ✅ Passed (2026-01-10) - No design changes that affect constitution compliance

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: N/A - This is a frontend-only feature, no CLI tools involved.
- [x] **Testing & Quality**: Visual testing via browser inspection + Lighthouse accessibility audits planned. Unit tests for new error boundary components.
- [x] **User-Centric Design**:
  - For analysis tools: N/A - Not an analysis tool
  - Are error messages clear and actionable? Yes - FR-008 through FR-011 require user-friendly messages
  - Is the implementation simple (YAGNI)? Yes - Using existing design token infrastructure, no new abstractions
  - Is structured logging included for observability? N/A - CSS styling, no logging needed
- [x] **Shared Infrastructure**: N/A - Frontend feature; does not interact with PhotoAdminConfig or CLI infrastructure.
- [x] **Simplicity**: Yes - Direct CSS modifications using existing design tokens. No new libraries or complex abstractions.
- [x] **Frontend UI Standards**: Applicable - All error states will follow the TopHeader KPI pattern where relevant.
- [x] **Global Unique Identifiers (GUIDs)**: N/A - No database entities or API changes in this feature.

**Violations/Exceptions**: None. This feature fully complies with all applicable constitution principles.

## Project Structure

### Documentation (this feature)

```text
specs/009-dark-theme-compliance/
├── plan.md              # This file
├── research.md          # Phase 0 output - scrollbar patterns, accessibility best practices
├── data-model.md        # Phase 1 output - N/A for this feature (no data model changes)
├── quickstart.md        # Phase 1 output - verification steps for testing dark theme
├── contracts/           # Phase 1 output - N/A for this feature (no API changes)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── globals.css                      # Global scrollbar styling, design token updates
│   ├── components/
│   │   ├── ui/
│   │   │   ├── alert.tsx                # Verify/update contrast for destructive variant
│   │   │   ├── badge.tsx                # Replace hardcoded colors (success, muted, info)
│   │   │   ├── button.tsx               # Verify focus states
│   │   │   ├── input.tsx                # Verify border/focus contrast
│   │   │   ├── select.tsx               # Verify dropdown styling
│   │   │   ├── textarea.tsx             # Verify styling consistency
│   │   │   └── form.tsx                 # Verify FormMessage contrast
│   │   ├── layout/
│   │   │   └── MainLayout.tsx           # Verify scrollable area styling
│   │   └── error/                       # NEW: Error handling components
│   │       ├── ErrorBoundary.tsx        # React error boundary
│   │       └── ErrorFallback.tsx        # Fallback UI for caught errors
│   ├── pages/
│   │   └── NotFoundPage.tsx             # NEW: 404 error page
│   └── App.tsx                          # Add error boundary wrapper, 404 route
├── docs/
│   └── design-system.md                 # Update with scrollbar guidelines, exceptions
└── tests/
    └── components/
        └── error/
            └── ErrorBoundary.test.tsx   # NEW: Error boundary tests
```

**Structure Decision**: Frontend-only web application changes. All modifications target the existing `frontend/` directory structure. New components added for error handling (ErrorBoundary, NotFoundPage) follow existing patterns in `components/` and `pages/` directories.

## Complexity Tracking

> No constitution violations. This feature uses simple, direct CSS modifications with no new abstractions.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | - | - |
