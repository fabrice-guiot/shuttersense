/**
 * Tests for DimensionMicroBar component.
 *
 * Issue #182: Calendar Conflict Visualization (Phase 8, US6)
 * Issue #208: Normalize DimensionMicroBar Segment Sizes
 */

import { describe, test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DimensionMicroBar } from '../DimensionMicroBar'
import type { EventScores, ScoringWeightsResponse } from '@/contracts/api/conflict-api'

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

function makeWeights(overrides: Partial<ScoringWeightsResponse> = {}): ScoringWeightsResponse {
  return {
    weight_venue_quality: 20,
    weight_organizer_reputation: 20,
    weight_performer_lineup: 20,
    weight_logistics_ease: 20,
    weight_readiness: 20,
    ...overrides,
  }
}

// ============================================================================
// Tests
// ============================================================================

describe('DimensionMicroBar', () => {
  test('renders 5 outer segments (one per dimension)', () => {
    const { container } = render(<DimensionMicroBar scores={makeScores()} />)
    const bar = container.querySelector('[role="img"]')
    expect(bar).toBeInTheDocument()
    expect(bar?.children).toHaveLength(5)
  })

  test('no weights prop → equal 20% segments', () => {
    const { container } = render(<DimensionMicroBar scores={makeScores()} />)
    const segments = container.querySelectorAll('[role="img"] > div')
    segments.forEach(seg => {
      expect(seg).toHaveStyle({ width: '20%' })
    })
  })

  test('equal weights → each outer segment is 20% wide', () => {
    const { container } = render(
      <DimensionMicroBar scores={makeScores()} weights={makeWeights()} />,
    )
    const segments = container.querySelectorAll('[role="img"] > div')
    segments.forEach(seg => {
      expect(seg).toHaveStyle({ width: '20%' })
    })
  })

  test('unequal weights → segment widths reflect weight proportions', () => {
    const weights = makeWeights({
      weight_venue_quality: 40,
      weight_organizer_reputation: 10,
      weight_performer_lineup: 20,
      weight_logistics_ease: 20,
      weight_readiness: 10,
    })
    const { container } = render(
      <DimensionMicroBar scores={makeScores()} weights={weights} />,
    )
    const segments = container.querySelectorAll('[role="img"] > div')
    // total = 100, so percentages match directly
    expect(segments[0]).toHaveStyle({ width: '40%' })
    expect(segments[1]).toHaveStyle({ width: '10%' })
    expect(segments[2]).toHaveStyle({ width: '20%' })
    expect(segments[3]).toHaveStyle({ width: '20%' })
    expect(segments[4]).toHaveStyle({ width: '10%' })
  })

  test('inner fill width matches score percentage', () => {
    const scores = makeScores({ venue_quality: 80, organizer_reputation: 30 })
    const { container } = render(
      <DimensionMicroBar scores={scores} weights={makeWeights()} />,
    )
    const fills = container.querySelectorAll('[role="img"] > div > div')
    expect(fills[0]).toHaveStyle({ width: '80%' })
    expect(fills[1]).toHaveStyle({ width: '30%' })
  })

  test('zero score → fill is 0%', () => {
    const scores = makeScores({ venue_quality: 0 })
    const { container } = render(
      <DimensionMicroBar scores={scores} weights={makeWeights()} />,
    )
    const fills = container.querySelectorAll('[role="img"] > div > div')
    expect(fills[0]).toHaveStyle({ width: '0%' })
  })

  test('score > 100 is clamped to 100%', () => {
    const scores = makeScores({ venue_quality: 150 })
    const { container } = render(
      <DimensionMicroBar scores={scores} weights={makeWeights()} />,
    )
    const fills = container.querySelectorAll('[role="img"] > div > div')
    expect(fills[0]).toHaveStyle({ width: '100%' })
  })

  test('all scores zero → outer segments still show, fills are 0%', () => {
    const scores = makeScores({
      venue_quality: 0,
      organizer_reputation: 0,
      performer_lineup: 0,
      logistics_ease: 0,
      readiness: 0,
    })
    const { container } = render(
      <DimensionMicroBar scores={scores} weights={makeWeights()} />,
    )
    const segments = container.querySelectorAll('[role="img"] > div')
    // Outer segments still 20% each (weight-based, not score-based)
    segments.forEach(seg => {
      expect(seg).toHaveStyle({ width: '20%' })
    })
    const fills = container.querySelectorAll('[role="img"] > div > div')
    fills.forEach(fill => {
      expect(fill).toHaveStyle({ width: '0%' })
    })
  })

  test('has hidden-on-mobile class', () => {
    const { container } = render(<DimensionMicroBar scores={makeScores()} />)
    const bar = container.querySelector('[role="img"]')
    expect(bar?.className).toContain('hidden')
    expect(bar?.className).toContain('sm:flex')
  })

  test('tooltip shows dimension label, score, and weight percentage', () => {
    const { container } = render(
      <DimensionMicroBar scores={makeScores()} weights={makeWeights()} />,
    )
    const segments = container.querySelectorAll('[role="img"] > div')
    expect(segments[0]).toHaveAttribute('title', 'Venue: 50 (20% weight)')
    expect(segments[1]).toHaveAttribute('title', 'Organizer: 50 (20% weight)')
    expect(segments[2]).toHaveAttribute('title', 'Performers: 50 (20% weight)')
    expect(segments[3]).toHaveAttribute('title', 'Logistics: 50 (20% weight)')
    expect(segments[4]).toHaveAttribute('title', 'Readiness: 50 (20% weight)')
  })

  test('has accessible role and label', () => {
    render(<DimensionMicroBar scores={makeScores()} />)
    expect(screen.getByRole('img', { name: 'Score dimensions' })).toBeInTheDocument()
  })

  test('accepts custom className', () => {
    const { container } = render(
      <DimensionMicroBar scores={makeScores()} className="mt-2" />,
    )
    const bar = container.querySelector('[role="img"]')
    expect(bar?.className).toContain('mt-2')
  })
})
