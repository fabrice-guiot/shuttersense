/**
 * Team Page
 *
 * Manage team members: invite users, view user list, and manage user status.
 * Accessible via user dropdown menu in TopHeader.
 *
 * Part of Issue #73 - User Story 4: User Management (Phase 8)
 */

import { useState, useEffect } from 'react'
import {
  Plus,
  Trash2,
  UserMinus,
  UserCheck,
  Clock,
  CheckCircle,
  XCircle,
  Mail,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useUsers, useUserStats, User } from '@/hooks/useUsers'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { useAuth } from '@/hooks/useAuth'
import { GuidBadge } from '@/components/GuidBadge'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/utils/dateFormat'

// ============================================================================
// Status Badge Component
// ============================================================================

interface StatusBadgeProps {
  status: 'pending' | 'active' | 'deactivated'
}

function StatusBadge({ status }: StatusBadgeProps) {
  const config = {
    pending: {
      label: 'Pending',
      icon: Clock,
      variant: 'secondary' as const,
      className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
    },
    active: {
      label: 'Active',
      icon: CheckCircle,
      variant: 'default' as const,
      className: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    },
    deactivated: {
      label: 'Deactivated',
      icon: XCircle,
      variant: 'destructive' as const,
      className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    },
  }

  const { label, icon: Icon, className } = config[status]

  return (
    <Badge variant="outline" className={cn('gap-1', className)}>
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  )
}

// ============================================================================
// User Avatar Component
// ============================================================================

interface UserAvatarProps {
  user: User
  size?: 'sm' | 'md'
}

function UserAvatar({ user, size = 'md' }: UserAvatarProps) {
  const sizeClasses = size === 'sm' ? 'h-8 w-8 text-xs' : 'h-10 w-10 text-sm'

  // Get initials from display name or email
  const getInitials = () => {
    if (user.display_name) {
      const parts = user.display_name.trim().split(/\s+/)
      if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      }
      return user.display_name.substring(0, 2).toUpperCase()
    }
    return user.email.substring(0, 2).toUpperCase()
  }

  if (user.picture_url) {
    return (
      <img
        src={user.picture_url}
        alt={user.display_name || user.email}
        className={cn('rounded-full object-cover', sizeClasses)}
      />
    )
  }

  return (
    <div
      className={cn(
        'flex items-center justify-center rounded-full bg-primary text-primary-foreground font-medium',
        sizeClasses
      )}
    >
      {getInitials()}
    </div>
  )
}

// ============================================================================
// User List Component
// ============================================================================

interface UserListProps {
  users: User[]
  loading: boolean
  currentUserGuid: string | undefined
  onDeletePending: (user: User) => void
  onDeactivate: (user: User) => void
  onReactivate: (user: User) => void
}

function UserList({
  users,
  loading,
  currentUserGuid,
  onDeletePending,
  onDeactivate,
  onReactivate,
}: UserListProps) {
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean
    user: User | null
  }>({ open: false, user: null })

  const [deactivateDialog, setDeactivateDialog] = useState<{
    open: boolean
    user: User | null
  }>({ open: false, user: null })

  const handleDeleteClick = (user: User) => {
    setDeleteDialog({ open: true, user })
  }

  const handleDeleteConfirm = () => {
    if (deleteDialog.user) {
      onDeletePending(deleteDialog.user)
      setDeleteDialog({ open: false, user: null })
    }
  }

  const handleDeactivateClick = (user: User) => {
    setDeactivateDialog({ open: true, user })
  }

  const handleDeactivateConfirm = () => {
    if (deactivateDialog.user) {
      onDeactivate(deactivateDialog.user)
      setDeactivateDialog({ open: false, user: null })
    }
  }

  if (loading && users.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-muted-foreground">Loading team members...</div>
      </div>
    )
  }

  if (users.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Mail className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium text-foreground mb-2">No team members yet</h3>
        <p className="text-muted-foreground max-w-md">
          Invite team members by clicking the "Invite User" button above.
        </p>
      </div>
    )
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[300px]">User</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Last Login</TableHead>
            <TableHead className="w-[100px]">ID</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.map(user => {
            const isCurrentUser = user.guid === currentUserGuid
            const canDelete = user.status === 'pending'
            const canDeactivate = user.status !== 'deactivated' && !isCurrentUser
            const canReactivate = user.status === 'deactivated'

            return (
              <TableRow key={user.guid}>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <UserAvatar user={user} size="sm" />
                    <div className="flex flex-col">
                      <span className="font-medium">
                        {user.display_name || user.email.split('@')[0]}
                        {isCurrentUser && (
                          <span className="ml-2 text-xs text-muted-foreground">(you)</span>
                        )}
                      </span>
                      <span className="text-sm text-muted-foreground">{user.email}</span>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <StatusBadge status={user.status} />
                </TableCell>
                <TableCell>
                  {user.last_login_at ? (
                    <span className="text-muted-foreground">
                      {formatRelativeTime(user.last_login_at)}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">Never</span>
                  )}
                </TableCell>
                <TableCell>
                  <GuidBadge guid={user.guid} />
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    {canDelete && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteClick(user)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                    {canDeactivate && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeactivateClick(user)}
                        className="text-orange-600 hover:text-orange-700"
                      >
                        <UserMinus className="h-4 w-4" />
                      </Button>
                    )}
                    {canReactivate && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onReactivate(user)}
                        className="text-green-600 hover:text-green-700"
                      >
                        <UserCheck className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>

      {/* Delete Pending User Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onOpenChange={open => !open && setDeleteDialog({ open: false, user: null })}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Invitation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the invitation for{' '}
              <strong>{deleteDialog.user?.email}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialog({ open: false, user: null })}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm}>
              Delete Invitation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Deactivate User Confirmation Dialog */}
      <Dialog
        open={deactivateDialog.open}
        onOpenChange={open => !open && setDeactivateDialog({ open: false, user: null })}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Deactivate User</DialogTitle>
            <DialogDescription>
              Are you sure you want to deactivate{' '}
              <strong>{deactivateDialog.user?.display_name || deactivateDialog.user?.email}</strong>
              ? They will no longer be able to log in.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeactivateDialog({ open: false, user: null })}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeactivateConfirm}>
              Deactivate User
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

