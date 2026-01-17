/**
 * Teams Tab Component (Super Admin Only)
 *
 * Manage teams across the platform with CRUD operations.
 * Only visible to super admin users.
 *
 * Part of Issue #73 - User Story 5: Team Management
 */

import { useState, useEffect } from 'react'
import { Plus, Building2, Power, PowerOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
import { useTeams, useTeamStats, Team } from '@/hooks/useTeams'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { GuidBadge } from '@/components/GuidBadge'

export function TeamsTab() {
  const { teams, loading, error, createTeam, deactivate, reactivate } =
    useTeams()

  // KPI Stats for header
  const { stats, refetch: refetchStats } = useTeamStats()
  const { setStats } = useHeaderStats()

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Active Teams', value: stats.active_teams },
        { label: 'Total Teams', value: stats.total_teams },
      ])
    }
    return () => setStats([]) // Clear stats on unmount
  }, [stats, setStats])

  // Dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Form state
  const [teamName, setTeamName] = useState('')
  const [adminEmail, setAdminEmail] = useState('')

  const handleOpenCreateDialog = () => {
    setTeamName('')
    setAdminEmail('')
    setFormError(null)
    setCreateDialogOpen(true)
  }

  const handleCloseCreateDialog = () => {
    setCreateDialogOpen(false)
    setTeamName('')
    setAdminEmail('')
    setFormError(null)
  }

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    setIsSubmitting(true)

    try {
      await createTeam(teamName.trim(), adminEmail.trim().toLowerCase())
      handleCloseCreateDialog()
      refetchStats()
    } catch (err: any) {
      setFormError(err.message || 'Failed to create team')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDeactivate = async (team: Team) => {
    try {
      await deactivate(team.guid)
      refetchStats()
    } catch (err) {
      // Error displayed via hook
    }
  }

  const handleReactivate = async (team: Team) => {
    try {
      await reactivate(team.guid)
      refetchStats()
    } catch (err) {
      // Error displayed via hook
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Action Row */}
      <div className="flex justify-end">
        <Button onClick={handleOpenCreateDialog} className="gap-2">
          <Plus className="h-4 w-4" />
          New Team
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Teams Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Team</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>Users</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="text-center text-muted-foreground py-8"
                >
                  Loading teams...
                </TableCell>
              </TableRow>
            ) : teams.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="text-center text-muted-foreground py-8"
                >
                  <Building2 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  No teams found
                </TableCell>
              </TableRow>
            ) : (
              teams.map(team => (
                <TableRow key={team.guid}>
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      <span className="font-medium">{team.name}</span>
                      <GuidBadge guid={team.guid} />
                    </div>
                  </TableCell>
                  <TableCell>
                    <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                      {team.slug}
                    </code>
                  </TableCell>
                  <TableCell>{team.user_count}</TableCell>
                  <TableCell>
                    {team.is_active ? (
                      <Badge variant="default" className="bg-green-600">
                        Active
                      </Badge>
                    ) : (
                      <Badge variant="secondary">Inactive</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {team.is_active ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeactivate(team)}
                        className="gap-1.5 text-destructive hover:text-destructive"
                      >
                        <PowerOff className="h-4 w-4" />
                        Deactivate
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleReactivate(team)}
                        className="gap-1.5"
                      >
                        <Power className="h-4 w-4" />
                        Reactivate
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create Team Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Team</DialogTitle>
            <DialogDescription>
              Create a new team with an initial admin user. The admin will be
              sent an invitation to complete their account setup.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateTeam}>
            <div className="grid gap-4 py-4">
              {formError && (
                <Alert variant="destructive">
                  <AlertDescription>{formError}</AlertDescription>
                </Alert>
              )}

              <div className="grid gap-2">
                <Label htmlFor="team-name">Team Name</Label>
                <Input
                  id="team-name"
                  value={teamName}
                  onChange={e => setTeamName(e.target.value)}
                  placeholder="Acme Photography"
                  required
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="admin-email">Admin Email</Label>
                <Input
                  id="admin-email"
                  type="email"
                  value={adminEmail}
                  onChange={e => setAdminEmail(e.target.value)}
                  placeholder="admin@acme.com"
                  required
                />
                <p className="text-xs text-muted-foreground">
                  This user will be created as the team administrator.
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={handleCloseCreateDialog}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Creating...' : 'Create Team'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default TeamsTab
