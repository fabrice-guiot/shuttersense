import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import EventsPage from '../EventsPage'

// Mock all hooks used by EventsPage
vi.mock('@/hooks/useEvents', () => ({
  useCalendar: vi.fn().mockReturnValue({
    currentMonth: new Date(2026, 1, 1),
    calendarDays: [],
    goToPreviousMonth: vi.fn(),
    goToNextMonth: vi.fn(),
    goToToday: vi.fn(),
  }),
  useEvents: vi.fn().mockReturnValue({
    events: [],
    loading: false,
    error: null,
    fetchEvents: vi.fn().mockResolvedValue([]),
    fetchEventsByMonth: vi.fn().mockResolvedValue([]),
    fetchEventsForCalendarView: vi.fn().mockResolvedValue([]),
  }),
  useEventStats: vi.fn().mockReturnValue({
    stats: {
      total_count: 10,
      upcoming_count: 3,
      this_month_count: 2,
      attended_count: 5,
    },
    loading: false,
    refetch: vi.fn(),
  }),
  useEventMutations: vi.fn().mockReturnValue({
    createEvent: vi.fn(),
    updateEvent: vi.fn(),
    deleteEvent: vi.fn(),
    createSeries: vi.fn(),
    loading: false,
    error: null,
  }),
}))

vi.mock('@/hooks/useConflicts', () => ({
  useConflicts: vi.fn().mockReturnValue({
    conflicts: [],
    loading: false,
    error: null,
    fetchConflicts: vi.fn(),
    detectConflicts: vi.fn().mockResolvedValue([]),
  }),
}))

vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: vi.fn().mockReturnValue({ setStats: vi.fn() }),
}))

vi.mock('@/hooks/useDateRange', () => ({
  useDateRange: vi.fn().mockReturnValue({
    preset: 'last_30d',
    range: {
      startDate: '2026-01-15',
      endDate: '2026-02-14',
    },
    customStart: '',
    customEnd: '',
    setPreset: vi.fn(),
    setCustomRange: vi.fn(),
  }),
}))

vi.mock('@/hooks/useScoringWeights', () => ({
  useScoringWeights: vi.fn().mockReturnValue({
    weights: null,
    loading: false,
  }),
}))

vi.mock('@/hooks/useCategories', () => ({
  useCategories: vi.fn().mockReturnValue({
    categories: [],
    loading: false,
  }),
}))

vi.mock('@/components/events', () => ({
  EventCalendar: () => <div data-testid="event-calendar">Calendar</div>,
  EventList: () => <div data-testid="event-list">Event List</div>,
  EventForm: () => <div data-testid="event-form">Event Form</div>,
  EventPerformersSection: () => <div data-testid="event-performers">Performers</div>,
}))

vi.mock('@/components/events/ConflictResolutionPanel', () => ({
  ConflictResolutionPanel: () => <div data-testid="conflict-panel" />,
}))

vi.mock('@/components/events/TimelinePlanner', () => ({
  TimelinePlanner: () => <div data-testid="timeline-planner" />,
}))

vi.mock('@/components/events/DateRangePicker', () => ({
  DateRangePicker: () => <div data-testid="date-range-picker" />,
}))

vi.mock('@/components/audit', () => ({
  AuditTrailSection: () => <div data-testid="audit-section" />,
}))

describe('EventsPage', () => {
  test('renders without errors', () => {
    render(
      <MemoryRouter>
        <EventsPage />
      </MemoryRouter>,
    )

    // Page renders with calendar view by default
    expect(screen.getByTestId('event-calendar')).toBeDefined()
  })

  test('renders New Event button', () => {
    render(
      <MemoryRouter>
        <EventsPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('New Event')).toBeDefined()
  })

  test('renders calendar view as default', () => {
    render(
      <MemoryRouter>
        <EventsPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('event-calendar')).toBeDefined()
  })
})
