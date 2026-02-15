/**
 * Tests for ResultsTable component.
 *
 * Merged from:
 * - src/components/results/ResultsTable.test.tsx (NO_CHANGE, audit, filtering)
 * - tests/components/results/ResultsTable.test.tsx (actions, pagination, duration)
 *
 * Part of Issue #92: Storage Optimization for Analysis Results.
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { ResultsTable } from '../ResultsTable'
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
    no_change_copy: false,
    connector_guid: null,
    connector_name: null,
    audit: {
      created_at: '2025-01-01T10:05:00Z',
      created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Alice Smith', email: 'alice@example.com' },
      updated_at: '2025-01-01T10:05:00Z',
      updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Alice Smith', email: 'alice@example.com' },
    },
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
    no_change_copy: true,
    connector_guid: null,
    connector_name: null,
    audit: {
      created_at: '2025-01-02T10:01:00Z',
      created_by: { guid: 'usr_01hgw2bbg00000000000000002', display_name: 'Bob Jones', email: 'bob@example.com' },
      updated_at: '2025-01-02T10:01:00Z',
      updated_by: { guid: 'usr_01hgw2bbg00000000000000002', display_name: 'Bob Jones', email: 'bob@example.com' },
    },
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
    no_change_copy: false,
    connector_guid: null,
    connector_name: null,
  }
]

const renderWithRouter = (ui: React.ReactElement) =>
  render(<BrowserRouter>{ui}</BrowserRouter>)

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

  describe('rendering', () => {
    test('renders table with results', () => {
      renderWithRouter(<ResultsTable {...defaultProps} />)

      const table = within(screen.getByTestId('desktop-view'))
      expect(table.getByText('Collection')).toBeInTheDocument()
      expect(table.getByText('Tool')).toBeInTheDocument()
      expect(table.getByText('Status')).toBeInTheDocument()
      expect(table.getByText('Files')).toBeInTheDocument()
      expect(table.getByText('Issues')).toBeInTheDocument()
      expect(table.getByText('Duration')).toBeInTheDocument()

      const testCollectionCells = table.getAllByText('Test Collection')
      expect(testCollectionCells.length).toBeGreaterThanOrEqual(1)
      expect(table.getByText('Another Collection')).toBeInTheDocument()
    })

    test('shows loading spinner when loading', () => {
      renderWithRouter(<ResultsTable {...defaultProps} loading={true} />)
      expect(screen.getByRole('status')).toBeInTheDocument()
      expect(screen.queryByText('Collection')).not.toBeInTheDocument()
    })

    test('shows empty state when no results', () => {
      renderWithRouter(<ResultsTable {...defaultProps} results={[]} total={0} />)
      expect(screen.getByText('No analysis results found')).toBeInTheDocument()
    })

    test('formats duration correctly', () => {
      renderWithRouter(<ResultsTable {...defaultProps} />)
      const table = within(screen.getByTestId('desktop-view'))
      expect(table.getByText('5m 0s')).toBeInTheDocument()
      expect(table.getByText('30.0s')).toBeInTheDocument()
    })
  })

  describe('NO_CHANGE indicator', () => {
    test('shows copy icon for NO_CHANGE result with no_change_copy=true', () => {
      renderWithRouter(<ResultsTable {...defaultProps} />)
      const rows = screen.getAllByRole('row')
      const noChangeRow = rows[2]
      expect(within(noChangeRow).getByText('No Change')).toBeInTheDocument()
    })

    test('does not show copy icon for regular COMPLETED result', () => {
      renderWithRouter(<ResultsTable {...defaultProps} />)
      const rows = screen.getAllByRole('row')
      const completedRow = rows[1]
      expect(within(completedRow).getByText('Completed')).toBeInTheDocument()
    })

    test('NO_CHANGE status badge is rendered correctly', () => {
      renderWithRouter(<ResultsTable {...defaultProps} />)
      expect(screen.getAllByText('No Change')[0]).toBeInTheDocument()
    })
  })

  describe('status badges', () => {
    test('renders COMPLETED status badge', () => {
      renderWithRouter(<ResultsTable {...defaultProps} />)
      const completedElements = screen.getAllByText('Completed')
      const badge = completedElements.find(el => el.classList.contains('bg-success'))
      expect(badge).toBeInTheDocument()
    })

    test('renders FAILED status with destructive variant', () => {
      renderWithRouter(<ResultsTable {...defaultProps} />)
      expect(screen.getAllByText('Failed')[0]).toBeInTheDocument()
    })

    test('renders NO_CHANGE status with default variant', () => {
      renderWithRouter(<ResultsTable {...defaultProps} />)
      expect(screen.getAllByText('No Change')[0]).toBeInTheDocument()
    })
  })

  describe('Created by column', () => {
    test('shows user display name when audit data is available', () => {
      renderWithRouter(<ResultsTable {...defaultProps} />)
      expect(screen.getByText('Alice Smith')).toBeInTheDocument()
      expect(screen.getByText('Bob Jones')).toBeInTheDocument()
    })

    test('shows em dash when audit data is not available', () => {
      renderWithRouter(<ResultsTable {...defaultProps} results={[mockResults[2]]} total={1} />)
      const rows = screen.getAllByRole('row')
      const dataRow = rows[1]
      expect(within(dataRow).getByText('\u2014')).toBeInTheDocument()
    })

    test('falls back to email when display_name is null', () => {
      const resultsWithEmailOnly: AnalysisResultSummary[] = [
        {
          ...mockResults[0],
          audit: {
            created_at: '2025-01-01T10:05:00Z',
            created_by: { guid: 'usr_01hgw2bbg00000000000000003', display_name: null, email: 'fallback@example.com' },
            updated_at: '2025-01-01T10:05:00Z',
            updated_by: null,
          },
        }
      ]
      renderWithRouter(<ResultsTable {...defaultProps} results={resultsWithEmailOnly} total={1} />)
      expect(screen.getByText('fallback@example.com')).toBeInTheDocument()
    })
  })

  describe('actions', () => {
    test('calls onView when view button clicked', async () => {
      const user = userEvent.setup()
      renderWithRouter(<ResultsTable {...defaultProps} />)

      const viewButtons = screen.getAllByRole('button').filter(btn =>
        btn.querySelector('svg.lucide-eye')
      )
      await user.click(viewButtons[0])
      expect(defaultProps.onView).toHaveBeenCalledWith(mockResults[0])
    })

    test('shows download button only for results with reports', () => {
      renderWithRouter(<ResultsTable {...defaultProps} />)
      const downloadButtons = screen.getAllByRole('button').filter(btn =>
        btn.querySelector('svg.lucide-download')
      )
      // 2 results with has_report=true × 2 views (desktop + mobile) = 4
      expect(downloadButtons).toHaveLength(4)
    })

    test('calls onDownloadReport when download button is clicked', async () => {
      const user = userEvent.setup()
      renderWithRouter(<ResultsTable {...defaultProps} />)
      const downloadButtons = screen.getAllByRole('button').filter(btn =>
        btn.querySelector('svg.lucide-download')
      )
      await user.click(downloadButtons[0])
      expect(defaultProps.onDownloadReport).toHaveBeenCalledWith(mockResults[0])
    })

    test('opens delete confirmation dialog', async () => {
      const user = userEvent.setup()
      renderWithRouter(<ResultsTable {...defaultProps} />)
      const deleteButtons = screen.getAllByRole('button').filter(btn =>
        btn.querySelector('svg.lucide-trash-2')
      )
      await user.click(deleteButtons[0])
      expect(screen.getByText('Delete Result')).toBeInTheDocument()
      expect(screen.getByText(/Are you sure you want to delete/i)).toBeInTheDocument()
    })

    test('calls onDelete when delete is confirmed', async () => {
      const user = userEvent.setup()
      renderWithRouter(<ResultsTable {...defaultProps} />)
      const deleteButtons = screen.getAllByRole('button').filter(btn =>
        btn.querySelector('svg.lucide-trash-2')
      )
      await user.click(deleteButtons[0])
      const confirmButton = screen.getByRole('button', { name: /^Delete$/i })
      await user.click(confirmButton)
      expect(defaultProps.onDelete).toHaveBeenCalledWith(mockResults[0])
    })

    test('closes delete dialog on cancel', async () => {
      const user = userEvent.setup()
      renderWithRouter(<ResultsTable {...defaultProps} />)
      const deleteButtons = screen.getAllByRole('button').filter(btn =>
        btn.querySelector('svg.lucide-trash-2')
      )
      await user.click(deleteButtons[0])
      const cancelButton = screen.getByRole('button', { name: /Cancel/i })
      await user.click(cancelButton)
      await waitFor(() => {
        expect(screen.queryByText('Delete Result')).not.toBeInTheDocument()
      })
      expect(defaultProps.onDelete).not.toHaveBeenCalled()
    })
  })

  describe('filtering', () => {
    test('has filter dropdowns available', () => {
      renderWithRouter(<ResultsTable {...defaultProps} />)
      expect(screen.getByText('Tool:')).toBeInTheDocument()
      expect(screen.getByText('Status:')).toBeInTheDocument()
      const comboboxes = screen.getAllByRole('combobox')
      expect(comboboxes.length).toBeGreaterThanOrEqual(2)
    })

    test('can filter by status', async () => {
      const user = userEvent.setup()
      renderWithRouter(<ResultsTable {...defaultProps} />)
      const statusTrigger = screen.getAllByRole('combobox')[1]
      await user.click(statusTrigger)
      const noChangeOption = screen.getByText('No Change', { selector: '[role="option"] *' })
      await user.click(noChangeOption)
      expect(defaultProps.onFiltersChange).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'NO_CHANGE' })
      )
    })

    test('can filter by tool', async () => {
      const user = userEvent.setup()
      renderWithRouter(<ResultsTable {...defaultProps} />)
      const toolTrigger = screen.getAllByRole('combobox')[0]
      await user.click(toolTrigger)
      const photostatsOption = screen.getByText('PhotoStats', { selector: '[role="option"] *' })
      await user.click(photostatsOption)
      expect(defaultProps.onFiltersChange).toHaveBeenCalledWith(
        expect.objectContaining({ tool: 'photostats' })
      )
    })
  })

  describe('pagination', () => {
    test('handles pagination navigation', async () => {
      const user = userEvent.setup()
      renderWithRouter(<ResultsTable {...defaultProps} total={50} limit={20} />)
      expect(screen.getByText(/1-20 of 50/i)).toBeInTheDocument()
      expect(screen.getByText(/Page 1 of 3/i)).toBeInTheDocument()

      const nextButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-right')
      )
      if (nextButton) {
        await user.click(nextButton)
        expect(defaultProps.onPageChange).toHaveBeenCalledWith(2)
      }
    })

    test('shows rows per page selector', () => {
      renderWithRouter(<ResultsTable {...defaultProps} />)
      expect(screen.getByText('Rows per page:')).toBeInTheDocument()
    })

    test('disables previous button on first page', () => {
      renderWithRouter(<ResultsTable {...defaultProps} page={1} />)
      const prevButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-left')
      )
      expect(prevButton).toBeDisabled()
    })

    test('disables next button on last page', () => {
      renderWithRouter(<ResultsTable {...defaultProps} page={1} total={3} limit={20} />)
      const nextButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-right')
      )
      expect(nextButton).toBeDisabled()
    })
  })
})
