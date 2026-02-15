import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SettingsPage from '../SettingsPage'

const mockUseIsSuperAdmin = vi.fn().mockReturnValue(false)

vi.mock('@/hooks/useAuth', () => ({
  useIsSuperAdmin: () => mockUseIsSuperAdmin(),
}))

vi.mock('@/components/settings/ConnectorsTab', () => ({
  ConnectorsTab: () => <div data-testid="connectors-tab" />,
}))

vi.mock('@/components/settings/ConfigTab', () => ({
  ConfigTab: () => <div data-testid="config-tab" />,
}))

vi.mock('@/components/settings/CategoriesTab', () => ({
  CategoriesTab: () => <div data-testid="categories-tab" />,
}))

vi.mock('@/components/settings/TokensTab', () => ({
  TokensTab: () => <div data-testid="tokens-tab" />,
}))

vi.mock('@/components/settings/TeamsTab', () => ({
  TeamsTab: () => <div data-testid="teams-tab" />,
}))

vi.mock('@/components/settings/ReleaseManifestsTab', () => ({
  ReleaseManifestsTab: () => <div data-testid="release-manifests-tab" />,
}))

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseIsSuperAdmin.mockReturnValue(false)
  })

  test('renders base tab labels', () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )

    // Tab text appears in both TabsTrigger and the responsive Select dropdown
    expect(screen.getAllByText('Configuration').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Categories').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Connectors').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('API Tokens').length).toBeGreaterThanOrEqual(1)
  })

  test('does not show admin tabs for non-super-admin', () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )

    expect(screen.queryByText('Teams')).toBeNull()
    expect(screen.queryByText('Release Manifests')).toBeNull()
  })

  test('shows admin tabs for super admin', async () => {
    mockUseIsSuperAdmin.mockReturnValue(true)

    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )

    expect(screen.getAllByText('Teams').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Release Manifests').length).toBeGreaterThanOrEqual(1)
  })

  test('renders config tab content by default', () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('config-tab')).toBeDefined()
  })
})
