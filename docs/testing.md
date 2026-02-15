# Testing & Coverage Report

> **Last updated:** 2026-02-14
> **Commit:** `5cb6626` (branch `203-frontend-test-coverage`)
> **Test suite version:** v1.0 — Phase 1 of Code Quality Enhancement Plan (Issue #203)

This document describes the test infrastructure, folder organization, coverage metrics, and recommended practices across all three ShutterSense components: **Frontend**, **Backend**, and **Agent**.

Coverage numbers and test counts are point-in-time snapshots. Re-run the commands in [Running Coverage Reports](#running-coverage-reports) to get current numbers.

---

## Table of Contents

- [Coverage Summary](#coverage-summary)
- [Frontend](#frontend)
  - [Test Runner & Configuration](#frontend-test-runner--configuration)
  - [Folder Structure](#frontend-folder-structure)
  - [Mocking Strategy](#frontend-mocking-strategy)
  - [Recommended Practices](#frontend-recommended-practices)
  - [Known Patterns & Pitfalls](#frontend-known-patterns--pitfalls)
- [Backend](#backend)
  - [Test Runner & Configuration](#backend-test-runner--configuration)
  - [Folder Structure](#backend-folder-structure)
  - [Fixtures & Test Database](#backend-fixtures--test-database)
  - [Recommended Practices](#backend-recommended-practices)
- [Agent](#agent)
  - [Test Runner & Configuration](#agent-test-runner--configuration)
  - [Folder Structure](#agent-folder-structure)
  - [Recommended Practices](#agent-recommended-practices)
- [Running Coverage Reports](#running-coverage-reports)
- [CI/CD Integration](#cicd-integration)
- [Changelog](#changelog)

---

## Coverage Summary

| Component | Line Coverage | Statements | Tests Passing | Test Files |
|-----------|:------------:|:----------:|:-------------:|:----------:|
| Frontend  | **67.05%**   | 66.08%     | 1,956         | 140        |
| Backend   | **71.69%**   | —          | 2,719         | 132        |
| Agent     | **53.05%**   | —          | 660           | 41         |
| **Total** | —            | —          | **5,335**     | **313**    |

*Measured 2026-02-14. Frontend uses V8 provider (statements/branches/functions/lines). Backend and Agent use pytest-cov (line coverage).*

### Coverage Targets

| Component | Target | Current | Status |
|-----------|:------:|:-------:|:------:|
| Frontend  | 50%+   | 67%     | Met    |
| Backend   | 65%+   | 72%     | Met    |
| Agent     | 50%+   | 53%     | Met    |

---

## Frontend

### Frontend Test Runner & Configuration

| Setting        | Value                                          |
|----------------|------------------------------------------------|
| Framework      | [Vitest](https://vitest.dev/) 4.x              |
| Environment    | jsdom                                          |
| Coverage       | `@vitest/coverage-v8`                          |
| UI             | `@vitest/ui` (optional)                        |
| Setup file     | `frontend/tests/setup.ts`                      |
| Config         | `frontend/vitest.config.ts`                    |
| React support  | `@vitejs/plugin-react`                         |

**Key dependencies:**

| Package                      | Purpose                     |
|------------------------------|-----------------------------|
| `@testing-library/react`     | Component rendering/queries |
| `@testing-library/jest-dom`  | DOM matchers                |
| `@testing-library/user-event`| User interaction simulation |
| `jsdom`                      | Browser environment         |
| `msw`                        | HTTP mocking (integration)  |

**Test setup** (`tests/setup.ts`) provides global mocks for:
- `ResizeObserver` (required by Radix UI)
- `window.matchMedia` (responsive components)
- Pointer capture methods on `Element.prototype`
- `scrollIntoView`
- MSW server lifecycle (`beforeAll` / `afterEach` / `afterAll`)

### Frontend Folder Structure

```text
frontend/
├── src/
│   ├── components/
│   │   ├── audit/__tests__/          # 2 test files
│   │   ├── events/__tests__/         # 6 test files
│   │   ├── results/__tests__/        # 1 test file
│   │   ├── settings/__tests__/       # 2 test files
│   │   └── ui/__tests__/            # 2 test files
│   ├── contexts/__tests__/           # 2 test files
│   ├── hooks/__tests__/              # 21 test files
│   ├── pages/__tests__/              # 18 test files
│   └── services/__tests__/           # 22 test files
├── tests/                            # Legacy tests (read-only)
│   ├── components/                   # Component integration tests
│   ├── hooks/                        # Hook tests (older style)
│   ├── integration/                  # Multi-layer integration tests
│   ├── lib/                          # Utility tests
│   ├── mocks/handlers.ts             # MSW request handlers
│   ├── setup.ts                      # Global test setup
│   └── utils/                        # Test helpers
└── vitest.config.ts                  # Test configuration
```

**Convention:** All new tests MUST be co-located with their source file in a sibling `__tests__/` directory:

```text
src/hooks/useAuth.ts
src/hooks/__tests__/useAuth.test.tsx
```

Legacy tests in `tests/` remain valid and run as part of the suite, but new tests should not be added there.

### Frontend Mocking Strategy

**Unit tests** use `vi.mock()` for module-level mocking:

```typescript
// Service tests — mock the axios instance
vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

// Hook tests — mock the underlying service
vi.mock('@/services/categories', () => ({
  listCategories: vi.fn(),
  createCategory: vi.fn(),
}))

// Page tests — mock hooks and child components
vi.mock('@/hooks/useEvents', () => ({
  useEvents: vi.fn().mockReturnValue({ events: [], loading: false }),
}))
```

**Integration tests** use [MSW](https://mswjs.io/) (Mock Service Worker) for HTTP-level mocking. Handlers are defined in `tests/mocks/handlers.ts`.

### Frontend Recommended Practices

1. **Use `vi.clearAllMocks()` in `beforeEach`**, not `vi.restoreAllMocks()`.
   `restoreAllMocks()` resets all mock implementations — including module-level `vi.fn().mockResolvedValue()` declarations — which silently breaks subsequent tests.

2. **Use `getAllByText` for text that appears in responsive layouts.**
   Components using `ResponsiveTabsList` render text in both `TabsTrigger` and a `Select` dropdown, causing `getByText` to throw "found multiple elements".

3. **Test hooks that re-throw errors with `autoFetch=false`.**
   Many hooks call `throw err` in their catch block after setting error state. When triggered from `useEffect`, this becomes an unhandled promise rejection. Instead:

   ```typescript
   const { result } = renderHook(() => useMyHook(false)) // autoFetch=false
   await act(async () => {
     try {
       await result.current.fetchData()
     } catch {
       // Expected — hook re-throws after setting error state
     }
   })
   expect(result.current.error).toBe('Some error')
   ```

4. **Match mock shapes to actual hook return types.**
   Always check the hook source for the exact return type. Common pitfalls:
   - `useAgentPoolStatus` returns `{ poolStatus: { online_count } }` not `{ onlineCount }`
   - `useDateRange` returns `{ range: { startDate, endDate } }` not `{ dateRange }`
   - `useConflicts` requires `detectConflicts: vi.fn().mockResolvedValue([])` (must return a promise)

5. **Page smoke tests should assert on real rendered text.**
   Read the actual page component source to find exact button labels, KPI card titles, and section headings before writing assertions.

### Frontend Known Patterns & Pitfalls

| Pattern | Details |
|---------|---------|
| Path aliases | `@/` maps to `src/` — works in test files via vitest config |
| `import.meta.env` | Cannot be stubbed via `vi.stubGlobal` — test the real instance instead |
| Axios interceptors | Access via `api.interceptors.response.handlers` internal array |
| Icon-only buttons | `<Button size="icon">` renders no text — don't assert on text content |
| Multiple text matches | Responsive components often render text twice — use `getAllByText` |

---

## Backend

### Backend Test Runner & Configuration

| Setting        | Value                                  |
|----------------|----------------------------------------|
| Framework      | [pytest](https://pytest.org/) 7.x+     |
| Config file    | `pytest.ini` (project root)            |
| Test database  | SQLite in-memory (`:memory:`)          |
| Coverage       | `pytest-cov`                           |
| Async support  | `pytest-asyncio`                       |

**pytest.ini markers:**
- `@pytest.mark.slow` — long-running tests (deselect with `-m "not slow"`)
- `@pytest.mark.integration` — integration tests
- `@pytest.mark.unit` — unit tests

### Backend Folder Structure

```text
backend/tests/
├── conftest.py                       # Core fixtures (DB, auth, tenant)
├── unit/                             # Unit tests
│   ├── api/                          # API route unit tests
│   ├── models/                       # ORM model tests (8 files)
│   ├── schemas/                      # Pydantic schema tests (2 files)
│   ├── services/                     # Service layer tests (8 files)
│   └── test_*.py                     # Top-level unit tests (67 files)
└── integration/                      # Integration tests
    ├── api/                          # API endpoint integration (3 files)
    └── test_*.py                     # Top-level integration tests (42 files)
```

**Total: ~132 test files, 2,719 tests passing**

### Backend Fixtures & Test Database

The main `conftest.py` provides:

| Fixture | Purpose |
|---------|---------|
| `session` | SQLAlchemy async session with in-memory SQLite (`autoflush=False`) |
| `mock_encryptor` | Fernet encryption for credential tests |
| `tenant_context` | `TenantContext` with `team_id` and `user_id` for multi-tenancy |
| `sample_team` / `sample_user` | Pre-created Team and User ORM objects |
| `job_queue` | In-memory job queue for testing |
| `connection_manager` | WebSocket connection manager |

**Important:** The test session uses `autoflush=False`. When querying for objects that were `.add()`-ed but not committed, call `session.flush()` first.

### Backend Recommended Practices

1. **Always scope data to a tenant.** Services require `team_id` — use the `tenant_context` fixture.

2. **Use `GuidService.parse_guid()` for GUID lookups**, not `Model.guid == value`. The `guid` property is a Python `@property`, not a `@hybrid_property`, so it cannot be used in SQLAlchemy filter expressions.

3. **Provide required foreign keys in fixtures.** `Location` and `Organizer` models require a non-null `category_id`.

4. **Prefer `session.flush()` over `session.commit()`** in tests to keep changes within the transaction. Only commit when testing commit-dependent behavior.

5. **Use markers for slow tests.** Tag expensive tests with `@pytest.mark.slow` so they can be skipped during rapid iteration: `pytest -m "not slow"`.

---

## Agent

### Agent Test Runner & Configuration

| Setting        | Value                              |
|----------------|------------------------------------|
| Framework      | pytest 7.x+ with pytest-asyncio   |
| HTTP mocking   | [respx](https://lundberg.github.io/respx/) (httpx mock) |
| Coverage       | pytest-cov                         |
| Config         | `agent/pyproject.toml`             |

### Agent Folder Structure

```text
agent/tests/
├── conftest.py                       # Agent config fixtures
├── unit/                             # Unit tests (34 files)
│   ├── test_api_client.py            # HTTP client
│   ├── test_cli_*.py                 # CLI command tests
│   ├── test_config_*.py              # Configuration
│   ├── test_credential_store.py      # Encryption
│   ├── test_inventory_*.py           # Inventory parsing
│   ├── test_job_executor.py          # Job execution
│   └── ...
└── integration/                      # Integration tests (7 files)
    ├── test_job_execution.py         # Full job cycle
    ├── test_offline_sync_flow.py     # Offline → sync
    ├── test_registration.py          # Agent registration
    └── ...
```

**Total: 41 test files, 660 tests passing**

### Agent Recommended Practices

1. **Use `respx` for HTTP mocking**, not `unittest.mock.patch`. The agent uses `httpx` as its HTTP client, and `respx` provides native route-matching support.

2. **Use temp directories for config and cache tests.** The `conftest.py` provides a `tmp_config_dir` fixture for isolated filesystem tests.

3. **Test across platforms when possible.** The agent runs on Linux, macOS, and Windows. CI runs tests on all three OS variants.

---

## Running Coverage Reports

### Frontend

```bash
cd frontend
npx vitest run --coverage
# Output: text summary to terminal + HTML report in coverage/
```

### Backend

```bash
# From project root, using the venv
venv/bin/python -m pytest backend/tests/ \
  --cov=backend/src \
  --cov-report=term-missing
```

### Agent

```bash
# From project root, using the venv
venv/bin/python -m pytest agent/tests/ \
  --cov=agent/src --cov=agent/cli \
  --cov-report=term-missing
```

### Quick Full Suite (All Components)

```bash
# Frontend
(cd frontend && npx vitest run)

# Backend
venv/bin/python -m pytest backend/tests/ -v

# Agent
venv/bin/python -m pytest agent/tests/ -v
```

---

## CI/CD Integration

Tests run automatically on push/PR via `.github/workflows/test.yml`:

| Job | OS | Python/Node | Scope |
|-----|------|-----------|-------|
| `frontend-test` | ubuntu-latest | Node 20 | `npm test -- --run` |
| `backend-web-test` | ubuntu-latest | Python 3.11, 3.12 | `backend/tests/unit/` |
| `agent-test` | ubuntu, macOS, Windows | Python 3.11, 3.12 | `agent/tests/` |

Coverage reports are uploaded to [Codecov](https://codecov.io/) from:
- Frontend: all OS/Node combinations
- Backend: Python 3.11 only
- Agent: Ubuntu + Python 3.11 only

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-14 | v1.0 | Initial document. Phase 1 coverage push: 63 new frontend test files, full suite green (5,335 tests). Frontend 67%, Backend 72%, Agent 53%. |
