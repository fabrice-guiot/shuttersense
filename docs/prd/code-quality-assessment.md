# PRD: Code Quality Assessment & Improvement Roadmap

**Issue**: TBD
**Status**: Draft
**Created**: 2026-02-14
**Last Updated**: 2026-02-14
**Related Documents**:
- [Design System](../../frontend/docs/design-system.md)
- [CLAUDE.md](../../CLAUDE.md)

---

## Executive Summary

A comprehensive code quality assessment was performed across the entire ShutterSense.ai repository (~262K lines of code, 784 source files). The codebase is **production-grade** with an overall rating of **A-** (Very Good). The backend is the strongest component (A), with excellent architecture, security, and testing. The agent scores similarly well (A-) with strong CLI design and thorough documentation. The frontend (B+) is solid architecturally but has the widest improvement gap, primarily in test coverage and component size.

This PRD documents the findings and defines a prioritized improvement roadmap organized into four phases. The focus areas are: increasing frontend test coverage, decomposing oversized files, tightening TypeScript strictness, and reducing minor code smells across the stack.

### Key Design Decisions

1. **Phased approach over big-bang refactoring**: Improvements are organized into four phases of increasing scope. Each phase is independently shippable and delivers measurable value without disrupting feature development.
2. **Frontend-first prioritization**: The frontend has the largest quality gap relative to the backend and agent. Investing in frontend testing and component decomposition yields the highest marginal return.
3. **No architectural changes**: The existing layered architecture (API/Service/Model), multi-tenancy patterns, GUID system, and audit trails are all well-implemented. This roadmap focuses on incremental quality improvements, not structural redesign.
4. **Measurable checkpoints**: Each phase has concrete success criteria (e.g., "frontend test file coverage reaches 30%") to avoid subjective assessments of "done."

---

## Background

### Current State

**Codebase Scale:**

| Component | Files | Lines of Code | % of Total |
|-----------|-------|---------------|------------|
| Backend (Python/FastAPI) | 345 | 136,477 | 52.2% |
| Frontend (TypeScript/React) | 342 | 87,635 | 33.5% |
| Agent (Python/Click) | 92 | 34,035 | 13.0% |
| Utils (Python) | 5 | 3,443 | 1.3% |
| **Total** | **784** | **261,590** | **100%** |

**Test Coverage:**

| Component | Test Files | Test Lines | Test-to-Code Ratio |
|-----------|-----------|------------|---------------------|
| Backend | 132 | 64,029 | 47% |
| Agent | 43 | 15,964 | 47% |
| Frontend | 14 | 24,601 | 28% (but only 9% file coverage) |
| **Total** | **182+** | **~104,594** | **40%** |

**Architecture Compliance:**
All documented architectural principles from CLAUDE.md are properly implemented:
- Issue #42 (GUID-based Identifiers) — fully implemented
- Issue #73 (Multi-Tenancy & Authentication) — fully implemented
- Issue #90 (Agent-Only Execution) — fully implemented
- Issue #108 (Agent-Only Tool Execution) — fully implemented
- Issue #120 (Audit Trail & User Attribution) — fully implemented

### Problem Statement

While the codebase is production-ready, several quality gaps create maintainability and reliability risks:

- **Frontend test coverage is critically low**: Only 14 of 157 TypeScript files (~9%) have tests. Hooks containing critical business logic (debouncing, API error handling) are completely untested.
- **Oversized files increase cognitive load**: 5 backend services exceed 1,800 lines; 3 frontend pages exceed 800 lines. Large files slow code reviews, increase merge conflict frequency, and make onboarding harder.
- **Inconsistent error handling in the frontend**: Some hooks use `setError()`, others use toast notifications, and some detect error types via fragile string matching.
- **Code duplication across CLI commands**: The same config-loading boilerplate is repeated 5+ times across agent CLI commands.
- **TypeScript strictness is incomplete**: `strict: false` in `tsconfig.json` with selective flags. Some `any` types remain in page-level handlers.

