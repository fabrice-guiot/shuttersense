/**
 * EventCalendar Component Integration Tests
 *
 * Tests for calendar grid with responsive mobile/desktop rendering.
 * Feature: 016-mobile-calendar-view (GitHub Issue #69)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { EventCalendar } from '@/components/events/EventCalendar'
import type { Event } from '@/contracts/api/event-api'

// Mock matchMedia to simulate mobile/desktop viewports
const mockMatchMedia = (matches: boolean) => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

describe('EventCalendar', () => {
  const mockOnPreviousMonth = vi.fn()
  const mockOnNextMonth = vi.fn()
  const mockOnToday = vi.fn()
  const mockOnEventClick = vi.fn()
  const mockOnDayClick = vi.fn()

  const defaultProps = {
    events: [] as Event[],
    year: 2026,
    month: 1, // January
    onPreviousMonth: mockOnPreviousMonth,
    onNextMonth: mockOnNextMonth,
    onToday: mockOnToday,
    onEventClick: mockOnEventClick,
    onDayClick: mockOnDayClick,
  }

  const mockEvent: Event = {
    guid: 'evt_test123',
    title: 'Test Concert',
    event_date: '2026-01-15',
    status: 'confirmed',
    attendance: 'going',
    is_all_day: false,
    category: {
      guid: 'cat_music',
      name: 'Music',
      icon: 'music',
      color: '#3b82f6',
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Mobile Viewport (Compact Mode)', () => {
    beforeEach(() => {
      // Simulate mobile: matchMedia returns false for (min-width: 640px)
      mockMatchMedia(false)
    })

    it('renders compact calendar cells on mobile viewport', () => {
      render(<EventCalendar {...defaultProps} events={[mockEvent]} />)

      // Compact view should show day numbers without event cards
      // Look for a cell with category badge structure
      const grid = screen.getByRole('grid')
      const cells = within(grid).getAllByRole('gridcell')

      // Should have 42 cells (6 rows × 7 days)
      expect(cells.length).toBe(42)

      // Day 15 should have an event and display category badge
      // Find the cell containing day 15 with events
      const day15Cell = cells.find((cell) => cell.textContent?.includes('15'))
      expect(day15Cell).toBeDefined()
    })

    it('calls onDayClick when compact cell is clicked', () => {
      render(<EventCalendar {...defaultProps} events={[mockEvent]} />)

      const grid = screen.getByRole('grid')
      const cells = within(grid).getAllByRole('gridcell')

      // Find and click the cell for January 15, 2026
      // The aria-label should contain the date
      const day15Cell = cells.find((cell) =>
        cell.getAttribute('aria-label')?.includes('January 15')
      )
      expect(day15Cell).toBeDefined()

      fireEvent.click(day15Cell!)

      expect(mockOnDayClick).toHaveBeenCalledTimes(1)
      // Verify the date passed is correct (January 15, 2026)
      const calledDate = mockOnDayClick.mock.calls[0][0]
      expect(calledDate.getDate()).toBe(15)
      expect(calledDate.getMonth()).toBe(0) // January
      expect(calledDate.getFullYear()).toBe(2026)
    })

    it('calls onDayClick for empty day (opens create dialog)', () => {
      render(<EventCalendar {...defaultProps} events={[]} />)

      const grid = screen.getByRole('grid')
      const cells = within(grid).getAllByRole('gridcell')

      // Click on an empty day (January 20)
      const day20Cell = cells.find((cell) =>
        cell.getAttribute('aria-label')?.includes('January 20')
      )
      expect(day20Cell).toBeDefined()

      fireEvent.click(day20Cell!)

      expect(mockOnDayClick).toHaveBeenCalledTimes(1)
      const calledDate = mockOnDayClick.mock.calls[0][0]
      expect(calledDate.getDate()).toBe(20)
    })

    it('handles keyboard Enter to select day', () => {
      render(<EventCalendar {...defaultProps} events={[mockEvent]} />)

      const grid = screen.getByRole('grid')
      const cells = within(grid).getAllByRole('gridcell')

      const day15Cell = cells.find((cell) =>
        cell.getAttribute('aria-label')?.includes('January 15')
      )
      expect(day15Cell).toBeDefined()

      // Focus the cell and press Enter
      day15Cell!.focus()
      fireEvent.keyDown(day15Cell!, { key: 'Enter' })

      expect(mockOnDayClick).toHaveBeenCalledTimes(1)
    })

    it('handles keyboard Space to select day', () => {
      render(<EventCalendar {...defaultProps} events={[mockEvent]} />)

      const grid = screen.getByRole('grid')
      const cells = within(grid).getAllByRole('gridcell')

      const day15Cell = cells.find((cell) =>
        cell.getAttribute('aria-label')?.includes('January 15')
      )
      expect(day15Cell).toBeDefined()

      // Focus the cell and press Space
      day15Cell!.focus()
      fireEvent.keyDown(day15Cell!, { key: ' ' })

      expect(mockOnDayClick).toHaveBeenCalledTimes(1)
    })

    it('displays category badges for days with events', () => {
      const eventsOnSameDay: Event[] = [
        mockEvent,
        {
          ...mockEvent,
          guid: 'evt_test456',
          title: 'Sports Game',
          category: {
            guid: 'cat_sports',
            name: 'Sports',
            icon: 'trophy',
            color: '#10b981',
          },
        },
      ]

      render(<EventCalendar {...defaultProps} events={eventsOnSameDay} />)

      // Find the cell for January 15 and check it has category badges
      const day15Cell = screen
        .getAllByRole('gridcell')
        .find((cell) => cell.getAttribute('aria-label')?.includes('January 15'))

      expect(day15Cell).toBeDefined()
      // The aria-label should mention the event count
      expect(day15Cell!.getAttribute('aria-label')).toContain('2 events')
    })
  })

  describe('Desktop Viewport (Standard Mode)', () => {
    beforeEach(() => {
      // Simulate desktop: matchMedia returns true for (min-width: 640px)
      mockMatchMedia(true)
    })

    it('renders standard calendar cells on desktop viewport', () => {
      render(<EventCalendar {...defaultProps} events={[mockEvent]} />)

      // Desktop view should show event cards, not just badges
      // The event title should be visible
      expect(screen.getByText('Test Concert')).toBeInTheDocument()
    })

    it('calls onEventClick when event card is clicked on desktop', () => {
      render(<EventCalendar {...defaultProps} events={[mockEvent]} />)

      // EventCard renders as a button with role="listitem"
      const eventCard = screen.getByRole('listitem', { name: /test concert/i })
      expect(eventCard).toBeInTheDocument()

      fireEvent.click(eventCard)

      expect(mockOnEventClick).toHaveBeenCalledTimes(1)
      expect(mockOnEventClick).toHaveBeenCalledWith(mockEvent)
    })
  })

  describe('Calendar Navigation', () => {
    beforeEach(() => {
      mockMatchMedia(false) // Mobile
    })

    it('calls onPreviousMonth when previous button is clicked', () => {
      render(<EventCalendar {...defaultProps} />)

      const prevButton = screen.getByRole('button', { name: /previous month/i })
      fireEvent.click(prevButton)

      expect(mockOnPreviousMonth).toHaveBeenCalledTimes(1)
    })

    it('calls onNextMonth when next button is clicked', () => {
      render(<EventCalendar {...defaultProps} />)

      const nextButton = screen.getByRole('button', { name: /next month/i })
      fireEvent.click(nextButton)

      expect(mockOnNextMonth).toHaveBeenCalledTimes(1)
    })

    it('calls onToday when today button is clicked', () => {
      render(<EventCalendar {...defaultProps} />)

      const todayButton = screen.getByRole('button', { name: /go to today/i })
      fireEvent.click(todayButton)

      expect(mockOnToday).toHaveBeenCalledTimes(1)
    })

    it('displays correct month and year', () => {
      render(<EventCalendar {...defaultProps} />)

      expect(screen.getByText('January 2026')).toBeInTheDocument()
    })

    it('keyboard PageDown navigates to next month', () => {
      render(<EventCalendar {...defaultProps} />)

      const grid = screen.getByRole('grid')
      const cells = within(grid).getAllByRole('gridcell')
      const firstCurrentMonthCell = cells.find(
        (cell) => !cell.classList.contains('bg-muted/30')
      )

      firstCurrentMonthCell!.focus()
      fireEvent.keyDown(firstCurrentMonthCell!, { key: 'PageDown' })

      expect(mockOnNextMonth).toHaveBeenCalledTimes(1)
    })

    it('keyboard PageUp navigates to previous month', () => {
      render(<EventCalendar {...defaultProps} />)

      const grid = screen.getByRole('grid')
      const cells = within(grid).getAllByRole('gridcell')
      const firstCurrentMonthCell = cells.find(
        (cell) => !cell.classList.contains('bg-muted/30')
      )

      firstCurrentMonthCell!.focus()
      fireEvent.keyDown(firstCurrentMonthCell!, { key: 'PageUp' })

      expect(mockOnPreviousMonth).toHaveBeenCalledTimes(1)
    })
  })

  describe('Accessibility', () => {
    beforeEach(() => {
      mockMatchMedia(false) // Mobile
    })

    it('has proper ARIA labels for calendar grid', () => {
      render(<EventCalendar {...defaultProps} />)

      const grid = screen.getByRole('grid')
      expect(grid).toHaveAttribute('aria-label', 'Calendar for January 2026')
    })

    it('provides screen reader instructions', () => {
      render(<EventCalendar {...defaultProps} />)

      expect(
        screen.getByText(/use arrow keys to navigate dates/i)
      ).toBeInTheDocument()
    })

    it('cells have descriptive aria-labels', () => {
      render(<EventCalendar {...defaultProps} events={[mockEvent]} />)

      const day15Cell = screen
        .getAllByRole('gridcell')
        .find((cell) => cell.getAttribute('aria-label')?.includes('January 15'))

      expect(day15Cell).toBeDefined()
      expect(day15Cell!.getAttribute('aria-label')).toContain('Thursday')
      expect(day15Cell!.getAttribute('aria-label')).toContain('2026')
    })
  })

  describe('Touch Targets (Mobile Navigation)', () => {
    beforeEach(() => {
      mockMatchMedia(false) // Mobile viewport
    })

    it('navigation buttons have touch-friendly size classes on mobile (44x44px minimum)', () => {
      render(<EventCalendar {...defaultProps} />)

      const prevButton = screen.getByRole('button', { name: /previous month/i })
      const nextButton = screen.getByRole('button', { name: /next month/i })
      const todayButton = screen.getByRole('button', { name: /go to today/i })

      // Buttons should have h-11 w-11 classes (44x44px) for mobile touch targets
      expect(prevButton).toHaveClass('h-11', 'w-11')
      expect(nextButton).toHaveClass('h-11', 'w-11')
      expect(todayButton).toHaveClass('h-11', 'w-11')
    })

    it('month/year title is visible and readable on mobile', () => {
      render(<EventCalendar {...defaultProps} />)

      const title = screen.getByRole('heading', { level: 2 })
      expect(title).toHaveTextContent('January 2026')
      // Title should have responsive text size (text-lg on mobile)
      expect(title).toHaveClass('text-lg')
    })

    it('navigation buttons remain functional after multiple clicks', () => {
      render(<EventCalendar {...defaultProps} />)

      const prevButton = screen.getByRole('button', { name: /previous month/i })
      const nextButton = screen.getByRole('button', { name: /next month/i })

      // Simulate rapid navigation
      fireEvent.click(nextButton)
      fireEvent.click(nextButton)
      fireEvent.click(prevButton)

      expect(mockOnNextMonth).toHaveBeenCalledTimes(2)
      expect(mockOnPreviousMonth).toHaveBeenCalledTimes(1)
    })
  })

  describe('Loading State', () => {
    beforeEach(() => {
      mockMatchMedia(false) // Mobile
    })

    it('shows loading indicator when loading prop is true', () => {
      render(<EventCalendar {...defaultProps} loading={true} />)

      expect(screen.getByRole('status')).toBeInTheDocument()
      expect(screen.getByText('Loading events...')).toBeInTheDocument()
    })

    it('applies loading styles to calendar grid in compact mode', () => {
      render(<EventCalendar {...defaultProps} loading={true} />)

      const grid = screen.getByRole('grid')
      const rowgroup = grid.querySelector('[role="rowgroup"]')
      expect(rowgroup).toHaveClass('opacity-50', 'pointer-events-none')
    })

    it('hides loading indicator when loading is false', () => {
      render(<EventCalendar {...defaultProps} loading={false} />)

      expect(screen.queryByRole('status')).not.toBeInTheDocument()
    })
  })

  describe('View Mode Preservation', () => {
    it('maintains compact view mode after month navigation on mobile', () => {
      mockMatchMedia(false) // Mobile

      const { rerender } = render(
        <EventCalendar {...defaultProps} events={[mockEvent]} />
      )

      // Verify compact mode - should not show event title text directly
      // In compact mode, events are shown as category badges, not event cards
      const grid = screen.getByRole('grid')
      const cells = within(grid).getAllByRole('gridcell')

      // Compact cells should exist
      expect(cells.length).toBe(42)

      // Simulate month change by rerendering with new month
      rerender(
        <EventCalendar
          {...defaultProps}
          month={2}
          events={[{ ...mockEvent, event_date: '2026-02-15' }]}
        />
      )

      // Should still be in compact mode (42 grid cells)
      const newCells = within(screen.getByRole('grid')).getAllByRole('gridcell')
      expect(newCells.length).toBe(42)

      // Title should update to new month
      expect(screen.getByText('February 2026')).toBeInTheDocument()
    })

    it('maintains desktop view mode after month navigation', () => {
      mockMatchMedia(true) // Desktop

      const { rerender } = render(
        <EventCalendar {...defaultProps} events={[mockEvent]} />
      )

      // In desktop mode, event title should be visible
      expect(screen.getByText('Test Concert')).toBeInTheDocument()

      // Simulate month change
      rerender(
        <EventCalendar
          {...defaultProps}
          month={2}
          events={[{ ...mockEvent, event_date: '2026-02-15' }]}
        />
      )

      // Should still show event card with title
      expect(screen.getByText('Test Concert')).toBeInTheDocument()
      expect(screen.getByText('February 2026')).toBeInTheDocument()
    })
  })
})
