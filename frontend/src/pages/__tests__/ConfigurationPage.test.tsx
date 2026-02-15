import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ConfigurationPage from '../ConfigurationPage'

// ============================================================================
// Mock Hooks
// ============================================================================

vi.mock('@/hooks/useConfig', () => ({
  useConfig: vi.fn().mockReturnValue({
    configuration: {
      cameras: {},
      processing_methods: {},
      extensions: {
        photo_extensions: [],
        metadata_extensions: [],
        require_sidecar: [],
      },
    },
    loading: false,
    error: null,
    fetchConfiguration: vi.fn(),
    createConfigValue: vi.fn(),
    updateConfigValue: vi.fn(),
    deleteConfigValue: vi.fn(),
    startImport: vi.fn(),
    getImportSession: vi.fn(),
    resolveImport: vi.fn(),
    cancelImport: vi.fn(),
    exportConfiguration: vi.fn(),
  }),
  useConfigStats: vi.fn().mockReturnValue({
    stats: null,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: vi.fn().mockReturnValue({
    stats: [],
    setStats: vi.fn(),
    clearStats: vi.fn(),
  }),
}))

// ============================================================================
// Tests
// ============================================================================

describe('ConfigurationPage', () => {
  test('renders without crashing', () => {
    render(
      <MemoryRouter>
        <ConfigurationPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Configuration')).toBeDefined()
  })

  test('renders category section headings', () => {
    render(
      <MemoryRouter>
        <ConfigurationPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Camera Mappings')).toBeDefined()
    expect(screen.getByText('Processing Methods')).toBeDefined()
    expect(screen.getByText('File Extensions')).toBeDefined()
  })

  test('renders category descriptions', () => {
    render(
      <MemoryRouter>
        <ConfigurationPage />
      </MemoryRouter>,
    )

    expect(
      screen.getByText('Map camera IDs to camera names and serial numbers'),
    ).toBeDefined()
    expect(
      screen.getByText('Define processing method codes and descriptions'),
    ).toBeDefined()
    expect(
      screen.getByText('Configure photo and metadata file extensions'),
    ).toBeDefined()
  })

  test('renders Import YAML and Export YAML buttons', () => {
    render(
      <MemoryRouter>
        <ConfigurationPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Import YAML')).toBeDefined()
    expect(screen.getByText('Export YAML')).toBeDefined()
  })

  test('renders Add buttons for cameras and processing methods', () => {
    render(
      <MemoryRouter>
        <ConfigurationPage />
      </MemoryRouter>,
    )

    // Cameras and processing_methods sections each have an Add button
    const addButtons = screen.getAllByText('Add')
    expect(addButtons.length).toBe(2)
  })

  test('shows empty state when no items configured', () => {
    render(
      <MemoryRouter>
        <ConfigurationPage />
      </MemoryRouter>,
    )

    // Cameras and processing_methods have no entries, so they show "No items configured"
    const emptyMessages = screen.getAllByText('No items configured')
    expect(emptyMessages.length).toBe(2)
  })

  test('renders extension keys even when empty', () => {
    render(
      <MemoryRouter>
        <ConfigurationPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('photo_extensions')).toBeDefined()
    expect(screen.getByText('metadata_extensions')).toBeDefined()
    expect(screen.getByText('require_sidecar')).toBeDefined()
  })

  test('displays error alert when error exists', async () => {
    const { useConfig } = await import('@/hooks/useConfig')
    vi.mocked(useConfig).mockReturnValue({
      configuration: null,
      loading: false,
      error: 'Failed to load configuration',
      fetchConfiguration: vi.fn(),
      createConfigValue: vi.fn(),
      updateConfigValue: vi.fn(),
      deleteConfigValue: vi.fn(),
      startImport: vi.fn(),
      getImportSession: vi.fn(),
      resolveImport: vi.fn(),
      cancelImport: vi.fn(),
      exportConfiguration: vi.fn(),
    } as any)

    render(
      <MemoryRouter>
        <ConfigurationPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Failed to load configuration')).toBeDefined()
  })
})