### Strategic Context

Addressing these gaps now is important because:
- **Team growth**: As more contributors join, lower-quality areas become bottlenecks for onboarding and code review.
- **Feature velocity**: Large, untested files slow iteration — changes require manual verification and create regression risk.
- **Confidence in refactoring**: Without test coverage, refactoring frontend hooks or services carries high regression risk.
- **Technical debt compounds**: Small issues left unaddressed grow into larger problems as the codebase evolves.

---

## Goals

### Primary Goals

1. **Increase frontend test coverage** from 9% file coverage to 40%+ file coverage, prioritizing hooks and services.
2. **Decompose oversized files** so no single source file exceeds 800 lines (backend services) or 600 lines (frontend components/pages).
3. **Establish consistent error handling patterns** across the frontend with structured error codes instead of string matching.
4. **Eliminate code duplication** in agent CLI commands via shared utility functions.

### Secondary Goals

5. Enable `strict: true` in TypeScript configuration incrementally.
6. Remove all production `console.log` statements from frontend code.
7. Introduce `@pytest.mark.parametrize` for repetitive test cases across the test suite.
8. Clean up the backup file (`utils/pipeline_processor.py.backup`) from incomplete refactoring.

### Non-Goals (v1)

- **Rewriting the architecture**: The existing API/Service/Model layering is sound and does not need redesign.
- **Migrating state management**: The Context-based approach is appropriate for the current scale. Redux or Zustand migration is not warranted.
- **Adding end-to-end (E2E) tests**: While valuable, E2E testing (Playwright/Cypress) is a separate initiative.
- **Performance optimization**: No performance issues have been identified. This roadmap focuses on maintainability and reliability.

---

## Detailed Findings

### Component Assessment: Backend (Rating: A)

**Strengths:**
- Excellent custom exception hierarchy (`NotFoundError`, `ConflictError`, `ValidationError`) with proper HTTP status code mapping in every API route.
- Comprehensive Pydantic v2 schemas with field validators (hex color format, whitespace trimming, length constraints).
- Smart mixin architecture (`GuidMixin`, `AuditMixin`) eliminates boilerplate across 30+ models.
- SQL injection prevention via exclusive ORM usage — no raw SQL anywhere.
- Multi-tenant isolation with `TenantContext` consistently applied across all 40+ services.
- Security headers (CSP, X-Frame-Options, X-Content-Type-Options) applied in `main.py`.
- Rate limiting on failed authentication attempts with progressive blocking thresholds.
- 132 test files with factory-pattern fixtures, in-memory SQLite, and dedicated tenant isolation tests.

**Issues Found:**

| ID | Issue | Severity | Files Affected |
|----|-------|----------|----------------|
| BE-1 | Services exceeding 2,000 lines | Medium | `event_service.py` (2,435), `job_coordinator_service.py` (2,459), `trend_service.py` (1,822) |
| BE-2 | Duplicate query logic in bound/unbound job discovery | Low | `job_coordinator_service.py` (lines 206-326) |
| BE-3 | Deep query nesting in job status filtering | Low | `job_coordinator_service.py` (lines 268-284) |
| BE-4 | Three-state Boolean column (`is_accessible`: True/False/None) | Low | `collection.py` (line 164) |

### Component Assessment: Frontend (Rating: B+)

**Strengths:**
- Centralized API contracts in `/contracts/api/` (22 files) with comprehensive JSDoc.
- Consistent use of `react-hook-form` + Zod validation across all forms.
- Clean Context-based state management (`AuthContext`, `HeaderStatsContext`) without Redux overhead.
- Domain-driven component organization (143 components across 12+ domain folders).
- Proper use of Radix UI primitives for accessibility.
- Error boundary implementation with optional custom fallback.

**Issues Found:**

