/**
 * Tests for ConflictBadge component.
 *
 * Issue #182: Calendar Conflict Visualization (Phase 3, US1)
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConflictBadge } from '../ConflictBadge'
import type { ConflictBadgeProps } from '../ConflictBadge'
import type { ConflictType } from '@/contracts/api/conflict-api'

// ============================================================================
// Fixtures
// ============================================================================

const timeOverlapConflict: ConflictBadgeProps['conflicts'] = [
  {
    type: 'time_overlap' as ConflictType,
    otherEventTitle: 'Event B',
    detail: 'Events overlap from 11:00 to 12:00',
  },
]

const distanceConflict: ConflictBadgeProps['conflicts'] = [
  {
    type: 'distance' as ConflictType,
    otherEventTitle: 'LA Event',
    detail: '2,451 miles apart within 1 day',
  },
]

const multipleConflicts: ConflictBadgeProps['conflicts'] = [
  {
    type: 'time_overlap' as ConflictType,
    otherEventTitle: 'Event A',
    detail: 'Events overlap from 10:00 to 11:00',
  },
  {
    type: 'distance' as ConflictType,
    otherEventTitle: 'Event B',
    detail: '100 miles apart within 1 day',
  },
]

// ============================================================================
// Tests
// ============================================================================

describe('ConflictBadge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders nothing when conflicts array is empty', () => {
    const { container } = render(
      <ConflictBadge conflicts={[]} status="unresolved" />
    )
    expect(container.firstChild).toBeNull()
  })

  test('renders amber badge for unresolved time overlap conflict', () => {
    render(
      <ConflictBadge conflicts={timeOverlapConflict} status="unresolved" />
    )
    const badge = screen.getByRole('img')
    expect(badge).toBeInTheDocument()
    expect(badge.className).toContain('text-amber-600')
    expect(badge.className).toContain('bg-amber-500/15')
  })

  test('renders dashed gray badge for resolved conflict', () => {
    render(
      <ConflictBadge conflicts={timeOverlapConflict} status="resolved" />
    )
    const badge = screen.getByRole('img')
    expect(badge).toBeInTheDocument()
    expect(badge.className).toContain('text-muted-foreground')
    expect(badge.className).toContain('border-dashed')
  })

  test('includes conflict type and event name in aria-label', () => {
    render(
      <ConflictBadge conflicts={timeOverlapConflict} status="unresolved" />
    )
    const badge = screen.getByRole('img')
    expect(badge.getAttribute('aria-label')).toContain('Time overlap')
    expect(badge.getAttribute('aria-label')).toContain('Event B')
  })

  test('handles multiple conflict edges', () => {
    render(
      <ConflictBadge conflicts={multipleConflicts} status="unresolved" />
    )
    const badge = screen.getByRole('img')
    expect(badge.getAttribute('aria-label')).toContain('Time overlap with Event A')
    expect(badge.getAttribute('aria-label')).toContain('Distance conflict with Event B')
    // Shows count for multiple conflicts
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  test('renders distance conflict badge', () => {
    render(
      <ConflictBadge conflicts={distanceConflict} status="unresolved" />
    )
    const badge = screen.getByRole('img')
    expect(badge).toBeInTheDocument()
    expect(badge.getAttribute('aria-label')).toContain('Distance conflict')
    expect(badge.getAttribute('aria-label')).toContain('LA Event')
  })

  test('compact mode renders smaller badge', () => {
    render(
      <ConflictBadge
        conflicts={timeOverlapConflict}
        status="unresolved"
        compact
      />
    )
    const badge = screen.getByRole('img')
    expect(badge.className).toContain('h-4')
    expect(badge.className).toContain('w-4')
  })

  test('compact mode does not show count text', () => {
    render(
      <ConflictBadge
        conflicts={multipleConflicts}
        status="unresolved"
        compact
      />
    )
    // In compact mode, count text is not rendered even with multiple conflicts
    expect(screen.queryByText('2')).not.toBeInTheDocument()
  })

  test('partially_resolved uses amber styling (not resolved)', () => {
    render(
      <ConflictBadge
        conflicts={timeOverlapConflict}
        status="partially_resolved"
      />
    )
    const badge = screen.getByRole('img')
    expect(badge.className).toContain('text-amber-600')
    expect(badge.className).not.toContain('border-dashed')
  })
})
