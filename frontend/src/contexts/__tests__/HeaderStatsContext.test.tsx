import { describe, test, expect, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import type { ReactNode } from 'react'
import { HeaderStatsProvider, useHeaderStats } from '../HeaderStatsContext'
import type { HeaderStat } from '@/components/layout/TopHeader'

describe('HeaderStatsContext', () => {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <HeaderStatsProvider>{children}</HeaderStatsProvider>
  )

  describe('HeaderStatsProvider', () => {
    test('provides empty stats by default', () => {
      const { result } = renderHook(() => useHeaderStats(), { wrapper })

      expect(result.current.stats).toEqual([])
    })

    test('uses defaultStats when provided', () => {
      const defaults: HeaderStat[] = [{ label: 'Total', value: 42 }]

      const customWrapper = ({ children }: { children: ReactNode }) => (
        <HeaderStatsProvider defaultStats={defaults}>{children}</HeaderStatsProvider>
      )

      const { result } = renderHook(() => useHeaderStats(), { wrapper: customWrapper })

      expect(result.current.stats).toEqual([{ label: 'Total', value: 42 }])
    })

    test('setStats updates stats', () => {
      const { result } = renderHook(() => useHeaderStats(), { wrapper })

      const newStats: HeaderStat[] = [
        { label: 'Collections', value: 10 },
        { label: 'Active', value: 8 },
      ]

      act(() => {
        result.current.setStats(newStats)
      })

      expect(result.current.stats).toEqual(newStats)
    })

    test('clearStats resets to empty', () => {
      const defaults: HeaderStat[] = [{ label: 'Total', value: 42 }]

      const customWrapper = ({ children }: { children: ReactNode }) => (
        <HeaderStatsProvider defaultStats={defaults}>{children}</HeaderStatsProvider>
      )

      const { result } = renderHook(() => useHeaderStats(), { wrapper: customWrapper })

      expect(result.current.stats).toHaveLength(1)

      act(() => {
        result.current.clearStats()
      })

      expect(result.current.stats).toEqual([])
    })

    test('setStats replaces previous stats', () => {
      const { result } = renderHook(() => useHeaderStats(), { wrapper })

      act(() => {
        result.current.setStats([{ label: 'First', value: 1 }])
      })

      act(() => {
        result.current.setStats([{ label: 'Second', value: 2 }])
      })

      expect(result.current.stats).toEqual([{ label: 'Second', value: 2 }])
    })
  })

  describe('useHeaderStats', () => {
    test('throws when used outside HeaderStatsProvider', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

      expect(() => {
        renderHook(() => useHeaderStats())
      }).toThrow('useHeaderStats must be used within a HeaderStatsProvider')

      spy.mockRestore()
    })
  })
})