| ID | Issue | Severity | Files Affected |
|----|-------|----------|----------------|
| FE-1 | Critically low test coverage (9% file coverage) | High | All hooks/, services/, most pages/ |
| FE-2 | Oversized page components | High | `PipelineEditorPage.tsx` (1,278), `EventsPage.tsx` (1,083), `AnalyticsPage.tsx` (794) |
| FE-3 | `console.log` statements in production code | Medium | `CollectionForm.tsx` (lines 208, 214-217), `api.ts` (lines 72-92) |
| FE-4 | `any` types in page handlers | Medium | `CollectionsPage.tsx` (line 114) |
| FE-5 | Error detection via string matching | Medium | `useCollections.ts` (lines 161-166) |
| FE-6 | Duplicate `BetaChip` component definition | Low | `CollectionList.tsx` (line 35), `CollectionForm.tsx` (line 48) |
| FE-7 | 17+ `useState` hooks in single component | Medium | `AnalyticsPage.tsx` (lines 61-100) |
| FE-8 | `strict: false` in TypeScript config | Medium | `tsconfig.json` |

### Component Assessment: Agent (Rating: A-)

**Strengths:**
- Comprehensive docstrings with Args/Returns/Raises on virtually all public methods.
- Full type hints across analysis modules (100% coverage in `photostats_analyzer.py`, `photo_pairing_analyzer.py`, `pipeline_analyzer.py`).
- Well-designed custom exception hierarchy (`ApiError`, `ConnectionError`, `RegistrationError`, `AuthenticationError`, `AgentRevokedError`).
- Secure configuration management with `0o600` file permissions and `0o700` directory permissions.
- Clean async/await patterns with proper context manager cleanup.
- 43 test files with factory-pattern fixtures and proper async test support.

**Issues Found:**

| ID | Issue | Severity | Files Affected |
|----|-------|----------|----------------|
| AG-1 | Config loading boilerplate repeated 5+ times | Medium | `run.py`, `collection.py` (4x), `sync_results.py` |
| AG-2 | `compare_inventory()` function is 481 lines | Medium | `debug.py` (line 580) |
| AG-3 | Broad `except Exception` catches | Low | `run.py` (line 84), `collection.py` (line 238) |
| AG-4 | Hardcoded chunked upload threshold (`1 * 1024 * 1024`) | Low | `api_client.py` (lines 925, 1026) |
| AG-5 | Magic column widths in table output | Low | `collection.py` (line 445) |

### Component Assessment: Testing (Rating: A-)

**Strengths:**
- 182+ test files totaling ~104K lines of test code (40% of codebase).
- Consistent AAA (Arrange-Act-Assert) pattern across all tests.
- Excellent fixture hierarchy with factory patterns for flexible test data.
- Dedicated tenant isolation tests with separate authenticated clients.
- In-memory SQLite with FK constraints enabled for fast, reliable tests.
- Proper async test support via `pytest-asyncio` with auto mode.

**Issues Found:**

| ID | Issue | Severity | Files Affected |
|----|-------|----------|----------------|
| TS-1 | Frontend test coverage critically low (9%) | High | Frontend hooks, services, pages |
| TS-2 | Limited use of `@pytest.mark.parametrize` | Low | Across agent and backend tests |
| TS-3 | Some tests use implicit assertion messages | Low | Various test files |
| TS-4 | `@pytest.mark.integration` not consistently applied | Low | Backend integration tests |

---

## Requirements

### Functional Requirements

**FR-100: Frontend Test Coverage Expansion**
- FR-100.1: All custom hooks in `frontend/src/hooks/` MUST have test files covering primary flows and error paths.
- FR-100.2: All service files in `frontend/src/services/` MUST have test files covering API call success and failure scenarios.
- FR-100.3: All page components in `frontend/src/pages/` SHOULD have at least smoke tests verifying rendering without errors.
- FR-100.4: Frontend test file coverage MUST reach 40% (minimum 63 of 157 files).

