import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { renderHook } from '@testing-library/react'
import { AuthProvider, useAuthContext } from '../AuthContext'
import { getMe, logout as logoutApi } from '@/services/auth'
import type { UserInfo } from '@/contracts/api/auth-api'

vi.mock('@/services/auth', () => ({
  getMe: vi.fn(),
  logout: vi.fn(),
}))

const mockUser: UserInfo = {
  user_guid: 'usr_01hgw2bbg00000000000000001',
  email: 'test@example.com',
  team_guid: 'ten_01hgw2bbg00000000000000001',
  team_name: 'Test Team',
  display_name: 'Test User',
  picture_url: null,
  is_super_admin: false,
  first_name: 'Test',
  last_name: 'User',
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Prevent actual navigation
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
    })
  })

  describe('AuthProvider', () => {
    test('renders children', async () => {
      vi.mocked(getMe).mockResolvedValue({ authenticated: true, user: mockUser })

      render(
        <AuthProvider>
          <div>Child Content</div>
        </AuthProvider>,
      )

      expect(screen.getByText('Child Content')).toBeDefined()
    })

    test('checks auth on mount and sets user', async () => {
      vi.mocked(getMe).mockResolvedValue({ authenticated: true, user: mockUser })

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: AuthProvider,
      })

      // Initially loading
      expect(result.current.isLoading).toBe(true)

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.user).toEqual(mockUser)
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.error).toBeNull()
      expect(getMe).toHaveBeenCalledOnce()
    })

    test('sets user to null when not authenticated', async () => {
      vi.mocked(getMe).mockResolvedValue({ authenticated: false, user: null })

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
    })

    test('handles auth check failure with error', async () => {
      const error = new Error('Network error')
      ;(error as any).userMessage = 'Failed to connect'
      vi.mocked(getMe).mockRejectedValue(error)

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.error).toBe('Failed to connect')
      // User state preserved (null initially)
      expect(result.current.user).toBeNull()
    })

    test('handles auth check failure with default error message', async () => {
      vi.mocked(getMe).mockRejectedValue(new Error('some error'))

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.error).toBe('Failed to check authentication status')
    })

    test('logout clears user and redirects', async () => {
      vi.mocked(getMe).mockResolvedValue({ authenticated: true, user: mockUser })
      vi.mocked(logoutApi).mockResolvedValue({ success: true, message: 'Logged out' })

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true)
      })

      await act(async () => {
        await result.current.logout()
      })

      expect(logoutApi).toHaveBeenCalledOnce()
      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      expect(window.location.href).toBe('/login')
    })

    test('logout clears user even if API call fails', async () => {
      vi.mocked(getMe).mockResolvedValue({ authenticated: true, user: mockUser })
      vi.mocked(logoutApi).mockRejectedValue(new Error('API error'))

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true)
      })

      await act(async () => {
        await result.current.logout()
      })

      expect(result.current.user).toBeNull()
      expect(window.location.href).toBe('/login')
    })

    test('refreshAuth re-checks auth status', async () => {
      vi.mocked(getMe).mockResolvedValue({ authenticated: true, user: mockUser })

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true)
      })

      // Clear mock and set up new response
      vi.mocked(getMe).mockResolvedValue({ authenticated: false, user: null })

      await act(async () => {
        await result.current.refreshAuth()
      })

      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      // Once on mount + once on refresh
      expect(getMe).toHaveBeenCalledTimes(2)
    })
  })

  describe('useAuthContext', () => {
    test('throws when used outside AuthProvider', () => {
      // Suppress console.error for expected error
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

      expect(() => {
        renderHook(() => useAuthContext())
      }).toThrow('useAuthContext must be used within an AuthProvider')

      spy.mockRestore()
    })
  })
})
