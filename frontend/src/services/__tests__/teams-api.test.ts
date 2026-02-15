import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  createTeam,
  listTeams,
  getTeamStats,
  getTeam,
  deactivateTeam,
  reactivateTeam,
} from '@/services/teams-api'
import type { Team, TeamWithAdmin, TeamListResponse, TeamStatsResponse } from '@/services/teams-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

describe('Teams API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockTeam: Team = {
    guid: 'ten_01hgw2bbg00000000000000001',
    name: 'Test Team',
    slug: 'test-team',
    is_active: true,
    user_count: 5,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }

  describe('createTeam', () => {
    test('creates a team with admin user', async () => {
      const mockResponse: TeamWithAdmin = {
        team: mockTeam,
        admin_email: 'admin@example.com',
        admin_guid: 'usr_01hgw2bbg00000000000000001',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await createTeam('Test Team', 'admin@example.com')

      expect(api.post).toHaveBeenCalledWith('/admin/teams', {
        name: 'Test Team',
        admin_email: 'admin@example.com',
      })
      expect(result).toEqual(mockResponse)
      expect(result.team.name).toBe('Test Team')
      expect(result.admin_email).toBe('admin@example.com')
    })
  })

  describe('listTeams', () => {
    test('lists all teams without filters', async () => {
      const mockResponse: TeamListResponse = {
        teams: [mockTeam],
        total: 1,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listTeams()

      expect(api.get).toHaveBeenCalledWith('/admin/teams', { params: expect.any(URLSearchParams) })
      const call = vi.mocked(api.get).mock.calls[0]
      const params = call[1]?.params as URLSearchParams
      expect(params.toString()).toBe('')
      expect(result).toEqual(mockResponse)
    })

    test('lists active teams only', async () => {
      const mockResponse: TeamListResponse = {
        teams: [mockTeam],
        total: 1,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      await listTeams({ activeOnly: true })

      const call = vi.mocked(api.get).mock.calls[0]
      const params = call[1]?.params as URLSearchParams
      expect(params.get('active_only')).toBe('true')
    })
  })

  describe('getTeamStats', () => {
    test('retrieves team statistics', async () => {
      const mockStats: TeamStatsResponse = {
        total_teams: 10,
        active_teams: 8,
        inactive_teams: 2,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockStats })

      const result = await getTeamStats()

      expect(api.get).toHaveBeenCalledWith('/admin/teams/stats')
      expect(result).toEqual(mockStats)
    })
  })

  describe('getTeam', () => {
    test('retrieves a team by GUID', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockTeam })

      const result = await getTeam('ten_01hgw2bbg00000000000000001')

      expect(api.get).toHaveBeenCalledWith('/admin/teams/ten_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockTeam)
    })
  })

  describe('deactivateTeam', () => {
    test('deactivates a team', async () => {
      const deactivatedTeam = { ...mockTeam, is_active: false }
      vi.mocked(api.post).mockResolvedValue({ data: deactivatedTeam })

      const result = await deactivateTeam('ten_01hgw2bbg00000000000000001')

      expect(api.post).toHaveBeenCalledWith('/admin/teams/ten_01hgw2bbg00000000000000001/deactivate')
      expect(result.is_active).toBe(false)
    })
  })

  describe('reactivateTeam', () => {
    test('reactivates a team', async () => {
      const reactivatedTeam = { ...mockTeam, is_active: true }
      vi.mocked(api.post).mockResolvedValue({ data: reactivatedTeam })

      const result = await reactivateTeam('ten_01hgw2bbg00000000000000001')

      expect(api.post).toHaveBeenCalledWith('/admin/teams/ten_01hgw2bbg00000000000000001/reactivate')
      expect(result.is_active).toBe(true)
    })
  })
})
