/**
 * Tests for ConflictRulesSection component.
 *
 * Issue #182: Calendar Conflict Visualization (Phase 6, US4)
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConflictRulesSection } from '../ConflictRulesSection'
import type { ConflictRulesResponse } from '@/contracts/api/conflict-api'

// ============================================================================
// Fixtures
// ============================================================================

const defaultSettings: ConflictRulesResponse = {
  distance_threshold_miles: 100,
  consecutive_window_days: 3,
  travel_buffer_days: 1,
  colocation_radius_miles: 5,
  performer_ceiling: 10,
}

// ============================================================================
// Tests
// ============================================================================

describe('ConflictRulesSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders card with title and description', () => {
    render(
      <ConflictRulesSection settings={defaultSettings} onUpdate={vi.fn()} />
    )
    expect(screen.getByText('Conflict Detection Rules')).toBeInTheDocument()
    expect(screen.getByText('Configure thresholds and parameters for conflict detection')).toBeInTheDocument()
  })

  test('renders loading skeletons when loading', () => {
    const { container } = render(
      <ConflictRulesSection settings={null} loading={true} onUpdate={vi.fn()} />
    )
    const skeletons = container.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBe(5)
  })

  test('renders all rule rows with values', () => {
    render(
      <ConflictRulesSection settings={defaultSettings} onUpdate={vi.fn()} />
    )
    expect(screen.getByText('Distance Threshold')).toBeInTheDocument()
    expect(screen.getByText('100 miles')).toBeInTheDocument()
    expect(screen.getByText('Consecutive Window')).toBeInTheDocument()
    expect(screen.getByText('3 days')).toBeInTheDocument()
    expect(screen.getByText('Travel Buffer')).toBeInTheDocument()
    expect(screen.getByText('1 day')).toBeInTheDocument()
    expect(screen.getByText('Co-location Radius')).toBeInTheDocument()
    expect(screen.getByText('5 miles')).toBeInTheDocument()
    expect(screen.getByText('Performer Ceiling')).toBeInTheDocument()
    expect(screen.getByText('10 performers')).toBeInTheDocument()
  })

  test('shows fallback message when settings are null', () => {
    render(
      <ConflictRulesSection settings={null} onUpdate={vi.fn()} />
    )
    expect(screen.getByText('Unable to load conflict rules')).toBeInTheDocument()
  })

  test('opens edit dialog when edit button is clicked', async () => {
    const user = userEvent.setup()
    render(
      <ConflictRulesSection settings={defaultSettings} onUpdate={vi.fn()} />
    )

    // Click the first edit button (Distance Threshold)
    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])

    expect(screen.getByText('Edit Distance Threshold')).toBeInTheDocument()
    expect(screen.getByLabelText('Value (miles)')).toHaveValue(100)
  })

  test('calls onUpdate with correct payload when saving', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(
      <ConflictRulesSection settings={defaultSettings} onUpdate={onUpdate} />
    )

    // Click edit button for Distance Threshold
    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])

    // Change the value
    const input = screen.getByLabelText('Value (miles)')
    await user.clear(input)
    await user.type(input, '150')

    // Save
    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith({ distance_threshold_miles: 150 })
    })
  })

  test('shows validation error for invalid number', async () => {
    const user = userEvent.setup()
    render(
      <ConflictRulesSection settings={defaultSettings} onUpdate={vi.fn()} />
    )

    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])

    const input = screen.getByLabelText('Value (miles)')
    await user.clear(input)
    await user.type(input, 'abc')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(screen.getByText('Please enter a valid number')).toBeInTheDocument()
  })

  test('shows validation error when value exceeds max', async () => {
    const user = userEvent.setup()
    render(
      <ConflictRulesSection settings={defaultSettings} onUpdate={vi.fn()} />
    )

    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])

    const input = screen.getByLabelText('Value (miles)')
    await user.clear(input)
    await user.type(input, '999')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(screen.getByText('Maximum value is 500')).toBeInTheDocument()
  })

  test('shows validation error when value is below min', async () => {
    const user = userEvent.setup()
    render(
      <ConflictRulesSection settings={defaultSettings} onUpdate={vi.fn()} />
    )

    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])

    const input = screen.getByLabelText('Value (miles)')
    await user.clear(input)
    await user.type(input, '0')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(screen.getByText('Minimum value is 1')).toBeInTheDocument()
  })

  test('closes dialog on cancel', async () => {
    const user = userEvent.setup()
    render(
      <ConflictRulesSection settings={defaultSettings} onUpdate={vi.fn()} />
    )

    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])
    expect(screen.getByText('Edit Distance Threshold')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    await waitFor(() => {
      expect(screen.queryByText('Edit Distance Threshold')).not.toBeInTheDocument()
    })
  })

  test('shows API error when update fails', async () => {
    const onUpdate = vi.fn().mockRejectedValue(new Error('Server error'))
    const user = userEvent.setup()
    render(
      <ConflictRulesSection settings={defaultSettings} onUpdate={onUpdate} />
    )

    const editButtons = screen.getAllByRole('button')
    await user.click(editButtons[0])

    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeInTheDocument()
    })
  })

  test('displays rule descriptions', () => {
    render(
      <ConflictRulesSection settings={defaultSettings} onUpdate={vi.fn()} />
    )
    expect(screen.getByText('Distance above which travel buffer rules apply between events')).toBeInTheDocument()
    expect(screen.getByText('Minimum days between distant events when at least one requires travel')).toBeInTheDocument()
  })
})
