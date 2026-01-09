import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../utils/test-utils'
import { ResultsTable } from '@/components/results/ResultsTable'
import type { AnalysisResultSummary } from '@/contracts/api/results-api'

describe('ResultsTable', () => {
  const mockResults: AnalysisResultSummary[] = [
    {
      id: 1,
      collection_id: 1,
      collection_name: 'Test Collection',
      tool: 'photostats',
      pipeline_id: null,
      pipeline_version: null,
      pipeline_name: null,
      status: 'COMPLETED',
      started_at: '2025-01-01T10:00:00Z',
      completed_at: '2025-01-01T10:05:00Z',
      duration_seconds: 300,
      files_scanned: 1000,
      issues_found: 5,
      has_report: true
    },
    {
      id: 2,
      collection_id: 1,
      collection_name: 'Test Collection',
      tool: 'photo_pairing',
      pipeline_id: null,
      pipeline_version: null,
      pipeline_name: null,
      status: 'COMPLETED',
      started_at: '2025-01-01T11:00:00Z',
      completed_at: '2025-01-01T11:03:00Z',
      duration_seconds: 180,
      files_scanned: 800,
      issues_found: 2,
      has_report: true
    },
    {
      id: 3,
      collection_id: 2,
      collection_name: 'Remote Collection',
      tool: 'photostats',
      pipeline_id: null,
      pipeline_version: null,
      pipeline_name: null,
      status: 'FAILED',
      started_at: '2025-01-01T12:00:00Z',
      completed_at: '2025-01-01T12:00:30Z',
      duration_seconds: 30,
      files_scanned: 0,
      issues_found: 0,
      has_report: false
    }
  ]

  const mockOnPageChange = vi.fn()
  const mockOnLimitChange = vi.fn()
  const mockOnFiltersChange = vi.fn()
  const mockOnView = vi.fn()
  const mockOnDelete = vi.fn()
  const mockOnDownloadReport = vi.fn()

  const defaultProps = {
    results: mockResults,
    total: 3,
    page: 1,
    limit: 20,
    loading: false,
    onPageChange: mockOnPageChange,
    onLimitChange: mockOnLimitChange,
    onFiltersChange: mockOnFiltersChange,
    onView: mockOnView,
    onDelete: mockOnDelete,
    onDownloadReport: mockOnDownloadReport
  }

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('should render table with results', () => {
    render(<ResultsTable {...defaultProps} />)

    // Check table headers
    expect(screen.getByText('Collection')).toBeInTheDocument()
    expect(screen.getByText('Tool')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Files')).toBeInTheDocument()
    expect(screen.getByText('Issues')).toBeInTheDocument()
    expect(screen.getByText('Duration')).toBeInTheDocument()

    // Check that "Completed" header exists
    const completedHeaders = screen.getAllByText('Completed')
    expect(completedHeaders.length).toBeGreaterThanOrEqual(1)

    // Check data rows - use getAllByText for repeated collection names
    const testCollectionCells = screen.getAllByText('Test Collection')
    expect(testCollectionCells.length).toBeGreaterThanOrEqual(1)

    expect(screen.getByText('Remote Collection')).toBeInTheDocument()
    // PhotoStats appears in multiple rows
    const photoStatsBadges = screen.getAllByText('PhotoStats')
    expect(photoStatsBadges.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Photo Pairing')).toBeInTheDocument()
  })

  it('should show loading spinner when loading', () => {
    render(<ResultsTable {...defaultProps} loading={true} />)

    expect(screen.getByRole('status')).toBeInTheDocument()
    // Table should not be visible
    expect(screen.queryByText('Collection')).not.toBeInTheDocument()
  })

  it('should show empty state when no results', () => {
    render(<ResultsTable {...defaultProps} results={[]} total={0} />)

    expect(screen.getByText('No analysis results found')).toBeInTheDocument()
  })

  it('should format duration correctly', () => {
    render(<ResultsTable {...defaultProps} />)

    // 300 seconds = 5m 0s
    expect(screen.getByText('5m 0s')).toBeInTheDocument()
    // 180 seconds = 3m 0s
    expect(screen.getByText('3m 0s')).toBeInTheDocument()
    // 30 seconds = 30.0s
    expect(screen.getByText('30.0s')).toBeInTheDocument()
  })

  it('should show correct status badges', () => {
    render(<ResultsTable {...defaultProps} />)

    // Should have completed badges (at least 2: table header + data rows)
    const completedBadges = screen.getAllByText('Completed')
    expect(completedBadges.length).toBeGreaterThanOrEqual(2)

    // Should have failed badge
    expect(screen.getByText('Failed')).toBeInTheDocument()
  })

  it('should call onView when view button is clicked', async () => {
    const user = userEvent.setup()
    render(<ResultsTable {...defaultProps} />)

    // Get all view buttons (using the Eye icon button)
    const viewButtons = screen.getAllByRole('button').filter(btn =>
      btn.querySelector('svg.lucide-eye')
    )

    await user.click(viewButtons[0])

    expect(mockOnView).toHaveBeenCalledWith(mockResults[0])
  })

  it('should show download button only for results with reports', async () => {
    const user = userEvent.setup()
    render(<ResultsTable {...defaultProps} />)

    // Results with has_report: true should have download button
    // Result 3 (failed) has no report
    const downloadButtons = screen.getAllByRole('button').filter(btn =>
      btn.querySelector('svg.lucide-download')
    )

    // Should have 2 download buttons (for results 1 and 2)
    expect(downloadButtons).toHaveLength(2)
  })

  it('should call onDownloadReport when download button is clicked', async () => {
    const user = userEvent.setup()
    render(<ResultsTable {...defaultProps} />)

    const downloadButtons = screen.getAllByRole('button').filter(btn =>
      btn.querySelector('svg.lucide-download')
    )

    await user.click(downloadButtons[0])

    expect(mockOnDownloadReport).toHaveBeenCalledWith(mockResults[0])
  })

  it('should open delete confirmation dialog', async () => {
    const user = userEvent.setup()
    render(<ResultsTable {...defaultProps} />)

    const deleteButtons = screen.getAllByRole('button').filter(btn =>
      btn.querySelector('svg.lucide-trash-2')
    )

    await user.click(deleteButtons[0])

    // Dialog should open
    expect(screen.getByText('Delete Result')).toBeInTheDocument()
    expect(screen.getByText(/Are you sure you want to delete/i)).toBeInTheDocument()
  })

  it('should call onDelete when delete is confirmed', async () => {
    const user = userEvent.setup()
    render(<ResultsTable {...defaultProps} />)

    const deleteButtons = screen.getAllByRole('button').filter(btn =>
      btn.querySelector('svg.lucide-trash-2')
    )

    await user.click(deleteButtons[0])

    // Confirm delete
    const confirmButton = screen.getByRole('button', { name: /^Delete$/i })
    await user.click(confirmButton)

    expect(mockOnDelete).toHaveBeenCalledWith(mockResults[0])
  })

  it('should close delete dialog on cancel', async () => {
    const user = userEvent.setup()
    render(<ResultsTable {...defaultProps} />)

    const deleteButtons = screen.getAllByRole('button').filter(btn =>
      btn.querySelector('svg.lucide-trash-2')
    )

    await user.click(deleteButtons[0])

    // Cancel delete
    const cancelButton = screen.getByRole('button', { name: /Cancel/i })
    await user.click(cancelButton)

    // Dialog should close
    await waitFor(() => {
      expect(screen.queryByText('Delete Result')).not.toBeInTheDocument()
    })

    expect(mockOnDelete).not.toHaveBeenCalled()
  })

  it('should have filter dropdowns available', () => {
    render(<ResultsTable {...defaultProps} />)

    // Verify filter UI elements exist
    expect(screen.getByText('Tool:')).toBeInTheDocument()
    expect(screen.getByText('Status:')).toBeInTheDocument()

    // Verify comboboxes exist
    const comboboxes = screen.getAllByRole('combobox')
    expect(comboboxes.length).toBeGreaterThanOrEqual(2) // Tool and Status filters
  })

  it('should show correct filter labels', () => {
    render(<ResultsTable {...defaultProps} />)

    // Filter labels should be visible
    expect(screen.getByText('Tool:')).toBeInTheDocument()
    expect(screen.getByText('Status:')).toBeInTheDocument()
  })

  it('should handle pagination', async () => {
    const user = userEvent.setup()
    render(<ResultsTable {...defaultProps} total={50} />)

    // Should show pagination info
    expect(screen.getByText(/1-20 of 50/i)).toBeInTheDocument()
    expect(screen.getByText(/Page 1 of 3/i)).toBeInTheDocument()

    // Find and click next page button using chevron icon
    const buttons = screen.getAllByRole('button')
    const nextButton = buttons.find(btn => btn.querySelector('svg.lucide-chevron-right'))

    if (nextButton) {
      await user.click(nextButton)
      expect(mockOnPageChange).toHaveBeenCalledWith(2)
    }
  })

  it('should show rows per page selector', () => {
    render(<ResultsTable {...defaultProps} />)

    // Rows per page selector should be visible
    expect(screen.getByText('Rows per page:')).toBeInTheDocument()

    // Should have pagination comboboxes
    const comboboxes = screen.getAllByRole('combobox')
    expect(comboboxes.length).toBeGreaterThanOrEqual(2)
  })

  it('should disable previous button on first page', () => {
    render(<ResultsTable {...defaultProps} page={1} />)

    // The previous button should be disabled
    const buttons = screen.getAllByRole('button')
    const prevButton = buttons.find(btn => btn.querySelector('svg.lucide-chevron-left'))
    expect(prevButton).toBeDisabled()
  })

  it('should disable next button on last page', () => {
    render(<ResultsTable {...defaultProps} page={1} total={3} limit={20} />)

    // With 3 results and limit 20, we're on the only page
    const buttons = screen.getAllByRole('button')
    const nextButton = buttons.find(btn => btn.querySelector('svg.lucide-chevron-right'))
    expect(nextButton).toBeDisabled()
  })
})
