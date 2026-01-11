/**
 * Unit tests for date formatting utilities.
 *
 * Tests cover:
 *   - parseDate() - ISO 8601 parsing, null/undefined/invalid handling
 *   - hasIntlSupport() - Intl.DateTimeFormat detection
 *   - hasRelativeTimeSupport() - Intl.RelativeTimeFormat detection
 *   - formatDateTime() - absolute date/time formatting
 *   - formatDate() - date-only formatting
 *   - formatTime() - time-only formatting
 *   - formatRelativeTime() - relative time formatting
 *   - Edge cases - year boundaries, locales, DST transitions
 *
 * @module dateFormat.test
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  parseDate,
  hasIntlSupport,
  hasRelativeTimeSupport,
  formatDateTime,
  formatDate,
  formatTime,
  getRelativeTimeUnit,
  formatRelativeTime,
} from '@/utils/dateFormat'

// ============================================================================
// Phase 2: Foundational Tests
// ============================================================================

describe('parseDate', () => {
  it('should parse valid ISO 8601 string', () => {
    const result = parseDate('2026-01-07T15:45:00')
    expect(result).toBeInstanceOf(Date)
    expect(result?.getFullYear()).toBe(2026)
    expect(result?.getMonth()).toBe(0) // January is 0
    expect(result?.getDate()).toBe(7)
  })

  it('should parse ISO 8601 string with Z suffix', () => {
    const result = parseDate('2026-01-07T15:45:00Z')
    expect(result).toBeInstanceOf(Date)
    expect(result?.getUTCHours()).toBe(15)
    expect(result?.getUTCMinutes()).toBe(45)
  })

  it('should parse ISO 8601 string with timezone offset', () => {
    const result = parseDate('2026-01-07T15:45:00-05:00')
    expect(result).toBeInstanceOf(Date)
    // UTC time should be 20:45 (15:45 + 5 hours)
    expect(result?.getUTCHours()).toBe(20)
  })

  // UTC normalization tests - critical for backend datetime compatibility
  it('should treat datetime without timezone as UTC (backend compatibility)', () => {
    // Backend sends "2026-01-07T15:45:00" without Z, representing UTC
    const result = parseDate('2026-01-07T15:45:00')
    expect(result).toBeInstanceOf(Date)
    // Should be interpreted as 15:45 UTC, not local time
    expect(result?.getUTCHours()).toBe(15)
    expect(result?.getUTCMinutes()).toBe(45)
  })

  it('should produce same result for datetime with and without Z suffix', () => {
    const withZ = parseDate('2026-01-07T15:45:00Z')
    const withoutZ = parseDate('2026-01-07T15:45:00')

    expect(withZ?.getTime()).toBe(withoutZ?.getTime())
  })

  it('should respect explicit timezone offset when provided', () => {
    // +02:00 means the time is 2 hours ahead of UTC
    const result = parseDate('2026-01-07T15:45:00+02:00')
    expect(result).toBeInstanceOf(Date)
    // UTC time should be 13:45 (15:45 - 2 hours)
    expect(result?.getUTCHours()).toBe(13)
  })

  it('should return null for null input', () => {
    const result = parseDate(null)
    expect(result).toBeNull()
  })

  it('should return null for undefined input', () => {
    const result = parseDate(undefined)
    expect(result).toBeNull()
  })

  it('should return null for empty string', () => {
    const result = parseDate('')
    expect(result).toBeNull()
  })

  it('should return null for invalid date string', () => {
    const result = parseDate('not-a-date')
    expect(result).toBeNull()
  })

  it('should return null for impossible date', () => {
    // Month 13 doesn't exist
    const result = parseDate('2026-13-45T15:45:00')
    expect(result).toBeNull()
  })

  it('should handle date-only string (no T, no timezone appended)', () => {
    const result = parseDate('2026-01-07')
    expect(result).toBeInstanceOf(Date)
    expect(result?.getFullYear()).toBe(2026)
    // Date-only strings are interpreted as local date at midnight
  })
})

describe('hasIntlSupport', () => {
  it('should return true when Intl.DateTimeFormat is available', () => {
    // In modern browsers/jsdom, Intl is always available
    const result = hasIntlSupport()
    expect(result).toBe(true)
  })

  it('should return false when Intl is unavailable', () => {
    // Save original Intl
    const originalIntl = globalThis.Intl

    // Remove Intl
    // @ts-expect-error - intentionally setting Intl to undefined for testing
    globalThis.Intl = undefined

    const result = hasIntlSupport()
    expect(result).toBe(false)

    // Restore Intl
    globalThis.Intl = originalIntl
  })
})

describe('hasRelativeTimeSupport', () => {
  it('should return true when Intl.RelativeTimeFormat is available', () => {
    // In modern browsers/jsdom, RelativeTimeFormat is available
    const result = hasRelativeTimeSupport()
    expect(result).toBe(true)
  })

  it('should return false when Intl.RelativeTimeFormat is unavailable', () => {
    // Save original
    const originalRelativeTimeFormat = Intl.RelativeTimeFormat

    // Remove RelativeTimeFormat
    // @ts-expect-error - intentionally setting to undefined for testing
    Intl.RelativeTimeFormat = undefined

    const result = hasRelativeTimeSupport()
    expect(result).toBe(false)

    // Restore
    Intl.RelativeTimeFormat = originalRelativeTimeFormat
  })

  it('should return false when Intl is completely unavailable', () => {
    // Save original Intl
    const originalIntl = globalThis.Intl

    // Remove Intl
    // @ts-expect-error - intentionally setting Intl to undefined for testing
    globalThis.Intl = undefined

    const result = hasRelativeTimeSupport()
    expect(result).toBe(false)

    // Restore Intl
    globalThis.Intl = originalIntl
  })
})

// ============================================================================
// Phase 3: User Story 1 Tests - Absolute Date/Time Formatting
// ============================================================================

describe('formatDateTime', () => {
  it('should format valid date with default options (medium date, short time)', () => {
    const result = formatDateTime('2026-01-07T15:45:00')

    // Should contain date parts (locale-dependent format)
    expect(result).toMatch(/2026/)
    expect(result).toMatch(/7/)
    // Should contain time (format varies by locale)
    expect(result).not.toBe('Never')
    expect(result).not.toBe('Invalid date')
  })

  it('should format valid date with custom dateStyle', () => {
    const shortResult = formatDateTime('2026-01-07T15:45:00', { dateStyle: 'short' })
    const longResult = formatDateTime('2026-01-07T15:45:00', { dateStyle: 'long' })

    // Short should be more compact than long
    expect(shortResult.length).toBeLessThan(longResult.length)
  })

  it('should format valid date with custom timeStyle', () => {
    const shortResult = formatDateTime('2026-01-07T15:45:00', { timeStyle: 'short' })
    const mediumResult = formatDateTime('2026-01-07T15:45:00', { timeStyle: 'medium' })

    // Medium includes seconds, short doesn't
    expect(shortResult).not.toMatch(/:00$/) // No seconds at end
    expect(mediumResult).toMatch(/:\d{2}.*:\d{2}/) // Has HH:MM:SS pattern somewhere
  })

  it('should format date with both custom dateStyle and timeStyle', () => {
    const result = formatDateTime('2026-01-07T15:45:00', {
      dateStyle: 'full',
      timeStyle: 'short',
    })

    // Full date style includes day of week
    expect(result.toLowerCase()).toMatch(/january|jan|wednesday|wed/)
  })

  it('should handle UTC dates correctly', () => {
    const result = formatDateTime('2026-01-07T15:45:00Z')

    expect(result).not.toBe('Never')
    expect(result).not.toBe('Invalid date')
    expect(result).toMatch(/2026/)
  })
})

describe('formatDate', () => {
  it('should format date with default medium style', () => {
    const result = formatDate('2026-01-07T15:45:00')

    // Medium style: "Jan 7, 2026" format (locale-dependent)
    expect(result).toMatch(/2026/)
    expect(result).toMatch(/7/)
    // Should NOT contain time
    expect(result).not.toMatch(/:/);
  })

  it('should format date with short style', () => {
    const result = formatDate('2026-01-07T15:45:00', { dateStyle: 'short' })

    // Short style: "1/7/26" or similar (locale-dependent)
    expect(result.length).toBeLessThan(15) // Short format is compact
    expect(result).not.toMatch(/:/) // No time component
  })

  it('should format date with long style', () => {
    const result = formatDate('2026-01-07T15:45:00', { dateStyle: 'long' })

    // Long style: "January 7, 2026" (locale-dependent)
    expect(result).toMatch(/2026/)
    expect(result.length).toBeGreaterThan(10)
  })

  it('should format date with full style', () => {
    const result = formatDate('2026-01-07T15:45:00', { dateStyle: 'full' })

    // Full style includes day of week: "Wednesday, January 7, 2026"
    expect(result.toLowerCase()).toMatch(/wednesday|wed|january|jan/)
    expect(result).toMatch(/2026/)
  })

  it('should ignore timeStyle option', () => {
    // Even with timeStyle, should not include time
    const result = formatDate('2026-01-07T15:45:00', { timeStyle: 'short' })

    expect(result).not.toMatch(/:/)
  })
})

describe('formatTime', () => {
  it('should format time with default short style', () => {
    const result = formatTime('2026-01-07T15:45:00')

    // Short time: "3:45 PM" or "15:45" (locale-dependent)
    expect(result).toMatch(/:/)
    expect(result).toMatch(/45/)
    // Should NOT contain date components
    expect(result).not.toMatch(/2026/)
    expect(result).not.toMatch(/Jan/)
  })

  it('should format time with medium style', () => {
    const result = formatTime('2026-01-07T15:45:30', { timeStyle: 'medium' })

    // Medium includes seconds: "3:45:30 PM" or "15:45:30"
    expect(result).toMatch(/45/)
    expect(result).toMatch(/30/) // seconds
  })

  it('should format time with long style', () => {
    const result = formatTime('2026-01-07T15:45:00', { timeStyle: 'long' })

    // Long includes timezone abbreviation
    expect(result).toMatch(/:/)
    expect(result.length).toBeGreaterThan(5)
  })

  it('should ignore dateStyle option', () => {
    // Even with dateStyle, should not include date
    const result = formatTime('2026-01-07T15:45:00', { dateStyle: 'full' })

    expect(result).not.toMatch(/2026/)
    expect(result).not.toMatch(/Jan/)
    expect(result).not.toMatch(/Wednesday/)
  })
})

// ============================================================================
// Phase 4: User Story 2 Tests - Relative Time Formatting
// ============================================================================

describe('getRelativeTimeUnit', () => {
  // T023: Tests for getRelativeTimeUnit()

  it('should return seconds for differences under 1 minute', () => {
    // 30 seconds ago
    const diffMs = 30 * 1000
    const result = getRelativeTimeUnit(diffMs)
    expect(result.unit).toBe('second')
    expect(result.value).toBe(-30)
  })

  it('should return minutes for differences under 1 hour', () => {
    // 15 minutes ago
    const diffMs = 15 * 60 * 1000
    const result = getRelativeTimeUnit(diffMs)
    expect(result.unit).toBe('minute')
    expect(result.value).toBe(-15)
  })

  it('should return hours for differences under 1 day', () => {
    // 5 hours ago
    const diffMs = 5 * 60 * 60 * 1000
    const result = getRelativeTimeUnit(diffMs)
    expect(result.unit).toBe('hour')
    expect(result.value).toBe(-5)
  })

  it('should return days for differences under 1 week', () => {
    // 3 days ago
    const diffMs = 3 * 24 * 60 * 60 * 1000
    const result = getRelativeTimeUnit(diffMs)
    expect(result.unit).toBe('day')
    expect(result.value).toBe(-3)
  })

  it('should return weeks for differences under 1 month', () => {
    // 2 weeks ago (14 days)
    const diffMs = 14 * 24 * 60 * 60 * 1000
    const result = getRelativeTimeUnit(diffMs)
    expect(result.unit).toBe('week')
    expect(result.value).toBe(-2)
  })

  it('should return months for differences under 1 year', () => {
    // 3 months ago (~90 days)
    const diffMs = 90 * 24 * 60 * 60 * 1000
    const result = getRelativeTimeUnit(diffMs)
    expect(result.unit).toBe('month')
    expect(result.value).toBe(-3)
  })

  it('should return years for differences over 1 year', () => {
    // 2 years ago (~730 days)
    const diffMs = 730 * 24 * 60 * 60 * 1000
    const result = getRelativeTimeUnit(diffMs)
    expect(result.unit).toBe('year')
    expect(result.value).toBe(-2)
  })

  it('should handle zero difference', () => {
    const result = getRelativeTimeUnit(0)
    expect(result.unit).toBe('second')
    expect(result.value).toBe(0)
  })

  it('should handle exactly 1 minute', () => {
    const diffMs = 60 * 1000
    const result = getRelativeTimeUnit(diffMs)
    expect(result.unit).toBe('minute')
    expect(result.value).toBe(-1)
  })

  it('should handle exactly 1 hour', () => {
    const diffMs = 60 * 60 * 1000
    const result = getRelativeTimeUnit(diffMs)
    expect(result.unit).toBe('hour')
    expect(result.value).toBe(-1)
  })

  it('should handle exactly 1 day', () => {
    const diffMs = 24 * 60 * 60 * 1000
    const result = getRelativeTimeUnit(diffMs)
    expect(result.unit).toBe('day')
    expect(result.value).toBe(-1)
  })
})

describe('formatRelativeTime', () => {
  // T024: Tests for formatRelativeTime()

  beforeEach(() => {
    // Set a fixed "now" time for consistent testing
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-11T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should format time from seconds ago', () => {
    // 30 seconds ago
    const result = formatRelativeTime('2026-01-11T11:59:30Z')
    // Should contain "second" in some form
    expect(result.toLowerCase()).toMatch(/second|now/)
  })

  it('should format time from minutes ago', () => {
    // 5 minutes ago
    const result = formatRelativeTime('2026-01-11T11:55:00Z')
    expect(result.toLowerCase()).toMatch(/5.*minute|minute.*5/)
  })

  it('should format time from hours ago', () => {
    // 3 hours ago
    const result = formatRelativeTime('2026-01-11T09:00:00Z')
    expect(result.toLowerCase()).toMatch(/3.*hour|hour.*3/)
  })

  it('should format "yesterday" for 1 day ago', () => {
    // 1 day ago
    const result = formatRelativeTime('2026-01-10T12:00:00Z')
    // Intl with numeric: 'auto' returns "yesterday"
    expect(result.toLowerCase()).toMatch(/yesterday|1.*day/)
  })

  it('should format hours ago within threshold', () => {
    // 20 hours ago (still within 1-day threshold)
    const result = formatRelativeTime('2026-01-10T16:00:00Z')
    expect(result.toLowerCase()).toMatch(/20.*hour|hour.*20/)
  })

  it('should return absolute date for times older than 1 day', () => {
    // 2 days ago - should return absolute date format (threshold is 1 day)
    const result = formatRelativeTime('2026-01-09T12:00:00Z')
    // Should NOT contain relative time indicators, should contain year
    expect(result).toMatch(/2026/)
    expect(result.toLowerCase()).not.toMatch(/ago|hour|minute|second/)
  })

  it('should return absolute date for times older than 1 week', () => {
    // 10 days ago
    const result = formatRelativeTime('2026-01-01T12:00:00Z')
    // Should return absolute date format
    expect(result).toMatch(/2026/)
  })

  it('should return absolute date for times older than 1 month', () => {
    // 60 days ago
    const result = formatRelativeTime('2025-11-12T12:00:00Z')
    // Should return absolute date format
    expect(result).toMatch(/2025/)
  })

  it('should handle null input', () => {
    const result = formatRelativeTime(null)
    expect(result).toBe('Never')
  })

  it('should handle undefined input', () => {
    const result = formatRelativeTime(undefined)
    expect(result).toBe('Never')
  })

  it('should handle invalid date string', () => {
    const result = formatRelativeTime('invalid-date')
    expect(result).toBe('Invalid date')
  })

  it('should handle future dates', () => {
    // 1 hour in the future
    const result = formatRelativeTime('2026-01-11T13:00:00Z')
    // Should handle gracefully - either show "in X time" or absolute
    expect(result).not.toBe('Never')
    expect(result).not.toBe('Invalid date')
  })
})

// ============================================================================
// Phase 5: User Story 3 Tests - Null/Invalid Handling
// ============================================================================

describe('null/undefined handling', () => {
  // T029: Tests for null/undefined handling

  describe('formatDateTime', () => {
    it('should return "Never" for null', () => {
      expect(formatDateTime(null)).toBe('Never')
    })

    it('should return "Never" for undefined', () => {
      expect(formatDateTime(undefined)).toBe('Never')
    })

    it('should return "Never" for empty string', () => {
      expect(formatDateTime('')).toBe('Never')
    })
  })

  describe('formatDate', () => {
    it('should return "Never" for null', () => {
      expect(formatDate(null)).toBe('Never')
    })

    it('should return "Never" for undefined', () => {
      expect(formatDate(undefined)).toBe('Never')
    })

    it('should return "Never" for empty string', () => {
      expect(formatDate('')).toBe('Never')
    })
  })

  describe('formatTime', () => {
    it('should return "Never" for null', () => {
      expect(formatTime(null)).toBe('Never')
    })

    it('should return "Never" for undefined', () => {
      expect(formatTime(undefined)).toBe('Never')
    })

    it('should return "Never" for empty string', () => {
      expect(formatTime('')).toBe('Never')
    })
  })

  describe('formatRelativeTime', () => {
    it('should return "Never" for null', () => {
      expect(formatRelativeTime(null)).toBe('Never')
    })

    it('should return "Never" for undefined', () => {
      expect(formatRelativeTime(undefined)).toBe('Never')
    })

    it('should return "Never" for empty string', () => {
      expect(formatRelativeTime('')).toBe('Never')
    })
  })
})

describe('invalid date handling', () => {
  // T030: Tests for invalid date handling

  describe('formatDateTime', () => {
    it('should return "Invalid date" for invalid string', () => {
      expect(formatDateTime('not-a-date')).toBe('Invalid date')
    })

    it('should return "Invalid date" for impossible date', () => {
      // Month 13 doesn't exist
      expect(formatDateTime('2026-13-45T15:45:00')).toBe('Invalid date')
    })

    it('should return "Invalid date" for malformed timestamp', () => {
      expect(formatDateTime('2026-01-07T25:99:00')).toBe('Invalid date')
    })

    it('should return "Invalid date" for random text', () => {
      expect(formatDateTime('hello world')).toBe('Invalid date')
    })
  })

  describe('formatDate', () => {
    it('should return "Invalid date" for invalid string', () => {
      expect(formatDate('not-a-date')).toBe('Invalid date')
    })

    it('should return "Invalid date" for impossible date', () => {
      expect(formatDate('2026-13-45')).toBe('Invalid date')
    })

    it('should return "Invalid date" for random text', () => {
      expect(formatDate('some random text')).toBe('Invalid date')
    })
  })

  describe('formatTime', () => {
    it('should return "Invalid date" for invalid string', () => {
      expect(formatTime('not-a-date')).toBe('Invalid date')
    })

    it('should return "Invalid date" for impossible time', () => {
      expect(formatTime('2026-01-07T25:99:00')).toBe('Invalid date')
    })

    it('should return "Invalid date" for random text', () => {
      expect(formatTime('random text here')).toBe('Invalid date')
    })
  })

  describe('formatRelativeTime', () => {
    it('should return "Invalid date" for invalid string', () => {
      expect(formatRelativeTime('not-a-date')).toBe('Invalid date')
    })

    it('should return "Invalid date" for impossible date', () => {
      expect(formatRelativeTime('2026-13-45T15:45:00')).toBe('Invalid date')
    })

    it('should return "Invalid date" for random text', () => {
      expect(formatRelativeTime('xyz123')).toBe('Invalid date')
    })
  })
})

// ============================================================================
// Phase 6: Polish Tests - Edge Cases & Locales
// ============================================================================

describe('locale variations', () => {
  // T037: Tests for locale variations will be added here
  it.todo('should format correctly with en-US locale')
  it.todo('should format correctly with fr-FR locale')
  it.todo('should format correctly with de-DE locale')
})

describe('edge cases', () => {
  // T038: Tests for edge cases will be added here
  it.todo('should handle year boundary correctly')
  it.todo('should handle dates from previous year')
  it.todo('should handle dates far in the past')
})
