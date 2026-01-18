/**
 * Sidebar Component Tests
 *
 * Tests for sidebar collapse functionality and state persistence.
 * Issue #41: UX improvement for tablet - force collapse menu to hamburger mode
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Sidebar } from '@/components/layout/Sidebar'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

// Helper to render sidebar with router
const renderSidebar = (props: Partial<React.ComponentProps<typeof Sidebar>> = {}) => {
  return render(
    <MemoryRouter>
      <Sidebar {...props} />
    </MemoryRouter>
  )
}

describe('Sidebar', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders the sidebar with navigation items', () => {
      renderSidebar()

      expect(screen.getByText('ShutterSense.ai')).toBeInTheDocument()
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.getByText('Events')).toBeInTheDocument()
      expect(screen.getByText('Collections')).toBeInTheDocument()
      expect(screen.getByText('Directory')).toBeInTheDocument()
      expect(screen.getByText('Settings')).toBeInTheDocument()
    })

    it('renders version in footer', async () => {
      renderSidebar()

      await waitFor(() => {
        expect(screen.getByText('v1.0.0')).toBeInTheDocument()
      })
    })
  })

  describe('Collapse Functionality (Issue #41)', () => {
    it('renders collapse button when onCollapse is provided and not collapsed', () => {
      const onCollapse = vi.fn()
      renderSidebar({ onCollapse, isCollapsed: false })

      const collapseButton = screen.getByLabelText('Collapse sidebar')
      expect(collapseButton).toBeInTheDocument()
    })

    it('does not render collapse button when already collapsed', () => {
      const onCollapse = vi.fn()
      renderSidebar({ onCollapse, isCollapsed: true })

      expect(screen.queryByLabelText('Collapse sidebar')).not.toBeInTheDocument()
    })

    it('calls onCollapse when collapse button is clicked', () => {
      const onCollapse = vi.fn()
      renderSidebar({ onCollapse, isCollapsed: false })

      const collapseButton = screen.getByLabelText('Collapse sidebar')
      fireEvent.click(collapseButton)

      expect(onCollapse).toHaveBeenCalledTimes(1)
    })

    it('renders Pin button when collapsed and onPin is provided', () => {
      const onPin = vi.fn()
      renderSidebar({ onPin, isCollapsed: true })

      const pinButton = screen.getByLabelText('Pin sidebar')
      expect(pinButton).toBeInTheDocument()
    })

    it('does not render Pin button when not collapsed', () => {
      const onPin = vi.fn()
      renderSidebar({ onPin, isCollapsed: false })

      expect(screen.queryByLabelText('Pin sidebar')).not.toBeInTheDocument()
    })

    it('calls onPin when Pin button is clicked', () => {
      const onPin = vi.fn()
      renderSidebar({ onPin, isCollapsed: true })

      const pinButton = screen.getByLabelText('Pin sidebar')
      fireEvent.click(pinButton)

      expect(onPin).toHaveBeenCalledTimes(1)
    })
  })

  describe('Mobile Menu', () => {
    it('renders close button for mobile menu', () => {
      renderSidebar({ isMobileMenuOpen: true, onCloseMobileMenu: vi.fn() })

      expect(screen.getByLabelText('Close menu')).toBeInTheDocument()
    })

    it('calls onCloseMobileMenu when close button is clicked', () => {
      const onCloseMobileMenu = vi.fn()
      renderSidebar({ isMobileMenuOpen: true, onCloseMobileMenu })

      const closeButton = screen.getByLabelText('Close menu')
      fireEvent.click(closeButton)

      expect(onCloseMobileMenu).toHaveBeenCalledTimes(1)
    })
  })

  describe('Navigation', () => {
    it('applies active styles to the current route item', () => {
      render(
        <MemoryRouter initialEntries={['/collections']}>
          <Sidebar />
        </MemoryRouter>
      )

      const collectionsLink = screen.getByRole('link', { name: /collections/i })
      expect(collectionsLink).toHaveClass('bg-sidebar-accent')
    })

    it('closes mobile menu when navigation item is clicked', () => {
      const onCloseMobileMenu = vi.fn()
      renderSidebar({ isMobileMenuOpen: true, onCloseMobileMenu })

      const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
      fireEvent.click(dashboardLink)

      expect(onCloseMobileMenu).toHaveBeenCalled()
    })
  })
})
