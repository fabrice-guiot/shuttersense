import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  createManifest,
  listManifests,
  getManifestStats,
  getManifest,
  updateManifest,
  deleteManifest,
} from '@/services/release-manifests-api'
import type {
  ReleaseManifest,
  ReleaseManifestCreateRequest,
  ReleaseManifestUpdateRequest,
  ReleaseManifestListResponse,
  ReleaseManifestStatsResponse,
} from '@/contracts/api/release-manifests-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

describe('Release Manifests API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('createManifest', () => {
    test('creates a release manifest with required fields', async () => {
      const request: ReleaseManifestCreateRequest = {
        version: '1.0.0',
        platforms: ['darwin-arm64'],
        checksum: 'a'.repeat(64),
      }
      const mockManifest: ReleaseManifest = {
        guid: 'rel_01hgw2bbg00000000000000001',
        version: '1.0.0',
        platforms: ['darwin-arm64'],
        checksum: 'a'.repeat(64),
        is_active: true,
        notes: null,
        artifacts: [],
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockManifest })

      const result = await createManifest(request)

      expect(api.post).toHaveBeenCalledWith('/admin/release-manifests', request)
      expect(result).toEqual(mockManifest)
    })

    test('creates a release manifest with artifacts', async () => {
      const request: ReleaseManifestCreateRequest = {
        version: '1.0.0',
        platforms: ['darwin-arm64', 'linux-amd64'],
        checksum: 'a'.repeat(64),
        notes: 'Test release',
        is_active: false,
        artifacts: [
          {
            platform: 'darwin-arm64',
            filename: 'agent-darwin-arm64',
            checksum: 'sha256:' + 'b'.repeat(64),
            file_size: 1024000,
          },
        ],
      }

      vi.mocked(api.post).mockResolvedValue({
        data: {
          guid: 'rel_01hgw2bbg00000000000000001',
          ...request,
          artifacts: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      })

      await createManifest(request)

      expect(api.post).toHaveBeenCalledWith('/admin/release-manifests', request)
    })
  })

  describe('listManifests', () => {
    test('lists manifests without filters', async () => {
      const mockResponse: ReleaseManifestListResponse = {
        manifests: [
          {
            guid: 'rel_01hgw2bbg00000000000000001',
            version: '1.0.0',
            platforms: ['darwin-arm64'],
            checksum: 'a'.repeat(64),
            is_active: true,
            notes: null,
            artifacts: [],
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
          },
        ],
        total_count: 1,
        active_count: 1,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listManifests()

      expect(api.get).toHaveBeenCalledWith('/admin/release-manifests', {
        params: expect.any(URLSearchParams),
      })
      expect(result).toEqual(mockResponse)
    })

    test('lists manifests with active_only filter', async () => {
      const mockResponse: ReleaseManifestListResponse = {
        manifests: [],
        total_count: 0,
        active_count: 0,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      await listManifests({ active_only: true })

      const call = vi.mocked(api.get).mock.calls[0]
      const params = call[1]?.params as URLSearchParams
      expect(params.get('active_only')).toBe('true')
    })

    test('lists manifests with platform filter', async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { manifests: [], total_count: 0, active_count: 0 },
      })

      await listManifests({ platform: 'darwin-arm64' })

      const call = vi.mocked(api.get).mock.calls[0]
      const params = call[1]?.params as URLSearchParams
      expect(params.get('platform')).toBe('darwin-arm64')
    })

    test('lists manifests with version filter', async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { manifests: [], total_count: 0, active_count: 0 },
      })

      await listManifests({ version: '1.0.0' })

      const call = vi.mocked(api.get).mock.calls[0]
      const params = call[1]?.params as URLSearchParams
      expect(params.get('version')).toBe('1.0.0')
    })

    test('lists manifests with multiple filters', async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { manifests: [], total_count: 0, active_count: 0 },
      })

      await listManifests({
        active_only: true,
        platform: 'linux-amd64',
        version: '2.0.0',
      })

      const call = vi.mocked(api.get).mock.calls[0]
      const params = call[1]?.params as URLSearchParams
      expect(params.get('active_only')).toBe('true')
      expect(params.get('platform')).toBe('linux-amd64')
      expect(params.get('version')).toBe('2.0.0')
    })
  })

  describe('getManifestStats', () => {
    test('retrieves manifest statistics', async () => {
      const mockStats: ReleaseManifestStatsResponse = {
        total_count: 10,
        active_count: 5,
        platforms: ['darwin-arm64', 'linux-amd64'],
        versions: ['2.0.0', '1.0.0'],
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockStats })

      const result = await getManifestStats()

      expect(api.get).toHaveBeenCalledWith('/admin/release-manifests/stats')
      expect(result).toEqual(mockStats)
    })
  })

  describe('getManifest', () => {
    test('retrieves a specific manifest by GUID', async () => {
      const mockManifest: ReleaseManifest = {
        guid: 'rel_01hgw2bbg00000000000000001',
        version: '1.0.0',
        platforms: ['darwin-arm64'],
        checksum: 'a'.repeat(64),
        is_active: true,
        notes: 'Test notes',
        artifacts: [],
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockManifest })

      const result = await getManifest('rel_01hgw2bbg00000000000000001')

      expect(api.get).toHaveBeenCalledWith('/admin/release-manifests/rel_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockManifest)
    })
  })

  describe('updateManifest', () => {
    test('updates manifest with is_active field', async () => {
      const updateData: ReleaseManifestUpdateRequest = {
        is_active: false,
      }
      const mockManifest: ReleaseManifest = {
        guid: 'rel_01hgw2bbg00000000000000001',
        version: '1.0.0',
        platforms: ['darwin-arm64'],
        checksum: 'a'.repeat(64),
        is_active: false,
        notes: null,
        artifacts: [],
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.patch).mockResolvedValue({ data: mockManifest })

      const result = await updateManifest('rel_01hgw2bbg00000000000000001', updateData)

      expect(api.patch).toHaveBeenCalledWith('/admin/release-manifests/rel_01hgw2bbg00000000000000001', updateData)
      expect(result).toEqual(mockManifest)
    })

    test('updates manifest with notes field', async () => {
      const updateData: ReleaseManifestUpdateRequest = {
        notes: 'Updated notes',
      }

      vi.mocked(api.patch).mockResolvedValue({
        data: {
          guid: 'rel_01hgw2bbg00000000000000001',
          version: '1.0.0',
          platforms: ['darwin-arm64'],
          checksum: 'a'.repeat(64),
          is_active: true,
          notes: 'Updated notes',
          artifacts: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      })

      await updateManifest('rel_01hgw2bbg00000000000000001', updateData)

      expect(api.patch).toHaveBeenCalledWith('/admin/release-manifests/rel_01hgw2bbg00000000000000001', updateData)
    })

    test('updates manifest with both fields', async () => {
      const updateData: ReleaseManifestUpdateRequest = {
        is_active: false,
        notes: 'Deprecated version',
      }

      vi.mocked(api.patch).mockResolvedValue({
        data: {
          guid: 'rel_01hgw2bbg00000000000000001',
          version: '1.0.0',
          platforms: ['darwin-arm64'],
          checksum: 'a'.repeat(64),
          is_active: false,
          notes: 'Deprecated version',
          artifacts: [],
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      })

      await updateManifest('rel_01hgw2bbg00000000000000001', updateData)

      expect(api.patch).toHaveBeenCalledWith('/admin/release-manifests/rel_01hgw2bbg00000000000000001', updateData)
    })
  })

  describe('deleteManifest', () => {
    test('deletes a manifest by GUID', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: undefined })

      await deleteManifest('rel_01hgw2bbg00000000000000001')

      expect(api.delete).toHaveBeenCalledWith('/admin/release-manifests/rel_01hgw2bbg00000000000000001')
    })
  })
})