**FR-200: File Size Reduction**
- FR-200.1: No backend service file SHALL exceed 800 lines. Files exceeding this limit MUST be decomposed into focused sub-modules.
- FR-200.2: No frontend page component SHALL exceed 600 lines. Pages exceeding this limit MUST extract sub-components (e.g., tab panels, form sections).
- FR-200.3: No agent CLI command function SHALL exceed 300 lines. Functions exceeding this limit MUST extract step-handler helper functions.

**FR-300: Error Handling Standardization**
- FR-300.1: Frontend error detection MUST NOT rely on string matching against error messages. Structured error codes or discriminated unions MUST be used instead.
- FR-300.2: A centralized `ErrorCode` enum or constant map MUST be created for all API error types used in the frontend.
- FR-300.3: Frontend hooks MUST use a consistent pattern for error reporting (either `setError()` or toast notifications, not both for the same error type).

**FR-400: Code Duplication Elimination**
- FR-400.1: Agent CLI config-loading boilerplate MUST be extracted to a shared utility function (e.g., `ensure_agent_config() -> AgentConfig`).
- FR-400.2: Duplicate frontend components (e.g., `BetaChip`) MUST be extracted to shared component files.

### Non-Functional Requirements

**NFR-100: TypeScript Strictness**
- NFR-100.1: `tsconfig.json` SHOULD enable `strict: true` or at minimum enable `strictNullChecks: true` and `noImplicitAny: true`.
- NFR-100.2: Zero `any` types SHALL remain in page-level handlers after completion.

**NFR-200: Production Hygiene**
- NFR-200.1: No `console.log` or `console.warn` statements SHALL exist in production code without a `import.meta.env.DEV` guard.
- NFR-200.2: Backup files (e.g., `pipeline_processor.py.backup`) MUST be removed from the repository.

**NFR-300: Test Infrastructure**
- NFR-300.1: Backend tests SHOULD use `@pytest.mark.parametrize` for cases testing multiple inputs against the same logic.
- NFR-300.2: `@pytest.mark.integration` SHOULD be consistently applied to all backend integration tests.

---

## Implementation Plan

### Phase 1: Frontend Test Coverage (Priority: HIGH)

The highest-impact improvement. Frontend hooks contain critical business logic (API error handling, search debouncing, optimistic updates) that is currently untested.

**Tasks:**

1. **Add tests for all custom hooks** (`frontend/src/hooks/`)
   - Priority targets: `useCollections.ts`, `useTools.ts`, `useEvents.ts`, `usePipelines.ts`
   - Cover: primary CRUD flows, error handling, debounce behavior, state transitions
   - Use `@testing-library/react` with `renderHook` utility

2. **Add tests for all service files** (`frontend/src/services/`)
   - Priority targets: `api.ts` (interceptors), `collections.ts`, `events.ts`
   - Cover: successful API calls, error transformation, auth redirect on 401
   - Use MSW (Mock Service Worker) for API mocking

3. **Add smoke tests for page components** (`frontend/src/pages/`)
   - Verify each page renders without errors
   - Verify loading states and error states display correctly
   - Priority targets: `CollectionsPage.tsx`, `EventsPage.tsx`, `AnalyticsPage.tsx`

**Checkpoint:** Frontend test file coverage reaches 40% (63+ test files). All hooks and services have test coverage.

---

### Phase 2: File Decomposition (Priority: HIGH)

Large files increase cognitive load, slow code reviews, and increase merge conflict frequency.

**Tasks:**

1. **Decompose oversized frontend pages**
   - `PipelineEditorPage.tsx` (1,278 lines) → Extract `<PipelineCanvas>`, `<StepConfigPanel>`, `<PipelineToolbar>` sub-components
   - `EventsPage.tsx` (1,083 lines) → Extract `<EventListTab>`, `<EventCalendarTab>` sub-components
   - `AnalyticsPage.tsx` (794 lines) → Extract `<TrendsTab>`, `<ReportsTab>`, `<RunsTab>` sub-components; consolidate 17+ `useState` hooks into a `useAnalyticsState` reducer

