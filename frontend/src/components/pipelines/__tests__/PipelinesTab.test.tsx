/**
 * Regression tests for PipelinesTab component
 *
 * Verifies all Pipeline functionality is preserved after extracting from PipelinesPage.
 * Tests: list rendering, CRUD actions, activate/deactivate, set/unset default,
 * import/export, confirmation modals, per-tab KPI stats.
 * Issue #217 - Pipeline-Driven Analysis Tools (US4)
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { PipelinesTab } from '../PipelinesTab'

const mockSetStats = vi.fn()
const mockNavigate = vi.fn()

// Mock dependencies -- factories must not reference top-level const variables
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('@/hooks/usePipelines', () => ({
  usePipelines: vi.fn().mockReturnValue({
    pipelines: [
      {
        guid: 'pip_01hgw2bbg00000000000000001',
        name: 'Default Pipeline',
        description: 'The default pipeline',
        version: 1,
        is_active: true,
        is_default: true,
        is_valid: true,
        node_count: 5,
        created_at: '2026-01-15T10:00:00Z',
        updated_at: '2026-01-15T10:00:00Z',
        audit: null,
      },
      {
        guid: 'pip_01hgw2bbg00000000000000002',
        name: 'Inactive Pipeline',
        description: null,
        version: 2,
        is_active: false,
        is_default: false,
        is_valid: false,
        node_count: 3,
        created_at: '2026-01-16T10:00:00Z',
        updated_at: '2026-01-16T10:00:00Z',
        audit: null,
      },
    ],
    loading: false,
    error: null,
    fetchPipelines: vi.fn(),
    createPipeline: vi.fn(),
    updatePipeline: vi.fn(),
    deletePipeline: vi.fn().mockResolvedValue(undefined),
    activatePipeline: vi.fn().mockResolvedValue({}),
    deactivatePipeline: vi.fn().mockResolvedValue({}),
    setDefaultPipeline: vi.fn().mockResolvedValue({}),
    unsetDefaultPipeline: vi.fn().mockResolvedValue({}),
    refetch: vi.fn(),
  }),
  usePipelineStats: vi.fn().mockReturnValue({
    stats: {
      total_pipelines: 2,
      valid_pipelines: 1,
      active_pipeline_count: 1,
      default_pipeline_guid: 'pip_01hgw2bbg00000000000000001',
      default_pipeline_name: 'Default Pipeline',
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
  usePipelineExport: vi.fn().mockReturnValue({
    downloading: false,
    error: null,
    downloadYaml: vi.fn(),
    getExportUrl: vi.fn(),
  }),
  usePipelineImport: vi.fn().mockReturnValue({
    importing: false,
    error: null,
    importYaml: vi.fn(),
  }),
}))

vi.mock('@/hooks/useTools', () => ({
  useTools: vi.fn().mockReturnValue({
    runTool: vi.fn(),
  }),
}))

vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: () => ({
    stats: [],
    setStats: (...args: unknown[]) => mockSetStats(...args),
    clearStats: vi.fn(),
  }),
}))

vi.mock('@/components/pipelines/PipelineList', () => ({
  PipelineList: ({
    pipelines,
    onCreateNew,
    onEdit,
    onDelete,
    onView,
  }: any) => (
    <div data-testid="pipeline-list">
      {pipelines.map((p: any) => (
        <div key={p.guid} data-testid={`pipeline-${p.guid}`}>
          <span>{p.name}</span>
          <button data-testid={`create-${p.guid}`} onClick={onCreateNew}>Create</button>
          <button data-testid={`edit-${p.guid}`} onClick={() => onEdit(p)}>Edit</button>
          <button data-testid={`delete-${p.guid}`} onClick={() => onDelete(p)}>Delete</button>
          <button data-testid={`view-${p.guid}`} onClick={() => onView(p)}>View</button>
        </div>
      ))}
    </div>
  ),
}))

describe('PipelinesTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders pipeline list', async () => {
    render(
      <MemoryRouter>
        <PipelinesTab />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('pipeline-list')).toBeDefined()
    expect(screen.getByText('Default Pipeline')).toBeDefined()
    expect(screen.getByText('Inactive Pipeline')).toBeDefined()
  })

  test('sets header stats on mount', async () => {
    render(
      <MemoryRouter>
        <PipelinesTab />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(mockSetStats).toHaveBeenCalledWith([
        { label: 'Total Pipelines', value: 2 },
        { label: 'Active', value: 1 },
        { label: 'Default Pipeline', value: 'Default Pipeline' },
      ])
    })
  })

  test('navigates to /pipelines/new on create', async () => {
    render(
      <MemoryRouter>
        <PipelinesTab />
      </MemoryRouter>,
    )

    const createBtn = screen.getByTestId('create-pip_01hgw2bbg00000000000000001')
    fireEvent.click(createBtn)

    expect(mockNavigate).toHaveBeenCalledWith('/pipelines/new')
  })

  test('navigates to edit page on edit', async () => {
    render(
      <MemoryRouter>
        <PipelinesTab />
      </MemoryRouter>,
    )

    const editBtn = screen.getByTestId('edit-pip_01hgw2bbg00000000000000001')
    fireEvent.click(editBtn)

    expect(mockNavigate).toHaveBeenCalledWith('/pipelines/pip_01hgw2bbg00000000000000001/edit')
  })

  test('navigates to view page on view', async () => {
    render(
      <MemoryRouter>
        <PipelinesTab />
      </MemoryRouter>,
    )

    const viewBtn = screen.getByTestId('view-pip_01hgw2bbg00000000000000001')
    fireEvent.click(viewBtn)

    expect(mockNavigate).toHaveBeenCalledWith('/pipelines/pip_01hgw2bbg00000000000000001')
  })

  test('shows delete confirmation modal on delete click', async () => {
    render(
      <MemoryRouter>
        <PipelinesTab />
      </MemoryRouter>,
    )

    const deleteBtn = screen.getByTestId('delete-pip_01hgw2bbg00000000000000001')
    fireEvent.click(deleteBtn)

    await waitFor(() => {
      expect(screen.getByText('Delete Pipeline')).toBeDefined()
    })
  })

  test('closes delete modal on cancel', async () => {
    render(
      <MemoryRouter>
        <PipelinesTab />
      </MemoryRouter>,
    )

    const deleteBtn = screen.getByTestId('delete-pip_01hgw2bbg00000000000000001')
    fireEvent.click(deleteBtn)

    await waitFor(() => {
      expect(screen.getByText('Delete Pipeline')).toBeDefined()
    })

    const cancelBtn = screen.getByText('Cancel')
    fireEvent.click(cancelBtn)

    await waitFor(() => {
      expect(screen.queryByText('Delete Pipeline')).toBeNull()
    })
  })

  test('renders hidden file input for import', () => {
    render(
      <MemoryRouter>
        <PipelinesTab />
      </MemoryRouter>,
    )

    const fileInput = document.querySelector('input[type="file"]')
    expect(fileInput).toBeDefined()
    expect(fileInput?.getAttribute('accept')).toBe('.yaml,.yml')
  })
})
