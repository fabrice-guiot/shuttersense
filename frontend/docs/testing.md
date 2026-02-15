# Frontend Testing Conventions

## Test File Location

All new tests MUST be co-located with the source code they test:

```
src/<path>/__tests__/<Name>.test.{ts,tsx}
```

Examples:
- `src/services/__tests__/auth.test.ts`
- `src/hooks/__tests__/useAuth.test.ts`
- `src/contexts/__tests__/AuthContext.test.tsx`
- `src/pages/__tests__/LoginPage.test.tsx`
- `src/components/results/__tests__/ResultsTable.test.tsx`

Legacy tests in `tests/` remain valid but new tests should not be added there.

## Mocking Strategy

### Unit tests: `vi.mock()`

Use `vi.mock()` for isolated unit tests of services, hooks, and components. This is the default for new tests.

```typescript
import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

describe('myService', () => {
  beforeEach(() => vi.clearAllMocks())

  test('fetches data', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [{ id: 1 }] })
    const result = await fetchData()
    expect(api.get).toHaveBeenCalledWith('/endpoint')
    expect(result).toEqual([{ id: 1 }])
  })
})
```

### Integration tests: MSW

Use MSW (Mock Service Worker) for integration tests that test multiple layers together. MSW handlers live in `tests/mocks/handlers.ts`.

## Import Patterns

- **Module under test**: Use relative imports (`../useAuth`)
- **Cross-cutting utilities**: Use `@/` alias (`@/services/api`, `@/utils/guid`)
- **Test utilities**: Use `@testing-library/react` directly (custom render in `tests/utils/test-utils.tsx` for components needing BrowserRouter)

## Hook Tests

Use `renderHook` + `waitFor` from `@testing-library/react`:

```typescript
import { renderHook, waitFor, act } from '@testing-library/react'

test('fetches on mount', async () => {
  const { result } = renderHook(() => useMyHook())
  await waitFor(() => expect(result.current.loading).toBe(false))
  expect(result.current.data).toBeDefined()
})
```

## Running Tests

```bash
cd frontend
npx vitest run                     # Run all tests once
npx vitest run --coverage          # With coverage report
npx vitest run --reporter=verbose  # Verbose output
npx vitest                         # Watch mode
```
