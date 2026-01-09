/**
 * Layout Component Contracts
 *
 * Defines prop interfaces for layout components (Sidebar, TopHeader, MainLayout)
 */

import type { LucideIcon } from 'lucide-react'
import { LayoutGrid, Workflow, FolderOpen, Archive, BarChart3, Users, Settings } from 'lucide-react'
import type { ReactNode } from 'react'

// ============================================================================
// Sidebar Component
// ============================================================================

export interface SidebarProps {
  /**
   * Currently active menu item (matches MenuItem.id)
   */
  activeItem?: string

  /**
   * Additional CSS classes
   */
  className?: string
}

export interface MenuItem {
  /**
   * Unique identifier for the menu item
   */
  id: string

  /**
   * Lucide icon component
   */
  icon: LucideIcon

  /**
   * Display label
   */
  label: string

  /**
   * Navigation href (React Router path)
   */
  href: string

  /**
   * Whether this item is currently active
   * Typically determined by matching current route
   */
  active?: boolean
}

/**
 * Menu items configuration
 * Defined in Sidebar component
 */
export const MENU_ITEMS: Omit<MenuItem, 'active'>[] = [
  { id: 'dashboard', icon: LayoutGrid, label: 'Dashboard', href: '/' },
  { id: 'workflows', icon: Workflow, label: 'Workflows', href: '/workflows' },
  { id: 'collections', icon: FolderOpen, label: 'Collections', href: '/collections' },
  { id: 'assets', icon: Archive, label: 'Assets', href: '/assets' },
  { id: 'analytics', icon: BarChart3, label: 'Analytics', href: '/analytics' },
  { id: 'team', icon: Users, label: 'Team', href: '/team' },
  { id: 'settings', icon: Settings, label: 'Settings', href: '/settings' }
]

// ============================================================================
// TopHeader Component
// ============================================================================

export interface TopHeaderProps {
  /**
   * Page title displayed in header
   */
  pageTitle: string

  /**
   * Optional icon displayed next to title
   */
  pageIcon?: LucideIcon

  /**
   * Statistics to display in header right section
   * Example: [{ label: 'Collections', value: '42' }]
   */
  stats?: HeaderStat[]

  /**
   * Additional CSS classes
   */
  className?: string
}

export interface HeaderStat {
  /**
   * Stat label (e.g., "Collections", "Storage")
   */
  label: string

  /**
   * Stat value (e.g., "42", "1.2 TB")
   * Can be string or number
   */
  value: string | number
}

// ============================================================================
// MainLayout Component
// ============================================================================

export interface MainLayoutProps {
  /**
   * Page content (typically a page component)
   */
  children: ReactNode

  /**
   * Optional page title for TopHeader
   * If not provided, header shows generic title
   */
  pageTitle?: string

  /**
   * Optional page icon for TopHeader
   */
  pageIcon?: LucideIcon

  /**
   * Optional stats for TopHeader
   */
  stats?: HeaderStat[]

  /**
   * Additional CSS classes for content area
   */
  className?: string
}

/**
 * Layout structure:
 *
 * <MainLayout>
 *   <Sidebar /> (fixed, left, 14rem width)
 *   <div className="flex-1 flex flex-col">
 *     <TopHeader /> (full width, 4rem height)
 *     <div className="flex-1 overflow-auto">
 *       {children} (scrollable content)
 *     </div>
 *   </div>
 * </MainLayout>
 */

// ============================================================================
// User Profile (TopHeader right section)
// ============================================================================

export interface UserProfile {
  /**
   * User initials for avatar (e.g., "JD")
   * Placeholder until authentication is implemented
   */
  initials: string

  /**
   * Optional full name
   */
  name?: string

  /**
   * Optional email
   */
  email?: string
}

/**
 * Default user profile (placeholder)
 * Note: Authentication is out of scope for v1.0 - single-user deployment assumed
 */
export const DEFAULT_USER_PROFILE: UserProfile = {
  initials: 'JD',
  name: 'John Doe',
  email: 'john.doe@example.com'
}
