import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import CollectionsPage from '../CollectionsPage'

vi.mock('@/hooks/useCollections', () => ({
  useCollections: vi.fn().mockReturnValue({
    collections: [],
    loading: false,
    error: null,
    search: '',
    setSearch: vi.fn(),
    filters: {},
    setFilters: vi.fn(),
    fetchCollections: vi.fn(),
    createCollection: vi.fn(),
    updateCollection: vi.fn(),
    deleteCollection: vi.fn(),
    testCollection: vi.fn(),
  }),
  useCollectionStats: vi.fn().mockReturnValue({
    stats: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('@/hooks/useConnectors', () => ({
  useConnectors: vi.fn().mockReturnValue({ connectors: [] }),
}))

vi.mock('@/hooks/usePipelines', () => ({
  usePipelines: vi.fn().mockReturnValue({ pipelines: [] }),
}))

vi.mock('@/hooks/useTools', () => ({
  useTools: vi.fn().mockReturnValue({ runAllTools: vi.fn() }),
}))

vi.mock('@/hooks/useAgentPoolStatus', () => ({
  useAgentPoolStatus: vi.fn().mockReturnValue({
    poolStatus: { online_count: 1 },
  }),
}))

vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: vi.fn().mockReturnValue({
    stats: [],
    setStats: vi.fn(),
    clearStats: vi.fn(),
  }),
}))

vi.mock('@/components/collections/CollectionList', () => ({
  CollectionList: () => <div data-testid="collection-list" />,
}))

vi.mock('@/components/collections/FiltersSection', () => ({
  FiltersSection: () => <div data-testid="filters-section" />,
}))

vi.mock('@/components/collections/CollectionForm', () => ({
  default: () => <div data-testid="collection-form" />,
}))

vi.mock('@/components/GuidBadge', () => ({
  GuidBadge: () => <span />,
}))

vi.mock('@/services/collections', () => ({
  clearInventoryCache: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    loading: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('CollectionsPage', () => {
  test('renders New Collection button', () => {
    render(
      <MemoryRouter>
        <CollectionsPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('New Collection')).toBeDefined()
  })

  test('renders collection list and filters', () => {
    render(
      <MemoryRouter>
        <CollectionsPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('collection-list')).toBeDefined()
    expect(screen.getByTestId('filters-section')).toBeDefined()
  })

  test('does not show agent warning when agents available', () => {
    render(
      <MemoryRouter>
        <CollectionsPage />
      </MemoryRouter>,
    )

    expect(screen.queryByText('No agents available')).toBeNull()
  })

  test('shows agent warning when no agents available', async () => {
    const { useAgentPoolStatus } = await import('@/hooks/useAgentPoolStatus')
    vi.mocked(useAgentPoolStatus).mockReturnValue({
      poolStatus: { online_count: 0 } as any,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter>
        <CollectionsPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('No agents available')).toBeDefined()
  })
})
