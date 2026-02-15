import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import { validateGuid } from '@/utils/guid'
import {
  runTool,
  listJobs,
  getJob,
  cancelJob,
  retryJob,
  getQueueStatus,
  getJobWebSocketUrl,
  getGlobalJobsWebSocketUrl,
  runAllTools,
} from '@/services/tools'
import type {
  ToolRunRequest,
  Job,
  JobListQueryParams,
  JobListResponse,
  QueueStatusResponse,
  RunAllToolsResponse,
} from '@/contracts/api/tools-api'

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

vi.mock('@/utils/guid', () => ({
  validateGuid: vi.fn((guid: string) => guid),
}))

describe('Tools API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockJob: Job = {
    id: 'job_01hgw2bbg00000000000000001',
    collection_guid: 'col_01hgw2bbg00000000000000001',
    tool: 'photostats',
    mode: null,
    pipeline_guid: null,
    status: 'queued',
    position: 1,
    created_at: '2026-01-01T00:00:00Z',
    scheduled_for: null,
    started_at: null,
    completed_at: null,
    progress: null,
    error_message: null,
    result_guid: null,
    agent_guid: null,
    agent_name: null,
  }

  describe('runTool', () => {
    test('starts a tool execution on a collection', async () => {
      const request: ToolRunRequest = {
        tool: 'photostats',
        collection_guid: 'col_01hgw2bbg00000000000000001',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockJob })

      const result = await runTool(request)

      expect(api.post).toHaveBeenCalledWith('/tools/run', request)
      expect(result).toEqual(mockJob)
    })

    test('starts pipeline_validation with mode and pipeline', async () => {
      const request: ToolRunRequest = {
        tool: 'pipeline_validation',
        collection_guid: 'col_01hgw2bbg00000000000000001',
        pipeline_guid: 'pip_01hgw2bbg00000000000000001',
        mode: 'validation',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockJob })

      await runTool(request)

      expect(api.post).toHaveBeenCalledWith('/tools/run', request)
    })

    test('starts display_graph mode without collection', async () => {
      const request: ToolRunRequest = {
        tool: 'pipeline_validation',
        pipeline_guid: 'pip_01hgw2bbg00000000000000001',
        mode: 'display_graph',
      }

      vi.mocked(api.post).mockResolvedValue({ data: { ...mockJob, collection_guid: null } })

      await runTool(request)

      expect(api.post).toHaveBeenCalledWith('/tools/run', request)
    })
  })

  describe('listJobs', () => {
    test('lists jobs without filters', async () => {
      const mockResponse: JobListResponse = {
        items: [mockJob],
        total: 1,
        limit: 50,
        offset: 0,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listJobs()

      expect(api.get).toHaveBeenCalledWith('/tools/jobs', {
        params: {},
        paramsSerializer: { indexes: null },
      })
      expect(result).toEqual(mockResponse)
    })

    test('lists jobs with single status filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0, limit: 50, offset: 0 } })

      await listJobs({ status: 'running' })

      expect(api.get).toHaveBeenCalledWith('/tools/jobs', {
        params: { status: 'running' },
        paramsSerializer: { indexes: null },
      })
    })

    test('lists jobs with multiple status filters', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0, limit: 50, offset: 0 } })

      await listJobs({ status: ['queued', 'running'] })

      expect(api.get).toHaveBeenCalledWith('/tools/jobs', {
        params: { status: ['queued', 'running'] },
        paramsSerializer: { indexes: null },
      })
    })

    test('lists jobs with collection filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0, limit: 50, offset: 0 } })

      await listJobs({ collection_guid: 'col_01hgw2bbg00000000000000001' })

      expect(api.get).toHaveBeenCalledWith('/tools/jobs', {
        params: { collection_guid: 'col_01hgw2bbg00000000000000001' },
        paramsSerializer: { indexes: null },
      })
    })

    test('lists jobs with pagination', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0, limit: 100, offset: 50 } })

      await listJobs({ limit: 100, offset: 50 })

      expect(api.get).toHaveBeenCalledWith('/tools/jobs', {
        params: { limit: 100, offset: 50 },
        paramsSerializer: { indexes: null },
      })
    })

    test('lists jobs with all filters', async () => {
      const params: JobListQueryParams = {
        status: ['completed', 'failed'],
        collection_guid: 'col_01hgw2bbg00000000000000001',
        tool: 'photostats',
        agent_guid: 'agt_01hgw2bbg00000000000000001',
        limit: 25,
        offset: 0,
      }

      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0, limit: 25, offset: 0 } })

      await listJobs(params)

      expect(api.get).toHaveBeenCalledWith('/tools/jobs', {
        params,
        paramsSerializer: { indexes: null },
      })
    })
  })

  describe('getJob', () => {
    test('retrieves a job by ID', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockJob })

      const result = await getJob('job_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('job_01hgw2bbg00000000000000001', 'job')
      expect(api.get).toHaveBeenCalledWith('/tools/jobs/job_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockJob)
    })
  })

  describe('cancelJob', () => {
    test('cancels a queued job', async () => {
      const cancelledJob = { ...mockJob, status: 'cancelled' as const }
      vi.mocked(api.post).mockResolvedValue({ data: cancelledJob })

      const result = await cancelJob('job_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('job_01hgw2bbg00000000000000001', 'job')
      expect(api.post).toHaveBeenCalledWith('/tools/jobs/job_01hgw2bbg00000000000000001/cancel')
      expect(result.status).toBe('cancelled')
    })
  })

  describe('retryJob', () => {
    test('retries a failed job', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: mockJob })

      const result = await retryJob('job_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('job_01hgw2bbg00000000000000001', 'job')
      expect(api.post).toHaveBeenCalledWith('/tools/jobs/job_01hgw2bbg00000000000000001/retry')
      expect(result).toEqual(mockJob)
    })
  })

  describe('getQueueStatus', () => {
    test('retrieves queue statistics', async () => {
      const mockStatus: QueueStatusResponse = {
        scheduled_count: 2,
        queued_count: 3,
        running_count: 1,
        completed_count: 10,
        failed_count: 2,
        cancelled_count: 1,
        current_job_id: 'job_01hgw2bbg00000000000000001',
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockStatus })

      const result = await getQueueStatus()

      expect(api.get).toHaveBeenCalledWith('/tools/queue/status')
      expect(result).toEqual(mockStatus)
    })
  })

  describe('getJobWebSocketUrl', () => {
    test('builds WebSocket URL for relative base URL', () => {
      const url = getJobWebSocketUrl('job_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('job_01hgw2bbg00000000000000001', 'job')
      expect(url).toContain('ws://')
      expect(url).toContain('/api/tools/ws/jobs/job_01hgw2bbg00000000000000001')
    })

    test('converts HTTPS to WSS for secure connections', () => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'https:', host: 'example.com' },
        writable: true,
      })

      const url = getJobWebSocketUrl('job_01hgw2bbg00000000000000001')

      expect(url).toContain('wss://')
    })
  })

  describe('getGlobalJobsWebSocketUrl', () => {
    test('builds WebSocket URL for global jobs channel', () => {
      // Reset window.location to http protocol for this test
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost' },
        writable: true,
      })

      const url = getGlobalJobsWebSocketUrl()

      expect(url).toContain('ws://')
      expect(url).toContain('/api/tools/ws/jobs/all')
    })
  })

  describe('runAllTools', () => {
    test('runs all tools on a collection', async () => {
      const mockResponse: RunAllToolsResponse = {
        jobs: [mockJob],
        skipped: [],
        message: 'All tools queued successfully',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await runAllTools('col_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('col_01hgw2bbg00000000000000001', 'col')
      expect(api.post).toHaveBeenCalledWith('/tools/run-all/col_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockResponse)
    })

    test('runs all tools with some skipped', async () => {
      const mockResponse: RunAllToolsResponse = {
        jobs: [mockJob],
        skipped: ['photo_pairing'],
        message: 'Some tools skipped (already running)',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await runAllTools('col_01hgw2bbg00000000000000001')

      expect(result.skipped).toContain('photo_pairing')
    })
  })
})
