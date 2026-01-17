/**
 * Top Header Component
 *
 * Displays page title, contextual stats, notifications, and user profile.
 * Updates dynamically based on current route and page context.
 */

import { useNavigate } from 'react-router-dom'
import { Bell, Menu, HelpCircle, LogOut, User, Users, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui/tooltip'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/hooks/useAuth'

// ============================================================================
// Types
// ============================================================================

export interface HeaderStat {
  label: string
  value: string | number
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
// Helpers
// ============================================================================

/**
 * Get user initials from display name or email
 */
function getUserInitials(displayName: string | null | undefined, email: string | undefined): string {
  if (displayName) {
    const parts = displayName.trim().split(/\s+/)
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    }
    return displayName.substring(0, 2).toUpperCase()
  }
  if (email) {
    return email.substring(0, 2).toUpperCase()
  }
  return 'PA'
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
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  // Compute user display info
  const displayName = user?.display_name || user?.email?.split('@')[0] || 'User'
  const email = user?.email || ''
  const pictureUrl = user?.picture_url
  const initials = getUserInitials(user?.display_name, user?.email)

  const handleViewProfile = () => {
    navigate('/profile')
  }

  const handleViewTeam = () => {
    navigate('/team')
  }

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

        {/* User Profile Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className="flex items-center gap-3 rounded-md p-2 hover:bg-accent transition-colors"
              aria-label="User profile menu"
            >
              {/* User info - hidden on mobile */}
              <div className="hidden md:block text-right">
                <div className="text-sm font-medium text-foreground">
                  {displayName}
                </div>
                <div className="text-xs text-muted-foreground">
                  {email}
                </div>
              </div>
              {pictureUrl ? (
                <img
                  src={pictureUrl}
                  alt={displayName}
                  className="h-10 w-10 rounded-full object-cover"
                />
              ) : (
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
                  {initials}
                </div>
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={handleViewProfile}
              className="cursor-pointer"
            >
              <User className="mr-2 h-4 w-4" />
              <span>View Profile</span>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={handleViewTeam}
              className="cursor-pointer"
            >
              <Users className="mr-2 h-4 w-4" />
              <span>Team</span>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={logout}
              className="cursor-pointer hover:bg-destructive hover:text-destructive-foreground focus:bg-destructive focus:text-destructive-foreground"
            >
              <LogOut className="mr-2 h-4 w-4 text-destructive" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}

export default TopHeader
