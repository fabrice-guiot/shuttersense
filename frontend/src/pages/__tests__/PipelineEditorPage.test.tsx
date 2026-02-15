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
      version: 1,
      nodes: [],
      edges: [],
      validation: { is_valid: true, errors: [], warnings: [] },
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
    exportPipeline: vi.fn(),
    loading: false,
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

    // In new mode, shows create form with Pipeline Details card
    expect(screen.getByText('Pipeline Details')).toBeDefined()
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
