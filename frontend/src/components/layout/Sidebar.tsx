/**
 * Sidebar Navigation Component
 *
 * Persistent sidebar with navigation menu items and active state highlighting.
 * Uses Lucide icons for visual consistency with the modern design system.
 */

import { Link, useLocation } from 'react-router-dom'
import {
  LayoutGrid,
  Workflow,
  FolderOpen,
  Archive,
  BarChart3,
  Users,
  Plug,
  Settings,
  X,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ============================================================================
// Types
// ============================================================================

export interface MenuItem {
  id: string
  icon: LucideIcon
  label: string
  href: string
  active?: boolean
}

export interface SidebarProps {
  activeItem?: string
  className?: string
  isMobileMenuOpen?: boolean
  onCloseMobileMenu?: () => void
}

// ============================================================================
// Menu Configuration
// ============================================================================

const MENU_ITEMS: Omit<MenuItem, 'active'>[] = [
  { id: 'dashboard', icon: LayoutGrid, label: 'Dashboard', href: '/' },
  { id: 'workflows', icon: Workflow, label: 'Workflows', href: '/workflows' },
  { id: 'collections', icon: FolderOpen, label: 'Collections', href: '/collections' },
  { id: 'assets', icon: Archive, label: 'Assets', href: '/assets' },
  { id: 'analytics', icon: BarChart3, label: 'Analytics', href: '/analytics' },
  { id: 'team', icon: Users, label: 'Team', href: '/team' },
  { id: 'connectors', icon: Plug, label: 'Connectors', href: '/connectors' },
  { id: 'settings', icon: Settings, label: 'Settings', href: '/settings' },
]

// ============================================================================
// Component
// ============================================================================

export function Sidebar({
  activeItem,
  className,
  isMobileMenuOpen = false,
  onCloseMobileMenu
}: SidebarProps) {
  const location = useLocation()

  // Determine active menu item based on current route
  const getActiveItem = () => {
    if (activeItem) return activeItem

    // Match route to menu item
    const currentPath = location.pathname
    const matchedItem = MENU_ITEMS.find(item => {
      // Exact match for root
      if (item.href === '/' && currentPath === '/') return true
      // Prefix match for other routes
      if (item.href !== '/' && currentPath.startsWith(item.href)) return true
      return false
    })

    return matchedItem?.id || 'dashboard'
  }

  const activeId = getActiveItem()

  return (
    <>
      {/* Mobile overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm md:hidden"
          onClick={onCloseMobileMenu}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'flex h-screen w-56 flex-col border-r border-sidebar-border bg-sidebar',
          // Mobile: fixed positioned, slide in from left
          'fixed left-0 top-0 z-50 transition-transform duration-300 md:relative md:translate-x-0',
          isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
          className
        )}
      >
      {/* Logo / Header */}
      <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-6">
        <div className="flex items-center gap-2">
          <Archive className="h-6 w-6 text-sidebar-primary" />
          <span className="text-lg font-semibold text-sidebar-foreground">
            Photo Admin
          </span>
        </div>
        {/* Mobile close button */}
        <button
          onClick={onCloseMobileMenu}
          className="md:hidden rounded-md p-1 hover:bg-sidebar-accent transition-colors"
          aria-label="Close menu"
        >
          <X className="h-5 w-5 text-sidebar-foreground" />
        </button>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {MENU_ITEMS.map((item) => {
          const isActive = item.id === activeId
          const Icon = item.icon

          return (
            <Link
              key={item.id}
              to={item.href}
              onClick={() => onCloseMobileMenu?.()}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                'hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'text-sidebar-foreground'
              )}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border px-3 py-3">
        <div className="text-xs text-muted-foreground px-3">
          v1.0.0
        </div>
      </div>
    </aside>
    </>
  )
}

export default Sidebar