2. **Decompose oversized backend services**
   - `job_coordinator_service.py` (2,459 lines) → Extract `JobClaimService`, `JobCompletionService`, `JobProgressService`
   - `event_service.py` (2,435 lines) → Extract event query building, event validation, and event series logic into focused modules
   - `trend_service.py` (1,822 lines) → Extract aggregation query builders into a helper module

3. **Decompose oversized agent functions**
   - `debug.py: compare_inventory()` (481 lines) → Extract into 3-4 focused comparison functions
   - `run.py: run()` (235 lines) → Extract `_run_online()` and `_run_offline()` helpers

**Checkpoint:** No source file exceeds 800 lines (backend) or 600 lines (frontend). No single function exceeds 300 lines.

---

### Phase 3: Error Handling & Code Hygiene (Priority: MEDIUM)

Standardize error patterns and remove production noise.

**Tasks:**

1. **Create frontend error code system**
   - Define `ErrorCode` constant map in `frontend/src/contracts/error-codes.ts`
   - Backend API responses SHOULD include an `error_code` field alongside `detail` messages
   - Replace all string-matching error detection in hooks with error code checks

2. **Standardize frontend error reporting**
   - Document when to use `setError()` (persistent page-level errors) vs. toast (transient notifications)
   - Update all hooks to follow the documented pattern consistently

3. **Remove production console statements**
   - Wrap all `console.log` / `console.warn` calls in `if (import.meta.env.DEV)` guards
   - Consider introducing a lightweight logger utility (`frontend/src/utils/logger.ts`) for structured dev logging

4. **Extract shared agent CLI utilities**
   - Create `agent/cli/utils.py` with `ensure_agent_config()` function
   - Replace 5+ instances of config-loading boilerplate

5. **Clean up repository**
   - Remove `utils/pipeline_processor.py.backup`
   - Extract duplicate `BetaChip` to `frontend/src/components/ui/beta-chip.tsx`

**Checkpoint:** Zero string-matching error detection in frontend hooks. Zero unguarded `console.log` in production code. Agent CLI has no config-loading duplication.

---

### Phase 4: TypeScript Strictness & Test Polish (Priority: LOW)

Incremental strictness improvements and test infrastructure refinements.

**Tasks:**

1. **Enable incremental TypeScript strictness**
   - Enable `strictNullChecks: true` first; fix all resulting errors
   - Enable `noImplicitAny: true`; fix remaining `any` types
   - Target: full `strict: true` if feasible without excessive churn

2. **Introduce `@pytest.mark.parametrize`**
   - Identify test methods with repeated similar logic (e.g., testing multiple input formats)
   - Convert to parametrized tests for conciseness and coverage expansion
   - Priority: `test_photostats_analyzer.py`, `test_category_service.py`

3. **Apply consistent test markers**
   - Ensure all `backend/tests/integration/` tests have `@pytest.mark.integration`
   - Ensure all slow tests have `@pytest.mark.slow`
   - Update CI to allow running unit-only or integration-only test suites

4. **Add explicit assertion messages to critical tests**
   - Focus on integration tests where failure context helps debugging
   - Use `assert condition, "descriptive message"` pattern

**Checkpoint:** `strict: true` enabled in `tsconfig.json` with zero `any` types. All integration tests consistently marked. Parametrized tests used where 3+ similar cases exist.

---

## Risks and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| File decomposition introduces regressions | High | Medium | Run full test suite after each decomposition. Decompose one file at a time with dedicated review. |
| TypeScript strict mode causes excessive churn | Medium | Medium | Enable flags incrementally (one at a time). Use `// @ts-expect-error` sparingly for known issues. |
| Frontend test writing slows feature velocity | Medium | Low | Tests are an investment. Prioritize hooks/services that change frequently. Timebox Phase 1 to avoid scope creep. |
| Error code system requires backend API changes | Low | Medium | Backend changes are optional. Frontend can map existing error messages to codes as an interim step. |

---

## Success Metrics

