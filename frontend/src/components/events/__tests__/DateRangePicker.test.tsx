/**
 * Tests for DateRangePicker component.
 *
 * Issue #182: Calendar Conflict Visualization (Phase 7, US5)
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DateRangePicker } from '../DateRangePicker'
import type { RangePreset, DateRange } from '@/hooks/useDateRange'

// Mock DatePicker so we can test DateRangePicker in isolation
vi.mock('@/components/ui/date-picker', () => ({
  DatePicker: ({ value, onChange, placeholder }: {
    value?: string
    onChange?: (v: string | undefined) => void
    placeholder?: string
  }) => (
    <input
      aria-label={placeholder}
      value={value ?? ''}
      onChange={e => onChange?.(e.target.value || undefined)}
    />
  ),
}))

// ============================================================================
// Helpers
// ============================================================================

function renderPicker(overrides: Partial<{
  preset: RangePreset
  range: DateRange
  customStart: string
  customEnd: string
}> = {}) {
  const props = {
    preset: 'next_30d' as RangePreset,
    range: { startDate: '2026-06-15', endDate: '2026-07-15' },
    customStart: '',
    customEnd: '',
    onPresetChange: vi.fn(),
    onCustomRangeChange: vi.fn(),
    ...overrides,
  }
  const result = render(<DateRangePicker {...props} />)
  return { ...result, props }
}

// ============================================================================
// Tests
// ============================================================================

describe('DateRangePicker', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders with default preset label', () => {
    renderPicker()
    expect(screen.getByText('Next 30 days')).toBeInTheDocument()
  })

  test('shows localized date range summary for non-custom preset', () => {
    renderPicker()
    expect(screen.getByText('June 15th, 2026 — July 15th, 2026')).toBeInTheDocument()
  })

  test('renders all preset options when dropdown is opened', async () => {
    const user = userEvent.setup()
    renderPicker()

    // Open the select
    await user.click(screen.getByRole('combobox'))

    // Rolling presets
    expect(screen.getByRole('option', { name: 'Next 30 days' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Next 60 days' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Next 90 days' })).toBeInTheDocument()

    // Monthly presets
    expect(screen.getByRole('option', { name: 'Next 1 month' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Next 2 months' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Next 3 months' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Next 6 months' })).toBeInTheDocument()

    // Custom option
    expect(screen.getByRole('option', { name: 'Custom range' })).toBeInTheDocument()
  })

  test('no "All" option in dropdown', async () => {
    const user = userEvent.setup()
    renderPicker()

    await user.click(screen.getByRole('combobox'))

    expect(screen.queryByRole('option', { name: /All/i })).not.toBeInTheDocument()
  })

  test('shows group labels in dropdown', async () => {
    const user = userEvent.setup()
    renderPicker()

    await user.click(screen.getByRole('combobox'))

    expect(screen.getByText('Rolling')).toBeInTheDocument()
    expect(screen.getByText('Monthly')).toBeInTheDocument()
  })

  test('calls onPresetChange when selecting a preset', async () => {
    const user = userEvent.setup()
    const { props } = renderPicker()

    await user.click(screen.getByRole('combobox'))
    await user.click(screen.getByRole('option', { name: 'Next 60 days' }))

    expect(props.onPresetChange).toHaveBeenCalledWith('next_60d')
  })

  test('shows date pickers when custom preset is selected', () => {
    renderPicker({
      preset: 'custom',
      customStart: '2026-07-01',
      customEnd: '2026-12-31',
    })

    const fromPicker = screen.getByLabelText('Start date')
    const toPicker = screen.getByLabelText('End date')
    expect(fromPicker).toHaveValue('2026-07-01')
    expect(toPicker).toHaveValue('2026-12-31')
  })

  test('hides date range summary when custom preset is active', () => {
    renderPicker({
      preset: 'custom',
      range: { startDate: '2026-07-01', endDate: '2026-12-31' },
      customStart: '2026-07-01',
      customEnd: '2026-12-31',
    })

    // Should not show the localized date range summary
    expect(screen.queryByText(/July 1st, 2026 —/)).not.toBeInTheDocument()
  })

  test('calls onCustomRangeChange when start date changes', () => {
    const { props } = renderPicker({
      preset: 'custom',
      customStart: '2026-07-01',
      customEnd: '2026-12-31',
    })

    const fromPicker = screen.getByLabelText('Start date')
    fireEvent.change(fromPicker, { target: { value: '2026-08-01' } })

    expect(props.onCustomRangeChange).toHaveBeenCalledWith('2026-08-01', '2026-12-31')
  })

  test('calls onCustomRangeChange when end date changes', () => {
    const { props } = renderPicker({
      preset: 'custom',
      customStart: '2026-07-01',
      customEnd: '2026-12-31',
    })

    const toPicker = screen.getByLabelText('End date')
    fireEvent.change(toPicker, { target: { value: '2026-09-30' } })

    expect(props.onCustomRangeChange).toHaveBeenCalledWith('2026-07-01', '2026-09-30')
  })

  test('renders Date Range label', () => {
    renderPicker()
    expect(screen.getByText('Date Range')).toBeInTheDocument()
  })

  test('shows From and To labels when custom preset is active', () => {
    renderPicker({
      preset: 'custom',
      customStart: '2026-07-01',
      customEnd: '2026-12-31',
    })

    expect(screen.getByText('From')).toBeInTheDocument()
    expect(screen.getByText('To')).toBeInTheDocument()
  })
})
