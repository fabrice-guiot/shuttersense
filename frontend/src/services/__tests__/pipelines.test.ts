import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  listPipelines,
  getPipeline,
  createPipeline,
  updatePipeline,
  deletePipeline,
  activatePipeline,
  deactivatePipeline,
  setDefaultPipeline,
  unsetDefaultPipeline,
  validatePipeline,
  previewFilenames,
  getPipelineHistory,
  getPipelineVersion,
  getPipelineStats,
  importPipeline,
  getExportUrl,
  downloadPipelineYaml,
  downloadPipelineVersionYaml,
} from '@/services/pipelines'
import type {
  Pipeline,
  PipelineSummary,
  PipelineListResponse,
  PipelineCreateRequest,
  PipelineUpdateRequest,
  PipelineStatsResponse,
  PipelineDeleteResponse,
  PipelineListQueryParams,
  ValidationResult,
  FilenamePreviewResponse,
  PipelineHistoryEntry,
} from '@/contracts/api/pipelines-api'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000/api' },
  },
}))

describe('Pipelines Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listPipelines', () => {
    test('lists all pipelines without filters', async () => {
      const mockPipelines: PipelineSummary[] = [
        {
          guid: 'pip_01hgw2bbg00000000000000001',
          name: 'Standard Pipeline',
          description: 'Default pipeline',
          version: 1,
          is_active: true,
          is_default: true,
          is_valid: true,
          node_count: 5,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ]

      const mockResponse: PipelineListResponse = {
        items: mockPipelines,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listPipelines()

      expect(api.get).toHaveBeenCalledWith('/pipelines', { params: {} })
      expect(result).toEqual(mockPipelines)
    })

    test('lists pipelines with filters', async () => {
      const params: PipelineListQueryParams = {
        is_active: true,
        is_valid: true,
      }

      const mockResponse: PipelineListResponse = {
        items: [],
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      await listPipelines(params)

      expect(api.get).toHaveBeenCalledWith('/pipelines', {
        params: { is_active: true, is_valid: true },
      })
    })
  })

  describe('getPipeline', () => {
    test('fetches a single pipeline by GUID', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'

      const mockPipeline: Pipeline = {
        guid: pipelineGuid,
        name: 'Standard Pipeline',
        description: 'Default pipeline',
        nodes: [],
        edges: [],
        version: 1,
        is_active: true,
        is_default: true,
        is_valid: true,
        validation_errors: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockPipeline })

      const result = await getPipeline(pipelineGuid)

      expect(api.get).toHaveBeenCalledWith(`/pipelines/${encodeURIComponent(pipelineGuid)}`)
      expect(result).toEqual(mockPipeline)
    })

    test('throws error for invalid GUID', async () => {
      await expect(getPipeline('invalid_guid')).rejects.toThrow('Invalid GUID format')
    })
  })

  describe('createPipeline', () => {
    test('creates a new pipeline', async () => {
      const requestData: PipelineCreateRequest = {
        name: 'New Pipeline',
        description: 'Test pipeline',
        nodes: [
          {
            id: 'capture',
            type: 'capture',
            properties: {
              sample_filename: 'AB3D0001',
              filename_regex: '([A-Z0-9]{4})([0-9]{4})',
              camera_id_group: '1',
            },
          },
        ],
        edges: [],
      }

      const mockPipeline: Pipeline = {
        guid: 'pip_01hgw2bbg00000000000000001',
        name: requestData.name,
        description: requestData.description || null,
        nodes: requestData.nodes,
        edges: requestData.edges,
        version: 1,
        is_active: false,
        is_default: false,
        is_valid: true,
        validation_errors: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockPipeline })

      const result = await createPipeline(requestData)

      expect(api.post).toHaveBeenCalledWith('/pipelines', requestData)
      expect(result).toEqual(mockPipeline)
    })
  })

  describe('updatePipeline', () => {
    test('updates an existing pipeline', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'
      const requestData: PipelineUpdateRequest = {
        name: 'Updated Pipeline',
        change_summary: 'Updated name',
      }

      const mockPipeline: Pipeline = {
        guid: pipelineGuid,
        name: requestData.name!,
        description: null,
        nodes: [],
        edges: [],
        version: 2,
        is_active: true,
        is_default: false,
        is_valid: true,
        validation_errors: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T12:00:00Z',
      }

      vi.mocked(api.put).mockResolvedValue({ data: mockPipeline })

      const result = await updatePipeline(pipelineGuid, requestData)

      expect(api.put).toHaveBeenCalledWith(
        `/pipelines/${encodeURIComponent(pipelineGuid)}`,
        requestData
      )
      expect(result).toEqual(mockPipeline)
    })
  })

  describe('deletePipeline', () => {
    test('deletes a pipeline', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'

      const mockResponse: PipelineDeleteResponse = {
        message: 'Pipeline deleted successfully',
        deleted_guid: pipelineGuid,
      }

      vi.mocked(api.delete).mockResolvedValue({ data: mockResponse })

      const result = await deletePipeline(pipelineGuid)

      expect(api.delete).toHaveBeenCalledWith(`/pipelines/${encodeURIComponent(pipelineGuid)}`)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('activatePipeline', () => {
    test('activates a pipeline', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'

      const mockPipeline: Pipeline = {
        guid: pipelineGuid,
        name: 'Pipeline',
        description: null,
        nodes: [],
        edges: [],
        version: 1,
        is_active: true,
        is_default: false,
        is_valid: true,
        validation_errors: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T12:00:00Z',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockPipeline })

      const result = await activatePipeline(pipelineGuid)

      expect(api.post).toHaveBeenCalledWith(
        `/pipelines/${encodeURIComponent(pipelineGuid)}/activate`
      )
      expect(result).toEqual(mockPipeline)
    })
  })

  describe('deactivatePipeline', () => {
    test('deactivates a pipeline', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'

      const mockPipeline: Pipeline = {
        guid: pipelineGuid,
        name: 'Pipeline',
        description: null,
        nodes: [],
        edges: [],
        version: 1,
        is_active: false,
        is_default: false,
        is_valid: true,
        validation_errors: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T12:00:00Z',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockPipeline })

      const result = await deactivatePipeline(pipelineGuid)

      expect(api.post).toHaveBeenCalledWith(
        `/pipelines/${encodeURIComponent(pipelineGuid)}/deactivate`
      )
      expect(result).toEqual(mockPipeline)
    })
  })

  describe('setDefaultPipeline', () => {
    test('sets a pipeline as default', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'

      const mockPipeline: Pipeline = {
        guid: pipelineGuid,
        name: 'Pipeline',
        description: null,
        nodes: [],
        edges: [],
        version: 1,
        is_active: true,
        is_default: true,
        is_valid: true,
        validation_errors: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T12:00:00Z',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockPipeline })

      const result = await setDefaultPipeline(pipelineGuid)

      expect(api.post).toHaveBeenCalledWith(
        `/pipelines/${encodeURIComponent(pipelineGuid)}/set-default`
      )
      expect(result).toEqual(mockPipeline)
    })
  })

  describe('unsetDefaultPipeline', () => {
    test('removes default status from a pipeline', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'

      const mockPipeline: Pipeline = {
        guid: pipelineGuid,
        name: 'Pipeline',
        description: null,
        nodes: [],
        edges: [],
        version: 1,
        is_active: true,
        is_default: false,
        is_valid: true,
        validation_errors: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T12:00:00Z',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockPipeline })

      const result = await unsetDefaultPipeline(pipelineGuid)

      expect(api.post).toHaveBeenCalledWith(
        `/pipelines/${encodeURIComponent(pipelineGuid)}/unset-default`
      )
      expect(result).toEqual(mockPipeline)
    })
  })

  describe('validatePipeline', () => {
    test('validates pipeline structure', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'

      const mockResponse: ValidationResult = {
        is_valid: true,
        errors: [],
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await validatePipeline(pipelineGuid)

      expect(api.post).toHaveBeenCalledWith(
        `/pipelines/${encodeURIComponent(pipelineGuid)}/validate`
      )
      expect(result).toEqual(mockResponse)
    })

    test('returns validation errors', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'

      const mockResponse: ValidationResult = {
        is_valid: false,
        errors: [
          {
            type: 'orphaned_node',
            message: 'Node is not connected',
            node_id: 'node1',
            suggestion: 'Connect to another node',
          },
        ],
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await validatePipeline(pipelineGuid)

      expect(result.is_valid).toBe(false)
      expect(result.errors).toHaveLength(1)
    })
  })

  describe('previewFilenames', () => {
    test('previews expected filenames', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'

      const mockResponse: FilenamePreviewResponse = {
        base_filename: 'AB3D0001',
        expected_files: [
          {
            path: '',
            filename: 'AB3D0001.dng',
            optional: false,
          },
          {
            path: '',
            filename: 'AB3D0001.xmp',
            optional: true,
          },
        ],
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await previewFilenames(pipelineGuid)

      expect(api.post).toHaveBeenCalledWith(
        `/pipelines/${encodeURIComponent(pipelineGuid)}/preview`,
        {}
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getPipelineHistory', () => {
    test('fetches pipeline version history', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'

      const mockHistory: PipelineHistoryEntry[] = [
        {
          version: 2,
          change_summary: 'Updated nodes',
          changed_by: 'user@example.com',
          created_at: '2026-01-01T12:00:00Z',
        },
        {
          version: 1,
          change_summary: null,
          changed_by: 'user@example.com',
          created_at: '2026-01-01T00:00:00Z',
        },
      ]

      vi.mocked(api.get).mockResolvedValue({ data: mockHistory })

      const result = await getPipelineHistory(pipelineGuid)

      expect(api.get).toHaveBeenCalledWith(
        `/pipelines/${encodeURIComponent(pipelineGuid)}/history`
      )
      expect(result).toEqual(mockHistory)
    })
  })

  describe('getPipelineVersion', () => {
    test('fetches a specific pipeline version', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'
      const version = 1

      const mockPipeline: Pipeline = {
        guid: pipelineGuid,
        name: 'Pipeline',
        description: null,
        nodes: [],
        edges: [],
        version: 1,
        is_active: false,
        is_default: false,
        is_valid: true,
        validation_errors: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockPipeline })

      const result = await getPipelineVersion(pipelineGuid, version)

      expect(api.get).toHaveBeenCalledWith(
        `/pipelines/${encodeURIComponent(pipelineGuid)}/versions/${version}`
      )
      expect(result).toEqual(mockPipeline)
    })
  })

  describe('getPipelineStats', () => {
    test('fetches pipeline statistics', async () => {
      const mockResponse: PipelineStatsResponse = {
        total_pipelines: 10,
        valid_pipelines: 8,
        active_pipeline_count: 5,
        default_pipeline_guid: 'pip_01hgw2bbg00000000000000001',
        default_pipeline_name: 'Standard Pipeline',
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getPipelineStats()

      expect(api.get).toHaveBeenCalledWith('/pipelines/stats')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('importPipeline', () => {
    test('imports pipeline from YAML file', async () => {
      const mockFile = new File(['content'], 'pipeline.yaml', { type: 'application/yaml' })

      const mockPipeline: Pipeline = {
        guid: 'pip_01hgw2bbg00000000000000001',
        name: 'Imported Pipeline',
        description: null,
        nodes: [],
        edges: [],
        version: 1,
        is_active: false,
        is_default: false,
        is_valid: true,
        validation_errors: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockPipeline })

      const result = await importPipeline(mockFile)

      expect(api.post).toHaveBeenCalledWith(
        '/pipelines/import',
        expect.any(FormData),
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )

      const formDataArg = vi.mocked(api.post).mock.calls[0][1] as FormData
      expect(formDataArg.get('file')).toBe(mockFile)

      expect(result).toEqual(mockPipeline)
    })
  })

  describe('getExportUrl', () => {
    test('returns export URL for a pipeline', () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'

      const url = getExportUrl(pipelineGuid)

      expect(url).toBe(
        `http://localhost:8000/api/pipelines/${encodeURIComponent(pipelineGuid)}/export`
      )
    })
  })

  describe('downloadPipelineYaml', () => {
    test('downloads pipeline as YAML with filename from header', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'
      const mockBlob = new Blob(['yaml content'], { type: 'application/yaml' })

      vi.mocked(api.get).mockResolvedValue({
        data: mockBlob,
        headers: {
          'content-disposition': 'attachment; filename="standard-pipeline.yaml"',
        },
      })

      const result = await downloadPipelineYaml(pipelineGuid)

      expect(api.get).toHaveBeenCalledWith(
        `/pipelines/${encodeURIComponent(pipelineGuid)}/export`,
        { responseType: 'blob' }
      )
      expect(result.blob).toBe(mockBlob)
      expect(result.filename).toBe('standard-pipeline.yaml')
    })

    test('uses fallback filename if header missing', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'
      const mockBlob = new Blob(['yaml content'], { type: 'application/yaml' })

      vi.mocked(api.get).mockResolvedValue({
        data: mockBlob,
        headers: {},
      })

      const result = await downloadPipelineYaml(pipelineGuid)

      expect(result.filename).toBe(`pipeline_${pipelineGuid}.yaml`)
    })
  })

  describe('downloadPipelineVersionYaml', () => {
    test('downloads specific pipeline version as YAML', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'
      const version = 2
      const mockBlob = new Blob(['yaml content'], { type: 'application/yaml' })

      vi.mocked(api.get).mockResolvedValue({
        data: mockBlob,
        headers: {
          'content-disposition': 'attachment; filename="pipeline-v2.yaml"',
        },
      })

      const result = await downloadPipelineVersionYaml(pipelineGuid, version)

      expect(api.get).toHaveBeenCalledWith(
        `/pipelines/${encodeURIComponent(pipelineGuid)}/versions/${version}/export`,
        { responseType: 'blob' }
      )
      expect(result.blob).toBe(mockBlob)
      expect(result.filename).toBe('pipeline-v2.yaml')
    })

    test('uses fallback filename with version if header missing', async () => {
      const pipelineGuid = 'pip_01hgw2bbg00000000000000001'
      const version = 3
      const mockBlob = new Blob(['yaml content'], { type: 'application/yaml' })

      vi.mocked(api.get).mockResolvedValue({
        data: mockBlob,
        headers: {},
      })

      const result = await downloadPipelineVersionYaml(pipelineGuid, version)

      expect(result.filename).toBe(`pipeline_${pipelineGuid}_v${version}.yaml`)
    })
  })
})
