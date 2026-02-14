/**
 * Tests for DimensionMicroBar component.
 *
 * Issue #182: Calendar Conflict Visualization (Phase 8, US6)
 */

import { describe, test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DimensionMicroBar } from '../DimensionMicroBar'
import type { EventScores } from '@/contracts/api/conflict-api'

// ============================================================================
// Helpers
// ============================================================================

function makeScores(overrides: Partial<EventScores> = {}): EventScores {
  return {
    venue_quality: 50,
    organizer_reputation: 50,
    performer_lineup: 50,
    logistics_ease: 50,
    readiness: 50,
    composite: 50,
    ...overrides,
  }
}

// ============================================================================
// Tests
// ============================================================================

describe('DimensionMicroBar', () => {
  test('renders 5 segments', () => {
    const { container } = render(<DimensionMicroBar scores={makeScores()} />)
    const bar = container.querySelector('[role="img"]')
    expect(bar).toBeInTheDocument()
    // 5 child segments
    expect(bar?.children).toHaveLength(5)
  })

  test('segments have proportional widths for equal scores', () => {
    const { container } = render(<DimensionMicroBar scores={makeScores()} />)
    const segments = container.querySelectorAll('[role="img"] > div')
    // All equal → each should be 20%
    segments.forEach(seg => {
      expect(seg).toHaveStyle({ width: '20%' })
    })
  })

  test('segments reflect uneven score distribution', () => {
    const scores = makeScores({
      venue_quality: 100,
      organizer_reputation: 0,
      performer_lineup: 0,
      logistics_ease: 0,
      readiness: 0,
    })
    const { container } = render(<DimensionMicroBar scores={scores} />)
    const segments = container.querySelectorAll('[role="img"] > div')
    // venue_quality dominates at 100%
    expect(segments[0]).toHaveStyle({ width: '100%' })
    expect(segments[1]).toHaveStyle({ width: '0%' })
  })

  test('all scores zero renders equal segments', () => {
    const scores = makeScores({
      venue_quality: 0,
      organizer_reputation: 0,
      performer_lineup: 0,
      logistics_ease: 0,
      readiness: 0,
    })
    const { container } = render(<DimensionMicroBar scores={scores} />)
    const segments = container.querySelectorAll('[role="img"] > div')
    // Fallback: each gets 20%
    segments.forEach(seg => {
      expect(seg).toHaveStyle({ width: '20%' })
    })
  })

  test('all scores 100 renders equal segments', () => {
    const scores = makeScores({
      venue_quality: 100,
      organizer_reputation: 100,
      performer_lineup: 100,
      logistics_ease: 100,
      readiness: 100,
    })
    const { container } = render(<DimensionMicroBar scores={scores} />)
    const segments = container.querySelectorAll('[role="img"] > div')
    segments.forEach(seg => {
      expect(seg).toHaveStyle({ width: '20%' })
    })
  })

  test('has hidden-on-mobile class', () => {
    const { container } = render(<DimensionMicroBar scores={makeScores()} />)
    const bar = container.querySelector('[role="img"]')
    expect(bar?.className).toContain('hidden')
    expect(bar?.className).toContain('sm:flex')
  })

  test('shows dimension labels in segment titles', () => {
    const { container } = render(<DimensionMicroBar scores={makeScores()} />)
    const segments = container.querySelectorAll('[role="img"] > div')
    expect(segments[0]).toHaveAttribute('title', 'Venue: 50')
    expect(segments[1]).toHaveAttribute('title', 'Organizer: 50')
    expect(segments[2]).toHaveAttribute('title', 'Performers: 50')
    expect(segments[3]).toHaveAttribute('title', 'Logistics: 50')
    expect(segments[4]).toHaveAttribute('title', 'Readiness: 50')
  })

  test('has accessible role and label', () => {
    render(<DimensionMicroBar scores={makeScores()} />)
    expect(screen.getByRole('img', { name: 'Score dimensions' })).toBeInTheDocument()
  })

  test('accepts custom className', () => {
    const { container } = render(
      <DimensionMicroBar scores={makeScores()} className="mt-2" />
    )
    const bar = container.querySelector('[role="img"]')
    expect(bar?.className).toContain('mt-2')
  })
})
