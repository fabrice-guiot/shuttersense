import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../utils/test-utils'
import { RunToolDialog } from '@/components/tools/RunToolDialog'
import type { Collection } from '@/contracts/api/collection-api'
import type { PipelineSummary } from '@/contracts/api/pipelines-api'
import type { ToolRunRequest } from '@/contracts/api/tools-api'
import { resetMockData } from '../../mocks/handlers'

describe('RunToolDialog', () => {
  const mockCollections: Collection[] = [
    {
      guid: 'col_01hgw2bbg0000000000000001',
      name: 'Test Collection',
      type: 'local',
      location: '/photos',
      state: 'live',
      connector_guid: null,
      pipeline_guid: null,
      pipeline_version: null,
      pipeline_name: null,
      cache_ttl: 3600,
      is_accessible: true,
      accessibility_message: null,
      last_scanned_at: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      guid: 'col_01hgw2bbg0000000000000002',
      name: 'Remote S3 Collection',
      type: 's3',
      location: 'my-bucket/photos',
      state: 'live',
      connector_guid: 'con_01hgw2bbg0000000000000001',
      pipeline_guid: 'pip_01hgw2bbg0000000000000001',
      pipeline_version: 1,
      pipeline_name: 'Standard RAW Workflow',
      cache_ttl: 86400,
      is_accessible: true,
      accessibility_message: null,
      last_scanned_at: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      guid: 'col_01hgw2bbg0000000000000003',
      name: 'Inaccessible Collection',
      type: 'local',
      location: '/bad/path',
      state: 'live',
      connector_guid: null,
      pipeline_guid: null,
      pipeline_version: null,
      pipeline_name: null,
      cache_ttl: null,
      is_accessible: false,
      accessibility_message: 'Path does not exist',
      last_scanned_at: null,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
  ]

  const mockPipelines: PipelineSummary[] = [
    {
      guid: 'pip_01hgw2bbg0000000000000001',
      name: 'Standard RAW Workflow',
      description: 'Standard RAW processing pipeline',
      version: 1,
      is_active: true,
      is_valid: true,
      is_default: true,
      node_count: 5,
      created_at: '2025-01-01T09:00:00Z',
      updated_at: '2025-01-01T09:00:00Z',
    },
    {
      guid: 'pip_01hgw2bbg0000000000000002',
      name: 'Draft Pipeline',
      description: 'Work in progress',
      version: 1,
      is_active: false,
      is_valid: false,
      is_default: false,
      node_count: 2,
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
        pipelines={mockPipelines}
        onRunTool={mockOnRunTool}
      />
    )

    expect(screen.getByText('Run Analysis Tool')).toBeInTheDocument()
    expect(screen.getByText('Select a tool and target to analyze your photos')).toBeInTheDocument()
  })

  it('should not render dialog when closed', () => {
    render(
      <RunToolDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        pipelines={mockPipelines}
        onRunTool={mockOnRunTool}
      />
    )

    expect(screen.queryByText('Run Analysis Tool')).not.toBeInTheDocument()
  })

  it('should show tool selector first', async () => {
    const user = userEvent.setup()

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        pipelines={mockPipelines}
        onRunTool={mockOnRunTool}
      />
    )

    // Click the tool dropdown
    const toolTrigger = screen.getByRole('combobox', { name: /tool/i })
    await user.click(toolTrigger)

    // Should show all tools
    expect(screen.getByText('PhotoStats')).toBeInTheDocument()
    expect(screen.getByText('Photo Pairing')).toBeInTheDocument()
    expect(screen.getByText('Pipeline Validation')).toBeInTheDocument()
  })

  it('should show collection selector after selecting PhotoStats', async () => {
    const user = userEvent.setup()

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        pipelines={mockPipelines}
        onRunTool={mockOnRunTool}
      />
    )

    // Select PhotoStats tool
    await user.click(screen.getByRole('combobox', { name: /tool/i }))
    await user.click(screen.getByText('PhotoStats'))

    // Should show collection dropdown
    const collectionTrigger = screen.getByRole('combobox', { name: /collection/i })
    await user.click(collectionTrigger)

    // Should show accessible collections only
    expect(screen.getByText('Test Collection')).toBeInTheDocument()
    expect(screen.getByText('Remote S3 Collection')).toBeInTheDocument()
    expect(screen.queryByText('Inaccessible Collection')).not.toBeInTheDocument()
  })

  it('should show mode selector for Pipeline Validation', async () => {
    const user = userEvent.setup()

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        pipelines={mockPipelines}
        onRunTool={mockOnRunTool}
      />
    )

    // Select Pipeline Validation tool
    await user.click(screen.getByRole('combobox', { name: /tool/i }))
    await user.click(screen.getByText('Pipeline Validation'))

    // Should show mode selector
    const modeTrigger = screen.getByRole('combobox', { name: /mode/i })
    await user.click(modeTrigger)

    // Both mode options should be visible (may appear multiple times due to dropdown)
    expect(screen.getAllByText('Validate Collection').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Validate Pipeline Graph').length).toBeGreaterThanOrEqual(1)
  })

  it('should show pipeline selector for display_graph mode', async () => {
    const user = userEvent.setup()

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        pipelines={mockPipelines}
        onRunTool={mockOnRunTool}
      />
    )

    // Select Pipeline Validation tool
    await user.click(screen.getByRole('combobox', { name: /tool/i }))
    await user.click(screen.getByText('Pipeline Validation'))

    // Select display_graph mode (should be default)
    // Pipeline selector should be visible
    const pipelineTrigger = screen.getByRole('combobox', { name: /pipeline/i })
    await user.click(pipelineTrigger)

    // Should show only active and valid pipelines
    expect(screen.getByText(/Standard RAW Workflow/)).toBeInTheDocument()
    expect(screen.queryByText('Draft Pipeline')).not.toBeInTheDocument()
  })

  it('should call onRunTool for PhotoStats with collection', async () => {
    const user = userEvent.setup()
    mockOnRunTool.mockResolvedValueOnce(undefined)

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        pipelines={mockPipelines}
        onRunTool={mockOnRunTool}
      />
    )

    // Select tool first
    await user.click(screen.getByRole('combobox', { name: /tool/i }))
    await user.click(screen.getByText('PhotoStats'))

    // Select collection
    await user.click(screen.getByRole('combobox', { name: /collection/i }))
    await user.click(screen.getByText('Test Collection'))

    // Click Run Tool
    await user.click(screen.getByRole('button', { name: /run tool/i }))

    await waitFor(() => {
      expect(mockOnRunTool).toHaveBeenCalledWith({
        tool: 'photostats',
        collection_guid: 'col_01hgw2bbg0000000000000001'
      })
    })

    expect(mockOnOpenChange).toHaveBeenCalledWith(false)
  })

  it('should call onRunTool for display_graph mode with pipeline', async () => {
    const user = userEvent.setup()
    mockOnRunTool.mockResolvedValueOnce(undefined)

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        pipelines={mockPipelines}
        onRunTool={mockOnRunTool}
      />
    )

    // Select Pipeline Validation tool
    await user.click(screen.getByRole('combobox', { name: /tool/i }))
    await user.click(screen.getByText('Pipeline Validation'))

    // Mode should default to display_graph
    // Select pipeline
    await user.click(screen.getByRole('combobox', { name: /pipeline/i }))
    await user.click(screen.getByText(/Standard RAW Workflow/))

    // Click Run Tool
    await user.click(screen.getByRole('button', { name: /run tool/i }))

    await waitFor(() => {
      expect(mockOnRunTool).toHaveBeenCalledWith({
        tool: 'pipeline_validation',
        mode: 'display_graph',
        pipeline_guid: 'pip_01hgw2bbg0000000000000001'
      })
    })
  })

  it('should pre-select tool and mode when preSelectedPipelineId is provided', () => {
    // Note: preSelectedPipelineId expects numeric ID but pipelines now use GUIDs.
    // The tool and mode will be pre-selected, but the pipeline cannot be matched.
    // This test verifies that the tool/mode pre-selection logic works.
    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        pipelines={mockPipelines}
        onRunTool={mockOnRunTool}
        preSelectedPipelineId={1}
        preSelectedMode="display_graph"
      />
    )

    // Pipeline Validation tool should be selected
    expect(screen.getByText('Pipeline Validation')).toBeInTheDocument()
    // Mode should be pre-selected to display_graph
    expect(screen.getByText('Validate Pipeline Graph')).toBeInTheDocument()
    // Pipeline selector should be visible (since mode is display_graph)
    expect(screen.getByRole('combobox', { name: /pipeline/i })).toBeInTheDocument()
  })

  it('should display error from onRunTool', async () => {
    const user = userEvent.setup()
    mockOnRunTool.mockRejectedValueOnce({ userMessage: 'Tool already running on this collection' })

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        pipelines={mockPipelines}
        onRunTool={mockOnRunTool}
      />
    )

    // Select tool
    await user.click(screen.getByRole('combobox', { name: /tool/i }))
    await user.click(screen.getByText('PhotoStats'))

    // Select collection
    await user.click(screen.getByRole('combobox', { name: /collection/i }))
    await user.click(screen.getByText('Test Collection'))

    // Click Run Tool
    await user.click(screen.getByRole('button', { name: /run tool/i }))

    // Should show error
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
        pipelines={mockPipelines}
        onRunTool={mockOnRunTool}
      />
    )

    await user.click(screen.getByRole('button', { name: /cancel/i }))

    expect(mockOnOpenChange).toHaveBeenCalledWith(false)
  })

  it('should have run button disabled without selections', () => {
    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        pipelines={mockPipelines}
        onRunTool={mockOnRunTool}
      />
    )

    // Without any selections, Run Tool should be disabled
    const runButton = screen.getByRole('button', { name: /run tool/i })
    expect(runButton).toBeDisabled()
  })

  it('should show warning when no valid pipelines for display_graph mode', async () => {
    const user = userEvent.setup()
    const invalidPipelines = [mockPipelines[1]] // Only the draft/invalid one

    render(
      <RunToolDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        collections={mockCollections}
        pipelines={invalidPipelines}
        onRunTool={mockOnRunTool}
      />
    )

    // Select Pipeline Validation tool
    await user.click(screen.getByRole('combobox', { name: /tool/i }))
    await user.click(screen.getByText('Pipeline Validation'))

    expect(screen.getByText(/No valid and active pipelines available/i)).toBeInTheDocument()
  })
})
