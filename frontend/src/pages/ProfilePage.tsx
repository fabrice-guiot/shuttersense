/**
 * Profile Page
 *
 * Displays the current user's profile information.
 * Part of Issue #73 - Teams/Tenants and User Management.
 */

import { useAuth } from '@/hooks/useAuth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Building2, Mail, Shield, User } from 'lucide-react'
import { NotificationPreferences } from '@/components/profile/NotificationPreferences'

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

export default function ProfilePage() {
  const { user } = useAuth()

  if (!user) {
    return null
  }

  const displayName = user.display_name || user.email.split('@')[0]
  const initials = getUserInitials(user.display_name, user.email)
  const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ')

  return (
    <div className="space-y-6">
      {/* Profile Header Card */}
      <Card>
        <CardHeader>
          <div className="flex items-start gap-6">
            {/* Avatar */}
            {user.picture_url ? (
              <img
                src={user.picture_url}
                alt={displayName}
                className="h-24 w-24 rounded-full object-cover"
              />
            ) : (
              <div className="flex h-24 w-24 items-center justify-center rounded-full bg-primary text-primary-foreground text-3xl font-semibold">
                {initials}
              </div>
            )}

            {/* Name and badges */}
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-3">
                <CardTitle className="text-2xl">{displayName}</CardTitle>
                {user.is_super_admin && (
                  <Badge variant="secondary" className="gap-1">
                    <Shield className="h-3 w-3" />
                    Super Admin
                  </Badge>
                )}
              </div>
              <CardDescription className="text-base">{user.email}</CardDescription>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Profile Details Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Profile Details</CardTitle>
        </CardHeader>
        <CardContent className="divide-y divide-border">
          {/* Full Name */}
          {fullName && (
            <div className="flex items-center gap-3 py-4 first:pt-0">
              <User className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Full Name</p>
                <p className="font-medium">{fullName}</p>
              </div>
            </div>
          )}

          {/* Email */}
          <div className="flex items-center gap-3 py-4 first:pt-0">
            <Mail className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Email</p>
              <p className="font-medium">{user.email}</p>
            </div>
          </div>

          {/* Team/Organization */}
          <div className="flex items-center gap-3 py-4 first:pt-0 last:pb-0">
            <Building2 className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Organization</p>
              <p className="font-medium">{user.team_name}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notification Preferences (Issue #114) */}
      <NotificationPreferences />
    </div>
  )
}
