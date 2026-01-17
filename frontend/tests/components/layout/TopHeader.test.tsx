/**
 * TopHeader Component Tests
 *
 * Tests for user display, profile picture/initials, and dropdown menu.
 * Issue #73: Teams/Tenants and User Management - Phase 5 (US2)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { TopHeader } from '@/components/layout/TopHeader'
import type { UserInfo } from '@/contracts/api/auth-api'

// Mock useAuth hook
const mockLogout = vi.fn()
const mockNavigate = vi.fn()

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    logout: mockLogout,
    refreshAuth: vi.fn(),
  })),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Import the mocked module to control it
import { useAuth } from '@/hooks/useAuth'

// Helper to set mock user
function setMockUser(user: UserInfo | null) {
  vi.mocked(useAuth).mockReturnValue({
    user,
    isAuthenticated: !!user,
    isLoading: false,
    error: null,
    logout: mockLogout,
    refreshAuth: vi.fn(),
  })
}

// Helper to render TopHeader with router
function renderTopHeader(props: Partial<React.ComponentProps<typeof TopHeader>> = {}) {
  return render(
    <MemoryRouter>
      <TopHeader
        pageTitle="Test Page"
        {...props}
      />
    </MemoryRouter>
  )
}

// Sample user data
const sampleUser: UserInfo = {
  user_guid: 'usr_01234567890abcdefghjkmnpqr',
  email: 'john.doe@example.com',
  team_guid: 'ten_01234567890abcdefghjkmnpqr',
  team_name: 'Test Team',
  display_name: 'John Doe',
  picture_url: null,
  is_super_admin: false,
  first_name: 'John',
  last_name: 'Doe',
}

describe('TopHeader', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setMockUser(null)
  })

  describe('Basic Rendering', () => {
    it('renders page title', () => {
      renderTopHeader({ pageTitle: 'Dashboard' })
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
    })

    it('renders page icon when provided', () => {
      const TestIcon = () => <svg data-testid="test-icon" />
      renderTopHeader({ pageIcon: TestIcon })
      expect(screen.getByTestId('test-icon')).toBeInTheDocument()
    })

    it('renders help tooltip when pageHelp is provided', async () => {
      renderTopHeader({ pageHelp: 'Help text for page' })
      const helpButton = screen.getByLabelText('Page help')
      expect(helpButton).toBeInTheDocument()
    })
  })

  describe('User Display (T047)', () => {
    it('displays user display name when authenticated', () => {
      setMockUser(sampleUser)
      renderTopHeader()

      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })

    it('displays user email when authenticated', () => {
      setMockUser(sampleUser)
      renderTopHeader()

      expect(screen.getByText('john.doe@example.com')).toBeInTheDocument()
    })

    it('displays email prefix when no display name', () => {
      setMockUser({
        ...sampleUser,
        display_name: null,
      })
      renderTopHeader()

      // Should show "john.doe" as display name (email prefix)
      expect(screen.getByText('john.doe')).toBeInTheDocument()
    })

    it('displays initials when no profile picture', () => {
      setMockUser(sampleUser)
      renderTopHeader()

      // "John Doe" -> "JD"
      expect(screen.getByText('JD')).toBeInTheDocument()
    })

    it('displays profile picture when available', () => {
      setMockUser({
        ...sampleUser,
        picture_url: 'https://example.com/photo.jpg',
      })
      renderTopHeader()

      const img = screen.getByRole('img', { name: 'John Doe' })
      expect(img).toBeInTheDocument()
      expect(img).toHaveAttribute('src', 'https://example.com/photo.jpg')
    })

    it('generates initials from email when no display name', () => {
      setMockUser({
        ...sampleUser,
        display_name: null,
      })
      renderTopHeader()

      // Email "john.doe@example.com" -> initials "JO" (first 2 chars of email)
      expect(screen.getByText('JO')).toBeInTheDocument()
    })

    it('generates initials from single-word display name', () => {
      setMockUser({
        ...sampleUser,
        display_name: 'Admin',
      })
      renderTopHeader()

      // "Admin" -> "AD" (first 2 chars)
      expect(screen.getByText('AD')).toBeInTheDocument()
    })
  })

  describe('User Dropdown Menu (T048)', () => {
    it('opens dropdown menu when clicking user avatar', async () => {
      const user = userEvent.setup()
      setMockUser(sampleUser)
      renderTopHeader()

      const avatarButton = screen.getByLabelText('User profile menu')
      await user.click(avatarButton)

      await waitFor(() => {
        expect(screen.getByRole('menuitem', { name: /view profile/i })).toBeInTheDocument()
        expect(screen.getByRole('menuitem', { name: /log out/i })).toBeInTheDocument()
      })
    })

    it('displays user info in dropdown header', async () => {
      const user = userEvent.setup()
      setMockUser(sampleUser)
      renderTopHeader()

      const avatarButton = screen.getByLabelText('User profile menu')
      await user.click(avatarButton)

      await waitFor(() => {
        // Dropdown should show name and email in header
        const dropdownLabels = screen.getAllByText('John Doe')
        expect(dropdownLabels.length).toBeGreaterThanOrEqual(1)
      })
    })

    it('navigates to /profile when View Profile is clicked', async () => {
      const user = userEvent.setup()
      setMockUser(sampleUser)
      renderTopHeader()

      const avatarButton = screen.getByLabelText('User profile menu')
      await user.click(avatarButton)

      const viewProfileOption = await screen.findByRole('menuitem', { name: /view profile/i })
      await user.click(viewProfileOption)

      expect(mockNavigate).toHaveBeenCalledWith('/profile')
    })

    it('calls logout when Log out is clicked', async () => {
      const user = userEvent.setup()
      setMockUser(sampleUser)
      renderTopHeader()

      const avatarButton = screen.getByLabelText('User profile menu')
      await user.click(avatarButton)

      const logoutOption = await screen.findByRole('menuitem', { name: /log out/i })
      await user.click(logoutOption)

      expect(mockLogout).toHaveBeenCalled()
    })
  })

  describe('Stats Display', () => {
    it('renders stats when provided', () => {
      setMockUser(sampleUser)
      renderTopHeader({
        stats: [
          { label: 'Collections', value: 10 },
          { label: 'Events', value: 25 },
        ],
      })

      expect(screen.getByText('Collections')).toBeInTheDocument()
      expect(screen.getByText('10')).toBeInTheDocument()
      expect(screen.getByText('Events')).toBeInTheDocument()
      expect(screen.getByText('25')).toBeInTheDocument()
    })
  })

  describe('Mobile Menu Button', () => {
    it('renders menu button', () => {
      renderTopHeader()
      expect(screen.getByLabelText('Open menu')).toBeInTheDocument()
    })

    it('calls onOpenMobileMenu when menu button is clicked', () => {
      const onOpenMobileMenu = vi.fn()
      renderTopHeader({ onOpenMobileMenu })

      const menuButton = screen.getByLabelText('Open menu')
      fireEvent.click(menuButton)

      expect(onOpenMobileMenu).toHaveBeenCalled()
    })
  })
})
