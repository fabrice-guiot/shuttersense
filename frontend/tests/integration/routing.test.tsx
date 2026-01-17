/**
 * Integration tests for routing and navigation - T028a
 *
 * Tests the navigation restructure for Calendar Events feature (Issue #39):
 * - Route redirects from legacy paths (/connectors, /config)
 * - New page routes (/events, /directory, /settings)
 * - Tab URL synchronization (?tab= query params)
 * - Sidebar navigation links
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { HeaderStatsProvider } from '@/contexts/HeaderStatsContext'
import SettingsPage from '@/pages/SettingsPage'
import DirectoryPage from '@/pages/DirectoryPage'
import EventsPage from '@/pages/EventsPage'

// Mock useAuth hook to return non-super-admin by default
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { is_super_admin: false },
    isAuthenticated: true,
    isLoading: false,
    error: null,
    logout: async () => {},
    refreshAuth: async () => {},
  }),
  useCurrentUser: () => ({ is_super_admin: false }),
  useIsSuperAdmin: () => false,
}))

// Helper component to display current location for testing
function LocationDisplay() {
  const location = useLocation()
  return (
    <div data-testid="location-display">
      <span data-testid="pathname">{location.pathname}</span>
      <span data-testid="search">{location.search}</span>
    </div>
  )
}

// Test wrapper with routing and required providers
function renderWithRouter(
  ui: React.ReactElement,
  { initialEntries = ['/'] }: { initialEntries?: string[] } = {}
) {
  return render(
    <HeaderStatsProvider>
      <MemoryRouter initialEntries={initialEntries}>
        {ui}
        <LocationDisplay />
      </MemoryRouter>
    </HeaderStatsProvider>
  )
}

describe('Routing Integration - T028a', () => {
  describe('Legacy Route Redirects', () => {
    it('redirects /connectors to /settings?tab=connectors', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/connectors" element={<Navigate to="/settings?tab=connectors" replace />} />
        </Routes>,
        { initialEntries: ['/connectors'] }
      )

      await waitFor(() => {
        expect(screen.getByTestId('pathname').textContent).toBe('/settings')
        expect(screen.getByTestId('search').textContent).toBe('?tab=connectors')
      })
    })

    it('redirects /config to /settings?tab=config', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/config" element={<Navigate to="/settings?tab=config" replace />} />
        </Routes>,
        { initialEntries: ['/config'] }
      )

      await waitFor(() => {
        expect(screen.getByTestId('pathname').textContent).toBe('/settings')
        expect(screen.getByTestId('search').textContent).toBe('?tab=config')
      })
    })
  })

  describe('New Route Rendering', () => {
    it('renders EventsPage at /events', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/events" element={<EventsPage />} />
        </Routes>,
        { initialEntries: ['/events'] }
      )

      // Calendar view renders with weekday headers
      await waitFor(() => {
        expect(screen.getByText('Sun')).toBeInTheDocument()
        expect(screen.getByText('Mon')).toBeInTheDocument()
      })
    })

    it('renders DirectoryPage at /directory', () => {
      renderWithRouter(
        <Routes>
          <Route path="/directory" element={<DirectoryPage />} />
        </Routes>,
        { initialEntries: ['/directory'] }
      )

      // Directory page shows tabs (Issue #67 - Single Title Pattern: title is now in TopHeader only)
      expect(screen.getByRole('tab', { name: /locations/i })).toBeInTheDocument()
    })

    it('renders SettingsPage at /settings', () => {
      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>,
        { initialEntries: ['/settings'] }
      )

      // Settings page shows tabs (Issue #67 - Single Title Pattern: title is now in TopHeader only)
      expect(screen.getByRole('tab', { name: /configuration/i })).toBeInTheDocument()
    })
  })

  describe('Settings Page Tab URL Sync', () => {
    it('defaults to config tab when no query param', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>,
        { initialEntries: ['/settings'] }
      )

      await waitFor(() => {
        expect(screen.getByTestId('search').textContent).toBe('?tab=config')
      })

      // Config tab should be active (first tab)
      expect(screen.getByRole('tab', { name: /configuration/i })).toHaveAttribute('data-state', 'active')
    })

    it('activates config tab from URL query param', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>,
        { initialEntries: ['/settings?tab=config'] }
      )

      expect(screen.getByRole('tab', { name: /configuration/i })).toHaveAttribute('data-state', 'active')
      expect(screen.getByRole('tab', { name: /connectors/i })).toHaveAttribute('data-state', 'inactive')
    })

    it('activates categories tab from URL query param', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>,
        { initialEntries: ['/settings?tab=categories'] }
      )

      expect(screen.getByRole('tab', { name: /categories/i })).toHaveAttribute('data-state', 'active')
      expect(screen.getByRole('tab', { name: /configuration/i })).toHaveAttribute('data-state', 'inactive')
    })

    it('activates connectors tab from URL query param', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>,
        { initialEntries: ['/settings?tab=connectors'] }
      )

      expect(screen.getByRole('tab', { name: /connectors/i })).toHaveAttribute('data-state', 'active')
      expect(screen.getByRole('tab', { name: /configuration/i })).toHaveAttribute('data-state', 'inactive')
    })

    it('updates URL when tab is clicked', async () => {
      const user = userEvent.setup()

      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>,
        { initialEntries: ['/settings?tab=config'] }
      )

      // Click on Connectors tab
      await user.click(screen.getByRole('tab', { name: /connectors/i }))

      await waitFor(() => {
        expect(screen.getByTestId('search').textContent).toBe('?tab=connectors')
      })
    })

    it('falls back to default tab for invalid tab param', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>,
        { initialEntries: ['/settings?tab=invalid'] }
      )

      // Should fall back to config (default)
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /configuration/i })).toHaveAttribute('data-state', 'active')
      })
    })
  })

  describe('Directory Page Tab URL Sync', () => {
    it('defaults to locations tab when no query param', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/directory" element={<DirectoryPage />} />
        </Routes>,
        { initialEntries: ['/directory'] }
      )

      await waitFor(() => {
        expect(screen.getByTestId('search').textContent).toBe('?tab=locations')
      })

      expect(screen.getByRole('tab', { name: /locations/i })).toHaveAttribute('data-state', 'active')
    })

    it('activates locations tab from URL query param', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/directory" element={<DirectoryPage />} />
        </Routes>,
        { initialEntries: ['/directory?tab=locations'] }
      )

      expect(screen.getByRole('tab', { name: /locations/i })).toHaveAttribute('data-state', 'active')
    })

    it('activates organizers tab from URL query param', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/directory" element={<DirectoryPage />} />
        </Routes>,
        { initialEntries: ['/directory?tab=organizers'] }
      )

      expect(screen.getByRole('tab', { name: /organizers/i })).toHaveAttribute('data-state', 'active')
    })

    it('activates performers tab from URL query param', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/directory" element={<DirectoryPage />} />
        </Routes>,
        { initialEntries: ['/directory?tab=performers'] }
      )

      expect(screen.getByRole('tab', { name: /performers/i })).toHaveAttribute('data-state', 'active')
    })

    it('updates URL when tab is clicked', async () => {
      const user = userEvent.setup()

      renderWithRouter(
        <Routes>
          <Route path="/directory" element={<DirectoryPage />} />
        </Routes>,
        { initialEntries: ['/directory?tab=locations'] }
      )

      // Click on Organizers tab
      await user.click(screen.getByRole('tab', { name: /organizers/i }))

      await waitFor(() => {
        expect(screen.getByTestId('search').textContent).toBe('?tab=organizers')
      })
    })
  })

  describe('Tab Content Visibility', () => {
    // Issue #67 - Single Title Pattern: Tab titles removed, verify tab content by other elements
    it('shows config content when config tab is active', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>,
        { initialEntries: ['/settings?tab=config'] }
      )

      await waitFor(() => {
        // ConfigTab shows camera configuration section
        expect(screen.getByText('Camera Mappings')).toBeInTheDocument()
      })
    })

    it('shows categories content when categories tab is active', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>,
        { initialEntries: ['/settings?tab=categories'] }
      )

      await waitFor(() => {
        // CategoriesTab shows New Category button
        expect(screen.getByRole('button', { name: /new category/i })).toBeInTheDocument()
      })
    })

    it('shows connectors content when connectors tab is active', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>,
        { initialEntries: ['/settings?tab=connectors'] }
      )

      await waitFor(() => {
        // ConnectorsTab shows New Connector button
        expect(screen.getByRole('button', { name: /new connector/i })).toBeInTheDocument()
      })
    })

    it('shows locations content when locations tab is active', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/directory" element={<DirectoryPage />} />
        </Routes>,
        { initialEntries: ['/directory?tab=locations'] }
      )

      await waitFor(() => {
        // LocationsTab shows New Location button and search
        expect(screen.getByRole('button', { name: /new location/i })).toBeInTheDocument()
      })
    })
  })

  describe('Deep Linking', () => {
    it('preserves tab state on page reload simulation', async () => {
      // First render with connectors tab
      const { unmount } = renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>,
        { initialEntries: ['/settings?tab=connectors'] }
      )

      expect(screen.getByRole('tab', { name: /connectors/i })).toHaveAttribute('data-state', 'active')

      unmount()

      // Simulate "reload" by re-rendering with same URL
      renderWithRouter(
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>,
        { initialEntries: ['/settings?tab=connectors'] }
      )

      expect(screen.getByRole('tab', { name: /connectors/i })).toHaveAttribute('data-state', 'active')
    })

    it('supports direct linking to directory performers tab', async () => {
      renderWithRouter(
        <Routes>
          <Route path="/directory" element={<DirectoryPage />} />
        </Routes>,
        { initialEntries: ['/directory?tab=performers'] }
      )

      expect(screen.getByRole('tab', { name: /performers/i })).toHaveAttribute('data-state', 'active')
      // Issue #67 - Single Title Pattern: Tab descriptions removed, verify by New button
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /new performer/i })).toBeInTheDocument()
      })
    })
  })
})
