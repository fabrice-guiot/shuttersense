import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  listResults,
  getResult,
  deleteResult,
  getReportUrl,
  downloadReport,
  getResultStats,
} from '@/services/results'
import type {
  ResultListResponse,
  ResultStatsResponse,
} from '@/contracts/api/results-api'

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

describe('results service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listResults', () => {
    test('fetches results without params', async () => {
      const mockResponse: ResultListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await listResults()

      expect(api.get).toHaveBeenCalledWith('/results', { params: {} })
      expect(result).toEqual(mockResponse)
    })

    test('fetches results with params', async () => {
      const mockResponse: ResultListResponse = {
        items: [],
        total: 0,
        limit: 10,
        offset: 0,
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await listResults({ tool: 'photostats', status: 'COMPLETED', limit: 10 })

      expect(api.get).toHaveBeenCalledWith('/results', {
        params: { tool: 'photostats', status: 'COMPLETED', limit: 10 },
      })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getResult', () => {
    test('fetches result by guid', async () => {
      const mockResult = { guid: 'res_01hgw2bbg00000000000000001', tool: 'photostats' }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResult })

      const result = await getResult('res_01hgw2bbg00000000000000001')

      expect(api.get).toHaveBeenCalledWith('/results/res_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockResult)
    })
  })

  describe('deleteResult', () => {
    test('deletes result', async () => {
      const mockResponse = { message: 'Deleted', deleted_guid: 'res_01hgw2bbg00000000000000001' }

      vi.mocked(api.delete).mockResolvedValueOnce({ data: mockResponse })

      const result = await deleteResult('res_01hgw2bbg00000000000000001')

      expect(api.delete).toHaveBeenCalledWith('/results/res_01hgw2bbg00000000000000001')
      expect(result.deleted_guid).toBe('res_01hgw2bbg00000000000000001')
    })
  })

  describe('getReportUrl', () => {
    test('returns report URL', () => {
      const result = getReportUrl('res_01hgw2bbg00000000000000001')
      expect(result).toBe('/api/results/res_01hgw2bbg00000000000000001/report')
    })
  })

  describe('downloadReport', () => {
    test('downloads report with filename from header', async () => {
      const mockBlob = new Blob(['<html>Report</html>'], { type: 'text/html' })

      vi.mocked(api.get).mockResolvedValueOnce({
        data: mockBlob,
        headers: { 'content-disposition': 'attachment; filename="photostats_report.html"' },
      })

      const result = await downloadReport('res_01hgw2bbg00000000000000001')

      expect(api.get).toHaveBeenCalledWith('/results/res_01hgw2bbg00000000000000001/report', {
        responseType: 'blob',
      })
      expect(result.blob).toEqual(mockBlob)
      expect(result.filename).toBe('photostats_report.html')
    })

    test('uses fallback filename when header missing', async () => {
      const mockBlob = new Blob(['<html>Report</html>'], { type: 'text/html' })

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockBlob, headers: {} })

      const result = await downloadReport('res_01hgw2bbg00000000000000001')

      expect(result.filename).toBe('report_res_01hgw2bbg00000000000000001.html')
    })
  })

  describe('getResultStats', () => {
    test('fetches result statistics', async () => {
      const mockStats: ResultStatsResponse = {
        total_results: 50,
        completed_count: 45,
        failed_count: 3,
        by_tool: {
          photostats: 30,
          photo_pairing: 15,
          pipeline_validation: 5,
          collection_test: 0,
          inventory_validate: 0,
          inventory_import: 0,
        },
        last_run: '2026-02-01T10:00:00Z',
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockStats })

      const result = await getResultStats()

      expect(api.get).toHaveBeenCalledWith('/results/stats')
      expect(result).toEqual(mockStats)
    })
  })
})
