import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AnalyticsPage from '../AnalyticsPage'

// ============================================================================
// Mock Hooks
// ============================================================================

vi.mock('@/hooks/useTools', () => ({
  useTools: vi.fn().mockReturnValue({
    jobs: [],
    loading: false,
    error: null,
    total: 0,
    fetchJobs: vi.fn(),
    runTool: vi.fn(),
    cancelJob: vi.fn(),
    retryJob: vi.fn(),
  }),
  useQueueStatus: vi.fn().mockReturnValue({
    queueStatus: null,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('@/hooks/useAgentPoolStatus', () => ({
  useAgentPoolStatus: vi.fn().mockReturnValue({
    poolStatus: { online_count: 1 },
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('@/hooks/useResults', () => ({
  useResults: vi.fn().mockReturnValue({
    results: [],
    total: 0,
    loading: false,
    error: null,
    filters: {},
    setFilters: vi.fn(),
    page: 1,
    setPage: vi.fn(),
    limit: 20,
    setLimit: vi.fn(),
    deleteResult: vi.fn(),
    refetch: vi.fn(),
  }),
  useResult: vi.fn().mockReturnValue({
    result: null,
    loading: false,
    error: null,
  }),
  useResultStats: vi.fn().mockReturnValue({
    stats: null,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useReportDownload: vi.fn().mockReturnValue({
    downloadReport: vi.fn(),
    downloading: false,
    error: null,
  }),
}))

vi.mock('@/hooks/useTrends', () => ({
  usePhotoStatsTrends: vi.fn().mockReturnValue({
    data: null,
    loading: false,
    error: null,
    filters: {},
    setFilters: vi.fn(),
    refetch: vi.fn(),
  }),
  usePhotoPairingTrends: vi.fn().mockReturnValue({
    data: null,
    loading: false,
    error: null,
    filters: {},
    setFilters: vi.fn(),
    refetch: vi.fn(),
  }),
  usePipelineValidationTrends: vi.fn().mockReturnValue({
    data: null,
    loading: false,
    error: null,
    filters: {},
    setFilters: vi.fn(),
    refetch: vi.fn(),
  }),
  useDisplayGraphTrends: vi.fn().mockReturnValue({
    data: null,
    loading: false,
    error: null,
    filters: {},
    setFilters: vi.fn(),
    refetch: vi.fn(),
  }),
  useTrendSummary: vi.fn().mockReturnValue({
    summary: null,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('@/hooks/useCollections', () => ({
  useCollections: vi.fn().mockReturnValue({
    collections: [],
    loading: false,
    error: null,
  }),
}))

vi.mock('@/hooks/usePipelines', () => ({
  usePipelines: vi.fn().mockReturnValue({
    pipelines: [],
    loading: false,
    error: null,
  }),
}))

vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: vi.fn().mockReturnValue({
    stats: [],
    setStats: vi.fn(),
    clearStats: vi.fn(),
  }),
}))

// ============================================================================
// Mock Child Components
// ============================================================================

vi.mock('@/components/tools/RunToolDialog', () => ({
  RunToolDialog: () => <div data-testid="run-tool-dialog" />,
}))

vi.mock('@/components/tools/JobProgressCard', () => ({
  JobProgressCard: () => <div data-testid="job-progress-card" />,
}))

vi.mock('@/components/results/ResultsTable', () => ({
  ResultsTable: () => <div data-testid="results-table" />,
}))

vi.mock('@/components/results/ResultDetailPanel', () => ({
  ResultDetailPanel: () => <div data-testid="result-detail-panel" />,
}))

vi.mock('@/components/trends', () => ({
  PhotoStatsTrend: () => <div data-testid="photostats-trend" />,
  PhotoPairingTrend: () => <div data-testid="photopairing-trend" />,
  PipelineValidationTrend: () => <div data-testid="pipeline-validation-trend" />,
  DisplayGraphTrend: () => <div data-testid="display-graph-trend" />,
  DateRangeFilter: () => <div data-testid="date-range-filter" />,
  CollectionCompare: () => <div data-testid="collection-compare" />,
  PipelineFilter: () => <div data-testid="pipeline-filter" />,
  TrendSummaryCard: () => <div data-testid="trend-summary-card" />,
}))

vi.mock('@/components/analytics/ReportStorageTab', () => ({
  ReportStorageTab: () => <div data-testid="report-storage-tab" />,
}))

vi.mock('@/contracts/api/trends-api', () => ({
  getDateRangeFromPreset: vi.fn().mockReturnValue({
    from_date: '2026-01-01',
    to_date: '2026-01-31',
  }),
}))

// ============================================================================
// Tests
// ============================================================================

describe('AnalyticsPage', () => {
  test('renders without crashing', () => {
    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>,
    )

    // Page should render without throwing
    expect(screen.getByText('Run Tool')).toBeDefined()
  })

  test('renders main tab labels', () => {
    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>,
    )

    // Tab labels may appear multiple times (TabsTrigger + ResponsiveTabsList options)
    expect(screen.getAllByText('Trends').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Reports').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Runs').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Storage').length).toBeGreaterThan(0)
  })

  test('renders Run Tool button', () => {
    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Run Tool')).toBeDefined()
  })

  test('renders trend components on default tab', () => {
    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('photostats-trend')).toBeDefined()
    expect(screen.getByTestId('photopairing-trend')).toBeDefined()
    expect(screen.getByTestId('pipeline-validation-trend')).toBeDefined()
    expect(screen.getByTestId('display-graph-trend')).toBeDefined()
    expect(screen.getByTestId('trend-summary-card')).toBeDefined()
  })

  test('renders trend filter components', () => {
    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('date-range-filter')).toBeDefined()
    expect(screen.getByTestId('collection-compare')).toBeDefined()
    expect(screen.getByTestId('pipeline-filter')).toBeDefined()
  })

  test('does not show agent warning when agents are available', () => {
    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>,
    )

    expect(screen.queryByText('No agents available')).toBeNull()
  })

  test('shows agent warning when no agents available', async () => {
    const { useAgentPoolStatus } = await import('@/hooks/useAgentPoolStatus')
    vi.mocked(useAgentPoolStatus).mockReturnValue({
      poolStatus: { online_count: 0 } as any,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('No agents available')).toBeDefined()
  })
})
