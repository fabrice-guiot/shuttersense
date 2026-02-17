import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import PipelineEditorPage from '../PipelineEditorPage'

vi.mock('@/hooks/usePipelines', () => ({
  usePipeline: vi.fn().mockReturnValue({
    pipeline: {
      guid: 'pip_01hgw2bbg00000000000000001',
      name: 'Test Pipeline',
      description: 'A test pipeline',
      is_active: true,
      is_valid: true,
      version: 1,
      nodes: [
        { id: 'capture_1', type: 'capture', properties: { sample_filename: 'AB3D0001', filename_regex: '([A-Z0-9]{4})([0-9]{4})', camera_id_group: '1' } },
        { id: 'file_raw', type: 'file', properties: { extension: '.dng' } },
        { id: 'done', type: 'termination', properties: { termination_type: 'Black Box Archive' } },
      ],
      edges: [
        { from: 'capture_1', to: 'file_raw' },
        { from: 'file_raw', to: 'done' },
      ],
      validation_errors: [],
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-15T00:00:00Z',
      audit: null,
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
    currentVersion: 1,
    latestVersion: 1,
    history: [],
    loadVersion: vi.fn(),
  }),
  usePipelines: vi.fn().mockReturnValue({
    pipelines: [],
    loading: false,
    createPipeline: vi.fn(),
    updatePipeline: vi.fn(),
    deletePipeline: vi.fn(),
  }),
  usePipelineExport: vi.fn().mockReturnValue({
    downloadYaml: vi.fn(),
    downloading: false,
  }),
}))

vi.mock('@/components/GuidBadge', () => ({
  GuidBadge: ({ guid }: { guid: string }) => <span>{guid}</span>,
}))

vi.mock('@/components/audit', () => ({
  AuditTrailSection: () => <div data-testid="audit-section" />,
}))

vi.mock('@/components/layout/MainLayout', () => ({
  MainLayout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/pipelines/graph/PipelineGraphView', () => ({
  PipelineGraphView: () => <div data-testid="pipeline-graph-view" />,
}))

vi.mock('@/components/pipelines/graph/PropertyPanel', () => ({
  PropertyPanel: () => <div data-testid="property-panel" />,
}))

vi.mock('@/components/pipelines/graph/PipelineGraphEditor', async () => {
  const React = await import('react')
  const PipelineGraphEditor = React.forwardRef((_props: any, _ref: any) => (
    <div data-testid="pipeline-graph-editor" />
  ))
  PipelineGraphEditor.displayName = 'PipelineGraphEditor'
  return { PipelineGraphEditor, default: PipelineGraphEditor }
})

vi.mock('@xyflow/react', () => ({
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

function renderViewMode() {
  return render(
    <MemoryRouter initialEntries={['/pipelines/pip_01hgw2bbg00000000000000001']}>
      <Routes>
        <Route path="/pipelines/:id" element={<PipelineEditorPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

function renderNewMode() {
  return render(
    <MemoryRouter initialEntries={['/pipelines/new']}>
      <Routes>
        <Route path="/pipelines/new" element={<PipelineEditorPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('PipelineEditorPage', () => {
  test('renders in view mode without errors', () => {
    renderViewMode()

    expect(screen.getByText('Test Pipeline')).toBeDefined()
  })

  test('renders pipeline graph view in view mode', () => {
    renderViewMode()

    expect(screen.getByTestId('pipeline-graph-view')).toBeDefined()
  })

  test('does not show beta banner in view mode', () => {
    renderViewMode()

    expect(screen.queryByText('Coming Soon:', { exact: false })).toBeNull()
    expect(screen.queryByText('Beta Feature:', { exact: false })).toBeNull()
  })

  test('renders pipeline description in view mode', () => {
    renderViewMode()

    expect(screen.getByText('A test pipeline')).toBeDefined()
  })

  test('renders back button', () => {
    renderViewMode()

    expect(screen.getByText('Back to Pipelines')).toBeDefined()
  })

  test('renders edit button in view mode', () => {
    renderViewMode()

    const matches = screen.getAllByText('Edit Pipeline')
    expect(matches.length).toBeGreaterThanOrEqual(1)
  })

  test('renders new pipeline form', () => {
    renderNewMode()

    // In new mode, shows graph editor with name input and Create button
    expect(screen.getByLabelText(/name/i)).toBeDefined()
    expect(screen.getByText('Create')).toBeDefined()
    expect(screen.getByTestId('pipeline-graph-editor')).toBeDefined()
  })

  test('does not show beta banner in edit mode', () => {
    renderNewMode()

    expect(screen.queryByText('Beta Feature:', { exact: false })).toBeNull()
  })

  test('shows loading state', async () => {
    const { usePipeline } = await import('@/hooks/usePipelines')
    vi.mocked(usePipeline).mockReturnValue({
      pipeline: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
    } as any)

    renderViewMode()

    expect(screen.queryByText('Test Pipeline')).toBeNull()
  })
})
