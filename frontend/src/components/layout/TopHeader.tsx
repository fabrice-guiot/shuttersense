/**
 * Top Header Component
 *
 * Displays page title, contextual stats, notifications, and user profile.
 * Updates dynamically based on current route and page context.
 */

import { Bell, Menu, HelpCircle, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui/tooltip'

// ============================================================================
// Types
// ============================================================================

export interface HeaderStat {
  label: string
  value: string | number
}

export interface UserProfile {
  initials: string
  name?: string
  email?: string
}

export interface TopHeaderProps {
  pageTitle: string
  pageIcon?: LucideIcon
  stats?: HeaderStat[]
  className?: string
  onOpenMobileMenu?: () => void
  /**
   * Whether sidebar is collapsed (Issue #41)
   * When true, show hamburger button even on tablet/desktop
   */
  isSidebarCollapsed?: boolean
  /**
   * Optional help text for the page (Issue #67)
   * When provided, displays a help icon with tooltip next to the page title
   */
  pageHelp?: string
}

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_USER_PROFILE: UserProfile = {
  initials: 'PA',
  name: 'Photo Admin',
  email: 'admin@photoapp.local',
}

// ============================================================================
// Component
// ============================================================================

export function TopHeader({
  pageTitle,
  pageIcon: PageIcon,
  stats = [],
  className,
  onOpenMobileMenu,
  isSidebarCollapsed = false,
  pageHelp
}: TopHeaderProps) {
  return (
    <header
      className={cn(
        'flex h-16 items-center justify-between border-b border-border bg-background px-4 md:px-6',
        className
      )}
    >
      {/* Left: Mobile Menu Button + Page Title & Icon */}
      <div className="flex items-center gap-3">
        {/* Menu button - shown on mobile OR when sidebar is collapsed on tablet+ (Issue #41) */}
        <button
          onClick={onOpenMobileMenu}
          className={cn(
            'rounded-md p-2 hover:bg-accent transition-colors',
            // Show on mobile, or when sidebar is collapsed on tablet+
            isSidebarCollapsed ? 'flex' : 'md:hidden'
          )}
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5 text-foreground" />
        </button>
        {PageIcon && <PageIcon className="h-6 w-6 text-primary" />}
        <h1 className="text-xl font-semibold text-foreground">{pageTitle}</h1>
        {pageHelp && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className="rounded-md p-1 hover:bg-accent transition-colors"
                  aria-label="Page help"
                >
                  <HelpCircle className="h-4 w-4 text-muted-foreground" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-xs">
                <p>{pageHelp}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>

      {/* Right: Stats, Notifications, User Profile */}
      <div className="flex items-center gap-3 md:gap-6">
        {/* Stats - hidden on mobile */}
        {stats.length > 0 && (
          <div className="hidden md:flex items-center gap-4">
            {stats.map((stat, index) => (
              <div key={index} className="flex flex-col">
                <span className="text-xs text-muted-foreground">{stat.label}</span>
                <span className="text-sm font-medium text-foreground">
                  {stat.value}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Notifications */}
        <button
          className="relative rounded-md p-2 hover:bg-accent transition-colors"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5 text-foreground" />
          <Badge
            className="absolute -right-1 -top-1 h-5 w-5 rounded-full p-0 text-xs flex items-center justify-center"
            variant="destructive"
          >
            3
          </Badge>
        </button>

        {/* User Profile */}
        <button
          className="flex items-center gap-3 rounded-md p-2 hover:bg-accent transition-colors"
          aria-label="User profile menu"
        >
          {/* User info - hidden on mobile */}
          <div className="hidden md:block text-right">
            <div className="text-sm font-medium text-foreground">
              {DEFAULT_USER_PROFILE.name}
            </div>
            <div className="text-xs text-muted-foreground">
              {DEFAULT_USER_PROFILE.email}
            </div>
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
            {DEFAULT_USER_PROFILE.initials}
          </div>
        </button>
      </div>
    </header>
  )
}

export default TopHeader
