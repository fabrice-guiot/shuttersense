import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../utils/test-utils'
import { JobProgressCard } from '@/components/tools/JobProgressCard'
import type { Job, ProgressData } from '@/contracts/api/tools-api'

// Mock the useJobProgress hook since it uses WebSocket
vi.mock('@/hooks/useTools', () => ({
  useJobProgress: vi.fn(() => ({
    progress: null,
    status: null,
    connected: false,
    error: null,
    connect: vi.fn(),
    disconnect: vi.fn()
  }))
}))

import { useJobProgress } from '@/hooks/useTools'
const mockedUseJobProgress = vi.mocked(useJobProgress)

describe('JobProgressCard', () => {
  const mockOnCancel = vi.fn()
  const mockOnViewResult = vi.fn()

  const baseJob: Job = {
    id: 'job-1',
    collection_id: 1,
    tool: 'photostats',
    pipeline_id: null,
    mode: null,
    status: 'queued',
    position: 1,
    created_at: '2025-01-01T10:00:00Z',
    started_at: null,
    completed_at: null,
    progress: null,
    result_id: null,
    error_message: null
  }

  afterEach(() => {
    vi.clearAllMocks()
    // Reset the mock to default behavior
    mockedUseJobProgress.mockReturnValue({
      progress: null,
      status: null,
      connected: false,
      error: null,
      connect: vi.fn(),
      disconnect: vi.fn()
    })
  })

  it('should render queued job with position', () => {
    render(
      <JobProgressCard
        job={baseJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    expect(screen.getByText('PhotoStats')).toBeInTheDocument()
    expect(screen.getByText('Queued')).toBeInTheDocument()
    expect(screen.getByText(/Position in queue:/i)).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
  })

  it('should show cancel button for queued jobs', () => {
    render(
      <JobProgressCard
        job={baseJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    // Cancel button should be visible
    const cancelButton = screen.getByRole('button')
    expect(cancelButton).toBeInTheDocument()
  })

  it('should call onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup()

    render(
      <JobProgressCard
        job={baseJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    const cancelButton = screen.getByRole('button')
    await user.click(cancelButton)

    expect(mockOnCancel).toHaveBeenCalledWith('job-1')
  })

  it('should render running job with progress from WebSocket', () => {
    const mockProgress: ProgressData = {
      stage: 'scanning',
      files_scanned: 150,
      total_files: 500,
      issues_found: 3,
      percentage: 30
    }

    mockedUseJobProgress.mockReturnValue({
      progress: mockProgress,
      status: 'running',
      connected: true,
      error: null,
      connect: vi.fn(),
      disconnect: vi.fn()
    })

    const runningJob: Job = {
      ...baseJob,
      status: 'running',
      started_at: '2025-01-01T10:01:00Z',
      position: null
    }

    render(
      <JobProgressCard
        job={runningJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    expect(screen.getByText('Running')).toBeInTheDocument()
    expect(screen.getByText('scanning')).toBeInTheDocument()
    expect(screen.getByText('30%')).toBeInTheDocument()
    expect(screen.getByText('150 files scanned')).toBeInTheDocument()
    expect(screen.getByText('3 issues found')).toBeInTheDocument()
  })

  it('should render completed job with View Result button', () => {
    const completedJob: Job = {
      ...baseJob,
      status: 'completed',
      started_at: '2025-01-01T10:01:00Z',
      completed_at: '2025-01-01T10:05:00Z',
      result_id: 123,
      position: null
    }

    render(
      <JobProgressCard
        job={completedJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    expect(screen.getByText('Completed')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /View Result/i })).toBeInTheDocument()
  })

  it('should call onViewResult when View Result button is clicked', async () => {
    const user = userEvent.setup()

    const completedJob: Job = {
      ...baseJob,
      status: 'completed',
      started_at: '2025-01-01T10:01:00Z',
      completed_at: '2025-01-01T10:05:00Z',
      result_id: 123,
      position: null
    }

    render(
      <JobProgressCard
        job={completedJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    await user.click(screen.getByRole('button', { name: /View Result/i }))

    expect(mockOnViewResult).toHaveBeenCalledWith(123)
  })

  it('should render failed job with error message', () => {
    const failedJob: Job = {
      ...baseJob,
      status: 'failed',
      started_at: '2025-01-01T10:01:00Z',
      completed_at: '2025-01-01T10:01:30Z',
      error_message: 'Connection timeout',
      position: null
    }

    render(
      <JobProgressCard
        job={failedJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.getByText('Connection timeout')).toBeInTheDocument()
  })

  it('should render cancelled job', () => {
    const cancelledJob: Job = {
      ...baseJob,
      status: 'cancelled',
      completed_at: '2025-01-01T10:00:30Z',
      position: null
    }

    render(
      <JobProgressCard
        job={cancelledJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    expect(screen.getByText('Cancelled')).toBeInTheDocument()
  })

  it('should not show cancel button for running jobs', () => {
    const runningJob: Job = {
      ...baseJob,
      status: 'running',
      started_at: '2025-01-01T10:01:00Z',
      position: null
    }

    render(
      <JobProgressCard
        job={runningJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    // Cancel button should not be visible for running jobs
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument()
  })

  it('should display tool name correctly for photo_pairing', () => {
    const job: Job = {
      ...baseJob,
      tool: 'photo_pairing'
    }

    render(
      <JobProgressCard
        job={job}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    expect(screen.getByText('Photo Pairing')).toBeInTheDocument()
  })

  it('should display collection ID', () => {
    render(
      <JobProgressCard
        job={baseJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    expect(screen.getByText('Collection:')).toBeInTheDocument()
    expect(screen.getByText('ID 1')).toBeInTheDocument()
  })

  it('should display created timestamp', () => {
    render(
      <JobProgressCard
        job={baseJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    expect(screen.getByText('Created:')).toBeInTheDocument()
    // Should show the formatted date (locale-dependent)
    expect(screen.getByText(/1\/1\/2025|01\/01\/2025|2025/)).toBeInTheDocument()
  })

  it('should show started timestamp when job has started', () => {
    const startedJob: Job = {
      ...baseJob,
      status: 'running',
      started_at: '2025-01-01T10:01:00Z',
      position: null
    }

    render(
      <JobProgressCard
        job={startedJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    expect(screen.getByText('Started:')).toBeInTheDocument()
  })

  it('should show completed timestamp when job is done', () => {
    const completedJob: Job = {
      ...baseJob,
      status: 'completed',
      started_at: '2025-01-01T10:01:00Z',
      completed_at: '2025-01-01T10:05:00Z',
      result_id: 123,
      position: null
    }

    render(
      <JobProgressCard
        job={completedJob}
        onCancel={mockOnCancel}
        onViewResult={mockOnViewResult}
      />
    )

    expect(screen.getByText('Completed:')).toBeInTheDocument()
  })
})
