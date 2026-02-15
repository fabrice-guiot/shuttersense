import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  listConnectors,
  getConnector,
  createConnector,
  updateConnector,
  deleteConnector,
  testConnector,
  getConnectorStats,
} from '@/services/connectors'
import type {
  Connector,
  ConnectorTestResponse,
  ConnectorStatsResponse,
} from '@/contracts/api/connector-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

const mockConnector: Connector = {
  guid: 'con_01hgw2bbg00000000000000001',
  name: 'AWS S3 Production',
  type: 's3',
  credential_location: 'server',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('connectors service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listConnectors', () => {
    test('fetches connectors without filters', async () => {
      vi.mocked(api.get).mockResolvedValueOnce({ data: [mockConnector] })

      const result = await listConnectors()

      expect(api.get).toHaveBeenCalledWith('/connectors', { params: {} })
      expect(result).toEqual([mockConnector])
    })

    test('fetches connectors with type filter', async () => {
      vi.mocked(api.get).mockResolvedValueOnce({ data: [mockConnector] })

      const result = await listConnectors({ type: 's3' })

      expect(api.get).toHaveBeenCalledWith('/connectors', { params: { type: 's3' } })
      expect(result).toEqual([mockConnector])
    })
  })

  describe('getConnector', () => {
    test('fetches connector by guid', async () => {
      vi.mocked(api.get).mockResolvedValueOnce({ data: mockConnector })

      const result = await getConnector('con_01hgw2bbg00000000000000001')

      expect(api.get).toHaveBeenCalledWith('/connectors/con_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockConnector)
    })
  })

  describe('createConnector', () => {
    test('creates new connector', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({ data: mockConnector })

      const result = await createConnector({ name: 'New', type: 's3' })

      expect(api.post).toHaveBeenCalledWith('/connectors', { name: 'New', type: 's3' })
      expect(result).toEqual(mockConnector)
    })
  })

  describe('updateConnector', () => {
    test('updates connector', async () => {
      vi.mocked(api.put).mockResolvedValueOnce({ data: { ...mockConnector, name: 'Updated' } })

      const result = await updateConnector('con_01hgw2bbg00000000000000001', { name: 'Updated' })

      expect(api.put).toHaveBeenCalledWith('/connectors/con_01hgw2bbg00000000000000001', { name: 'Updated' })
      expect(result.name).toBe('Updated')
    })
  })

  describe('deleteConnector', () => {
    test('deletes connector', async () => {
      vi.mocked(api.delete).mockResolvedValueOnce({ data: undefined })

      await deleteConnector('con_01hgw2bbg00000000000000001')

      expect(api.delete).toHaveBeenCalledWith('/connectors/con_01hgw2bbg00000000000000001')
    })
  })

  describe('testConnector', () => {
    test('tests connector connection', async () => {
      const mockResult: ConnectorTestResponse = {
        success: true,
        message: 'Connection successful',
      }

      vi.mocked(api.post).mockResolvedValueOnce({ data: mockResult })

      const result = await testConnector('con_01hgw2bbg00000000000000001')

      expect(api.post).toHaveBeenCalledWith('/connectors/con_01hgw2bbg00000000000000001/test')
      expect(result).toEqual(mockResult)
    })
  })

  describe('getConnectorStats', () => {
    test('fetches connector statistics', async () => {
      const mockStats: ConnectorStatsResponse = {
        total_connectors: 5,
        active_connectors: 4,
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockStats })

      const result = await getConnectorStats()

      expect(api.get).toHaveBeenCalledWith('/connectors/stats')
      expect(result).toEqual(mockStats)
    })
  })
})
