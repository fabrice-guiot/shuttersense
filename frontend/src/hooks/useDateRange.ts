/**
 * useDateRange Hook
 *
 * State management for date range selection with URL sync.
 * Supports rolling presets (30/60/90 days), calendar-month presets
 * (1/2/3/6 months), and custom date ranges.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 7, US5)
 */

import { useMemo, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'

// ============================================================================
// Types
// ============================================================================

export type RangePreset =
  | 'next_30d'
  | 'next_60d'
  | 'next_90d'
  | 'next_1m'
  | 'next_2m'
  | 'next_3m'
  | 'next_6m'
  | 'custom'

export interface DateRange {
  startDate: string   // YYYY-MM-DD
  endDate: string     // YYYY-MM-DD
}

export interface UseDateRangeReturn {
  /** Currently selected preset (or 'custom') */
  preset: RangePreset
  /** Computed start and end dates */
  range: DateRange
  /** Custom start date (only relevant when preset='custom') */
  customStart: string
  /** Custom end date (only relevant when preset='custom') */
  customEnd: string
  /** Change preset selection */
  setPreset: (preset: RangePreset) => void
  /** Set custom date range */
  setCustomRange: (start: string, end: string) => void
}

// ============================================================================
// Constants
// ============================================================================

const VALID_PRESETS: RangePreset[] = [
  'next_30d', 'next_60d', 'next_90d',
  'next_1m', 'next_2m', 'next_3m', 'next_6m',
  'custom',
]

const DEFAULT_PRESET: RangePreset = 'next_30d'

export const PRESET_LABELS: Record<RangePreset, string> = {
  next_30d: 'Next 30 days',
  next_60d: 'Next 60 days',
  next_90d: 'Next 90 days',
  next_1m: 'Next 1 month',
  next_2m: 'Next 2 months',
  next_3m: 'Next 3 months',
  next_6m: 'Next 6 months',
  custom: 'Custom range',
}

export const PRESET_GROUPS = [
  {
    label: 'Rolling',
    presets: ['next_30d', 'next_60d', 'next_90d'] as RangePreset[],
  },
  {
    label: 'Monthly',
    presets: ['next_1m', 'next_2m', 'next_3m', 'next_6m'] as RangePreset[],
  },
]

// ============================================================================
// Helpers
// ============================================================================

function formatDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function computeRange(preset: RangePreset, customStart: string, customEnd: string): DateRange {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  switch (preset) {
    case 'next_30d': {
      const end = new Date(today)
      end.setDate(end.getDate() + 30)
      return { startDate: formatDate(today), endDate: formatDate(end) }
    }
    case 'next_60d': {
      const end = new Date(today)
      end.setDate(end.getDate() + 60)
      return { startDate: formatDate(today), endDate: formatDate(end) }
    }
    case 'next_90d': {
      const end = new Date(today)
      end.setDate(end.getDate() + 90)
      return { startDate: formatDate(today), endDate: formatDate(end) }
    }
    case 'next_1m': {
      const start = new Date(today.getFullYear(), today.getMonth(), 1)
      const end = new Date(today.getFullYear(), today.getMonth() + 1, 0)
      return { startDate: formatDate(start), endDate: formatDate(end) }
    }
    case 'next_2m': {
      const start = new Date(today.getFullYear(), today.getMonth(), 1)
      const end = new Date(today.getFullYear(), today.getMonth() + 2, 0)
      return { startDate: formatDate(start), endDate: formatDate(end) }
    }
    case 'next_3m': {
      const start = new Date(today.getFullYear(), today.getMonth(), 1)
      const end = new Date(today.getFullYear(), today.getMonth() + 3, 0)
      return { startDate: formatDate(start), endDate: formatDate(end) }
    }
    case 'next_6m': {
      const start = new Date(today.getFullYear(), today.getMonth(), 1)
      const end = new Date(today.getFullYear(), today.getMonth() + 6, 0)
      return { startDate: formatDate(start), endDate: formatDate(end) }
    }
    case 'custom':
      return {
        startDate: customStart || formatDate(today),
        endDate: customEnd || formatDate(today),
      }
  }
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Hook for managing date range selection with URL persistence.
 *
 * @param paramPrefix - URL param prefix to avoid collisions (default: 'range')
 */
export function useDateRange(paramPrefix = 'range'): UseDateRangeReturn {
  const [searchParams, setSearchParams] = useSearchParams()

  const presetKey = paramPrefix
  const startKey = `${paramPrefix}_start`
  const endKey = `${paramPrefix}_end`

  // Read current state from URL
  const rawPreset = searchParams.get(presetKey)
  const preset: RangePreset = rawPreset && VALID_PRESETS.includes(rawPreset as RangePreset)
    ? (rawPreset as RangePreset)
    : DEFAULT_PRESET

  const customStart = searchParams.get(startKey) || ''
  const customEnd = searchParams.get(endKey) || ''

  // Compute date range from preset
  const range = useMemo(
    () => computeRange(preset, customStart, customEnd),
    [preset, customStart, customEnd],
  )

  const setPreset = useCallback((newPreset: RangePreset) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set(presetKey, newPreset)
      // Clear custom dates when switching away from custom
      if (newPreset !== 'custom') {
        next.delete(startKey)
        next.delete(endKey)
      }
      return next
    }, { replace: true })
  }, [setSearchParams, presetKey, startKey, endKey])

  const setCustomRange = useCallback((start: string, end: string) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set(presetKey, 'custom')
      next.set(startKey, start)
      next.set(endKey, end)
      return next
    }, { replace: true })
  }, [setSearchParams, presetKey, startKey, endKey])

  return { preset, range, customStart, customEnd, setPreset, setCustomRange }
}
