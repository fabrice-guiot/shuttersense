/**
 * Tests for useAuth hook
 *
 * Issue #73 - Teams/Tenants and User Management
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useAuth, useCurrentUser, useIsSuperAdmin } from '../useAuth'
import * as AuthContext from '@/contexts/AuthContext'
import type { UserInfo } from '@/contracts/api/auth-api'

// Mock the AuthContext
vi.mock('@/contexts/AuthContext')

describe('useAuth', () => {
  const mockUser: UserInfo = {
    user_guid: 'usr_01hgw2bbg00000000000000001',
    email: 'test@example.com',
    display_name: 'Test User',
    is_super_admin: false,
    team_guid: 'ten_01hgw2bbg00000000000000001',
    team_name: 'Test Team',
    picture_url: null,
    first_name: 'Test',
    last_name: 'User',
  }

  const mockAuthContextValue = {
    user: mockUser,
    isAuthenticated: true,
    isLoading: false,
    error: null,
    logout: vi.fn(),
    refreshAuth: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(AuthContext.useAuthContext).mockReturnValue(mockAuthContextValue)
  })

  it('should return auth context values', () => {
    const { result } = renderHook(() => useAuth())

    expect(result.current.user).toEqual(mockUser)
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.logout).toBeDefined()
    expect(result.current.refreshAuth).toBeDefined()
  })

  it('should return null user when not authenticated', () => {
    vi.mocked(AuthContext.useAuthContext).mockReturnValue({
      ...mockAuthContextValue,
      user: null,
      isAuthenticated: false,
    })

    const { result } = renderHook(() => useAuth())

    expect(result.current.user).toBe(null)
    expect(result.current.isAuthenticated).toBe(false)
  })
})

describe('useCurrentUser', () => {
  const mockUser: UserInfo = {
    user_guid: 'usr_01hgw2bbg00000000000000001',
    email: 'test@example.com',
    display_name: 'Test User',
    is_super_admin: false,
    team_guid: 'ten_01hgw2bbg00000000000000001',
    team_name: 'Test Team',
    picture_url: null,
    first_name: 'Test',
    last_name: 'User',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should return current user', () => {
    vi.mocked(AuthContext.useAuthContext).mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      isLoading: false,
      error: null,
      logout: vi.fn(),
      refreshAuth: vi.fn(),
    })

    const { result } = renderHook(() => useCurrentUser())

    expect(result.current).toEqual(mockUser)
  })

  it('should return null when not authenticated', () => {
    vi.mocked(AuthContext.useAuthContext).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      logout: vi.fn(),
      refreshAuth: vi.fn(),
    })

    const { result } = renderHook(() => useCurrentUser())

    expect(result.current).toBe(null)
  })
})

describe('useIsSuperAdmin', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should return true for super admin user', () => {
    const superAdminUser: UserInfo = {
      user_guid: 'usr_01hgw2bbg00000000000000001',
      email: 'admin@example.com',
      display_name: 'Super Admin',
      is_super_admin: true,
      team_guid: 'ten_01hgw2bbg00000000000000001',
      team_name: 'Admin Team',
      picture_url: null,
      first_name: 'Super',
      last_name: 'Admin',
    }

    vi.mocked(AuthContext.useAuthContext).mockReturnValue({
      user: superAdminUser,
      isAuthenticated: true,
      isLoading: false,
      error: null,
      logout: vi.fn(),
      refreshAuth: vi.fn(),
    })

    const { result } = renderHook(() => useIsSuperAdmin())

    expect(result.current).toBe(true)
  })

  it('should return false for regular user', () => {
    const regularUser: UserInfo = {
      user_guid: 'usr_01hgw2bbg00000000000000002',
      email: 'user@example.com',
      display_name: 'Regular User',
      is_super_admin: false,
      team_guid: 'ten_01hgw2bbg00000000000000001',
      team_name: 'Test Team',
      picture_url: null,
      first_name: 'Regular',
      last_name: 'User',
    }

    vi.mocked(AuthContext.useAuthContext).mockReturnValue({
      user: regularUser,
      isAuthenticated: true,
      isLoading: false,
      error: null,
      logout: vi.fn(),
      refreshAuth: vi.fn(),
    })

    const { result } = renderHook(() => useIsSuperAdmin())

    expect(result.current).toBe(false)
  })

  it('should return false when not authenticated', () => {
    vi.mocked(AuthContext.useAuthContext).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      logout: vi.fn(),
      refreshAuth: vi.fn(),
    })

    const { result } = renderHook(() => useIsSuperAdmin())

    expect(result.current).toBe(false)
  })
})
