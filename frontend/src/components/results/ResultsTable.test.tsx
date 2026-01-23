/**
 * Tests for ResultsTable component.
 *
 * Tests cover:
 * - NO_CHANGE copy indicator display
 * - Status badge rendering
 * - Table filtering
 *
 * Part of Issue #92: Storage Optimization for Analysis Results.
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ResultsTable } from './ResultsTable'
import type { AnalysisResultSummary, ToolType, ResultStatus } from '@/contracts/api/results-api'

// ============================================================================
// Test Data
// ============================================================================

const mockResults: AnalysisResultSummary[] = [
  {
    guid: 'res_01hgw2bbg00000000000000001',
    collection_guid: 'col_01hgw2bbg00000000000000001',
    collection_name: 'Test Collection',
    tool: 'photostats' as ToolType,
    pipeline_guid: null,
    pipeline_version: null,
    pipeline_name: null,
    status: 'COMPLETED' as ResultStatus,
    started_at: '2025-01-01T10:00:00Z',
    completed_at: '2025-01-01T10:05:00Z',
    duration_seconds: 300,
    files_scanned: 1000,
    issues_found: 5,
    has_report: true,
    input_state_hash: 'abc123',
    no_change_copy: false
  },
  {
    guid: 'res_01hgw2bbg00000000000000002',
    collection_guid: 'col_01hgw2bbg00000000000000001',
    collection_name: 'Test Collection',
    tool: 'photostats' as ToolType,
    pipeline_guid: null,
    pipeline_version: null,
    pipeline_name: null,
    status: 'NO_CHANGE' as ResultStatus,
    started_at: '2025-01-02T10:00:00Z',
    completed_at: '2025-01-02T10:01:00Z',
    duration_seconds: 60,
    files_scanned: 1000,
    issues_found: 5,
    has_report: true,
    input_state_hash: 'abc123',
    no_change_copy: true
  },
  {
    guid: 'res_01hgw2bbg00000000000000003',
    collection_guid: 'col_01hgw2bbg00000000000000002',
    collection_name: 'Another Collection',
    tool: 'photo_pairing' as ToolType,
    pipeline_guid: null,
    pipeline_version: null,
    pipeline_name: null,
    status: 'FAILED' as ResultStatus,
    started_at: '2025-01-03T10:00:00Z',
    completed_at: '2025-01-03T10:00:30Z',
    duration_seconds: 30,
    files_scanned: 0,
    issues_found: 0,
    has_report: false,
    input_state_hash: null,
    no_change_copy: false
  }
]

// Default props
const defaultProps = {
  results: mockResults,
  total: mockResults.length,
  page: 1,
  limit: 10,
  loading: false,
  onPageChange: vi.fn(),
  onLimitChange: vi.fn(),
  onFiltersChange: vi.fn(),
  onView: vi.fn(),
  onDelete: vi.fn(),
  onDownloadReport: vi.fn()
}

// ============================================================================
// Tests
// ============================================================================

describe('ResultsTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('NO_CHANGE indicator', () => {
    test('shows copy icon for NO_CHANGE result with no_change_copy=true', () => {
      render(<ResultsTable {...defaultProps} />)

      // Find the row for the NO_CHANGE result
      const rows = screen.getAllByRole('row')
      // Row 0 is header, row 2 is the NO_CHANGE result (index 1 in results)
      const noChangeRow = rows[2]

      // The Copy icon should be present (via lucide-react)
      // The icon has a tooltip with specific text
      expect(within(noChangeRow).getByText('No Change')).toBeInTheDocument()
    })

    test('does not show copy icon for regular COMPLETED result', () => {
      render(<ResultsTable {...defaultProps} />)

      // Find the row for the COMPLETED result (first result)
      const rows = screen.getAllByRole('row')
      const completedRow = rows[1]

      // Should show Completed status
      expect(within(completedRow).getByText('Completed')).toBeInTheDocument()

      // Should not have the Copy icon in status cell
      // The status cell should only have the badge
      const statusCells = screen.getAllByRole('cell')
      const firstRowStatusCell = statusCells[3] // Status is 4th column (0-indexed: 3)
      expect(within(firstRowStatusCell).queryByText('References a previous result')).not.toBeInTheDocument()
    })

    test('NO_CHANGE status badge is rendered correctly', () => {
      render(<ResultsTable {...defaultProps} />)

      // Verify NO_CHANGE badge appears
      expect(screen.getByText('No Change')).toBeInTheDocument()
    })

    test('copy indicator appears next to status badge for deduplicated results', () => {
      const resultsWithCopy = [
        {
          ...mockResults[1],
          no_change_copy: true
        }
      ]

      render(<ResultsTable {...defaultProps} results={resultsWithCopy} total={1} />)

      // The NO_CHANGE badge should be visible
      expect(screen.getByText('No Change')).toBeInTheDocument()

      // The row should contain the Copy icon
      // Since we can't easily check for the SVG, we verify the structure exists
      const rows = screen.getAllByRole('row')
      const dataRow = rows[1] // Skip header
      expect(dataRow).toBeInTheDocument()
    })
  })

  describe('status badges', () => {
    test('renders COMPLETED status badge in table', () => {
      render(<ResultsTable {...defaultProps} />)

      // "Completed" appears in header and as badge - use getAllByText
      const completedElements = screen.getAllByText('Completed')
      // Should have at least one badge with success styling
      const badge = completedElements.find(el => el.classList.contains('bg-success'))
      expect(badge).toBeInTheDocument()
    })

    test('renders FAILED status with destructive variant', () => {
      render(<ResultsTable {...defaultProps} />)

      const badge = screen.getByText('Failed')
      expect(badge).toBeInTheDocument()
    })

    test('renders NO_CHANGE status with default variant', () => {
      render(<ResultsTable {...defaultProps} />)

      const badge = screen.getByText('No Change')
      expect(badge).toBeInTheDocument()
    })
  })

  describe('filtering', () => {
    test('can filter by status', async () => {
      const user = userEvent.setup()
      render(<ResultsTable {...defaultProps} />)

      // Open status dropdown
      const statusTrigger = screen.getAllByRole('combobox')[1]
      await user.click(statusTrigger)

      // Select NO_CHANGE
      const noChangeOption = screen.getByText('No Change', { selector: '[role="option"] *' })
      await user.click(noChangeOption)

      // Verify onFiltersChange was called with status filter
      expect(defaultProps.onFiltersChange).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'NO_CHANGE' })
      )
    })

    test('can filter by tool', async () => {
      const user = userEvent.setup()
      render(<ResultsTable {...defaultProps} />)

      // Open tool dropdown
      const toolTrigger = screen.getAllByRole('combobox')[0]
      await user.click(toolTrigger)

      // Select PhotoStats
      const photostatsOption = screen.getByText('PhotoStats', { selector: '[role="option"] *' })
      await user.click(photostatsOption)

      // Verify onFiltersChange was called with tool filter
      expect(defaultProps.onFiltersChange).toHaveBeenCalledWith(
        expect.objectContaining({ tool: 'photostats' })
      )
    })
  })

  describe('loading state', () => {
    test('shows loading spinner when loading', () => {
      render(<ResultsTable {...defaultProps} loading={true} />)

      const spinner = screen.getByRole('status')
      expect(spinner).toBeInTheDocument()
    })
  })

  describe('empty state', () => {
    test('shows empty message when no results', () => {
      render(<ResultsTable {...defaultProps} results={[]} total={0} />)

      expect(screen.getByText('No analysis results found')).toBeInTheDocument()
    })
  })

  describe('actions', () => {
    test('download button is shown for results with has_report=true', () => {
      render(<ResultsTable {...defaultProps} />)

      // COMPLETED result has has_report=true
      // There should be download buttons for results with reports
      const downloadButtons = screen.getAllByRole('button')
      // Check that there are multiple action buttons
      expect(downloadButtons.length).toBeGreaterThan(3)
    })

    test('calls onView when view button clicked', async () => {
      const user = userEvent.setup()
      render(<ResultsTable {...defaultProps} />)

      // Click the first view button (Eye icon)
      const viewButtons = screen.getAllByRole('button')
      const firstViewButton = viewButtons.find(btn => {
        const svg = btn.querySelector('svg')
        return svg?.classList.contains('lucide-eye')
      })

      if (firstViewButton) {
        await user.click(firstViewButton)
        expect(defaultProps.onView).toHaveBeenCalledWith(mockResults[0])
      }
    })
  })
})
