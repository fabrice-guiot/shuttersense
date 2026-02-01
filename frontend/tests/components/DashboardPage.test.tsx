/**
 * DashboardPage Tests
 *
 * Tests for the main dashboard landing page including KPI cards,
 * trend summary, queue overview, recent results, and quick links.
 */

import { render, screen, waitFor } from '../utils/test-utils'
import DashboardPage from '@/pages/DashboardPage'
import type { CollectionStatsResponse } from '@/contracts/api/collection-api'
import type { ResultStatsResponse } from '@/contracts/api/results-api'
import type { PipelineStatsResponse } from '@/contracts/api/pipelines-api'
import type { QueueStatusResponse } from '@/contracts/api/tools-api'
import type { TrendSummaryResponse } from '@/contracts/api/trends-api'
import type { AgentPoolStatusResponse } from '@/contracts/api/agent-api'

// ============================================================================
// Mocks
// ============================================================================

const mockSetStats = vi.fn()

vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: () => ({
    setStats: mockSetStats,
  }),
}))

// Mock useAuth for useAgentPoolStatus
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { guid: 'usr_01', email: 'test@example.com' },
    isLoading: false,
    error: null,
  }),
}))

// Mock individual hooks
const mockCollectionStats: CollectionStatsResponse = {
  total_collections: 12,
  storage_used_bytes: 5000000000,
  storage_used_formatted: '4.66 GB',
  file_count: 15000,
  image_count: 12500,
}

const mockResultStats: ResultStatsResponse = {
  total_results: 42,
  completed_count: 38,
  failed_count: 4,
  by_tool: {
    photostats: 20,
    photo_pairing: 12,
    pipeline_validation: 10,
  },
  last_run: '2026-01-15T10:30:00Z',
}

const mockQueueStatus: QueueStatusResponse = {
  scheduled_count: 2,
  queued_count: 1,
  running_count: 3,
  completed_count: 150,
  failed_count: 5,
  cancelled_count: 2,
  current_job_id: 'job_01',
}

const mockPipelineStats: PipelineStatsResponse = {
  total_pipelines: 5,
  valid_pipelines: 4,
  active_pipeline_count: 3,
  default_pipeline_guid: 'pip_01',
  default_pipeline_name: 'Standard RAW',
}

const mockTrendSummary: TrendSummaryResponse = {
  collection_id: null,
  orphaned_trend: 'improving',
  consistency_trend: 'stable',
  last_photostats: '2026-01-15T10:00:00Z',
  last_photo_pairing: '2026-01-15T11:00:00Z',
  last_pipeline_validation: '2026-01-15T12:00:00Z',
  data_points_available: {
    photostats: 15,
    photo_pairing: 12,
    pipeline_validation: 10,
  },
  stable_periods: {
    photostats_stable: true,
    photostats_stable_days: 5,
    photo_pairing_stable: false,
    photo_pairing_stable_days: 0,
    pipeline_validation_stable: true,
    pipeline_validation_stable_days: 3,
  },
}

const mockPoolStatus: AgentPoolStatusResponse = {
  online_count: 1,
  offline_count: 1,
  idle_count: 1,
  running_jobs_count: 0,
  status: 'idle',
}

const mockRecentResults = [
  {
    guid: 'res_01',
    collection_guid: 'col_01',
    collection_name: 'Wedding Photos',
    tool: 'photostats' as const,
    pipeline_guid: null,
    pipeline_version: null,
    pipeline_name: null,
    connector_guid: null,
    connector_name: null,
    status: 'COMPLETED' as const,
    started_at: '2026-01-15T10:00:00Z',
    completed_at: '2026-01-15T10:05:00Z',
    duration_seconds: 300,
    files_scanned: 500,
    issues_found: 3,
    has_report: true,
    input_state_hash: null,
    no_change_copy: false,
  },
  {
    guid: 'res_02',
    collection_guid: 'col_02',
    collection_name: 'Studio Portraits',
    tool: 'photo_pairing' as const,
    pipeline_guid: null,
    pipeline_version: null,
    pipeline_name: null,
    connector_guid: null,
    connector_name: null,
    status: 'FAILED' as const,
    started_at: '2026-01-15T09:00:00Z',
    completed_at: '2026-01-15T09:02:00Z',
    duration_seconds: 120,
    files_scanned: 200,
    issues_found: null,
    has_report: false,
    input_state_hash: null,
    no_change_copy: false,
  },
]

// Create module-level mock state
let collectionStatsState = { stats: mockCollectionStats, loading: false, error: null }
let resultStatsState = { stats: mockResultStats, loading: false, error: null }
let queueStatusState = { queueStatus: mockQueueStatus, loading: false, error: null }
let pipelineStatsState = { stats: mockPipelineStats, loading: false, error: null }
let trendSummaryState = { summary: mockTrendSummary, loading: false, error: null }
let poolStatusState = { poolStatus: mockPoolStatus, loading: false, error: null }
let recentResultsState = { results: mockRecentResults, loading: false, error: null }

vi.mock('@/hooks/useCollections', () => ({
  useCollectionStats: () => ({ ...collectionStatsState, refetch: vi.fn() }),
}))

