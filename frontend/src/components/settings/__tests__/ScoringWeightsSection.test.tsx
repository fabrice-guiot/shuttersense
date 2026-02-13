/**
 * Tests for ScoringWeightsSection component.
 *
 * Issue #182: Calendar Conflict Visualization (Phase 6, US4)
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ScoringWeightsSection } from '../ScoringWeightsSection'
import type { ScoringWeightsResponse } from '@/contracts/api/conflict-api'

// ============================================================================
// Fixtures
// ============================================================================

const defaultSettings: ScoringWeightsResponse = {
  weight_venue_quality: 1.0,
  weight_organizer_reputation: 1.0,
  weight_performer_lineup: 1.0,
  weight_logistics_ease: 1.0,
  weight_readiness: 1.0,
}

const unevenSettings: ScoringWeightsResponse = {
  weight_venue_quality: 2.0,
  weight_organizer_reputation: 1.0,
  weight_performer_lineup: 1.0,
  weight_logistics_ease: 0.5,
  weight_readiness: 0.5,
}

// ============================================================================
// Tests
// ============================================================================

describe('ScoringWeightsSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders card with title and description', () => {
    render(
      <ScoringWeightsSection settings={defaultSettings} onUpdate={vi.fn()} />
    )
    expect(screen.getByText('Event Scoring Weights')).toBeInTheDocument()
    expect(screen.getByText('Adjust how each dimension contributes to the composite event score')).toBeInTheDocument()
  })

  test('renders loading skeletons when loading', () => {
    const { container } = render(
      <ScoringWeightsSection settings={null} loading={true} onUpdate={vi.fn()} />
    )
    const skeletons = container.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBe(5)
  })

  test('renders all weight rows with values', () => {
    render(
      <ScoringWeightsSection settings={defaultSettings} onUpdate={vi.fn()} />
    )
    expect(screen.getByText('Venue Quality')).toBeInTheDocument()
    expect(screen.getByText('Organizer Reputation')).toBeInTheDocument()
    expect(screen.getByText('Performer Lineup')).toBeInTheDocument()
    expect(screen.getByText('Logistics Ease')).toBeInTheDocument()
    expect(screen.getByText('Readiness')).toBeInTheDocument()
  })

  test('shows equal percentage shares for equal weights', () => {
    render(
      <ScoringWeightsSection settings={defaultSettings} onUpdate={vi.fn()} />
    )
    // All weights are 1.0, total is 5.0, each is 20%
    const shares = screen.getAllByText('20%')
    expect(shares).toHaveLength(5)
  })

  test('shows correct percentage shares for uneven weights', () => {
    render(
      <ScoringWeightsSection settings={unevenSettings} onUpdate={vi.fn()} />
    )
    // Total = 5.0, venue=2.0→40%, org=1.0→20%, perf=1.0→20%, log=0.5→10%, ready=0.5→10%
    expect(screen.getByText('40%')).toBeInTheDocument()
    const twentyPercent = screen.getAllByText('20%')
    expect(twentyPercent).toHaveLength(2)
    const tenPercent = screen.getAllByText('10%')
    expect(tenPercent).toHaveLength(2)
  })

  test('shows fallback message when settings are null', () => {
    render(
      <ScoringWeightsSection settings={null} onUpdate={vi.fn()} />
    )
    expect(screen.getByText('Unable to load scoring weights')).toBeInTheDocument()
  })

  test('opens edit dialog when edit button is clicked', async () => {
    const user = userEvent.setup()
    render(
      <ScoringWeightsSection settings={defaultSettings} onUpdate={vi.fn()} />
    )

    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])

    expect(screen.getByText('Edit Venue Quality Weight')).toBeInTheDocument()
    expect(screen.getByLabelText('Weight')).toHaveValue(1)
  })

  test('calls onUpdate with correct payload when saving', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(
      <ScoringWeightsSection settings={defaultSettings} onUpdate={onUpdate} />
    )

    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])

    const input = screen.getByLabelText('Weight')
    await user.clear(input)
    await user.type(input, '2.5')

    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith({ weight_venue_quality: 2.5 })
    })
  })

  test('shows validation error for negative weight', async () => {
    const user = userEvent.setup()
    render(
      <ScoringWeightsSection settings={defaultSettings} onUpdate={vi.fn()} />
    )

    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])

    const input = screen.getByLabelText('Weight')
    await user.clear(input)
    await user.type(input, '-1')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(screen.getByText('Weight cannot be negative')).toBeInTheDocument()
  })

  test('shows validation error when weight exceeds max', async () => {
    const user = userEvent.setup()
    render(
      <ScoringWeightsSection settings={defaultSettings} onUpdate={vi.fn()} />
    )

    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])

    const input = screen.getByLabelText('Weight')
    await user.clear(input)
    await user.type(input, '15')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(screen.getByText('Weight cannot exceed 10')).toBeInTheDocument()
  })

  test('closes dialog on cancel', async () => {
    const user = userEvent.setup()
    render(
      <ScoringWeightsSection settings={defaultSettings} onUpdate={vi.fn()} />
    )

    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])
    expect(screen.getByText('Edit Venue Quality Weight')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    await waitFor(() => {
      expect(screen.queryByText('Edit Venue Quality Weight')).not.toBeInTheDocument()
    })
  })

  test('shows API error when update fails', async () => {
    const onUpdate = vi.fn().mockRejectedValue(new Error('Network error'))
    const user = userEvent.setup()
    render(
      <ScoringWeightsSection settings={defaultSettings} onUpdate={onUpdate} />
    )

    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])

    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  test('displays weight descriptions', () => {
    render(
      <ScoringWeightsSection settings={defaultSettings} onUpdate={vi.fn()} />
    )
    expect(screen.getByText('Weight for location/venue rating in the composite score')).toBeInTheDocument()
    expect(screen.getByText('Weight for event readiness status in the composite score')).toBeInTheDocument()
  })
})
