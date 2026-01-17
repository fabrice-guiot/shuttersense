/**
 * React hook for team management operations (super admin only).
 *
 * Provides state management and API integration for creating,
 * listing, and managing teams.
 *
 * Part of Issue #73 - User Story 5: Team Management
 */

import { useState, useCallback, useEffect } from 'react'
import {
  Team,
  TeamListResponse,
  TeamStatsResponse,
  TeamWithAdmin,
  createTeam as apiCreateTeam,
  listTeams as apiListTeams,
  getTeamStats as apiGetTeamStats,
  deactivateTeam as apiDeactivateTeam,
  reactivateTeam as apiReactivateTeam,
} from '@/services/teams-api'

// ============================================================================
// Types
// ============================================================================

interface UseTeamsOptions {
  /** Whether to only show active teams */
  activeOnly?: boolean
  /** Whether to auto-fetch teams on mount */
  autoFetch?: boolean
}

interface UseTeamsReturn {
  /** List of teams */
  teams: Team[]
  /** Total number of teams */
  total: number
  /** Team statistics */
  stats: TeamStatsResponse | null
  /** Loading state */
  loading: boolean
  /** Error message if any */
  error: string | null
  /** Refresh teams list */
  refresh: () => Promise<void>
  /** Create a new team */
  createTeam: (name: string, adminEmail: string) => Promise<TeamWithAdmin>
  /** Deactivate a team */
  deactivate: (guid: string) => Promise<Team>
  /** Reactivate a team */
  reactivate: (guid: string) => Promise<Team>
  /** Fetch team stats */
  fetchStats: () => Promise<void>
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useTeams(options: UseTeamsOptions = {}): UseTeamsReturn {
  const { activeOnly = false, autoFetch = true } = options

  const [teams, setTeams] = useState<Team[]>([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState<TeamStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch teams list from API.
   */
  const fetchTeams = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiListTeams({ activeOnly })
      setTeams(response.teams)
      setTotal(response.total)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch teams'
      setError(message)
      console.error('[useTeams] Failed to fetch teams:', err)
    } finally {
      setLoading(false)
    }
  }, [activeOnly])

  /**
   * Fetch team statistics from API.
   */
  const fetchStats = useCallback(async () => {
    try {
      const response = await apiGetTeamStats()
      setStats(response)
    } catch (err) {
      console.error('[useTeams] Failed to fetch stats:', err)
    }
  }, [])

  /**
   * Create a new team.
   */
  const createTeam = useCallback(
    async (name: string, adminEmail: string): Promise<TeamWithAdmin> => {
      setError(null)

      try {
        const result = await apiCreateTeam(name, adminEmail)
        // Refresh the list after creating
        await fetchTeams()
        await fetchStats()
        return result
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create team'
        setError(message)
        throw err
      }
    },
    [fetchTeams, fetchStats]
  )

  /**
   * Deactivate a team.
   */
  const deactivate = useCallback(
    async (guid: string): Promise<Team> => {
      setError(null)

      try {
        const team = await apiDeactivateTeam(guid)
        // Refresh the list after deactivation
        await fetchTeams()
        await fetchStats()
        return team
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to deactivate team'
        setError(message)
        throw err
      }
    },
    [fetchTeams, fetchStats]
  )

  /**
   * Reactivate a team.
   */
  const reactivate = useCallback(
    async (guid: string): Promise<Team> => {
      setError(null)

      try {
        const team = await apiReactivateTeam(guid)
        // Refresh the list after reactivation
        await fetchTeams()
        await fetchStats()
        return team
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to reactivate team'
        setError(message)
        throw err
      }
    },
    [fetchTeams, fetchStats]
  )

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchTeams()
      fetchStats()
    }
  }, [autoFetch, fetchTeams, fetchStats])

  return {
    teams,
    total,
    stats,
    loading,
    error,
    refresh: fetchTeams,
    createTeam,
    deactivate,
    reactivate,
    fetchStats,
  }
}

// ============================================================================
// Stats-only Hook
// ============================================================================

/**
 * Hook for fetching team statistics only.
 * Useful for TopHeader KPIs without loading full team list.
 */
export function useTeamStats() {
  const [stats, setStats] = useState<TeamStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiGetTeamStats()
      setStats(response)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch team stats'
      setError(message)
      console.error('[useTeamStats] Failed to fetch stats:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  return { stats, loading, error, refetch: fetchStats }
}

export type { Team, TeamListResponse, TeamStatsResponse, TeamWithAdmin }
