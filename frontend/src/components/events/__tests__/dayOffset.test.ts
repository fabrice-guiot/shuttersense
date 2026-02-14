/**
 * Tests for dayOffsetLabel utility.
 *
 * Issue #182: Calendar Conflict Visualization
 */

import { describe, test, expect } from 'vitest'
import { dayOffsetLabel } from '../dayOffset'

describe('dayOffsetLabel', () => {
  test('returns null when dates match', () => {
    expect(dayOffsetLabel('2026-06-15', '2026-06-15')).toBeNull()
  })

  test('returns D+1 for next day', () => {
    expect(dayOffsetLabel('2026-06-16', '2026-06-15')).toBe('D+1')
  })

  test('returns D-1 for previous day', () => {
    expect(dayOffsetLabel('2026-06-14', '2026-06-15')).toBe('D-1')
  })

  test('returns D+3 for 3 days ahead', () => {
    expect(dayOffsetLabel('2026-06-18', '2026-06-15')).toBe('D+3')
  })

  test('returns D-2 for 2 days before', () => {
    expect(dayOffsetLabel('2026-06-13', '2026-06-15')).toBe('D-2')
  })

  test('handles month boundary', () => {
    expect(dayOffsetLabel('2026-07-01', '2026-06-30')).toBe('D+1')
    expect(dayOffsetLabel('2026-06-30', '2026-07-01')).toBe('D-1')
  })

  test('returns null when eventDate is null', () => {
    expect(dayOffsetLabel(null, '2026-06-15')).toBeNull()
  })

  test('returns null when refDate is null', () => {
    expect(dayOffsetLabel('2026-06-15', null)).toBeNull()
  })

  test('returns null when both are undefined', () => {
    expect(dayOffsetLabel(undefined, undefined)).toBeNull()
  })
})
