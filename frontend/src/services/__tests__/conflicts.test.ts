import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  detectConflicts,
  getEventScore,
  resolveConflict,
  getConflictRules,
  updateConflictRules,
  getScoringWeights,
  updateScoringWeights,
} from '@/services/conflicts'
import type {
  ConflictDetectionResponse,
  EventScoreResponse,
  ConflictResolveRequest,
  ConflictResolveResponse,
  ConflictRulesResponse,
  ScoringWeightsResponse,
} from '@/contracts/api/conflict-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

describe('conflicts service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('detectConflicts', () => {
    test('detects conflicts for date range', async () => {
      const mockResponse: ConflictDetectionResponse = {
        conflict_groups: [],
        scored_events: [],
        summary: { total_groups: 0, unresolved: 0, partially_resolved: 0, resolved: 0 },
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await detectConflicts('2026-06-01', '2026-06-30')

      expect(api.get).toHaveBeenCalledWith('/events/conflicts', {
        params: { start_date: '2026-06-01', end_date: '2026-06-30' },
      })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getEventScore', () => {
    test('fetches event score', async () => {
      const mockResponse: EventScoreResponse = {
        guid: 'evt_01hgw2bbg00000000000000001',
        title: 'Summer Festival',
        event_date: '2026-06-15',
        scores: {
          venue_quality: 80,
          organizer_reputation: 70,
          performer_lineup: 90,
          logistics_ease: 60,
          readiness: 50,
          composite: 72,
        },
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await getEventScore('evt_01hgw2bbg00000000000000001')

      expect(api.get).toHaveBeenCalledWith('/events/evt_01hgw2bbg00000000000000001/score')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('resolveConflict', () => {
    test('resolves conflict', async () => {
      const request: ConflictResolveRequest = {
        group_id: 'cg_1',
        decisions: [
          { event_guid: 'evt_01hgw2bbg00000000000000001', attendance: 'planned' },
          { event_guid: 'evt_01hgw2bbg00000000000000002', attendance: 'skipped' },
        ],
      }

      const mockResponse: ConflictResolveResponse = {
        success: true,
        updated_count: 2,
      }

      vi.mocked(api.post).mockResolvedValueOnce({ data: mockResponse })

      const result = await resolveConflict(request)

      expect(api.post).toHaveBeenCalledWith('/events/conflicts/resolve', request)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getConflictRules', () => {
    test('fetches conflict rules', async () => {
      const mockResponse: ConflictRulesResponse = {
        distance_threshold_miles: 50,
        consecutive_window_days: 1,
        travel_buffer_days: 0,
        colocation_radius_miles: 5,
        performer_ceiling: 10,
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await getConflictRules()

      expect(api.get).toHaveBeenCalledWith('/config/conflict_rules')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('updateConflictRules', () => {
    test('updates conflict rules', async () => {
      const mockResponse: ConflictRulesResponse = {
        distance_threshold_miles: 100,
        consecutive_window_days: 2,
        travel_buffer_days: 1,
        colocation_radius_miles: 10,
        performer_ceiling: 15,
      }

      vi.mocked(api.put).mockResolvedValueOnce({ data: mockResponse })

      const result = await updateConflictRules({ distance_threshold_miles: 100 })

      expect(api.put).toHaveBeenCalledWith('/config/conflict_rules', { distance_threshold_miles: 100 })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getScoringWeights', () => {
    test('fetches scoring weights', async () => {
      const mockResponse: ScoringWeightsResponse = {
        weight_venue_quality: 20,
        weight_organizer_reputation: 20,
        weight_performer_lineup: 20,
        weight_logistics_ease: 20,
        weight_readiness: 20,
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await getScoringWeights()

      expect(api.get).toHaveBeenCalledWith('/config/scoring_weights')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('updateScoringWeights', () => {
    test('updates scoring weights', async () => {
      const mockResponse: ScoringWeightsResponse = {
        weight_venue_quality: 30,
        weight_organizer_reputation: 25,
        weight_performer_lineup: 20,
        weight_logistics_ease: 15,
        weight_readiness: 10,
      }

      vi.mocked(api.put).mockResolvedValueOnce({ data: mockResponse })

      const result = await updateScoringWeights({ weight_venue_quality: 30 })

      expect(api.put).toHaveBeenCalledWith('/config/scoring_weights', { weight_venue_quality: 30 })
      expect(result).toEqual(mockResponse)
    })
  })
})
