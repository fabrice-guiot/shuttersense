import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  getConfiguration,
  getCategoryConfig,
  getConfigValue,
  createConfigValue,
  updateConfigValue,
  deleteConfigValue,
  getConfigStats,
  startImport,
  getImportSession,
  resolveImport,
  cancelImport,
  exportConfiguration,
  getEventStatuses,
} from '@/services/config'
import type {
  ConfigurationResponse,
  CategoryConfigResponse,
  ConfigValueResponse,
  ConfigStatsResponse,
  ImportSessionResponse,
  ImportResultResponse,
  ConfigValueUpdateRequest,
  ConflictResolutionRequest,
  EventStatusesResponse,
} from '@/contracts/api/config-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

describe('Config Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getConfiguration', () => {
    test('fetches all configuration', async () => {
      const mockResponse: ConfigurationResponse = {
        extensions: {
          photo_extensions: ['.dng', '.cr3'],
          metadata_extensions: ['.xmp'],
          require_sidecar: ['.cr3'],
        },
        cameras: {
          AB3D: {
            name: 'Canon EOS R5',
            serial_number: '12345',
          },
        },
        processing_methods: {
          HDR: 'High Dynamic Range',
        },
        event_statuses: {
          confirmed: {
            label: 'Confirmed',
            display_order: 1,
          },
        },
        collection_ttl: {
          '3600': {
            value: 3600,
            label: '1 hour',
          },
        },
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getConfiguration()

      expect(api.get).toHaveBeenCalledWith('/config')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getCategoryConfig', () => {
    test('fetches configuration for a specific category', async () => {
      const mockResponse: CategoryConfigResponse = {
        category: 'cameras',
        items: [
          {
            key: 'AB3D',
            value: { name: 'Canon EOS R5', serial_number: '12345' },
            description: null,
            source: 'database',
            updated_at: '2026-01-01T00:00:00Z',
          },
        ],
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getCategoryConfig('cameras')

      expect(api.get).toHaveBeenCalledWith('/config/cameras')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getConfigValue', () => {
    test('fetches a specific configuration value', async () => {
      const mockResponse: ConfigValueResponse = {
        category: 'cameras',
        key: 'AB3D',
        value: { name: 'Canon EOS R5', serial_number: '12345' },
        description: null,
        source: 'database',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getConfigValue('cameras', 'AB3D')

      expect(api.get).toHaveBeenCalledWith('/config/cameras/AB3D')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('createConfigValue', () => {
    test('creates a configuration value', async () => {
      const requestData: ConfigValueUpdateRequest = {
        value: { name: 'Canon EOS R6', serial_number: '67890' },
        description: 'New camera',
      }

      const mockResponse: ConfigValueResponse = {
        category: 'cameras',
        key: 'XY12',
        value: requestData.value,
        description: requestData.description,
        source: 'database',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await createConfigValue('cameras', 'XY12', requestData)

      expect(api.post).toHaveBeenCalledWith('/config/cameras/XY12', requestData)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('updateConfigValue', () => {
    test('updates a configuration value', async () => {
      const requestData: ConfigValueUpdateRequest = {
        value: { name: 'Canon EOS R5 Mark II', serial_number: '12345' },
        description: 'Updated camera',
      }

      const mockResponse: ConfigValueResponse = {
        category: 'cameras',
        key: 'AB3D',
        value: requestData.value,
        description: requestData.description,
        source: 'database',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.put).mockResolvedValue({ data: mockResponse })

      const result = await updateConfigValue('cameras', 'AB3D', requestData)

      expect(api.put).toHaveBeenCalledWith('/config/cameras/AB3D', requestData)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('deleteConfigValue', () => {
    test('deletes a configuration value', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: null })

      await deleteConfigValue('cameras', 'AB3D')

      expect(api.delete).toHaveBeenCalledWith('/config/cameras/AB3D')
    })
  })

  describe('getConfigStats', () => {
    test('fetches configuration statistics', async () => {
      const mockResponse: ConfigStatsResponse = {
        total_items: 42,
        cameras_configured: 5,
        processing_methods_configured: 8,
        last_import: '2026-01-01T00:00:00Z',
        source_breakdown: {
          database: 30,
          yaml_import: 12,
        },
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getConfigStats()

      expect(api.get).toHaveBeenCalledWith('/config/stats')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('startImport', () => {
    test('starts YAML import with FormData', async () => {
      const mockFile = new File(['content'], 'config.yaml', { type: 'application/yaml' })

      const mockResponse: ImportSessionResponse = {
        session_id: 'imp_01hgw2bbg00000000000000001',
        status: 'pending',
        expires_at: '2026-01-01T01:00:00Z',
        file_name: 'config.yaml',
        total_items: 10,
        new_items: 5,
        conflicts: [],
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await startImport(mockFile)

      expect(api.post).toHaveBeenCalledWith(
        '/config/import',
        expect.any(FormData),
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )

      const formDataArg = vi.mocked(api.post).mock.calls[0][1] as FormData
      expect(formDataArg.get('file')).toBe(mockFile)

      expect(result).toEqual(mockResponse)
    })
  })

  describe('getImportSession', () => {
    test('fetches import session status', async () => {
      const sessionId = 'imp_01hgw2bbg00000000000000001'

      const mockResponse: ImportSessionResponse = {
        session_id: sessionId,
        status: 'pending',
        expires_at: '2026-01-01T01:00:00Z',
        file_name: 'config.yaml',
        total_items: 10,
        new_items: 5,
        conflicts: [
          {
            category: 'cameras',
            key: 'AB3D',
            database_value: { name: 'Canon EOS R5', serial_number: '12345' },
            yaml_value: { name: 'Canon EOS R5 II', serial_number: '12345' },
            resolved: false,
            resolution: null,
          },
        ],
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getImportSession(sessionId)

      expect(api.get).toHaveBeenCalledWith(`/config/import/${sessionId}`)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('resolveImport', () => {
    test('resolves conflicts and applies import', async () => {
      const sessionId = 'imp_01hgw2bbg00000000000000001'
      const requestData: ConflictResolutionRequest = {
        resolutions: [
          {
            category: 'cameras',
            key: 'AB3D',
            use_yaml: true,
          },
        ],
      }

      const mockResponse: ImportResultResponse = {
        success: true,
        items_imported: 5,
        items_skipped: 0,
        message: 'Import completed successfully',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await resolveImport(sessionId, requestData)

      expect(api.post).toHaveBeenCalledWith(`/config/import/${sessionId}/resolve`, requestData)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('cancelImport', () => {
    test('cancels an import session', async () => {
      const sessionId = 'imp_01hgw2bbg00000000000000001'

      vi.mocked(api.post).mockResolvedValue({ data: null })

      await cancelImport(sessionId)

      expect(api.post).toHaveBeenCalledWith(`/config/import/${sessionId}/cancel`)
    })
  })

  describe('exportConfiguration', () => {
    test('exports configuration as YAML blob', async () => {
      const mockBlob = new Blob(['yaml content'], { type: 'application/yaml' })

      vi.mocked(api.get).mockResolvedValue({ data: mockBlob })

      const result = await exportConfiguration()

      expect(api.get).toHaveBeenCalledWith('/config/export', {
        responseType: 'blob',
      })
      expect(result).toBe(mockBlob)
    })
  })

  describe('getEventStatuses', () => {
    test('fetches event statuses ordered by display order', async () => {
      const mockResponse: EventStatusesResponse = {
        statuses: [
          {
            key: 'future',
            label: 'Future',
            display_order: 1,
          },
          {
            key: 'confirmed',
            label: 'Confirmed',
            display_order: 2,
          },
        ],
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getEventStatuses()

      expect(api.get).toHaveBeenCalledWith('/config/event_statuses')
      expect(result).toEqual(mockResponse)
    })
  })
})
