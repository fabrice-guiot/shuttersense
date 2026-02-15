import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  listAgents,
  getAgent,
  updateAgent,
  revokeAgent,
  getPoolStatus,
  getAgentStats,
  createRegistrationToken,
  listRegistrationTokens,
  deleteRegistrationToken,
  getAgentDetail,
  getAgentJobHistory,
  getActiveRelease,
  getPoolStatusWebSocketUrl,
} from '@/services/agents'
import type {
  Agent,
  AgentListResponse,
  AgentUpdateRequest,
  AgentPoolStatusResponse,
  AgentDetailResponse,
  AgentJobHistoryResponse,
  RegistrationToken,
  RegistrationTokenCreateRequest,
  RegistrationTokenListItem,
  RegistrationTokenListResponse,
  ActiveReleaseResponse,
} from '@/contracts/api/agent-api'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    defaults: { baseURL: '/api' },
  },
}))

describe('Agents Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listAgents', () => {
    test('lists agents without revoked agents', async () => {
      const mockAgents: Agent[] = [
        {
          guid: 'agt_01hgw2bbg00000000000000001',
          name: 'Agent 1',
          hostname: 'macbook-pro.local',
          os_info: 'Darwin 25.2.0',
          status: 'online',
          error_message: null,
          last_heartbeat: '2026-01-01T12:00:00Z',
          capabilities: ['local_filesystem'],
          authorized_roots: ['/photos'],
          version: 'v1.0.0',
          created_at: '2026-01-01T00:00:00Z',
          team_guid: 'ten_01hgw2bbg00000000000000001',
          current_job_guid: null,
          running_jobs_count: 0,
        },
      ]

      const mockResponse: AgentListResponse = {
        agents: mockAgents,
        total_count: 1,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listAgents()

      expect(api.get).toHaveBeenCalledWith('/agent/v1', { params: {} })
      expect(result).toEqual(mockAgents)
    })

    test('lists agents including revoked', async () => {
      const mockAgents: Agent[] = [
        {
          guid: 'agt_01hgw2bbg00000000000000001',
          name: 'Agent 1',
          hostname: 'macbook-pro.local',
          os_info: 'Darwin 25.2.0',
          status: 'revoked',
          error_message: null,
          last_heartbeat: null,
          capabilities: [],
          authorized_roots: [],
          version: 'v1.0.0',
          created_at: '2026-01-01T00:00:00Z',
          team_guid: 'ten_01hgw2bbg00000000000000001',
          current_job_guid: null,
          running_jobs_count: 0,
        },
      ]

      const mockResponse: AgentListResponse = {
        agents: mockAgents,
        total_count: 1,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listAgents(true)

      expect(api.get).toHaveBeenCalledWith('/agent/v1', { params: { include_revoked: true } })
      expect(result).toEqual(mockAgents)
    })
  })

  describe('getAgent', () => {
    test('fetches a single agent by GUID', async () => {
      const agentGuid = 'agt_01hgw2bbg00000000000000001'

      const mockAgent: Agent = {
        guid: agentGuid,
        name: 'Agent 1',
        hostname: 'macbook-pro.local',
        os_info: 'Darwin 25.2.0',
        status: 'online',
        error_message: null,
        last_heartbeat: '2026-01-01T12:00:00Z',
        capabilities: ['local_filesystem'],
        authorized_roots: ['/photos'],
        version: 'v1.0.0',
        created_at: '2026-01-01T00:00:00Z',
        team_guid: 'ten_01hgw2bbg00000000000000001',
        current_job_guid: null,
        running_jobs_count: 0,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockAgent })

      const result = await getAgent(agentGuid)

      expect(api.get).toHaveBeenCalledWith(`/agent/v1/${encodeURIComponent(agentGuid)}`)
      expect(result).toEqual(mockAgent)
    })

    test('throws error for invalid GUID', async () => {
      await expect(getAgent('invalid_guid')).rejects.toThrow('Invalid GUID format')
    })
  })

  describe('updateAgent', () => {
    test('updates an agent', async () => {
      const agentGuid = 'agt_01hgw2bbg00000000000000001'
      const updateData: AgentUpdateRequest = {
        name: 'Updated Agent Name',
      }

      const mockAgent: Agent = {
        guid: agentGuid,
        name: updateData.name,
        hostname: 'macbook-pro.local',
        os_info: 'Darwin 25.2.0',
        status: 'online',
        error_message: null,
        last_heartbeat: '2026-01-01T12:00:00Z',
        capabilities: ['local_filesystem'],
        authorized_roots: ['/photos'],
        version: 'v1.0.0',
        created_at: '2026-01-01T00:00:00Z',
        team_guid: 'ten_01hgw2bbg00000000000000001',
        current_job_guid: null,
        running_jobs_count: 0,
      }

      vi.mocked(api.patch).mockResolvedValue({ data: mockAgent })

      const result = await updateAgent(agentGuid, updateData)

      expect(api.patch).toHaveBeenCalledWith(
        `/agent/v1/${encodeURIComponent(agentGuid)}`,
        updateData
      )
      expect(result).toEqual(mockAgent)
    })
  })

  describe('revokeAgent', () => {
    test('revokes an agent without reason', async () => {
      const agentGuid = 'agt_01hgw2bbg00000000000000001'

      vi.mocked(api.delete).mockResolvedValue({ data: null })

      await revokeAgent(agentGuid)

      expect(api.delete).toHaveBeenCalledWith(`/agent/v1/${encodeURIComponent(agentGuid)}`, {
        params: {},
      })
    })

    test('revokes an agent with reason', async () => {
      const agentGuid = 'agt_01hgw2bbg00000000000000001'
      const reason = 'Machine decommissioned'

      vi.mocked(api.delete).mockResolvedValue({ data: null })

      await revokeAgent(agentGuid, reason)

      expect(api.delete).toHaveBeenCalledWith(`/agent/v1/${encodeURIComponent(agentGuid)}`, {
        params: { reason },
      })
    })
  })

  describe('getPoolStatus', () => {
    test('fetches agent pool status', async () => {
      const mockResponse: AgentPoolStatusResponse = {
        online_count: 3,
        offline_count: 1,
        idle_count: 2,
        running_jobs_count: 5,
        status: 'running',
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getPoolStatus()

      expect(api.get).toHaveBeenCalledWith('/agent/v1/pool-status')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getAgentStats', () => {
    test('derives stats from agent list', async () => {
      const mockAgents: Agent[] = [
        {
          guid: 'agt_01hgw2bbg00000000000000001',
          name: 'Agent 1',
          hostname: 'host1',
          os_info: 'Darwin',
          status: 'online',
          error_message: null,
          last_heartbeat: '2026-01-01T12:00:00Z',
          capabilities: [],
          authorized_roots: [],
          version: 'v1.0.0',
          created_at: '2026-01-01T00:00:00Z',
          team_guid: 'ten_01hgw2bbg00000000000000001',
          current_job_guid: null,
          running_jobs_count: 0,
        },
        {
          guid: 'agt_01hgw2bbg00000000000000002',
          name: 'Agent 2',
          hostname: 'host2',
          os_info: 'Linux',
          status: 'offline',
          error_message: null,
          last_heartbeat: null,
          capabilities: [],
          authorized_roots: [],
          version: 'v1.0.0',
          created_at: '2026-01-01T00:00:00Z',
          team_guid: 'ten_01hgw2bbg00000000000000001',
          current_job_guid: null,
          running_jobs_count: 0,
        },
      ]

      vi.mocked(api.get).mockResolvedValue({
        data: { agents: mockAgents, total_count: 2 },
      })

      const result = await getAgentStats()

      expect(result).toEqual({
        total_agents: 2,
        online_agents: 1,
        offline_agents: 1,
      })
    })
  })

  describe('createRegistrationToken', () => {
    test('creates a registration token with defaults', async () => {
      const mockResponse: RegistrationToken = {
        guid: 'art_01hgw2bbg00000000000000001',
        token: 'secret_token_abc123',
        name: null,
        expires_at: '2026-01-02T00:00:00Z',
        is_valid: true,
        created_at: '2026-01-01T00:00:00Z',
        created_by_email: 'user@example.com',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await createRegistrationToken()

      expect(api.post).toHaveBeenCalledWith('/agent/v1/tokens', {})
      expect(result).toEqual(mockResponse)
    })

    test('creates a registration token with custom parameters', async () => {
      const requestData: RegistrationTokenCreateRequest = {
        name: 'Production Agent Token',
        expires_in_hours: 72,
      }

      const mockResponse: RegistrationToken = {
        guid: 'art_01hgw2bbg00000000000000001',
        token: 'secret_token_abc123',
        name: requestData.name,
        expires_at: '2026-01-04T00:00:00Z',
        is_valid: true,
        created_at: '2026-01-01T00:00:00Z',
        created_by_email: 'user@example.com',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await createRegistrationToken(requestData)

      expect(api.post).toHaveBeenCalledWith('/agent/v1/tokens', requestData)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('listRegistrationTokens', () => {
    test('lists tokens without used tokens', async () => {
      const mockTokens: RegistrationTokenListItem[] = [
        {
          guid: 'art_01hgw2bbg00000000000000001',
          name: 'Token 1',
          expires_at: '2026-01-02T00:00:00Z',
          is_valid: true,
          is_used: false,
          used_by_agent_guid: null,
          created_at: '2026-01-01T00:00:00Z',
          created_by_email: 'user@example.com',
        },
      ]

      const mockResponse: RegistrationTokenListResponse = {
        tokens: mockTokens,
        total_count: 1,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listRegistrationTokens()

      expect(api.get).toHaveBeenCalledWith('/agent/v1/tokens', { params: {} })
      expect(result).toEqual(mockTokens)
    })

    test('lists tokens including used', async () => {
      const mockTokens: RegistrationTokenListItem[] = [
        {
          guid: 'art_01hgw2bbg00000000000000001',
          name: 'Token 1',
          expires_at: '2026-01-02T00:00:00Z',
          is_valid: false,
          is_used: true,
          used_by_agent_guid: 'agt_01hgw2bbg00000000000000001',
          created_at: '2026-01-01T00:00:00Z',
          created_by_email: 'user@example.com',
        },
      ]

      const mockResponse: RegistrationTokenListResponse = {
        tokens: mockTokens,
        total_count: 1,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listRegistrationTokens(true)

      expect(api.get).toHaveBeenCalledWith('/agent/v1/tokens', { params: { include_used: true } })
      expect(result).toEqual(mockTokens)
    })
  })

  describe('deleteRegistrationToken', () => {
    test('deletes an unused registration token', async () => {
      const tokenGuid = 'art_01hgw2bbg00000000000000001'

      vi.mocked(api.delete).mockResolvedValue({ data: null })

      await deleteRegistrationToken(tokenGuid)

      expect(api.delete).toHaveBeenCalledWith(`/agent/v1/tokens/${encodeURIComponent(tokenGuid)}`)
    })

    test('throws error for invalid GUID', async () => {
      await expect(deleteRegistrationToken('invalid_guid')).rejects.toThrow('Invalid GUID format')
    })
  })

  describe('getAgentDetail', () => {
    test('fetches detailed agent information', async () => {
      const agentGuid = 'agt_01hgw2bbg00000000000000001'

      const mockResponse: AgentDetailResponse = {
        guid: agentGuid,
        name: 'Agent 1',
        hostname: 'macbook-pro.local',
        os_info: 'Darwin 25.2.0',
        status: 'online',
        error_message: null,
        last_heartbeat: '2026-01-01T12:00:00Z',
        capabilities: ['local_filesystem'],
        authorized_roots: ['/photos'],
        version: 'v1.0.0',
        created_at: '2026-01-01T00:00:00Z',
        team_guid: 'ten_01hgw2bbg00000000000000001',
        current_job_guid: null,
        metrics: {
          cpu_percent: 25.5,
          memory_percent: 45.0,
          disk_free_gb: 500.0,
        },
        bound_collections_count: 3,
        total_jobs_completed: 42,
        total_jobs_failed: 2,
        recent_jobs: [],
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getAgentDetail(agentGuid)

      expect(api.get).toHaveBeenCalledWith(`/agent/v1/${encodeURIComponent(agentGuid)}/detail`)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getAgentJobHistory', () => {
    test('fetches job history with default pagination', async () => {
      const agentGuid = 'agt_01hgw2bbg00000000000000001'

      const mockResponse: AgentJobHistoryResponse = {
        jobs: [],
        total_count: 0,
        offset: 0,
        limit: 20,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getAgentJobHistory(agentGuid)

      expect(api.get).toHaveBeenCalledWith(`/agent/v1/${encodeURIComponent(agentGuid)}/jobs`, {
        params: { offset: 0, limit: 20 },
      })
      expect(result).toEqual(mockResponse)
    })

    test('fetches job history with custom pagination', async () => {
      const agentGuid = 'agt_01hgw2bbg00000000000000001'

      const mockResponse: AgentJobHistoryResponse = {
        jobs: [],
        total_count: 100,
        offset: 50,
        limit: 10,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getAgentJobHistory(agentGuid, 50, 10)

      expect(api.get).toHaveBeenCalledWith(`/agent/v1/${encodeURIComponent(agentGuid)}/jobs`, {
        params: { offset: 50, limit: 10 },
      })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getActiveRelease', () => {
    test('fetches active release manifest', async () => {
      const mockResponse: ActiveReleaseResponse = {
        guid: 'rel_01hgw2bbg00000000000000001',
        version: 'v1.2.3',
        artifacts: [
          {
            platform: 'darwin-arm64',
            filename: 'shuttersense-agent-darwin-arm64',
            checksum: 'sha256:abc123...',
            file_size: 50000000,
            download_url: '/agent/v1/releases/rel_xxx/artifacts/darwin-arm64',
            signed_url: 'https://storage.example.com/signed-url',
          },
        ],
        notes: 'Bug fixes and improvements',
        dev_mode: false,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getActiveRelease()

      expect(api.get).toHaveBeenCalledWith('/agent/v1/releases/active')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getPoolStatusWebSocketUrl', () => {
    test('builds WebSocket URL from relative baseURL', () => {
      // Mock window.location
      Object.defineProperty(window, 'location', {
        value: {
          protocol: 'https:',
          host: 'app.example.com',
        },
        writable: true,
      })

      const url = getPoolStatusWebSocketUrl()

      expect(url).toBe('wss://app.example.com/api/agent/v1/ws/pool-status')
    })

    test('builds WebSocket URL from HTTP location', () => {
      Object.defineProperty(window, 'location', {
        value: {
          protocol: 'http:',
          host: 'localhost:3000',
        },
        writable: true,
      })

      const url = getPoolStatusWebSocketUrl()

      expect(url).toBe('ws://localhost:3000/api/agent/v1/ws/pool-status')
    })
  })
})