| Metric | Current | Target | Phase |
|--------|---------|--------|-------|
| Frontend test file coverage | 9% (14/157) | 40% (63/157) | Phase 1 |
| Max backend service file size | 2,459 lines | 800 lines | Phase 2 |
| Max frontend page file size | 1,278 lines | 600 lines | Phase 2 |
| Unguarded `console.log` in production | 5+ instances | 0 | Phase 3 |
| String-matching error detection | 3+ instances | 0 | Phase 3 |
| Agent config-loading duplication | 5+ instances | 1 (shared utility) | Phase 3 |
| TypeScript `any` in page handlers | 3+ instances | 0 | Phase 4 |
| TypeScript `strict` mode | `false` | `true` | Phase 4 |

---

## Appendix

### A. Component Quality Scorecard

| Category | Backend | Frontend | Agent |
|----------|---------|----------|-------|
| Architecture & Organization | 5/5 | 4/5 | 5/5 |
| Type Safety & Validation | 5/5 | 4/5 | 4.5/5 |
| Error Handling | 5/5 | 3/5 | 4/5 |
| Documentation & Docstrings | 5/5 | 3.5/5 | 5/5 |
| Security | 5/5 | 4/5 | 4/5 |
| Test Coverage | 4.5/5 | 2/5 | 4/5 |
| Code Reuse / DRY | 4/5 | 3.5/5 | 3.5/5 |
| API Design | 5/5 | 4/5 | 4.5/5 |
| **Overall** | **A** | **B+** | **A-** |

### B. Largest Files by Component

**Backend Services (Top 5):**

| File | Lines | Recommended Action |
|------|-------|--------------------|
| `job_coordinator_service.py` | 2,459 | Split into Claim/Completion/Progress services |
| `event_service.py` | 2,435 | Extract query builder and validation modules |
| `trend_service.py` | 1,822 | Extract aggregation query helpers |
| `inventory_service.py` | 1,500+ | Review for decomposition opportunities |
| `collection_service.py` | 1,200+ | Review for decomposition opportunities |

**Frontend Pages (Top 5):**

| File | Lines | Recommended Action |
|------|-------|--------------------|
| `PipelineEditorPage.tsx` | 1,278 | Extract canvas, config panel, toolbar |
| `EventsPage.tsx` | 1,083 | Extract list and calendar tab components |
| `EventForm.tsx` | 934 | Extract form sections into sub-components |
| `AnalyticsPage.tsx` | 794 | Extract tab components, consolidate useState |
| `ResultDetailPanel.tsx` | 721 | Extract detail sections |

**Agent CLI (Top 3):**

| File | Lines | Recommended Action |
|------|-------|--------------------|
| `debug.py` | 1,061 | Decompose `compare_inventory()` (481 lines) |
| `collection.py` | 769 | Extract config loading utility |
| `run.py` | 669 | Extract online/offline execution helpers |

### C. Architectural Patterns Verified

All patterns below were confirmed as properly implemented and do NOT require changes:

| Pattern | Status | Key Files |
|---------|--------|-----------|
| GUID-based Identifiers (Issue #42) | Verified | `backend/src/services/guid.py`, `backend/src/models/mixins/guid.py` |
| Multi-Tenancy (Issue #73) | Verified | `backend/src/middleware/tenant.py` |
| Agent-Only Execution (Issue #90) | Verified | `backend/src/services/job_coordinator_service.py`, `agent/src/job_executor.py` |
| Agent-Only Tool Execution (Issue #108) | Verified | `agent/src/analysis/`, `agent/cli/run.py` |
| Audit Trail (Issue #120) | Verified | `backend/src/models/mixins/audit.py`, `frontend/src/components/audit/` |
| Design System Compliance | Verified | `frontend/docs/design-system.md` |
| Single Title Pattern (Issue #67) | Verified | All pages use `TopHeader` exclusively |

---

## Revision History

- **2026-02-14 (v1.0)**: Initial code quality assessment and improvement roadmap.
