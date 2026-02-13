/**
 * Tests for useDateRange hook.
 *
 * Issue #182: Calendar Conflict Visualization (Phase 7, US5)
 */

import { describe, test, expect, vi, beforeEach, afterAll } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useDateRange } from '../useDateRange'

// ============================================================================
// Helpers
// ============================================================================

function wrapper({ children }: { children: ReactNode }) {
  return <MemoryRouter>{children}</MemoryRouter>
}

function wrapperWithParams(search: string) {
  return ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[`/?${search}`]}>{children}</MemoryRouter>
  )
}

// ============================================================================
// Tests
// ============================================================================

describe('useDateRange', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 5, 15)) // June 15, 2026
  })

  afterAll(() => {
    vi.useRealTimers()
  })

  test('defaults to next_30d preset', () => {
    const { result } = renderHook(() => useDateRange(), { wrapper })
    expect(result.current.preset).toBe('next_30d')
  })

  test('next_30d: start=today, end=today+30', () => {
    const { result } = renderHook(() => useDateRange(), { wrapper })
    expect(result.current.range.startDate).toBe('2026-06-15')
    expect(result.current.range.endDate).toBe('2026-07-15')
  })

  test('next_60d: start=today, end=today+60', () => {
    const { result } = renderHook(() => useDateRange(), {
      wrapper: wrapperWithParams('range=next_60d'),
    })
    expect(result.current.range.startDate).toBe('2026-06-15')
    expect(result.current.range.endDate).toBe('2026-08-14')
  })

  test('next_90d: start=today, end=today+90', () => {
    const { result } = renderHook(() => useDateRange(), {
      wrapper: wrapperWithParams('range=next_90d'),
    })
    expect(result.current.range.startDate).toBe('2026-06-15')
    expect(result.current.range.endDate).toBe('2026-09-13')
  })

  test('next_1m: start=1st of current month, end=last day of current month', () => {
    const { result } = renderHook(() => useDateRange(), {
      wrapper: wrapperWithParams('range=next_1m'),
    })
    expect(result.current.range.startDate).toBe('2026-06-01')
    expect(result.current.range.endDate).toBe('2026-06-30')
  })

  test('next_2m: start=1st of current month, end=last day of month+1', () => {
    const { result } = renderHook(() => useDateRange(), {
      wrapper: wrapperWithParams('range=next_2m'),
    })
    expect(result.current.range.startDate).toBe('2026-06-01')
    expect(result.current.range.endDate).toBe('2026-07-31')
  })

  test('next_3m: start=1st of current month, end=last day of month+2', () => {
    const { result } = renderHook(() => useDateRange(), {
      wrapper: wrapperWithParams('range=next_3m'),
    })
    expect(result.current.range.startDate).toBe('2026-06-01')
    expect(result.current.range.endDate).toBe('2026-08-31')
  })

  test('next_6m: start=1st of current month, end=last day of month+5', () => {
    const { result } = renderHook(() => useDateRange(), {
      wrapper: wrapperWithParams('range=next_6m'),
    })
    expect(result.current.range.startDate).toBe('2026-06-01')
    expect(result.current.range.endDate).toBe('2026-11-30')
  })

  test('custom range uses provided start and end dates', () => {
    const { result } = renderHook(() => useDateRange(), {
      wrapper: wrapperWithParams('range=custom&range_start=2026-07-01&range_end=2026-12-31'),
    })
    expect(result.current.preset).toBe('custom')
    expect(result.current.range.startDate).toBe('2026-07-01')
    expect(result.current.range.endDate).toBe('2026-12-31')
  })

  test('setPreset changes the preset', () => {
    const { result } = renderHook(() => useDateRange(), { wrapper })
    expect(result.current.preset).toBe('next_30d')

    act(() => {
      result.current.setPreset('next_60d')
    })

    expect(result.current.preset).toBe('next_60d')
  })

  test('setCustomRange switches to custom and sets dates', () => {
    const { result } = renderHook(() => useDateRange(), { wrapper })

    act(() => {
      result.current.setCustomRange('2026-08-01', '2026-09-15')
    })

    expect(result.current.preset).toBe('custom')
    expect(result.current.range.startDate).toBe('2026-08-01')
    expect(result.current.range.endDate).toBe('2026-09-15')
  })

  test('URL sync: restores preset from search params', () => {
    const { result } = renderHook(() => useDateRange(), {
      wrapper: wrapperWithParams('range=next_90d'),
    })
    expect(result.current.preset).toBe('next_90d')
  })

  test('invalid preset in URL falls back to default', () => {
    const { result } = renderHook(() => useDateRange(), {
      wrapper: wrapperWithParams('range=invalid_preset'),
    })
    expect(result.current.preset).toBe('next_30d')
  })

  test('supports custom param prefix', () => {
    const { result } = renderHook(() => useDateRange('dr'), {
      wrapper: wrapperWithParams('dr=next_60d'),
    })
    expect(result.current.preset).toBe('next_60d')
  })
})
