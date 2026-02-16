import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import PipelinesPage from '../PipelinesPage'

vi.mock('@/hooks/usePipelines', () => ({
  usePipelines: vi.fn().mockReturnValue({
    pipelines: [],
    loading: false,
    error: null,
    deletePipeline: vi.fn(),
    activatePipeline: vi.fn(),
    deactivatePipeline: vi.fn(),
    setDefaultPipeline: vi.fn(),
    unsetDefaultPipeline: vi.fn(),
    refetch: vi.fn(),
  }),
  usePipelineStats: vi.fn().mockReturnValue({
    stats: null,
    refetch: vi.fn(),
  }),
  usePipelineExport: vi.fn().mockReturnValue({
    downloadYaml: vi.fn(),
    downloading: false,
  }),
  usePipelineImport: vi.fn().mockReturnValue({
    importYaml: vi.fn(),
    importing: false,
  }),
}))

vi.mock('@/hooks/useTools', () => ({
  useTools: vi.fn().mockReturnValue({
    runTool: vi.fn(),
  }),
}))

vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: vi.fn().mockReturnValue({
    stats: [],
    setStats: vi.fn(),
    clearStats: vi.fn(),
  }),
}))

vi.mock('@/components/pipelines/PipelineList', () => ({
  PipelineList: ({
    onCreateNew,
    onImport,
  }: {
    onCreateNew: () => void
    onImport: () => void
  }) => (
    <div data-testid="pipeline-list">
      <button onClick={onCreateNew}>New Pipeline</button>
      <button onClick={onImport}>Import</button>
    </div>
  ),
}))

describe('PipelinesPage', () => {
  test('renders without error', () => {
    render(
      <MemoryRouter>
        <PipelinesPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('pipeline-list')).toBeDefined()
  })

  test('does not show beta banner', () => {
    render(
      <MemoryRouter>
        <PipelinesPage />
      </MemoryRouter>,
    )

    expect(screen.queryByText('Beta Feature:', { exact: false })).toBeNull()
  })

  test('renders pipeline list with create button', () => {
    render(
      <MemoryRouter>
        <PipelinesPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('New Pipeline')).toBeDefined()
    expect(screen.getByText('Import')).toBeDefined()
  })

  test('renders loading state via PipelineList', async () => {
    const { usePipelines } = await import('@/hooks/usePipelines')
    vi.mocked(usePipelines).mockReturnValue({
      pipelines: [],
      loading: true,
      error: null,
      deletePipeline: vi.fn(),
      activatePipeline: vi.fn(),
      deactivatePipeline: vi.fn(),
      setDefaultPipeline: vi.fn(),
      unsetDefaultPipeline: vi.fn(),
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter>
        <PipelinesPage />
      </MemoryRouter>,
    )

    // Page still renders - loading is passed down to PipelineList
    expect(screen.getByTestId('pipeline-list')).toBeDefined()
  })

  test('does not show error alert when no error', () => {
    render(
      <MemoryRouter>
        <PipelinesPage />
      </MemoryRouter>,
    )

    expect(screen.queryByText('Dismiss')).toBeNull()
  })
})
