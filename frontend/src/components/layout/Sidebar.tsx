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
  Plug,
  Settings,
  X,
  ChevronLeft,
  Pin,
  ChartNoAxesCombined,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useVersion } from '@/hooks/useVersion'

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
  /**
   * Whether the sidebar is collapsed (tablet hamburger mode via user preference)
   * Issue #41: Allow manual collapse on tablet screens
   */
  isCollapsed?: boolean
  /**
   * Callback when collapse button is clicked (collapse sidebar to hamburger)
   */
  onCollapse?: () => void
  /**
   * Callback when pin button is clicked (restore sidebar from hamburger)
   */
  onPin?: () => void
}

// ============================================================================
// Menu Configuration
// ============================================================================

const MENU_ITEMS: Omit<MenuItem, 'active'>[] = [
  { id: 'dashboard', icon: LayoutGrid, label: 'Dashboard', href: '/' },
  { id: 'collections', icon: FolderOpen, label: 'Collections', href: '/collections' },
  { id: 'connectors', icon: Plug, label: 'Connectors', href: '/connectors' },
  { id: 'pipelines', icon: Workflow, label: 'Pipelines', href: '/pipelines' },
  { id: 'analytics', icon: ChartNoAxesCombined, label: 'Analytics', href: '/analytics' },
  { id: 'config', icon: Settings, label: 'Config', href: '/config' },
]

// ============================================================================
// Component
// ============================================================================

export function Sidebar({
  activeItem,
  className,
  isMobileMenuOpen = false,
  onCloseMobileMenu,
  isCollapsed = false,
  onCollapse,
  onPin
}: SidebarProps) {
  const location = useLocation()
  const { version } = useVersion()

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
      {/* Overlay - shown when mobile menu is open (on mobile or when collapsed on tablet+) */}
      {isMobileMenuOpen && (
        <div
          className={cn(
            'fixed inset-0 z-40 bg-background/80 backdrop-blur-sm',
            // On mobile: always show when menu is open
            // On tablet+: only show when collapsed (hamburger mode)
            isCollapsed ? '' : 'md:hidden'
          )}
          onClick={onCloseMobileMenu}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'flex h-screen w-56 flex-col border-r border-sidebar-border bg-sidebar',
          // Position and transition
          'fixed left-0 top-0 z-50 transition-transform duration-300',
          // On desktop (md+): relative positioning ONLY when not collapsed
          // When collapsed, stay fixed so it doesn't take layout space (Issue #41)
          !isCollapsed && 'md:relative',
          // Visibility logic:
          // - Mobile (<md): show when isMobileMenuOpen, hide otherwise
          // - Tablet/Desktop (md+): show unless isCollapsed (or mobile menu open)
          isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full',
          // On md+, show if not collapsed OR if mobile menu is open (for collapsed+hamburger click)
          isCollapsed
            ? (isMobileMenuOpen ? 'md:translate-x-0' : 'md:-translate-x-full')
            : 'md:translate-x-0',
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
        {/* Header buttons: Pin (for collapsed state) or Close (for mobile menu) */}
        <div className="flex items-center gap-1">
          {/* Pin button - shown when collapsed on tablet (Issue #41) */}
          {isCollapsed && onPin && (
            <button
              onClick={onPin}
              className="hidden md:flex rounded-md p-1 hover:bg-sidebar-accent transition-colors"
              aria-label="Pin sidebar"
              title="Pin sidebar"
            >
              <Pin className="h-5 w-5 text-sidebar-foreground" />
            </button>
          )}
          {/* Close button - shown on mobile */}
          <button
            onClick={onCloseMobileMenu}
            className="md:hidden rounded-md p-1 hover:bg-sidebar-accent transition-colors"
            aria-label="Close menu"
          >
            <X className="h-5 w-5 text-sidebar-foreground" />
          </button>
        </div>
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

      {/* Footer with collapse button */}
      <div className="border-t border-sidebar-border px-3 py-3 flex items-center justify-between">
        <div className="text-xs text-muted-foreground px-3">
          {version}
        </div>
        {/* Collapse button - aligned with version number (Issue #41)
            Only visible on tablet+ (md:) and when not already collapsed */}
        {!isCollapsed && onCollapse && (
          <button
            onClick={onCollapse}
            className={cn(
              'hidden md:flex items-center justify-center',
              'h-6 w-6 rounded-full',
              'bg-sidebar border border-sidebar-border',
              'text-sidebar-foreground hover:bg-sidebar-accent',
              'transition-colors duration-200',
              'shadow-sm'
            )}
            aria-label="Collapse sidebar"
            title="Collapse sidebar"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}
      </div>
    </aside>
    </>
  )
}

export default Sidebar
