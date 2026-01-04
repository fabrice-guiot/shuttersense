import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../utils/test-utils'
import { RunToolDialog } from '@/components/tools/RunToolDialog'
import type { Collection } from '@/contracts/api/collection-api'
import type { ToolRunRequest } from '@/contracts/api/tools-api'
import { resetMockData } from '../../mocks/handlers'

describe('RunToolDialog', () => {
  const mockCollections: Collection[] = [
    {
      id: 1,
      name: 'Test Collection',
      type: 'local',
      location: '/photos',
      state: 'live',
      connector_id: null,
      cache_ttl: 3600,
      is_accessible: true,
      accessibility_message: null,
      last_scanned_at: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      id: 2,
      name: 'Remote S3 Collection',
      type: 's3',
      location: 'my-bucket/photos',
      state: 'live',
      connector_id: 1,
      cache_ttl: 86400,
      is_accessible: true,
      accessibility_message: null,
      last_scanned_at: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      id: 3,
      name: 'Inaccessible Collection',
      type: 'local',
      location: '/bad/path',
      state: 'live',
      connector_id: null,
      cache_ttl: null,
      is_accessible: false,
      accessibility_message: 'Path does not exist',
      last_scanned_at: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
  ]

  const mockOnOpenChange = vi.fn()
  const mockOnRunTool = vi.fn<(request: ToolRunRequest) => Promise<void>>()

  beforeEach(() => {
    resetMockData()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('should render dialog when open', () => {
    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        onRunTool={mockOnRunTool}
      />
    )

    expect(screen.getByText('Run Analysis Tool')).toBeInTheDocument()
    expect(screen.getByText('Select a collection and tool to analyze your photos')).toBeInTheDocument()
  })

  it('should not render dialog when closed', () => {
    render(
      <RunToolDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        onRunTool={mockOnRunTool}
      />
    )

    expect(screen.queryByText('Run Analysis Tool')).not.toBeInTheDocument()
  })

  it('should only show accessible collections in dropdown', async () => {
    const user = userEvent.setup()

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        onRunTool={mockOnRunTool}
      />
    )

    // Click the collection dropdown
    const collectionTrigger = screen.getByRole('combobox', { name: /collection/i })
    await user.click(collectionTrigger)

    // Should show accessible collections only
    expect(screen.getByText('Test Collection')).toBeInTheDocument()
    expect(screen.getByText('Remote S3 Collection')).toBeInTheDocument()
    // Inaccessible collection should NOT be shown
    expect(screen.queryByText('Inaccessible Collection')).not.toBeInTheDocument()
  })

  it('should show warning when no accessible collections', () => {
    const inaccessibleOnly = [mockCollections[2]] // Only the inaccessible one

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={inaccessibleOnly}
        onRunTool={mockOnRunTool}
      />
    )

    expect(screen.getByText(/No accessible collections available/i)).toBeInTheDocument()
  })

  it('should pre-select collection when preSelectedCollectionId is provided', () => {
    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        onRunTool={mockOnRunTool}
        preSelectedCollectionId={1}
      />
    )

    // The collection name should be shown in the trigger
    expect(screen.getByText('Test Collection')).toBeInTheDocument()
  })

  it('should show tool descriptions when selected', async () => {
    const user = userEvent.setup()

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        onRunTool={mockOnRunTool}
      />
    )

    // Click the tool dropdown
    const toolTrigger = screen.getByRole('combobox', { name: /tool/i })
    await user.click(toolTrigger)

    // Select PhotoStats
    await user.click(screen.getByText('PhotoStats'))

    // Should show description
    expect(screen.getByText(/Analyze photo collection for orphaned files/i)).toBeInTheDocument()
  })

  it('should call onRunTool when form is submitted', async () => {
    const user = userEvent.setup()
    mockOnRunTool.mockResolvedValueOnce(undefined)

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        onRunTool={mockOnRunTool}
      />
    )

    // Select collection
    await user.click(screen.getByRole('combobox', { name: /collection/i }))
    await user.click(screen.getByText('Test Collection'))

    // Select tool
    await user.click(screen.getByRole('combobox', { name: /tool/i }))
    await user.click(screen.getByText('PhotoStats'))

    // Click Run Tool
    await user.click(screen.getByRole('button', { name: /run tool/i }))

    await waitFor(() => {
      expect(mockOnRunTool).toHaveBeenCalledWith({
        collection_id: 1,
        tool: 'photostats'
      })
    })

    // Should close dialog on success
    expect(mockOnOpenChange).toHaveBeenCalledWith(false)
  })

  it('should show error when tool selection is missing', async () => {
    const user = userEvent.setup()

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        onRunTool={mockOnRunTool}
        preSelectedCollectionId={1}
      />
    )

    // The Run Tool button should be disabled when no tool is selected
    const runButton = screen.getByRole('button', { name: /run tool/i })
    expect(runButton).toBeDisabled()

    expect(mockOnRunTool).not.toHaveBeenCalled()
  })

  it('should show error for pipeline_validation tool', async () => {
    const user = userEvent.setup()

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        onRunTool={mockOnRunTool}
        preSelectedCollectionId={1}
      />
    )

    // Select tool
    await user.click(screen.getByRole('combobox', { name: /tool/i }))
    await user.click(screen.getByText('Pipeline Validation'))

    // Click Run Tool
    await user.click(screen.getByRole('button', { name: /run tool/i }))

    // Should show "coming soon" error
    await waitFor(() => {
      expect(screen.getByText(/Pipeline validation requires selecting a pipeline/i)).toBeInTheDocument()
    })

    expect(mockOnRunTool).not.toHaveBeenCalled()
  })

  it('should display error from onRunTool', async () => {
    const user = userEvent.setup()
    mockOnRunTool.mockRejectedValueOnce({ userMessage: 'Tool already running on this collection' })

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        onRunTool={mockOnRunTool}
        preSelectedCollectionId={1}
      />
    )

    // Select tool
    await user.click(screen.getByRole('combobox', { name: /tool/i }))
    await user.click(screen.getByText('PhotoStats'))

    // Click Run Tool
    await user.click(screen.getByRole('button', { name: /run tool/i }))

    // Should show error from the rejection
    await waitFor(() => {
      expect(screen.getByText(/Tool already running on this collection/i)).toBeInTheDocument()
    })
  })

  it('should call onOpenChange when Cancel is clicked', async () => {
    const user = userEvent.setup()

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        onRunTool={mockOnRunTool}
      />
    )

    await user.click(screen.getByRole('button', { name: /cancel/i }))

    expect(mockOnOpenChange).toHaveBeenCalledWith(false)
  })

  it('should have run button disabled without selections', () => {
    // Test that Run Tool button is disabled when nothing is selected
    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        onRunTool={mockOnRunTool}
      />
    )

    // Without any selections, Run Tool should be disabled
    const runButton = screen.getByRole('button', { name: /run tool/i })
    expect(runButton).toBeDisabled()
  })
})