// ============================================================================
// Invite User Dialog Component
// ============================================================================

interface InviteUserDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onInvite: (email: string) => Promise<void>
  error: string | null
}

function InviteUserDialog({ open, onOpenChange, onInvite, error }: InviteUserDialogProps) {
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError(null)

    if (!email.trim()) {
      setLocalError('Email is required')
      return
    }

    // Basic email validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setLocalError('Please enter a valid email address')
      return
    }

    setIsSubmitting(true)
    try {
      await onInvite(email.trim())
      setEmail('')
      onOpenChange(false)
    } catch {
      // Error is handled by parent component
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setEmail('')
      setLocalError(null)
    }
    onOpenChange(newOpen)
  }

  const displayError = localError || error

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Invite Team Member</DialogTitle>
          <DialogDescription>
            Enter the email address of the person you want to invite. They will receive
            pending status until they log in via OAuth.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="email">Email address</Label>
              <Input
                id="email"
                type="email"
                placeholder="colleague@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                disabled={isSubmitting}
                autoFocus
              />
            </div>
            {displayError && (
              <Alert variant="destructive">
                <AlertDescription>{displayError}</AlertDescription>
              </Alert>
            )}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Registering...' : 'Register Invitation'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export default function TeamPage() {
  const { user: currentUser } = useAuth()
  const {
    users,
    loading,
    error,
    invite,
    deletePending,
    deactivate,
    reactivate,
  } = useUsers()
  const { stats, refetch: refetchStats } = useUserStats()
  const { setStats } = useHeaderStats()

  const [inviteDialogOpen, setInviteDialogOpen] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  // Update TopHeader stats
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Total Users', value: stats.total_users },
        { label: 'Active', value: stats.active_users },
        { label: 'Pending', value: stats.pending_users },
      ])
    }
    return () => setStats([])
  }, [stats, setStats])

  const handleInvite = async (email: string) => {
    setActionError(null)
    try {
      await invite(email)
      refetchStats()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to invite user'
      setActionError(message)
      throw err
    }
  }

  const handleDeletePending = async (user: User) => {
    setActionError(null)
    try {
      await deletePending(user.guid)
      refetchStats()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete invitation'
      setActionError(message)
    }
  }

  const handleDeactivate = async (user: User) => {
    setActionError(null)
    try {
      await deactivate(user.guid)
      refetchStats()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to deactivate user'
      setActionError(message)
    }
  }

  const handleReactivate = async (user: User) => {
    setActionError(null)
    try {
      await reactivate(user.guid)
      refetchStats()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to reactivate user'
      setActionError(message)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Action Bar */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-muted-foreground">
            Manage your team members, invite new users, and control access.
          </p>
        </div>
        <Button onClick={() => setInviteDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Invite User
        </Button>
      </div>

      {/* Error Alert */}
      {(error || actionError) && (
        <Alert variant="destructive">
          <AlertDescription>{error || actionError}</AlertDescription>
        </Alert>
      )}

      {/* User List */}
      <UserList
        users={users}
        loading={loading}
        currentUserGuid={currentUser?.user_guid}
        onDeletePending={handleDeletePending}
        onDeactivate={handleDeactivate}
        onReactivate={handleReactivate}
      />

      {/* Invite Dialog */}
      <InviteUserDialog
        open={inviteDialogOpen}
        onOpenChange={setInviteDialogOpen}
        onInvite={handleInvite}
        error={actionError}
      />
    </div>
  )
}
