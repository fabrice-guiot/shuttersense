import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from '../LoginPage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn().mockReturnValue({
    isAuthenticated: false,
    isLoading: false,
  }),
}))

vi.mock('@/services/auth', () => ({
  getProviders: vi.fn().mockResolvedValue({
    providers: [
      { name: 'google', display_name: 'Google', icon: 'google' },
    ],
  }),
}))

vi.mock('@/components/auth/OAuthButton', () => ({
  OAuthButton: ({ provider }: { provider: { display_name: string } }) => (
    <button>{provider.display_name}</button>
  ),
}))

vi.mock('@/components/auth/AuthRedirectHandler', () => ({
  AUTH_RETURN_URL_KEY: 'auth_return_url',
}))

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders login card with branding', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('ShutterSense.ai')).toBeDefined()
    expect(screen.getByText('Capture. Process. Analyze.')).toBeDefined()
  })

  test('renders OAuth provider buttons', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Google')).toBeDefined()
    })
  })

  test('shows no providers message when empty', async () => {
    const { getProviders } = await import('@/services/auth')
    vi.mocked(getProviders).mockResolvedValueOnce({ providers: [] })

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/No login providers are configured/)).toBeDefined()
    })
  })

  test('shows access limited footer text', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/Access is limited to pre-approved users/)).toBeDefined()
    })
  })
})
