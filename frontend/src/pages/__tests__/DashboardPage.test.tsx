import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DashboardPage from '../DashboardPage'

// Mock all hooks used by DashboardPage
vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: vi.fn().mockReturnValue({ setStats: vi.fn() }),
}))

vi.mock('@/hooks/useCollections', () => ({
  useCollectionStats: vi.fn().mockReturnValue({
    stats: {
      total_collections: 5,
      file_count: 1200,
      image_count: 980,
      storage_used_bytes: 1073741824,
      storage_used_formatted: '1.0 GB',
    },
    loading: false,
  }),
}))

vi.mock('@/hooks/useResults', () => ({
  useResultStats: vi.fn().mockReturnValue({
    stats: { total_count: 42, completed_count: 38, failed_count: 4 },
    loading: false,
  }),
}))

vi.mock('@/hooks/useTools', () => ({
  useQueueStatus: vi.fn().mockReturnValue({
    queueStatus: {
      scheduled_count: 2,
      queued_count: 1,
      running_count: 1,
      completed_count: 30,
      failed_count: 3,
      cancelled_count: 0,
    },
    loading: false,
  }),
}))

vi.mock('@/hooks/useTrends', () => ({
  useTrendSummary: vi.fn().mockReturnValue({
    summary: null,
    loading: false,
  }),
}))

vi.mock('@/hooks/usePipelines', () => ({
  usePipelineStats: vi.fn().mockReturnValue({
    stats: { total_pipelines: 3, active_pipelines: 2 },
    loading: false,
  }),
}))

vi.mock('@/hooks/useAgentPoolStatus', () => ({
  useAgentPoolStatus: vi.fn().mockReturnValue({
    poolStatus: { online_count: 2, total_agents: 3 },
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('@/hooks/useDashboard', () => ({
  useRecentResults: vi.fn().mockReturnValue({
    results: [],
    loading: false,
  }),
  useEventDashboardStats: vi.fn().mockReturnValue({
    stats: null,
    loading: false,
  }),
}))

vi.mock('@/components/trends', () => ({
  TrendSummaryCard: () => <div data-testid="trend-summary-card" />,
}))

describe('DashboardPage', () => {
  test('renders without errors', () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Queue Overview')).toBeDefined()
  })

  test('renders collection stats KPI cards', () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Total Storage')).toBeDefined()
    expect(screen.getByText('1.0 GB')).toBeDefined()
  })

  test('renders queue overview section', () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Queue Overview')).toBeDefined()
    expect(screen.getByText('Running')).toBeDefined()
    expect(screen.getByText('Queued')).toBeDefined()
    expect(screen.getByText('Completed')).toBeDefined()
  })

  test('renders recent analysis results section', () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Recent Analysis Results')).toBeDefined()
    expect(screen.getByText('No analysis results yet')).toBeDefined()
  })

  test('shows agent count in queue overview', () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('2 agents online')).toBeDefined()
  })
})
