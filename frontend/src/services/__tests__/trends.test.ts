import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  getPhotoStatsTrends,
  getPhotoPairingTrends,
  getPipelineValidationTrends,
  getDisplayGraphTrends,
  getTrendSummary,
} from '@/services/trends'
import type {
  PhotoStatsTrendResponse,
  PhotoPairingTrendResponse,
  PipelineValidationTrendResponse,
  DisplayGraphTrendResponse,
  TrendSummaryResponse,
} from '@/contracts/api/trends-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

describe('trends service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getPhotoStatsTrends', () => {
    test('fetches without params', async () => {
      const mockResponse: PhotoStatsTrendResponse = {
        mode: 'aggregated',
        data_points: [
          {
            date: '2026-01-01',
            orphaned_images: 5,
            orphaned_metadata: 3,
            collections_included: 2,
            no_change_count: 0,
            has_transition: false,
            calculated_count: 0,
          },
        ],
        collections: [],
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await getPhotoStatsTrends()

      expect(api.get).toHaveBeenCalledWith('/trends/photostats', { params: {} })
      expect(result).toEqual(mockResponse)
    })

    test('fetches with params and strips undefined', async () => {
      const mockResponse: PhotoStatsTrendResponse = {
        mode: 'aggregated',
        data_points: [],
        collections: [],
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      await getPhotoStatsTrends({ from_date: '2026-02-01', to_date: undefined })

      expect(api.get).toHaveBeenCalledWith('/trends/photostats', {
        params: { from_date: '2026-02-01' },
      })
    })
  })

  describe('getPhotoPairingTrends', () => {
    test('fetches photo pairing trends', async () => {
      const mockResponse: PhotoPairingTrendResponse = {
        mode: 'aggregated',
        data_points: [
          {
            date: '2026-01-01',
            group_count: 100,
            image_count: 500,
            collections_included: 2,
            no_change_count: 0,
            has_transition: false,
            calculated_count: 0,
          },
        ],
        collections: [],
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await getPhotoPairingTrends()

      expect(api.get).toHaveBeenCalledWith('/trends/photo-pairing', { params: {} })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getPipelineValidationTrends', () => {
    test('fetches pipeline validation trends', async () => {
      const mockResponse: PipelineValidationTrendResponse = {
        mode: 'aggregated',
        data_points: [
          {
            date: '2026-01-01',
            overall_consistency_pct: 95,
            overall_inconsistent_pct: 5,
            black_box_consistency_pct: 98,
            browsable_consistency_pct: 92,
            total_images: 1000,
            consistent_count: 950,
            inconsistent_count: 50,
            collections_included: 3,
            no_change_count: 0,
            has_transition: false,
            calculated_count: 0,
          },
        ],
        collections: [],
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await getPipelineValidationTrends()

      expect(api.get).toHaveBeenCalledWith('/trends/pipeline-validation', { params: {} })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getDisplayGraphTrends', () => {
    test('fetches display graph trends', async () => {
      const mockResponse: DisplayGraphTrendResponse = {
        data_points: [
          {
            date: '2026-01-01',
            total_paths: 25,
            valid_paths: 20,
            black_box_archive_paths: 10,
            browsable_archive_paths: 10,
          },
        ],
        pipelines_included: [{ pipeline_id: 1, pipeline_name: 'Main', result_count: 5 }],
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await getDisplayGraphTrends()

      expect(api.get).toHaveBeenCalledWith('/trends/display-graph', { params: {} })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getTrendSummary', () => {
    test('fetches trend summary', async () => {
      const mockResponse: TrendSummaryResponse = {
        collection_id: null,
        orphaned_trend: 'stable',
        consistency_trend: 'improving',
        last_photostats: '2026-02-01T10:00:00Z',
        last_photo_pairing: '2026-02-01T10:00:00Z',
        last_pipeline_validation: '2026-01-28T10:00:00Z',
        data_points_available: { photostats: 10, photo_pairing: 8, pipeline_validation: 5 },
        stable_periods: {
          photostats_stable: true,
          photostats_stable_days: 5,
          photo_pairing_stable: false,
          photo_pairing_stable_days: 0,
          pipeline_validation_stable: true,
          pipeline_validation_stable_days: 3,
        },
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await getTrendSummary()

      expect(api.get).toHaveBeenCalledWith('/trends/summary', { params: {} })
      expect(result).toEqual(mockResponse)
    })

    test('passes collection_guid param', async () => {
      vi.mocked(api.get).mockResolvedValueOnce({ data: {} })

      await getTrendSummary({ collection_guid: 'col_01hgw2bbg00000000000000001' })

      expect(api.get).toHaveBeenCalledWith('/trends/summary', {
        params: { collection_guid: 'col_01hgw2bbg00000000000000001' },
      })
    })
  })
})
