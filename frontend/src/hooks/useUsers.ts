/**
 * React hook for user management operations.
 *
 * Provides state management and API integration for inviting users,
 * listing team users, and managing user status.
 *
 * Part of Issue #73 - User Story 3: User Pre-Provisioning
 */

import { useState, useCallback, useEffect } from 'react'
import {
  User,
  UserListResponse,
  UserStatsResponse,
  inviteUser as apiInviteUser,
  listUsers as apiListUsers,
  getUserStats as apiGetUserStats,
  deletePendingUser as apiDeletePendingUser,
  deactivateUser as apiDeactivateUser,
  reactivateUser as apiReactivateUser,
} from '@/services/users-api'

// ============================================================================
// Types
// ============================================================================

interface UseUsersOptions {
  /** Initial status filter */
  initialStatus?: 'pending' | 'active' | 'deactivated'
  /** Whether to only show active users */
  activeOnly?: boolean
  /** Whether to auto-fetch users on mount */
  autoFetch?: boolean
}

interface UseUsersReturn {
  /** List of users */
  users: User[]
  /** Total number of users */
  total: number
  /** User statistics */
  stats: UserStatsResponse | null
  /** Loading state */
  loading: boolean
  /** Error message if any */
  error: string | null
  /** Refresh users list */
  refresh: () => Promise<void>
  /** Invite a new user */
  invite: (email: string) => Promise<User>
  /** Delete a pending user */
  deletePending: (guid: string) => Promise<void>
  /** Deactivate a user */
  deactivate: (guid: string) => Promise<User>
  /** Reactivate a user */
  reactivate: (guid: string) => Promise<User>
  /** Fetch user stats */
  fetchStats: () => Promise<void>
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useUsers(options: UseUsersOptions = {}): UseUsersReturn {
  const { initialStatus, activeOnly = false, autoFetch = true } = options

  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState<UserStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch users list from API.
   */
  const fetchUsers = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiListUsers({
        status: initialStatus,
        activeOnly,
      })
      setUsers(response.users)
      setTotal(response.total)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch users'
      setError(message)
      console.error('[useUsers] Failed to fetch users:', err)
    } finally {
      setLoading(false)
    }
  }, [initialStatus, activeOnly])

  /**
   * Fetch user statistics from API.
   */
  const fetchStats = useCallback(async () => {
    try {
      const response = await apiGetUserStats()
      setStats(response)
    } catch (err) {
      console.error('[useUsers] Failed to fetch stats:', err)
    }
  }, [])

  /**
   * Invite a new user.
   */
  const invite = useCallback(async (email: string): Promise<User> => {
    setError(null)

    try {
      const user = await apiInviteUser(email)
      // Refresh the list after inviting
      await fetchUsers()
      await fetchStats()
      return user
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to invite user'
      setError(message)
      throw err
    }
  }, [fetchUsers, fetchStats])

  /**
   * Delete a pending user.
   */
  const deletePending = useCallback(async (guid: string): Promise<void> => {
    setError(null)

    try {
      await apiDeletePendingUser(guid)
      // Refresh the list after deletion
      await fetchUsers()
      await fetchStats()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete user'
      setError(message)
      throw err
    }
  }, [fetchUsers, fetchStats])

  /**
   * Deactivate a user.
   */
  const deactivate = useCallback(async (guid: string): Promise<User> => {
    setError(null)

    try {
      const user = await apiDeactivateUser(guid)
      // Refresh the list after deactivation
      await fetchUsers()
      await fetchStats()
      return user
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to deactivate user'
      setError(message)
      throw err
    }
  }, [fetchUsers, fetchStats])

  /**
   * Reactivate a user.
   */
  const reactivate = useCallback(async (guid: string): Promise<User> => {
    setError(null)

    try {
      const user = await apiReactivateUser(guid)
      // Refresh the list after reactivation
      await fetchUsers()
      await fetchStats()
      return user
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to reactivate user'
      setError(message)
      throw err
    }
  }, [fetchUsers, fetchStats])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchUsers()
      fetchStats()
    }
  }, [autoFetch, fetchUsers, fetchStats])

  return {
    users,
    total,
    stats,
    loading,
    error,
    refresh: fetchUsers,
    invite,
    deletePending,
    deactivate,
    reactivate,
    fetchStats,
  }
}

// ============================================================================
// Stats-only Hook
// ============================================================================

/**
 * Hook for fetching user statistics only.
 * Useful for TopHeader KPIs without loading full user list.
 */
export function useUserStats() {
  const [stats, setStats] = useState<UserStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiGetUserStats()
      setStats(response)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch user stats'
      setError(message)
      console.error('[useUserStats] Failed to fetch stats:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  return { stats, loading, error, refetch: fetchStats }
}

export type { User, UserListResponse, UserStatsResponse }
