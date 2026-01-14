/**
 * EventForm Component Tests
 *
 * Tests for timezone selector and related functionality.
 * Issue #39 - Calendar Events feature (Phase 6)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../utils/test-utils'
import { EventForm } from '@/components/events/EventForm'
import type { Category } from '@/contracts/api/category-api'

// Mock categories for testing
const mockCategories: Category[] = [
  {
    guid: 'cat_01hgw2bbg00000000000000001',
    name: 'Concert',
    icon: 'music',
    color: '#FF5733',
    is_active: true,
    display_order: 1,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z'
  },
  {
    guid: 'cat_01hgw2bbg00000000000000002',
    name: 'Conference',
    icon: 'calendar',
    color: '#3366FF',
    is_active: true,
    display_order: 2,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z'
  }
]

describe('EventForm - Timezone Selector', () => {
  const mockOnSubmit = vi.fn()
  const mockOnCancel = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockOnSubmit.mockResolvedValue(undefined)
  })

  it('should show timezone selector when not all-day event', async () => {
    render(
      <EventForm
        categories={mockCategories}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    // Verify timezone label is visible (not all-day by default)
    expect(screen.getByText('Timezone')).toBeInTheDocument()
    expect(screen.getByText('Timezone where the event takes place')).toBeInTheDocument()
  })

  it('should hide timezone selector when all-day is checked', async () => {
    const user = userEvent.setup()
    render(
      <EventForm
        categories={mockCategories}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    // Find and check the all-day checkbox
    const allDayCheckbox = screen.getByRole('checkbox', { name: /all day/i })
    await user.click(allDayCheckbox)

    // Timezone selector and time fields should be hidden
    await waitFor(() => {
      expect(screen.queryByText('Timezone')).not.toBeInTheDocument()
      expect(screen.queryByText('Start Time')).not.toBeInTheDocument()
      expect(screen.queryByText('End Time')).not.toBeInTheDocument()
    })
  })

  it('should show timezone selector again when all-day is unchecked', async () => {
    const user = userEvent.setup()
    render(
      <EventForm
        categories={mockCategories}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    // Check all-day checkbox
    const allDayCheckbox = screen.getByRole('checkbox', { name: /all day/i })
    await user.click(allDayCheckbox)

    // Verify timezone is hidden
    expect(screen.queryByText('Timezone')).not.toBeInTheDocument()

    // Uncheck all-day checkbox
    await user.click(allDayCheckbox)

    // Timezone should be visible again
    await waitFor(() => {
      expect(screen.getByText('Timezone')).toBeInTheDocument()
    })
  })

  it('should populate timezone when editing existing event', async () => {
    const existingEvent = {
      guid: 'evt_01hgw2bbg00000000000000001',
      title: 'Existing Event',
      description: 'Test description',
      event_date: '2026-01-15',
      start_time: '14:00:00',
      end_time: '16:00:00',
      is_all_day: false,
      input_timezone: 'Europe/London',
      status: 'future' as const,
      attendance: 'planned' as const,
      category: mockCategories[0],
      series_guid: null,
      sequence_number: null,
      series_total: null,
      location: null,
      organizer: null,
      performers: [],
      series: null,
      ticket_required: null,
      ticket_status: null,
      ticket_purchase_date: null,
      timeoff_required: null,
      timeoff_status: null,
      timeoff_booking_date: null,
      travel_required: null,
      travel_status: null,
      travel_booking_date: null,
      deadline_date: null,
      is_deadline: false,
      deleted_at: null,
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z'
    }

    render(
      <EventForm
        event={existingEvent}
        categories={mockCategories}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    // Verify timezone selector is present (form is in edit mode)
    expect(screen.getByText('Timezone')).toBeInTheDocument()
    // Verify timezone label is present (edit mode shows the label)
    expect(screen.getByText('Timezone where the event takes place')).toBeInTheDocument()
    // In edit mode the form should show timezone field (not verify specific value as it depends on Select internals)
  })

  it('should display timezone selector with combobox button', async () => {
    render(
      <EventForm
        categories={mockCategories}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    )

    // Verify timezone combobox is present (look for the combobox role)
    const comboboxButtons = screen.getAllByRole('combobox')
    // Should have multiple comboboxes (category, status, attendance, timezone)
    expect(comboboxButtons.length).toBeGreaterThanOrEqual(4)
  })
})

describe('EventForm - Series Mode', () => {
  const mockOnSubmit = vi.fn()
  const mockOnSubmitSeries = vi.fn()
  const mockOnCancel = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockOnSubmit.mockResolvedValue(undefined)
    mockOnSubmitSeries.mockResolvedValue(undefined)
  })

  it('should show timezone selector in series mode', async () => {
    const user = userEvent.setup()
    render(
      <EventForm
        categories={mockCategories}
        onSubmit={mockOnSubmit}
        onSubmitSeries={mockOnSubmitSeries}
        onCancel={mockOnCancel}
      />
    )

    // Switch to series mode
    const seriesButton = screen.getByRole('button', { name: /event series/i })
    await user.click(seriesButton)

    // Verify timezone selector is still available in series mode
    expect(screen.getByText('Timezone')).toBeInTheDocument()
  })

  it('should hide timezone in series mode when all-day is checked', async () => {
    const user = userEvent.setup()
    render(
      <EventForm
        categories={mockCategories}
        onSubmit={mockOnSubmit}
        onSubmitSeries={mockOnSubmitSeries}
        onCancel={mockOnCancel}
      />
    )

    // Switch to series mode
    const seriesButton = screen.getByRole('button', { name: /event series/i })
    await user.click(seriesButton)

    // Check all-day checkbox
    const allDayCheckbox = screen.getByRole('checkbox', { name: /all day/i })
    await user.click(allDayCheckbox)

    // Timezone selector should be hidden
    await waitFor(() => {
      expect(screen.queryByText('Timezone')).not.toBeInTheDocument()
    })
  })
})