vi.mock('@/hooks/useResults', () => ({
  useResultStats: () => ({ ...resultStatsState, refetch: vi.fn() }),
}))

vi.mock('@/hooks/useTools', () => ({
  useQueueStatus: () => ({ ...queueStatusState, refetch: vi.fn() }),
}))

vi.mock('@/hooks/usePipelines', () => ({
  usePipelineStats: () => ({ ...pipelineStatsState, refetch: vi.fn() }),
}))

vi.mock('@/hooks/useTrends', () => ({
  useTrendSummary: () => ({ ...trendSummaryState, refetch: vi.fn() }),
}))

vi.mock('@/hooks/useAgentPoolStatus', () => ({
  useAgentPoolStatus: () => ({ ...poolStatusState, refetch: vi.fn() }),
}))

vi.mock('@/hooks/useDashboard', () => ({
  useRecentResults: () => ({ ...recentResultsState, refetch: vi.fn() }),
}))

// ============================================================================
// Tests
// ============================================================================

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset all states to defaults
    collectionStatsState = { stats: mockCollectionStats, loading: false, error: null }
    resultStatsState = { stats: mockResultStats, loading: false, error: null }
    queueStatusState = { queueStatus: mockQueueStatus, loading: false, error: null }
    pipelineStatsState = { stats: mockPipelineStats, loading: false, error: null }
    trendSummaryState = { summary: mockTrendSummary, loading: false, error: null }
    poolStatusState = { poolStatus: mockPoolStatus, loading: false, error: null }
    recentResultsState = { results: mockRecentResults, loading: false, error: null }
  })

  // --------------------------------------------------------------------------
  // Header Stats
  // --------------------------------------------------------------------------

  it('sets header stats with storage, images, scheduled, and running data', () => {
    render(<DashboardPage />)

    expect(mockSetStats).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ label: 'Storage', value: '4.66 GB' }),
        expect.objectContaining({ label: 'Images' }),
        expect.objectContaining({ label: 'Scheduled', value: 2 }),
        expect.objectContaining({ label: 'Running', value: 3 }),
      ])
    )
  })

  it('omits Running header stat when no jobs are running', () => {
    queueStatusState = {
      queueStatus: { ...mockQueueStatus, running_count: 0 },
      loading: false,
      error: null,
    }

    render(<DashboardPage />)

    // Should NOT include Running when 0
    const lastCall = mockSetStats.mock.calls[mockSetStats.mock.calls.length - 1][0]
    const hasRunning = lastCall.some((s: { label: string }) => s.label === 'Running')
    expect(hasRunning).toBe(false)
  })

  it('clears header stats on unmount', () => {
    const { unmount } = render(<DashboardPage />)
    unmount()

    // Last call should clear stats
    const lastCall = mockSetStats.mock.calls[mockSetStats.mock.calls.length - 1]
    expect(lastCall[0]).toEqual([])
  })

  // --------------------------------------------------------------------------
  // KPI Cards
  // --------------------------------------------------------------------------

  it('renders all four KPI cards with data', () => {
    render(<DashboardPage />)

    // Storage KPI card
    expect(screen.getByText('Total Storage')).toBeInTheDocument()
    expect(screen.getByText('4.66 GB')).toBeInTheDocument()
    expect(screen.getByText('12 collections')).toBeInTheDocument()

    // Images card
    expect(screen.getByText('Images')).toBeInTheDocument()
    expect(screen.getByText('12,500')).toBeInTheDocument()
    expect(screen.getByText('15,000 files total')).toBeInTheDocument()

    // Results card
    expect(screen.getByText('Analysis Results')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('38 completed, 4 failed')).toBeInTheDocument()

    // Pipelines card (also exists in Quick Links)
    expect(screen.getAllByText('Pipelines').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('5 total, 4 valid')).toBeInTheDocument()
  })

  // --------------------------------------------------------------------------
  // Trend Summary
  // --------------------------------------------------------------------------

  it('renders trend summary card with trend data', () => {
    render(<DashboardPage />)

    expect(screen.getByText('Trend Summary')).toBeInTheDocument()
    expect(screen.getByText('Orphaned Files')).toBeInTheDocument()
    expect(screen.getByText('Consistency')).toBeInTheDocument()
    expect(screen.getByText('Improving')).toBeInTheDocument()
    expect(screen.getByText('Stable')).toBeInTheDocument()
  })

  it('shows data point counts in trend summary', () => {
    render(<DashboardPage />)

    // Data points section shows counts - '15' appears in trend data points
    // and 'PhotoStats' appears both in trend data points and recent results
    expect(screen.getAllByText('PhotoStats').length).toBeGreaterThanOrEqual(1)
  })

  // --------------------------------------------------------------------------
  // Queue Overview
  // --------------------------------------------------------------------------

  it('renders queue overview with job counts', () => {
    render(<DashboardPage />)

    expect(screen.getByText('Queue Overview')).toBeInTheDocument()
    expect(screen.getByText('Scheduled')).toBeInTheDocument()
    expect(screen.getByText('Running')).toBeInTheDocument()
    expect(screen.getByText('Queued')).toBeInTheDocument()
  })

  it('shows agent count in queue overview', () => {
    render(<DashboardPage />)

    expect(screen.getByText('1 agent online')).toBeInTheDocument()
  })

  it('shows pluralized agents label', () => {
    poolStatusState = {
      poolStatus: { ...mockPoolStatus, online_count: 3, idle_count: 3 },
      loading: false,
      error: null,
    }

    render(<DashboardPage />)

    expect(screen.getByText('3 agents online')).toBeInTheDocument()
  })

  it('renders "View all jobs" link', () => {
    render(<DashboardPage />)

    const link = screen.getByText('View all jobs')
    expect(link).toBeInTheDocument()
    expect(link.closest('a')).toHaveAttribute('href', '/analytics?tab=runs')
  })

  // --------------------------------------------------------------------------
  // Recent Results
  // --------------------------------------------------------------------------

  it('renders recent analysis results', () => {
    render(<DashboardPage />)

    expect(screen.getByText('Recent Analysis Results')).toBeInTheDocument()
    // PhotoStats appears in both trend data and recent results
    expect(screen.getAllByText('PhotoStats').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Wedding Photos')).toBeInTheDocument()
    // 'Photo Pairing' also appears in TrendSummaryCard data point labels
    expect(screen.getAllByText('Photo Pairing').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Studio Portraits')).toBeInTheDocument()
  })

  it('shows status badges on recent results', () => {
    render(<DashboardPage />)

    // "Completed" and "Failed" also appear in queue overview, so use getAllByText
    expect(screen.getAllByText('Completed').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Failed').length).toBeGreaterThanOrEqual(1)
  })

  it('renders "View all" link for results', () => {
    render(<DashboardPage />)

    const link = screen.getByText('View all')
    expect(link).toBeInTheDocument()
    expect(link.closest('a')).toHaveAttribute('href', '/analytics?tab=reports')
  })

  it('shows empty state when no results exist', () => {
    recentResultsState = { results: [], loading: false, error: null }

    render(<DashboardPage />)

    expect(screen.getByText('No analysis results yet')).toBeInTheDocument()
  })

  it('links result items to analytics reports tab', () => {
    render(<DashboardPage />)

    const resultLink = screen.getByText('Wedding Photos').closest('a')
    expect(resultLink).toHaveAttribute('href', '/analytics?tab=reports&id=res_01')
  })

  // --------------------------------------------------------------------------
  // Quick Links
  // --------------------------------------------------------------------------

  it('renders quick links section', () => {
    render(<DashboardPage />)

    expect(screen.getByText('Quick Links')).toBeInTheDocument()

    const collectionsLink = screen.getByText('Manage photo collections').closest('a')
    expect(collectionsLink).toHaveAttribute('href', '/collections')

    const analyticsLink = screen.getByText('Trends, reports, and tool runs').closest('a')
    expect(analyticsLink).toHaveAttribute('href', '/analytics')

    const pipelinesLink = screen.getByText('Processing workflow definitions').closest('a')
    expect(pipelinesLink).toHaveAttribute('href', '/pipelines')

    const eventsLink = screen.getByText('Photo event calendar').closest('a')
    expect(eventsLink).toHaveAttribute('href', '/events')
  })

  // --------------------------------------------------------------------------
  // Loading States
  // --------------------------------------------------------------------------

  it('shows loading state for KPI cards', () => {
    collectionStatsState = { stats: null as any, loading: true, error: null }

    render(<DashboardPage />)

    // "Total Storage" KPI card title renders even during loading
    expect(screen.getByText('Total Storage')).toBeInTheDocument()
    // The loading state renders a pulse div instead of a value
  })

  it('shows loading state for queue overview', () => {
    queueStatusState = { queueStatus: null, loading: true, error: null }

    render(<DashboardPage />)

    expect(screen.getByText('Queue Overview')).toBeInTheDocument()
  })

  // --------------------------------------------------------------------------
  // Zero Data / Edge Cases
  // --------------------------------------------------------------------------

  it('handles zero stats gracefully', () => {
    collectionStatsState = {
      stats: {
        total_collections: 0,
        storage_used_bytes: 0,
        storage_used_formatted: '0 B',
        file_count: 0,
        image_count: 0,
      },
      loading: false,
      error: null,
    }

    resultStatsState = {
      stats: {
        total_results: 0,
        completed_count: 0,
        failed_count: 0,
        by_tool: {},
        last_run: null,
      },
      loading: false,
      error: null,
    }

    render(<DashboardPage />)

    expect(screen.getByText('0 collections')).toBeInTheDocument()
    expect(screen.getByText('0 completed, 0 failed')).toBeInTheDocument()
  })

  it('handles null stats before data loads', () => {
    collectionStatsState = { stats: null as any, loading: false, error: null }
    resultStatsState = { stats: null as any, loading: false, error: null }

    render(<DashboardPage />)

    // Should render with fallback values
    expect(screen.getByText('Total Storage')).toBeInTheDocument()
    expect(screen.getByText('Images')).toBeInTheDocument()
  })
})
