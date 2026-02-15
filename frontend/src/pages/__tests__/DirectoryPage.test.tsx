import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DirectoryPage from '../DirectoryPage'

vi.mock('@/hooks/useCategories', () => ({
  useCategories: vi.fn().mockReturnValue({ categories: [] }),
}))

vi.mock('@/components/directory/LocationsTab', () => ({
  LocationsTab: () => <div data-testid="locations-tab">Locations Content</div>,
}))

vi.mock('@/components/directory/OrganizersTab', () => ({
  OrganizersTab: () => <div data-testid="organizers-tab">Organizers Content</div>,
}))

vi.mock('@/components/directory/PerformersTab', () => ({
  PerformersTab: () => <div data-testid="performers-tab">Performers Content</div>,
}))

describe('DirectoryPage', () => {
  test('renders tab labels', () => {
    render(
      <MemoryRouter>
        <DirectoryPage />
      </MemoryRouter>,
    )

    // Tab text appears in both TabsTrigger and the responsive Select dropdown
    expect(screen.getAllByText('Locations').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Organizers').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Performers').length).toBeGreaterThanOrEqual(1)
  })

  test('renders locations tab content by default', () => {
    render(
      <MemoryRouter>
        <DirectoryPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('locations-tab')).toBeDefined()
  })
})
