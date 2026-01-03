/**
 * Main Layout Component
 *
 * Composes Sidebar + TopHeader + content area into a unified layout.
 * Provides consistent structure across all pages of the application.
 */

import { useState, type ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { Sidebar } from './Sidebar'
import { TopHeader } from './TopHeader'
import { cn } from '@/lib/utils'
import { HeaderStatsProvider, useHeaderStats } from '@/contexts/HeaderStatsContext'
import { useSidebarCollapse } from '@/hooks/useSidebarCollapse'

// ============================================================================
// Types
// ============================================================================

export interface MainLayoutProps {
  /**
   * Page content (typically a page component)
   */
  children: ReactNode

  /**
   * Optional page title for TopHeader
   * If not provided, defaults to "Photo Admin"
   */
  pageTitle?: string

  /**
   * Optional page icon for TopHeader
   */
  pageIcon?: LucideIcon

  /**
   * Additional CSS classes for content area
   */
  className?: string
}

// ============================================================================
// Inner Layout Component (uses context)
// ============================================================================

interface MainLayoutInnerProps extends MainLayoutProps {
  onOpenMobileMenu: () => void
  onCloseMobileMenu: () => void
  isMobileMenuOpen: boolean
  // Collapse state for tablet screens (Issue #41)
  isCollapsed: boolean
  onCollapse: () => void
  onPin: () => void
}

function MainLayoutInner({
  children,
  pageTitle = 'Photo Admin',
  pageIcon,
  className,
  onOpenMobileMenu,
  onCloseMobileMenu,
  isMobileMenuOpen,
  isCollapsed,
  onCollapse,
  onPin,
}: MainLayoutInnerProps) {
  // Get stats from context (set by page components)
  const { stats } = useHeaderStats()

  return (
    <div className="flex h-screen w-full bg-background">
      {/* Sidebar: Fixed left navigation with collapse support (Issue #41) */}
      <Sidebar
        isMobileMenuOpen={isMobileMenuOpen}
        onCloseMobileMenu={onCloseMobileMenu}
        isCollapsed={isCollapsed}
        onCollapse={onCollapse}
        onPin={onPin}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col">
        {/* TopHeader: Page title, stats, notifications, user profile */}
        <TopHeader
          pageTitle={pageTitle}
          pageIcon={pageIcon}
          stats={stats}
          onOpenMobileMenu={onOpenMobileMenu}
          isSidebarCollapsed={isCollapsed}
        />

        {/* Scrollable Content Area */}
        <main className={cn('flex-1 overflow-auto p-4 md:p-6', className)}>
          {/* Max-width container for ultra-wide monitors */}
          <div className="mx-auto w-full max-w-[2560px]">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * MainLayout provides the application shell:
 *
 * Layout Structure:
 * ┌─────────────┬──────────────────────────────┐
 * │             │ TopHeader (4rem height)      │
 * │  Sidebar    ├──────────────────────────────┤
 * │  (14rem)    │                              │
 * │             │  Content Area (scrollable)   │
 * │             │                              │
 * └─────────────┴──────────────────────────────┘
 */
export function MainLayout({
  children,
  pageTitle = 'Photo Admin',
  pageIcon,
  className,
}: MainLayoutProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  // Sidebar collapse state with localStorage persistence (Issue #41)
  const { isCollapsed, collapse, expand } = useSidebarCollapse()

  const handleOpenMobileMenu = () => setIsMobileMenuOpen(true)
  const handleCloseMobileMenu = () => setIsMobileMenuOpen(false)

  return (
    <HeaderStatsProvider>
      <MainLayoutInner
        pageTitle={pageTitle}
        pageIcon={pageIcon}
        className={className}
        onOpenMobileMenu={handleOpenMobileMenu}
        onCloseMobileMenu={handleCloseMobileMenu}
        isMobileMenuOpen={isMobileMenuOpen}
        isCollapsed={isCollapsed}
        onCollapse={collapse}
        onPin={expand}
      >
        {children}
      </MainLayoutInner>
    </HeaderStatsProvider>
  )
}

export default MainLayout
