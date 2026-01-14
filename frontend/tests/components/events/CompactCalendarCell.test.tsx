/**
 * CompactCalendarCell Component Tests
 *
 * Tests for mobile day cell with category badges.
 * Feature: 016-mobile-calendar-view (GitHub Issue #69)
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CompactCalendarCell } from '@/components/events/CompactCalendarCell'
import type { CategoryBadgeData } from '@/components/events/EventCalendar'

describe('CompactCalendarCell', () => {
  const mockDate = new Date(2026, 0, 15) // January 15, 2026
  const mockOnClick = vi.fn()
  const mockOnKeyDown = vi.fn()
  const mockOnFocus = vi.fn()

  const defaultBadges: CategoryBadgeData[] = [
    { categoryGuid: 'cat_1', name: 'Music', icon: 'music', color: '#3b82f6', count: 2 },
    { categoryGuid: 'cat_2', name: 'Sports', icon: 'trophy', color: '#10b981', count: 1 },
  ]

  const defaultProps = {
    date: mockDate,
    dayNumber: 15,
    isCurrentMonth: true,
    isToday: false,
    isFocused: false,
    badges: defaultBadges,
    overflowCount: 0,
    totalEventCount: 3,
    onClick: mockOnClick,
    onKeyDown: mockOnKeyDown,
    onFocus: mockOnFocus,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders day number', () => {
      render(<CompactCalendarCell {...defaultProps} />)

      expect(screen.getByText('15')).toBeInTheDocument()
    })

    it('renders category badges', () => {
      render(<CompactCalendarCell {...defaultProps} />)

      // Check for badge labels
      expect(screen.getByRole('img', { name: /2 music events/i })).toBeInTheDocument()
      expect(screen.getByRole('img', { name: /1 sports event/i })).toBeInTheDocument()
    })

    it('renders no badges when badges array is empty', () => {
      render(<CompactCalendarCell {...defaultProps} badges={[]} totalEventCount={0} />)

      expect(screen.queryByRole('list', { name: /event categories/i })).not.toBeInTheDocument()
    })

    it('renders overflow indicator when overflowCount > 0', () => {
      render(<CompactCalendarCell {...defaultProps} overflowCount={2} />)

      expect(screen.getByText('+2')).toBeInTheDocument()
    })

    it('does not render overflow indicator when overflowCount is 0', () => {
      render(<CompactCalendarCell {...defaultProps} overflowCount={0} />)

      expect(screen.queryByText(/^\+\d+$/)).not.toBeInTheDocument()
    })
  })

  describe('Day Styling', () => {
    it('highlights today with primary color', () => {
      render(<CompactCalendarCell {...defaultProps} isToday />)

      const dayNumber = screen.getByText('15')
      expect(dayNumber).toHaveClass('bg-primary', 'text-primary-foreground', 'rounded-full')
    })

    it('dims non-current month days', () => {
      render(<CompactCalendarCell {...defaultProps} isCurrentMonth={false} />)

      const cell = screen.getByRole('gridcell')
      expect(cell).toHaveClass('bg-muted/30', 'text-muted-foreground')
    })

    it('applies current month styling', () => {
      render(<CompactCalendarCell {...defaultProps} isCurrentMonth />)

      const cell = screen.getByRole('gridcell')
      expect(cell).not.toHaveClass('bg-muted/30')
    })
  })

  describe('Click Handler', () => {
    it('calls onClick with date when cell is clicked', () => {
      render(<CompactCalendarCell {...defaultProps} />)

      fireEvent.click(screen.getByRole('gridcell'))

      expect(mockOnClick).toHaveBeenCalledWith(mockDate)
      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('Keyboard Handler', () => {
    it('calls onKeyDown when key is pressed', () => {
      render(<CompactCalendarCell {...defaultProps} />)

      const cell = screen.getByRole('gridcell')
      fireEvent.keyDown(cell, { key: 'Enter' })

      expect(mockOnKeyDown).toHaveBeenCalledTimes(1)
    })
  })

  describe('Focus Management', () => {
    it('calls onFocus when cell receives focus', () => {
      render(<CompactCalendarCell {...defaultProps} />)

      fireEvent.focus(screen.getByRole('gridcell'))

      expect(mockOnFocus).toHaveBeenCalledTimes(1)
    })

    it('has correct tabIndex when not focused', () => {
      render(<CompactCalendarCell {...defaultProps} tabIndex={-1} />)

      expect(screen.getByRole('gridcell')).toHaveAttribute('tabIndex', '-1')
    })

    it('has correct tabIndex when focused', () => {
      render(<CompactCalendarCell {...defaultProps} tabIndex={0} isFocused />)

      expect(screen.getByRole('gridcell')).toHaveAttribute('tabIndex', '0')
    })
  })

  describe('Accessibility', () => {
    it('has role="gridcell"', () => {
      render(<CompactCalendarCell {...defaultProps} />)

      expect(screen.getByRole('gridcell')).toBeInTheDocument()
    })

    it('has correct aria-label with events', () => {
      render(<CompactCalendarCell {...defaultProps} />)

      const cell = screen.getByRole('gridcell')
      expect(cell).toHaveAttribute(
        'aria-label',
        expect.stringContaining('Thursday, January 15, 2026')
      )
      expect(cell).toHaveAttribute('aria-label', expect.stringContaining('3 events'))
      expect(cell).toHaveAttribute('aria-label', expect.stringContaining('2 Music'))
      expect(cell).toHaveAttribute('aria-label', expect.stringContaining('1 Sports'))
    })

    it('has correct aria-label with no events', () => {
      render(<CompactCalendarCell {...defaultProps} badges={[]} totalEventCount={0} />)

      const cell = screen.getByRole('gridcell')
      expect(cell).toHaveAttribute('aria-label', expect.stringContaining('No events'))
    })

    it('has correct aria-label with overflow categories', () => {
      render(<CompactCalendarCell {...defaultProps} overflowCount={3} />)

      const cell = screen.getByRole('gridcell')
      expect(cell).toHaveAttribute(
        'aria-label',
        expect.stringContaining('3 more categories')
      )
    })

    it('has aria-selected based on isFocused', () => {
      const { rerender } = render(<CompactCalendarCell {...defaultProps} isFocused={false} />)

      expect(screen.getByRole('gridcell')).toHaveAttribute('aria-selected', 'false')

      rerender(<CompactCalendarCell {...defaultProps} isFocused />)

      expect(screen.getByRole('gridcell')).toHaveAttribute('aria-selected', 'true')
    })
  })

  describe('Max Badges', () => {
    it('renders maximum 4 badges', () => {
      const manyBadges: CategoryBadgeData[] = [
        { categoryGuid: 'cat_1', name: 'Music', icon: 'music', color: '#3b82f6', count: 2 },
        { categoryGuid: 'cat_2', name: 'Sports', icon: 'trophy', color: '#10b981', count: 2 },
        { categoryGuid: 'cat_3', name: 'Theatre', icon: 'drama', color: '#f59e0b', count: 1 },
        { categoryGuid: 'cat_4', name: 'Food', icon: 'utensils', color: '#ef4444', count: 1 },
        { categoryGuid: 'cat_5', name: 'Travel', icon: 'plane', color: '#8b5cf6', count: 1 },
      ]

      render(
        <CompactCalendarCell
          {...defaultProps}
          badges={manyBadges}
          overflowCount={1}
          totalEventCount={7}
        />
      )

      // Should show 4 badges + overflow indicator
      const badgeList = screen.getByRole('list', { name: /event categories/i })
      const badges = badgeList.querySelectorAll('[role="listitem"]')
      expect(badges).toHaveLength(4)
      expect(screen.getByText('+1')).toBeInTheDocument()
    })
  })

  describe('Custom ClassName', () => {
    it('applies additional className', () => {
      render(<CompactCalendarCell {...defaultProps} className="custom-class" />)

      expect(screen.getByRole('gridcell')).toHaveClass('custom-class')
    })
  })
})
