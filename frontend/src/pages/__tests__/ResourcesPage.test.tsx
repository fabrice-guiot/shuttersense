/**
 * Tests for ResourcesPage
 *
 * Verifies tab rendering, URL-synced tab switching, and default tab behavior.
 * Issue #217 - Pipeline-Driven Analysis Tools (US4)
 */

import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ResourcesPage from '../ResourcesPage'

// Mock tab components to isolate page-level behavior
vi.mock('@/components/cameras/CamerasTab', () => ({
  CamerasTab: () => <div data-testid="cameras-tab">Cameras Tab Content</div>,
}))

vi.mock('@/components/pipelines/PipelinesTab', () => ({
  PipelinesTab: () => <div data-testid="pipelines-tab">Pipelines Tab Content</div>,
}))

vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: vi.fn().mockReturnValue({
    stats: [],
    setStats: vi.fn(),
    clearStats: vi.fn(),
  }),
}))

describe('ResourcesPage', () => {
  test('renders Cameras and Pipelines tab triggers', () => {
    render(
      <MemoryRouter initialEntries={['/resources?tab=cameras']}>
        <ResourcesPage />
      </MemoryRouter>,
    )

    // Each tab label appears in desktop TabsTrigger + mobile Select dropdown
    expect(screen.getAllByText('Cameras').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Pipelines').length).toBeGreaterThanOrEqual(1)
  })

  test('shows Cameras tab content by default', () => {
    render(
      <MemoryRouter initialEntries={['/resources?tab=cameras']}>
        <ResourcesPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('cameras-tab')).toBeDefined()
  })

  test('shows Pipelines tab content when tab=pipelines', () => {
    render(
      <MemoryRouter initialEntries={['/resources?tab=pipelines']}>
        <ResourcesPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('pipelines-tab')).toBeDefined()
  })

  test('defaults to cameras tab when no tab param provided', () => {
    render(
      <MemoryRouter initialEntries={['/resources']}>
        <ResourcesPage />
      </MemoryRouter>,
    )

    // CamerasTab should render since it's the default
    expect(screen.getByTestId('cameras-tab')).toBeDefined()
  })

  test('falls back to cameras tab with invalid tab param', () => {
    render(
      <MemoryRouter initialEntries={['/resources?tab=invalid']}>
        <ResourcesPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('cameras-tab')).toBeDefined()
  })
})
